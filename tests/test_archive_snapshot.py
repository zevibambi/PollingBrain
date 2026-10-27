import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('ledger', Path(__file__).resolve().parents[1] / 'scripts/archive_snapshot.py')
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)


def snapshot(name='TEST, PERSON'):
    records = [{'fec_id': 'H6NJ01001', 'name': name}]
    return {'dataset': 'fec_candidate_filings_2026', 'records': records,
            'record_count': 1, 'records_sha256': hashlib.sha256(ledger.canonical(records)).hexdigest(),
            'retrieved_at': '2026-10-27T12:00:00+00:00', 'ballot_qualification_verified': False,
            'source': {'url': 'https://www.fec.gov/files/bulk-downloads/2026/cn26.zip'}}


class ArchiveTests(unittest.TestCase):
    def test_unchanged_checks_do_not_duplicate_history(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger.archive(snapshot(), directory, 'first')
            result = ledger.archive(snapshot(), directory, 'second')
            item = result['datasets']['fec_candidate_filings_2026']
            self.assertEqual(item['last_successful_check_at'], 'second')
            self.assertEqual(len(item['versions']), 1)

    def test_changes_preserve_previous_records(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger.archive(snapshot(), directory)
            result = ledger.archive(snapshot('CHANGED, PERSON'), directory)
            versions = result['datasets']['fec_candidate_filings_2026']['versions']
            self.assertEqual(len(versions), 2)
            old = json.loads((Path(directory) / versions[0]['path']).read_text())
            self.assertEqual(old['records'][0]['name'], 'TEST, PERSON')

    def test_corruption_and_false_certification_do_not_write(self):
        for field, value in [('record_count', 2), ('records_sha256', 'bad'), ('ballot_qualification_verified', True)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                data = snapshot()
                data[field] = value
                with self.assertRaises(ValueError):
                    ledger.archive(data, directory)
                self.assertEqual(list(Path(directory).iterdir()), [])
