"""Integrity checks for the canonical 506-race nationwide catalog."""
import json
import unittest
from collections import Counter, defaultdict
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / "public/data/races_2026.json"

class TestNationalRaceCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(FILE.read_text(encoding="utf-8"))
        cls.races = cls.data["races"]

    def test_complete_2026_slate(self):
        self.assertEqual(len(self.races), 506)
        self.assertEqual(Counter(r["chamber"] for r in self.races),
                         {"house": 435, "senate": 35, "governor": 36})
        self.assertEqual(len(set(r["state"] for r in self.races)), 50)

    def test_unique_id_and_source(self):
        self.assertEqual(len({r["id"] for r in self.races}), 506)
        valid_sources = {s["id"] for s in self.data["source_refs"]}
        for r in self.races:
            self.assertTrue(r["id"].endswith("-2026"), r["id"])
            self.assertIn(r["contest_source_ref"], valid_sources)
            self.assertEqual(r["election_date"], "2026-11-03")
            self.assertIsNone(r["forecast"])
            self.assertFalse(r["forecast_verified"])
            self.assertFalse(r["ballot_candidates_verified"])

    def test_house_contiguous_numbering(self):
        by_state = defaultdict(list)
        for r in self.races:
            if r["chamber"] == "house":
                by_state[r["state"]].append(r["district"])
        self.assertEqual(sum(len(v) for v in by_state.values()), 435)
        for state, districts in by_state.items():
            if len(districts) == 1:
                self.assertEqual(districts, ["AL"], state)
            else:
                self.assertEqual(sorted(districts),
                    [str(i).zfill(2) for i in range(1, len(districts) + 1)], state)

    def test_two_senate_specials_only(self):
        special = {r["state"] for r in self.races if r["chamber"] == "senate" and r["special_election"]}
        self.assertEqual(special, {"FL", "OH"})
        self.assertEqual(len(self.races), self.data["summary"]["total_races"])

    def test_all_candidate_names_explicitly_unverified(self):
        for race in self.races:
            for c in race["candidates"]:
                self.assertEqual(c["verification"], "unverified_draft")

if __name__ == "__main__":
    unittest.main()
