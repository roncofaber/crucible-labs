import unittest

import pandas as pd

from clabs.tables import blank_text_null, coalesce_columns, parse_quantity


class BlankTextNull(unittest.TestCase):
    def test_placeholders_become_none(self):
        for value in ("NaN", "nan", "None", "N/A", "", "  "):
            self.assertIsNone(blank_text_null(value), value)

    def test_real_values_unchanged(self):
        for value in ("NA", 0, False, "DMF"):
            self.assertIs(blank_text_null(value), value)


class ParseQuantity(unittest.TestCase):
    def test_matching_units(self):
        cases = [("5000 rpm", "rpm", 5000.0), ("1000 rpm/s", "rpm/s", 1000.0),
                 ("100C", "C", 100.0), ("50 ul", "ul", 50.0), ("30 s", "s", 30.0),
                 (30, "s", 30.0), ("50 UL", "ul", 50.0), ("-2.5 C", "C", -2.5)]
        for value, unit, expected in cases:
            self.assertEqual(parse_quantity(value, unit), expected, value)

    def test_no_conversion_or_guessing(self):
        for value, unit in (("30 min", "s"), ("fast", "rpm"), (None, "rpm"), (True, "s")):
            self.assertIsNone(parse_quantity(value, unit), value)


class CoalesceColumns(unittest.TestCase):
    def test_alias_fills_blank_and_is_dropped(self):
        df = pd.DataFrame({"a": [None, "x"], "b": ["y", None]}, index=["r1", "r2"])
        out, conflicts = coalesce_columns(df, "a", "b")
        self.assertEqual(list(out["a"]), ["y", "x"])
        self.assertNotIn("b", out.columns)
        self.assertEqual(conflicts, [])

    def test_conflict_reported_and_canonical_wins(self):
        df = pd.DataFrame({"a": ["x"], "b": ["y"]}, index=["r1"])
        out, conflicts = coalesce_columns(df, "a", "b")
        self.assertEqual(out.loc["r1", "a"], "x")
        self.assertEqual(conflicts, ["r1"])


if __name__ == "__main__":
    unittest.main()
