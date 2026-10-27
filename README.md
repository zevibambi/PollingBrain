# PollingBrain

US 2026 election website, hosted as static assets on Cloudflare, with a Supabase source database.

## Implemented
- Responsive forecast preview, race search and saved races.
- Official FEC candidate filing collector, twice daily in GitHub Actions.
- Content-addressed source history and collection timestamps.
- Supabase: 4,424 versioned FEC filings, including one flagged missing name; filings do not certify ballot qualification.
- Four source-checked Texas poll observations across two ReconMR surveys (September and October 2026), including field dates, sample sizes, release URLs and review evidence.
- Twice-daily database sync from the source archive; every-two-hour discovery of Siena and Marquette release metadata into a pending review queue.
- `/sources.html` reads published poll observations and database sync timestamps using read-only public access.

## Deployment
`wrangler.jsonc` serves `public/`. Main-branch pushes use the existing Cloudflare Git integration. Database schema and deployed discovery setup are documented under `database/`. These files describe already-applied setup; do not blindly reapply initial schema to an existing project.

## Access model
Anonymous and ordinary signed-in users can read public source records and verified/published data; they cannot write. Private sync functions are not publicly callable. Backend worker write access must be configured separately. No OpenAI or Claude worker is running yet. No secret keys belong in public code.

## Remaining
The homepage model figures and sample matchups remain unverified draft content. Comprehensive certified ballots, historical polls and official returns, news extraction, model calibration/backtesting, AI worker integration and election-night results ingestion remain unfinished. Current verified poll coverage is an initial Texas baseline, not a national polling average.

## Validation
`python -m unittest discover -s tests -v`

See `DATA_SOURCES.md` for trust levels and source policy.
