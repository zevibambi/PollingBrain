# PollingBrain verified data policy (started October 27, 2026)

**IMPORTANT:** This pipeline is being assembled. The existing October 27 forecast percentages and example matchups are **unverified draft data** and must not be described as independent, sourced, or live.

## Three trust levels, never interchangeable

1. **State-certified ballot**: Candidate has been matched to an up-to-date official state election office's general-election certification, including corrections and election rules. Can be marked verified as appearing on the ballot.
2. **FEC candidate filing**: The FEC lists a candidate or related filing for the cycle. This confirms a filing record, **not** ballot qualification or an election matchup. FEC candidate master includes prior/future candidate records and candidates without ballot status.
3. **Unverified model input**: Draft candidates, polls, ratings, forecasts and crowd-sourced data. Excluded from the public 'verified' label until provenance and independent checks complete.

## Source inventory

The machine-readable, public-facing registry is [`public/data/source_registry.json`](public/data/source_registry.json). Official sources take precedence. Each accepted data record should carry `source_id`, canonical URL, original observation date/field dates, retrieved time, source type, record hash, version, review status, and any applicable rights.

## FEC ingestion

`scripts/refresh_fec.py` downloads the official 2025-26 FEC candidate master archive using no API key. It validates archive structure, the 15 published columns, candidate ID uniqueness, 2026 cycle and House/Senate office codes; publishes names/filing metadata **without campaign mailing addresses** into `public/data/fec_candidate_filings_2026.json`. The published file explicitly sets `ballot_qualification_verified: false`. A scheduled GitHub Actions workflow runs tests then refreshes twice daily; it commits only when the candidate row set changes.

FEC: https://www.fec.gov/campaign-finance-data/candidate-master-file-description/

This ingestion job must successfully execute before the database is described as populated. We cannot infer a successful source download or scheduled run from code alone.

## Still needed to produce verified forecasts

- Certified general-election ballots for all 50 states, including ranked-choice, special elections, runoffs and multiple candidates; no automatic FEC-to-nominee promotion.
- Poll-level collector from original releases with deduplication and rights verification; historical pollster backtesting and reproducible model math.
- 2026 district maps and official boundaries, county-level historical returns, source-linked ratings.
- Independent validation of forecast probabilities. Until then, label existing numbers provisional.
- Election-night licensed/official results feeds with timestamped raw snapshots, correction logic, and tested projected-vote algorithms.

## Failure policy

If a source changes format, reports conflicting rows, omits an expected key, or fails its integrity check, stop the ingestion job and keep the previous known-good snapshot. Never replace data with fabricated defaults. Never treat a third-party forecast as official election data.

## Versioned source archive

After a successful FEC refresh, `scripts/archive_snapshot.py` validates the record count, source URL, filing-only status and content hash before writing content-addressed snapshots under `public/data/history/fec_candidate_filings_2026/`. Existing snapshots are preserved. `public/data/collection_status.json` tracks successful checks separately from the retrieval time of the latest changed content. A failed refresh never advances that check timestamp. The workflow serializes refresh jobs to prevent competing commits.

The public archive now syncs into the PollingBrain Supabase database twice daily. Source-check timestamps remain separate from database sync timestamps. Four source-checked Texas race observations across September and October ReconMR surveys establish an initial comparison baseline. Siena and Marquette release feeds are checked every two hours; newly discovered metadata stays pending review. The public data page reads published data from Supabase with read-only permissions.

No OpenAI/Claude background workers or validated forecasts are deployed yet. National poll coverage, past-election poll archives, state-certified ballots, historical election returns, news extraction and model backtesting remain incomplete. See `database/` for deployed schema, source evidence seeds and discovery setup.
