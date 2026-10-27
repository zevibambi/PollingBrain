import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "scripts/import_40_elections.py"
spec = importlib.util.spec_from_file_location("import_40_elections", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class HistoricalImportTests(unittest.TestCase):
    def test_forty_election_years(self):
        self.assertEqual(len(mod.YEARS), 40)
        self.assertEqual(mod.YEARS[0], 1946)
        self.assertEqual(mod.YEARS[-1], 2024)
    def test_one_observed_record_each_year(self):
        raw = ("election_year,party,vote_share\n" +
               "".join(f"{year},DEM,47.5\n" for year in mod.YEARS)).encode()
        headers, rows, counts = mod.parse_csv(raw)
        self.assertEqual(len(rows), 40)
        self.assertEqual(set(counts.values()), {1})
    def test_missing_year_rejected(self):
        raw = ("election_year,party,vote_share\n" +
               "".join(f"{year},DEM,47.5\n" for year in mod.YEARS[:-1])).encode()
        with self.assertRaisesRegex(ValueError, "missing election years"):
            mod.parse_csv(raw)
    def test_no_made_up_rows(self):
        raw = ("election_year,party,vote_share\n" +
               "".join(f"{year},DEM,47.5\n" for year in mod.YEARS)).encode()
        result = mod.create(raw)
        self.assertEqual(result["covered_year_count"], 40)
        self.assertTrue(all("values" in x for x in result["source_records"]))
    def test_malformed_source_rejected(self):
        raw = ("election_year,party,vote_share\n1946,DEM\n").encode()
        with self.assertRaises(ValueError):
            mod.parse_csv(raw)

if __name__ == "__main__":
    unittest.main()
