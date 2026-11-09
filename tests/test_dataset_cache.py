import tempfile
import unittest
from pathlib import Path

import requests

from tests.helpers import make_dataset
from tests.test_export import FakeClient


class CachedFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name)
        self.dataset = make_dataset("scan", "m", mfid="d")

    def tearDown(self):
        self.tmp.cleanup()

    def seed(self, name, data=b"abc"):
        path = self.cache / "d" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_prefetch_ignores_file_no_longer_in_dataset(self):
        self.seed("old.h5")
        client = FakeClient({"d": {"old_corrected.h5": b"new"}})
        self.dataset.prefetch(client, str(self.cache))
        self.assertEqual([Path(f).name for f in self.dataset._files], ["old_corrected.h5"])
        self.assertEqual(client.datasets.downloads, ["d"])

    def test_prefetch_does_not_download_valid_cache(self):
        self.seed("f.h5")
        client = FakeClient({"d": {"f.h5": b"abc"}})
        self.dataset.prefetch(client, str(self.cache))
        self.assertEqual(client.datasets.downloads, [])
        self.assertIsInstance(self.dataset._files[0], str)

    def test_prefetch_replaces_truncated_file(self):
        self.seed("f.h5", b"a")
        client = FakeClient({"d": {"f.h5": b"abc"}})
        self.dataset.prefetch(client, str(self.cache))
        self.assertEqual(Path(self.dataset._files[0]).read_bytes(), b"abc")

    def test_load_without_prefetch_uses_dataset_folder_and_ignores_stale_file(self):
        self.seed("old.h5")
        client = FakeClient({"d": {"new.h5": b"new"}})
        seen = []
        type(self.dataset).register_loader("m", lambda ds, files, **kw: seen.extend(files))
        self.dataset.load(client, str(self.cache))
        self.assertEqual(seen, [str(self.cache / "d" / "new.h5")])
        self.assertFalse((self.cache / "d" / "d").exists())

    def test_unobtainable_file_warns_instead_of_raising(self):
        client = FakeClient({"d": {"f.h5": b"abc"}}, corrupting=["d"])
        with self.assertLogs("clabs.dataset", level="WARNING"):
            self.dataset.prefetch(client, str(self.cache))
        self.assertEqual(self.dataset._files, [])

    def test_listing_failure_falls_back_to_local_files(self):
        self.seed("f.h5")
        client = FakeClient({})
        def down(mfid):
            raise requests.exceptions.ConnectionError("offline")
        client.datasets.list_files = down
        with self.assertLogs("clabs.dataset", level="WARNING"):
            self.dataset.prefetch(client, str(self.cache))
        self.assertEqual([Path(f).name for f in self.dataset._files], ["f.h5"])


if __name__ == "__main__":
    unittest.main()
