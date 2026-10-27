# PollingBrain
Development preview for the 2026 US election forecasting website.

## Current status
- Responsive, static proof of concept with House/Senate overview, race search, saved races and detail panels.
- Figures and candidate names in this prototype are sourced from the user's October 27, 2026 project document and are **not independently verified**.
- This is not a live forecast feed and should not be presented as one.

## Hosting
The site is a single static `index.html` suitable for Cloudflare Pages. Set the production branch to `main` with no build command and root output directory.

## Next steps
- Import and validate the existing Python forecasting model.
- Replace static sample content with validated generated JSON.
- Implement historical backtesting and data provenance.
- Build scheduled data ingestion and forecast history.
- Add an election-night data feed only after source/licensing verification and testing.

No external scripts, cookies, database or paid services are needed for this prototype.