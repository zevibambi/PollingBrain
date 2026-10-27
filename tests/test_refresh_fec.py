import importlib.util
import io
import unittest
import zipfile
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "scripts/refresh_fec.py"
spec = importlib.util.spec_from_file_location("refresh_fec", path)
fec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fec)

def archive(*rows):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as output:
        output.writestr("cn.txt", "\n".join("|".join(row) for row in rows))
    return buf.getvalue()

def row(cid="H6NJ01001", year="2026", office="H"):
    return [cid, "TEST, PERSON", "DEM", year, "NJ", office, "01", "C", "C",
            "C12345678", "private addr", "", "CITY", "NJ", "00000"]

class FECTests(unittest.TestCase):
    def test_only_2026_house_senate_and_no_addresses(self):
        records = fec.parse_records(archive(row(), row("S6NJ01002", office="S"),
                                            row("H8NJ01003", year="2028")))
        self.assertEqual(len(records), 2)
        self.assertEqual(sorted(records[0]), sorted(fec.FIELDS))
        self.assertNotIn("private addr", str(records))
    def test_duplicate_id_fails(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            fec.parse_records(archive(row(), row()))
    def test_bad_columns_fail(self):
        with self.assertRaisesRegex(ValueError, "expected 15"):
            fec.parse_records(archive(row()[:-1]))
    def test_filing_never_certifies_ballot(self):
        output = fec.build_snapshot(archive(row()))
        self.assertFalse(output["ballot_qualification_verified"])
        self.assertEqual(output["record_count"], 1)

if __name__ == "__main__":
    unittest.main()
