import hashlib
import os
import stat
import tempfile
import unittest
from pathlib import Path

from clabs.export import (DatasetFileError, MeasurementExport, copy_file_writer, copy_folder_writer,
                          ensure_dataset_files, export_samples, folder_is_current, sha256_file)
from tests.helpers import make_dataset


def sha(data):
    return hashlib.sha256(data).hexdigest()


class FakeDatasets:
    def __init__(self, content, failing=(), corrupting=(), no_hash=()):
        self.content = content
        self.failing = set(failing)
        self.corrupting = set(corrupting)
        self.no_hash = set(no_hash)
        self.downloads = []

    def list_files(self, mfid):
        return [{"filename": name, "mfid": name, "size": len(data),
                 "sha256_hash": None if mfid in self.no_hash else sha(data)}
                for name, data in self.content[mfid].items()]

    def download(self, mfid, output_dir, no_record, overwrite_existing, include):
        self.downloads.append(mfid)
        if mfid in self.failing:
            raise OSError("network")
        dest = Path(output_dir) / mfid
        dest.mkdir(parents=True, exist_ok=True)
        for name, data in self.content[mfid].items():
            if name in include:
                (dest / name).parent.mkdir(parents=True, exist_ok=True)
                (dest / name).write_bytes(b"x" if mfid in self.corrupting else data)
        return []


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.datasets = FakeDatasets(*args, **kwargs)


class ExportBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cache = self.root / "cache"
        self.out = self.root / "out"

    def tearDown(self):
        self.tmp.cleanup()


class EnsureFiles(ExportBase):
    def seed(self, mfid, name, data):
        path = self.cache / mfid / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def test_valid_cache_not_downloaded(self):
        client = FakeClient({"d": {"f.h5": b"abc"}})
        self.seed("d", "f.h5", b"abc")
        files = ensure_dataset_files(client, "d", self.cache)
        self.assertEqual(client.datasets.downloads, [])
        self.assertEqual(files[0].name, "f.h5")
        self.assertEqual(files[0].sha256, sha(b"abc"))

    def test_truncated_cache_redownloaded(self):
        client = FakeClient({"d": {"f.h5": b"abc"}})
        self.seed("d", "f.h5", b"a")
        files = ensure_dataset_files(client, "d", self.cache)
        self.assertEqual(client.datasets.downloads, ["d"])
        self.assertEqual(files[0].path.read_bytes(), b"abc")

    def test_wrong_hash_redownloaded(self):
        client = FakeClient({"d": {"f.h5": b"abc"}})
        self.seed("d", "f.h5", b"xyz")
        ensure_dataset_files(client, "d", self.cache)
        self.assertEqual(client.datasets.downloads, ["d"])

    def test_missing_hash_uses_size_only(self):
        client = FakeClient({"d": {"f.h5": b"abc"}}, no_hash=["d"])
        self.seed("d", "f.h5", b"xyz")
        ensure_dataset_files(client, "d", self.cache)
        self.assertEqual(client.datasets.downloads, [])

    def test_download_that_stays_bad_raises(self):
        client = FakeClient({"d": {"f.h5": b"abc"}}, corrupting=["d"])
        with self.assertRaises(DatasetFileError):
            ensure_dataset_files(client, "d", self.cache)

    def test_storage_path_style_name_is_reduced(self):
        client = FakeClient({"d": {"api-uploads/f.png": b"abc"}})
        self.assertEqual(client.datasets.list_files("d")[0]["filename"], "api-uploads/f.png")
        self.seed("d", "f.png", b"abc")
        files = ensure_dataset_files(client, "d", self.cache)
        self.assertEqual(files[0].name, "f.png")


    def test_absolute_name_is_reduced_to_basename(self):
        client = FakeClient({"d": {"/mnt/gcs/api-uploads/f.h5": b"abc"}})
        self.seed("d", "f.h5", b"abc")
        files = ensure_dataset_files(client, "d", self.cache)
        self.assertEqual(client.datasets.downloads, [])
        self.assertEqual(files[0].name, "f.h5")
        self.assertEqual(files[0].path, self.cache / "d" / "f.h5")


    def shared_object_client(self):
        client = FakeClient({"d": {"api-uploads/f.png": b"current", "f.png": b"current"}})
        stale = {"filename": "api-uploads/f.png", "mfid": "1", "size": 3, "sha256_hash": sha(b"old"),
                 "storage_path": "bucket/d/f.png"}
        real = {"filename": "f.png", "mfid": "2", "size": 7, "sha256_hash": sha(b"current"),
                "storage_path": "bucket/d/f.png"}
        client.datasets.list_files = lambda mfid: [stale, real]
        return client

    def test_stale_record_of_shared_object_is_dropped(self):
        client = self.shared_object_client()
        files = ensure_dataset_files(client, "d", self.cache)
        self.assertEqual([f.name for f in files], ["f.png"])
        self.assertEqual(files[0].sha256, sha(b"current"))

    def test_valid_shared_object_needs_no_download(self):
        client = self.shared_object_client()
        self.seed("d", "f.png", b"current")
        ensure_dataset_files(client, "d", self.cache)
        self.assertEqual(client.datasets.downloads, [])

    def test_shared_object_with_no_matching_record_raises(self):
        client = self.shared_object_client()
        client.datasets.content["d"] = {"api-uploads/f.png": b"neither", "f.png": b"neither"}
        with self.assertRaises(DatasetFileError):
            ensure_dataset_files(client, "d", self.cache)


def well_export(selection, calls=None):
    def writer(dataset, files, targets):
        if calls is not None:
            calls.append((dataset.unique_id, sorted(targets)))
        return copy_file_writer(dataset, files, targets)
    return MeasurementExport(
        name="well", selection=selection, writer=writer,
        filename=lambda film, files: f"{film}_well.png",
        describe=lambda path: {"path": str(path)},
    )


class ExportSamples(ExportBase):
    def test_shared_dataset_downloaded_once_for_many_films(self):
        ds = make_dataset("shared", "m", mfid="d")
        client = FakeClient({"d": {"f.png": b"abc"}})
        calls = []
        selection = {f"TF{i}": ds for i in range(16)}
        result = export_samples(client, self.out, self.cache, [well_export(selection, calls)])
        self.assertEqual(client.datasets.downloads, ["d"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0][1]), 16)
        self.assertEqual(len(result.records), 16)
        self.assertEqual((self.out / "TF3" / "TF3_well.png").read_bytes(), b"abc")

    def test_failure_recorded_and_others_continue(self):
        good, bad = make_dataset("good", "m", mfid="g"), make_dataset("bad", "m", mfid="b")
        client = FakeClient({"g": {"f.png": b"abc"}, "b": {"f.png": b"xyz"}}, failing=["b"])
        result = export_samples(client, self.out, self.cache,
                                [well_export({"TF1": good, "TF2": bad})])
        self.assertTrue((self.out / "TF1" / "TF1_well.png").exists())
        self.assertFalse((self.out / "TF2").exists())
        self.assertEqual(list(result.records), [("TF1", "well")])
        self.assertEqual(result.failures[0]["dataset_mfid"], "b")
        self.assertEqual(result.failures[0]["films"], ["TF2"])

    def test_writer_error_recorded_and_others_continue(self):
        one, two = make_dataset("one", "m", mfid="o"), make_dataset("two", "m", mfid="t")
        client = FakeClient({"o": {"a.png": b"1", "b.png": b"2"}, "t": {"f.png": b"3"}})
        result = export_samples(client, self.out, self.cache,
                                [well_export({"TF1": one, "TF2": two})])
        self.assertEqual(list(result.records), [("TF2", "well")])
        self.assertEqual(result.failures[0]["films"], ["TF1"])

    def test_film_without_writer_output_is_a_failure(self):
        ds = make_dataset("d", "m", mfid="d")
        client = FakeClient({"d": {"f.png": b"abc"}})
        export = MeasurementExport(
            name="x", selection={"TF1": ds}, writer=lambda d, f, t: {},
            filename=lambda film, files: "x.png", describe=lambda p: {})
        result = export_samples(client, self.out, self.cache, [export])
        self.assertEqual(result.failures[0]["films"], ["TF1"])

    def test_no_folder_for_film_without_selection(self):
        client = FakeClient({})
        result = export_samples(client, self.out, self.cache, [well_export({})])
        self.assertEqual(result.records, {})
        self.assertFalse((self.out / "TF1").exists())

    def test_resume_skips_existing_output(self):
        ds = make_dataset("d", "m", mfid="d")
        client = FakeClient({"d": {"f.png": b"abc"}})
        export_samples(client, self.out, self.cache, [well_export({"TF1": ds})])
        calls = []
        result = export_samples(client, self.out, self.cache, [well_export({"TF1": ds}, calls)])
        self.assertEqual(calls, [])
        self.assertIn(("TF1", "well"), result.records)
        export_samples(client, self.out, self.cache, [well_export({"TF1": ds}, calls)], overwrite=True)
        self.assertEqual(len(calls), 1)

    def test_dataset_with_no_files_is_a_failure_not_a_crash(self):
        empty, good = make_dataset("e", "m", mfid="e"), make_dataset("g", "m", mfid="g")
        client = FakeClient({"e": {}, "g": {"f.png": b"abc"}})
        export = well_export({"TF1": empty, "TF2": good})
        export.filename = lambda film, files: f"{film}{Path(files[0].name).suffix}"
        result = export_samples(client, self.out, self.cache, [export])
        self.assertEqual(result.failures[0]["films"], ["TF1"])
        self.assertIn(("TF2", "well"), result.records)

    def test_unreadable_existing_output_is_rewritten(self):
        ds = make_dataset("d", "m", mfid="d")
        client = FakeClient({"d": {"f.png": b"abc"}})
        path = self.out / "TF1" / "TF1_well.png"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"corrupt")
        export = well_export({"TF1": ds})
        def describe(p):
            if p.read_bytes() == b"corrupt":
                raise OSError("bad file")
            return {"path": str(p)}
        export.describe = describe
        result = export_samples(client, self.out, self.cache, [export])
        self.assertEqual(result.failures, [])
        self.assertEqual(path.read_bytes(), b"abc")

    def test_output_from_other_source_is_rewritten(self):
        ds = make_dataset("d", "m", mfid="d")
        client = FakeClient({"d": {"f.png": b"abc"}})
        path = self.out / "TF1" / "TF1_well.png"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"old")
        export = well_export({"TF1": ds})
        export.is_current = lambda p, dataset, files: p.read_bytes() == b"abc"
        export_samples(client, self.out, self.cache, [export])
        self.assertEqual(path.read_bytes(), b"abc")

    def test_outputs_are_readable_per_umask(self):
        ds = make_dataset("d", "m", mfid="d")
        client = FakeClient({"d": {"f.png": b"abc"}})
        old = os.umask(0o022)
        try:
            export_samples(client, self.out, self.cache, [well_export({"TF1": ds})])
        finally:
            os.umask(old)
        self.assertEqual(stat.S_IMODE((self.out / "TF1" / "TF1_well.png").stat().st_mode), 0o644)

    def test_copy_writer_byte_identical(self):
        ds = make_dataset("d", "m", mfid="d")
        data = bytes(range(256)) * 50
        client = FakeClient({"d": {"f.png": data}})
        export_samples(client, self.out, self.cache, [well_export({"TF1": ds})])
        path = self.out / "TF1" / "TF1_well.png"
        self.assertEqual(sha256_file(path), sha(data))


def run_export(selection):
    return MeasurementExport(
        name="rga", selection=selection, writer=copy_folder_writer,
        filename=lambda film, files, dataset: f"rga/{dataset.name}",
        describe=lambda path: {"path": str(path)}, is_current=folder_is_current, multiple=True,
    )


class MultipleDatasets(ExportBase):
    def setUp(self):
        super().setUp()
        self.one = make_dataset("RUN1", "m", mfid="r1")
        self.two = make_dataset("RUN2", "m", mfid="r2")
        self.client = FakeClient({"r1": {"a.txt": b"1", "b.txt": b"22"}, "r2": {"a.txt": b"3", "b.txt": b"44"}})

    def test_each_dataset_gets_its_own_folder_with_all_files(self):
        result = export_samples(self.client, self.out, self.cache,
                                [run_export({"TF1": [self.one, self.two]})])
        self.assertEqual((self.out / "TF1" / "rga" / "RUN1" / "b.txt").read_bytes(), b"22")
        self.assertEqual((self.out / "TF1" / "rga" / "RUN2" / "a.txt").read_bytes(), b"3")
        self.assertEqual(len(result.records[("TF1", "rga")]), 2)

    def test_failed_dataset_leaves_others_and_no_partial_folder(self):
        self.client.datasets.failing = {"r2"}
        self.client.datasets.content["r2"] = {"a.txt": b"3"}
        result = export_samples(self.client, self.out, self.cache,
                                [run_export({"TF1": [self.one, self.two]})])
        self.assertTrue((self.out / "TF1" / "rga" / "RUN1").is_dir())
        self.assertFalse((self.out / "TF1" / "rga" / "RUN2").exists())
        self.assertEqual(len(result.records[("TF1", "rga")]), 1)
        self.assertEqual(result.failures[0]["dataset_mfid"], "r2")

    def test_resume_keeps_complete_folder_and_rewrites_incomplete(self):
        export_samples(self.client, self.out, self.cache, [run_export({"TF1": [self.one]})])
        folder = self.out / "TF1" / "rga" / "RUN1"
        (folder / "b.txt").unlink()
        export_samples(self.client, self.out, self.cache, [run_export({"TF1": [self.one]})])
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ["a.txt", "b.txt"])

    def test_folder_with_extra_or_changed_file_is_not_current(self):
        export_samples(self.client, self.out, self.cache, [run_export({"TF1": [self.one]})])
        folder = self.out / "TF1" / "rga" / "RUN1"
        files = ensure_dataset_files(self.client, "r1", self.cache)
        self.assertTrue(folder_is_current(folder, self.one, files))
        (folder / "a.txt").write_bytes(b"9")
        self.assertFalse(folder_is_current(folder, self.one, files))

    def test_folder_files_are_readable_per_umask(self):
        old = os.umask(0o022)
        try:
            export_samples(self.client, self.out, self.cache, [run_export({"TF1": [self.one]})])
        finally:
            os.umask(old)
        folder = self.out / "TF1" / "rga" / "RUN1"
        self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE((folder / "a.txt").stat().st_mode), 0o644)


if __name__ == "__main__":
    unittest.main()
