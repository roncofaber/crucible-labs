import tempfile
import unittest
from pathlib import Path
from unittest import mock

import h5py
import numpy as np

from clabs.measurements.uvvis.split import split_uvvis_file

ROOT = "measurement/pollux_oospec_multipos_line_scan"
N = 8


def rng_array(seed, shape):
    return np.random.default_rng(seed).random(shape)


def write_new(path, films, blank_shape=(3, N)):
    """films: list of (position index, key suffix, uuid)."""
    arrays = {}
    with h5py.File(path, "w") as f:
        g = f.create_group(ROOT)
        g["wavelengths"] = np.linspace(300, 900, N)
        g.create_group("settings").attrs.update({"scan_velocity": 100.0, "profile": "False"})
        positions = g.create_group("positions")
        for seed, (idx, suffix, uuid) in enumerate(films):
            p = positions.create_group(f"pos_{idx:03d}_{suffix}")
            arrays[suffix] = dict(raw=rng_array(seed, (3, N)), blank=rng_array(seed + 100, blank_shape),
                                  dark=rng_array(seed + 200, blank_shape))
            p["raw_intensities"] = arrays[suffix]["raw"]
            p["blank_intensities"] = arrays[suffix]["blank"]
            p["dark_intensities"] = arrays[suffix]["dark"]
            p.attrs.update(integration_time=0.0025, sample_name=suffix, tray_name="TRAY00001",
                           x_center=float(idx), y_center=-1.0, x_positions=np.full(3, float(idx)),
                           y_positions=np.arange(3.0))
            if uuid:
                p.attrs["sample_uuid"] = uuid
    return arrays


def write_old(path):
    arrays = {}
    with h5py.File(path, "w") as f:
        g = f.create_group(ROOT)
        g["wavelengths"] = np.linspace(300, 900, N)
        g["spec_integration_time"] = 0.0025
        g.create_group("settings").attrs.update({"scan_velocity": 10.0})
        positions = g.create_group("positions")
        dark = rng_array(1, (3, N))
        blank = rng_array(2, (3, N))
        for key, data in (("pos_000_DarkReference", dark), ("pos_001_BlankReference", blank)):
            p = positions.create_group(key)
            p["spectral_data"] = data
        for idx, (key, name) in enumerate((("pos_002_TF00089", b"TF00089"), ("pos_003_TF00090", b"TF00090")), 3):
            p = positions.create_group(key)
            arrays[key] = rng_array(idx, (3, N))
            p["spectral_data"] = arrays[key]
            p["sample_name"] = name
            p["x_center"] = float(idx)
            p["y_center"] = -1.0
            p["y_positions"] = np.arange(3.0)
    return arrays, dark, blank


class SplitBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.source = self.dir / "source.h5"

    def tearDown(self):
        self.tmp.cleanup()


class NewFormat(SplitBase):
    def setUp(self):
        super().setUp()
        self.arrays = write_new(self.source, [(0, "TF000001", "id1"), (1, "TF000002", "id2")])
        self.ids = {"TF000001": "id1", "TF000002": "id2"}

    def test_new_format_arrays_identical(self):
        out = self.dir / "a.h5"
        result = split_uvvis_file(self.source, {"TF000002": out}, self.ids)
        with h5py.File(out) as f:
            self.assertTrue(np.array_equal(f["raw_intensities"][()], self.arrays["TF000002"]["raw"]))
            self.assertTrue(np.array_equal(f["blank_intensities"][()], self.arrays["TF000002"]["blank"]))
            self.assertTrue(np.array_equal(f["dark_intensities"][()], self.arrays["TF000002"]["dark"]))
            self.assertTrue(np.array_equal(f["wavelengths"][()], np.linspace(300, 900, N)))
            self.assertTrue(np.array_equal(f["x_positions"][()], np.full(3, 1.0)))
            self.assertTrue(np.array_equal(f["y_positions"][()], np.arange(3.0)))
            self.assertEqual(f.attrs["sample_name"], "TF000002")
            self.assertEqual(f.attrs["sample_mfid"], "id2")
            self.assertEqual(f.attrs["tray_well"], "A2")
            self.assertEqual(f.attrs["integration_time"], 0.0025)
        self.assertEqual(result.written["TF000002"]["n_spots"], 3)
        self.assertEqual(result.written["TF000002"]["tray_well"], "A2")

    def test_root_level_wavelengths_and_settings(self):
        with h5py.File(self.source, "r+") as f:
            f.move(f"{ROOT}/wavelengths", "wavelengths")
            f.move(f"{ROOT}/settings", "settings")
        out = self.dir / "a.h5"
        split_uvvis_file(self.source, {"TF000001": out}, self.ids)
        with h5py.File(out) as f:
            self.assertTrue(np.array_equal(f["wavelengths"][()], np.linspace(300, 900, N)))
            self.assertEqual(f["settings"].attrs["scan_velocity"], 100.0)

    def test_duplicate_positions_for_one_film_are_not_written(self):
        write_new(self.source, [(0, "TF000001", "id1"), (1, "TF00001", "id1")])
        out = self.dir / "a.h5"
        result = split_uvvis_file(self.source, {"TF000001": out}, self.ids)
        self.assertFalse(out.exists())
        self.assertEqual(sorted(result.unmatched), ["pos_000_TF000001", "pos_001_TF00001"])
        self.assertEqual(result.missing, ["TF000001"])

    def test_reference_shape_kept_as_stored(self):
        arrays = write_new(self.source, [(0, "TF000001", "id1")], blank_shape=(N,))
        out = self.dir / "a.h5"
        split_uvvis_file(self.source, {"TF000001": out}, {"TF000001": "id1"})
        with h5py.File(out) as f:
            self.assertEqual(f["blank_intensities"].shape, (N,))
            self.assertTrue(np.array_equal(f["dark_intensities"][()], arrays["TF000001"]["dark"]))

    def test_other_films_absent(self):
        out = self.dir / "a.h5"
        split_uvvis_file(self.source, {"TF000001": out}, self.ids)
        self.assertEqual([p.name for p in self.dir.glob("a*")], ["a.h5"])
        with h5py.File(out) as f:
            self.assertFalse(np.array_equal(f["raw_intensities"][()], self.arrays["TF000002"]["raw"]))
            self.assertNotIn("positions", f)

    def test_uuid_conflicting_with_key_is_skipped(self):
        write_new(self.source, [(0, "TF000001", "id2")])
        a, b = self.dir / "a.h5", self.dir / "b.h5"
        result = split_uvvis_file(self.source, {"TF000001": a, "TF000002": b}, self.ids)
        self.assertFalse(a.exists())
        self.assertFalse(b.exists())
        self.assertEqual(result.unmatched, ["pos_000_TF000001"])
        self.assertEqual(sorted(result.missing), ["TF000001", "TF000002"])

    def test_position_not_linked_is_unmatched(self):
        result = split_uvvis_file(self.source, {"TF000001": self.dir / "a.h5"}, {"TF000001": "id1"})
        self.assertEqual(result.unmatched, ["pos_001_TF000002"])

    def test_target_absent_from_file_is_missing(self):
        out = self.dir / "z.h5"
        result = split_uvvis_file(self.source, {"TF000099": out}, {**self.ids, "TF000099": "id9"})
        self.assertEqual(result.missing, ["TF000099"])
        self.assertFalse(out.exists())

    def test_extra_attrs_and_settings_carried(self):
        out = self.dir / "a.h5"
        split_uvvis_file(self.source, {"TF000001": out}, self.ids, attrs={"source_dataset_mfid": "ds1"})
        with h5py.File(out) as f:
            self.assertEqual(f.attrs["source_dataset_mfid"], "ds1")
            self.assertEqual(f["settings"].attrs["scan_velocity"], 100.0)

    def test_interrupted_write_leaves_no_output(self):
        out = self.dir / "out" / "a.h5"
        out.parent.mkdir()
        with mock.patch.object(h5py.Group, "create_dataset", side_effect=OSError("disk")):
            with self.assertRaises(OSError):
                split_uvvis_file(self.source, {"TF000001": out}, self.ids)
        self.assertEqual(list(out.parent.iterdir()), [])

    def test_existing_output_not_replaced_unless_overwrite(self):
        out = self.dir / "a.h5"
        out.write_bytes(b"keep")
        split_uvvis_file(self.source, {"TF000001": out}, self.ids)
        self.assertEqual(out.read_bytes(), b"keep")
        split_uvvis_file(self.source, {"TF000001": out}, self.ids, overwrite=True)
        self.assertTrue(h5py.is_hdf5(out))


class OldFormat(SplitBase):
    def test_old_format_arrays_identical(self):
        arrays, dark, blank = write_old(self.source)
        out = self.dir / "a.h5"
        result = split_uvvis_file(self.source, {"TF000089": out}, {"TF000089": "id89", "TF000090": "id90"})
        with h5py.File(out) as f:
            self.assertTrue(np.array_equal(f["raw_intensities"][()], arrays["pos_002_TF00089"]))
            self.assertTrue(np.array_equal(f["dark_intensities"][()], dark))
            self.assertTrue(np.array_equal(f["blank_intensities"][()], blank))
            self.assertTrue(np.array_equal(f["x_positions"][()], np.full(3, 3.0)))
            self.assertEqual(f.attrs["sample_name"], "TF000089")
            self.assertEqual(f.attrs["sample_mfid"], "id89")
            self.assertEqual(f.attrs["tray_well"], "A1")
            self.assertEqual(f.attrs["integration_time"], 0.0025)
        self.assertEqual(result.unmatched, [])

    def test_stored_name_conflicting_with_key_is_skipped(self):
        write_old(self.source)
        with h5py.File(self.source, "r+") as f:
            group = f[f"{ROOT}/positions/pos_002_TF00089"]
            del group["sample_name"]
            group["sample_name"] = b"TF00090"
        out = self.dir / "a.h5"
        result = split_uvvis_file(self.source, {"TF000089": out}, {"TF000089": "a", "TF000090": "b"})
        self.assertFalse(out.exists())
        self.assertEqual(result.unmatched, ["pos_002_TF00089"])

    def test_references_are_not_treated_as_films(self):
        write_old(self.source)
        result = split_uvvis_file(self.source, {}, {"TF000089": "a", "TF000090": "b"})
        self.assertEqual(result.unmatched, [])


if __name__ == "__main__":
    unittest.main()
