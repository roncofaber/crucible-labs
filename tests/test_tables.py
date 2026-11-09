import unittest

from clabs import SampleCollection, build_table
from clabs import FieldSpec as F
from tests.helpers import make_dataset, make_sample


def film_with_stocks(name, solvents):
    film = make_sample(name)
    for idx, solvent in enumerate(solvents):
        stock = make_sample(f"SS{name}{idx}", sample_type="stock solution")
        stock.add_dataset(make_dataset(f"ss{name}{idx}", "Stock Solution synthesis",
                                       sm={"solvent": solvent, "operator": "X"}))
        film.add_parent(stock)
    return film


class ExistingBehavior(unittest.TestCase):
    def table(self, *films, **kwargs):
        return build_table(SampleCollection(samples=list(films)), include_ancestors=True, **kwargs)

    def test_two_ancestor_hits_get_numeric_suffix(self):
        df = self.table(film_with_stocks("TF1", ["DMF", "DMSO"]),
                        fields={"Stock Solution synthesis": ["solvent"]})
        self.assertEqual(df.loc["TF1", "solvent_1"], "DMF")
        self.assertEqual(df.loc["TF1", "solvent_2"], "DMSO")

    def test_one_ancestor_hit_has_no_suffix(self):
        df = self.table(film_with_stocks("TF1", ["DMF"]),
                        fields={"Stock Solution synthesis": ["solvent"]})
        self.assertEqual(df.loc["TF1", "solvent"], "DMF")

    def test_same_leaf_key_silently_overwrites(self):
        film = make_sample("TF1", sm={"x": 1})
        film.add_dataset(make_dataset("d", "m", sm={"x": 2}))
        df = self.table(film, fields={"m": F("x"), "s": F("x", kind="sample")})
        self.assertEqual(df.loc["TF1", "x"], 1)

    def test_attribute_kind_reads_sample_attribute(self):
        df = self.table(make_sample("TF1"), fields={"a": F("sample_type", kind="attribute")})
        self.assertEqual(df.loc["TF1", "sample_type"], "thin film")


class NewOptions(unittest.TestCase):
    def setUp(self):
        self.film = make_sample("TF1")
        self.stock = make_dataset("ss", "Stock Solution synthesis", session="s1",
                                  sm={"solvent": "DMF", "target_concentration_(m)": " 0.2 "})
        self.films = SampleCollection(samples=[self.film])

    def test_source_reads_metadata_of_selected_resource(self):
        df = build_table(self.films, fields={"a": F("solvent", source=lambda s: self.stock)})
        self.assertEqual(df.loc["TF1", "solvent"], "DMF")

    def test_source_returning_none_still_emits_blank_column(self):
        df = build_table(self.films, fields={"a": F("solvent", source=lambda s: None)})
        self.assertIn("solvent", df.columns)
        self.assertTrue(df["solvent"].isna().all())

    def test_source_with_attribute_kind_reads_dataset_attrs(self):
        df = build_table(self.films, fields={
            "a": F("session", "unique_id", kind="attribute", source=lambda s: self.stock)})
        self.assertEqual(df.loc["TF1", "session"], "s1")
        self.assertEqual(df.loc["TF1", "unique_id"], self.stock.unique_id)

    def test_prefix_rename_and_transform_apply(self):
        key = "target_concentration_(m)"
        df = build_table(self.films, fields={
            "a": F(key, prefix="ps_", rename={key: "target_concentration_m"},
                   transform=str.strip, source=lambda s: self.stock)})
        self.assertEqual(df.loc["TF1", "ps_target_concentration_m"], "0.2")

    def test_prefix_applies_without_source(self):
        self.film.add_dataset(self.stock)
        df = build_table(self.films, fields={"Stock Solution synthesis": F("solvent", prefix="ss_")})
        self.assertEqual(df.loc["TF1", "ss_solvent"], "DMF")

    def test_strict_raises_on_collision_naming_both_labels(self):
        with self.assertRaisesRegex(ValueError, "one.*two|two.*one"):
            build_table(self.films, strict=True, fields={
                "one": F("solvent", source=lambda s: self.stock),
                "two": F("solvent", source=lambda s: self.stock)})

    def test_source_with_type_or_sample_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            F("x", source=lambda s: None, type="m")
        with self.assertRaises(ValueError):
            F("x", source=lambda s: None, sample_type="thin film")

    def test_collection_to_dataframe_passes_strict(self):
        with self.assertRaises(ValueError):
            self.films.to_dataframe(strict=True, fields={
                "one": F("solvent", source=lambda s: self.stock),
                "two": F("solvent", source=lambda s: self.stock)})


if __name__ == "__main__":
    unittest.main()
