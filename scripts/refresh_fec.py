#!/usr/bin/env python3
"""Fetch official FEC 2026 filings, without implying ballot qualification."""
import csv
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SOURCE = "https://www.fec.gov/files/bulk-downloads/2026/cn26.zip"
DOCS = "https://www.fec.gov/campaign-finance-data/candidate-master-file-description/"
OUTPUT = Path(__file__).resolve().parents[1] / "public/data/fec_candidate_filings_2026.json"
FIELDS = ("fec_id", "name", "party", "election_year", "state", "office", "district", "incumbency", "fec_status")
MAX_BYTES = 20_000_000

def parse_records(data: bytes):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = [name for name in archive.namelist()
                   if name.lower().endswith((".txt", ".csv")) and not name.startswith("__")]
        if len(members) != 1:
            raise ValueError(f"Expected one tabular FEC file, got {members!r}")
        with archive.open(members[0]) as stream:
            reader = csv.reader(io.TextIOWrapper(stream, encoding="utf-8-sig",
                                errors="replace", newline=""), delimiter="|")
            seen, rows = set(), []
            for line_num, line in enumerate(reader, start=1):
                if len(line) != 15:
                    raise ValueError(f"FEC record {line_num} has {len(line)} fields; expected 15")
                if line[3] != "2026" or line[5] not in ("H", "S"):
                    continue
                key = line[0].strip()
                if len(key) != 9 or key in seen:
                    raise ValueError(f"Malformed or duplicate FEC ID at {line_num}: {key!r}")
                seen.add(key)
                rows.append(dict(zip(FIELDS, [line[i].strip() for i in range(9)])))
    if not rows:
        raise ValueError("Official archive contains no 2026 House/Senate FEC filings")
    return sorted(rows, key=lambda row: row["fec_id"])

def fetch_source():
    request = urllib.request.Request(SOURCE, headers={
        "User-Agent": "PollingBrain/0.1 (election source attribution and academic research)"})
    with urllib.request.urlopen(request, timeout=45) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Unexpectedly large FEC archive")
    return raw

def build_snapshot(archive: bytes, now=None):
    records = parse_records(archive)
    digest = hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "schema_version": 1,
        "dataset": "fec_candidate_filings_2026",
        "coverage": "FEC 2026 US House and Senate candidate records; NOT a certified election ballot",
        "ballot_qualification_verified": False,
        "source": {"provider": "Federal Election Commission", "url": SOURCE, "documentation": DOCS},
        "retrieved_at": (now or datetime.now(timezone.utc)).isoformat(),
        "source_archive_sha256": hashlib.sha256(archive).hexdigest(),
        "records_sha256": digest,
        "record_count": len(records),
        "records": records,
    }

def main():
    snapshot = build_snapshot(fetch_source())
    if OUTPUT.exists():
        old = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if old.get("records_sha256") == snapshot["records_sha256"]:
            print(f'FEC filings unchanged ({snapshot["record_count"]} records)')
            return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f'Refreshed {snapshot["record_count"]} FEC filings; NOT ballot certified')
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"REFRESH FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
