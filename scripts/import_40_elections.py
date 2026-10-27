#!/usr/bin/env python3
"""Ingest Brookings House election statistics for exactly 40 cycles (1946-2024).
Keep original field names and source metadata; never synthesize missing values.
"""
import csv
import hashlib
import io
import json
import re
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SOURCE = "https://www.brookings.edu/wp-content/uploads/2026/04/2-2.csv"
SOURCE_PAGE = "https://www.brookings.edu/articles/vital-statistics-on-congress/"
OUTPUT = Path(__file__).resolve().parents[1] / "public/data/house_40_election_cycles_1946_2024.json"
YEARS = tuple(range(1946, 2025, 2))
MAX_BYTES = 2_500_000

def extract_year(row):
    matches = set()
    for field in row.values():
        if field is not None:
            match = re.fullmatch(r"\s*(?:19|20)\d{2}(?:\.0)?\s*", field)
            if match:
                matches.add(int(float(field)))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one election year in CSV record: {row!r}")
    return matches.pop()

def parse_csv(raw):
    text = raw.decode("utf-8-sig")
    dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t")
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames or len(reader.fieldnames) < 2:
        raise ValueError("Missing CSV headers")
    headers = [str(x or "").strip() for x in reader.fieldnames]
    if len(set(headers)) != len(headers):
        raise ValueError("Duplicate source column headers")
    source_rows = []
    for i, item in enumerate(reader, 2):
        if None in item or any(v is None for v in item.values()):
            raise ValueError(f"Malformed source CSV row {i}")
        row = {key.strip(): value.strip() for key, value in item.items()}
        year = extract_year(row)
        if year in YEARS:
            source_rows.append({"year": year, "values": row})
    counts = Counter(x["year"] for x in source_rows)
    if sorted(counts) != list(YEARS):
        missing = sorted(set(YEARS) - counts.keys())
        raise ValueError(f"Source is missing election years {missing}")
    return headers, source_rows, counts

def create(raw):
    headers, rows, counts = parse_csv(raw)
    return {
        "schema_version": 1,
        "collection": "40_completed_federal_general_election_cycles",
        "election_years": list(YEARS),
        "covered_year_count": len(counts),
        "scope": "U.S. House national popular vote and seats by party; not district-level race records, not polls",
        "status": "historical_observed_data_from_named_source",
        "source": {
            "publisher": "Brookings Institution",
            "dataset": "Vital Statistics on Congress, Table 2-2: Popular Vote and House Seats Won by Party, 1946–2024",
            "data_url": SOURCE, "landing_page": SOURCE_PAGE,
            "note": "Retains source-provided field names, values and categories. Check table notes for methodology."
        },
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "columns": headers,
        "records_per_year": {str(y): counts[y] for y in YEARS},
        "source_records": rows,
    }

def main():
    req = urllib.request.Request(SOURCE, headers={"User-Agent": "PollingBrain historical data research (source attribution provided)"})
    with urllib.request.urlopen(req, timeout=45) as response:
        raw = response.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("Missing or oversized Brookings CSV")
    result = create(raw)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT.exists():
        old = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if old.get("source_sha256") == result["source_sha256"]:
            print("No changes in 40-cycle historical dataset")
            return
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f'Ingested {result["covered_year_count"]} historical election cycles and {len(result["source_records"])} raw source records')

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"HISTORICAL IMPORT FAILED: {e}", file=sys.stderr)
        raise SystemExit(1)
