# Forecast engine patch review (2026-10-27)

Status: **NOT APPLIED OR TESTED**. The unified diff has been pasted in chat, but no actual `pollingbrain-forecast-engine.patch` file has been uploaded/mounted or committed to this branch. Do not merge or claim passing tests until the entire file has been applied and independently executed.

## Critical fixes before merge

1. **Same-party and multi-candidate House races are modeled incorrectly.** `build_house` sets `chal_party: "D"` and uses a standard Democrat-versus-Republican simulation even when California top-two elections feature two Democrats (e.g. CA-11) or two Republicans (CA-40). In a same-party election both candidates are of the same party, so these probabilities cannot be used as party-seat probabilities. `SENATE/GOVERNOR` special rules also acknowledge unmodeled multi-party outcomes. Separate candidate-win probabilities from party-seat results and suppress unsupported outcome probabilities.
2. **Misleading verified status.** `build_statewide` sets `"verified": True` for every race although the data source is a manually transcribed compilation, and `build_house` marks some inherited/third-party assignments `verified`. Reserve verified for specific independently sourced claims, not the overall race or model.
3. **Polls from aggregator list are model inputs despite explicitly unverified original releases.** A public forecast should not treat these as verified nor show primary-source tags for them. Require independent original-release verification or strict experimental labeling; avoid assigning them the weight of source-checked polls.
4. **Failure can still result in publication with outdated poll cache.** The workflow uses `continue-on-error: true` for database collection, followed by model, build, commit. This is intentional with stale warnings, but set enforceable max-age gates for public publishing and distinguish freshness from data update time.
5. **Historical claims not auditable in this patch.** `ERROR_FIT` narrative says 900 statewide races and `SD_NATIONAL/SD_STATE` are fitted, yet no underlying backtest pipeline or raw provenance is supplied. The `HISTORY`/ `MISSES` objects contain curated figures without row-level input references. Treat as unvalidated assertions until independently reproduced.
6. **Same-party California general elections and mixed-party House seat counting.** `hd = sum((r["_sim"]>0) for r in house)` counts a Democratic-vs-Democratic race as a D-versus-R probability, wrongly allowing it to flip Republican; and CA-40 two Republicans can be miscounted Democratic. This affects national House control simulations.
7. **Hardcoded generic ballot and ratings stale after first check.** `GENERIC_BALLOT` and rating tables never refresh automatically in the hourly pipeline. The `inputs/status.json` freshness warnings may correctly show staleness but hourly reconstruction does not fetch updated inputs.
8. **Poll de-duplication fragile.** `_norm_pollster` uses only first token, falsely colliding unrelated firms; release-date vs field-end windows may miss true duplicates. `effective_pollsters` is not normalized the same way.
9. **Source validity and licensing.** Generic RCP URLs are collection pages, not primary releases. Review terms for redistribution, and record original links and field dates.
10. **Hourly site redeployment.** `record_check` changes status timestamp on every successful polling DB check; forecast embeds time into `generated`; every build therefore commits even if no model input changes. Decouple `last_checked` from forecast content and retain previous forecast on no material changes.
11. **As-of date after election.** Model has no post-election lockout; running hourly indefinitely could imply forecasts remain relevant after polls close. Implement phase boundaries.
12. **Input source downloads are unpinned.** Both `tonmcg` and `congress-legislators/main` are live mutable branches. Pin commit/version or hash and validate expected schemas; never allow historical baseline drift.
13. **Test integrity.** Existing tests mostly assert schema and self-consistency, not external correctness of candidate lists, official ballot certification, 2024 county results or probability calibration.

## Merge gates

- Apply complete patch to the `claude/forecast-engine` branch.
- Pin dependencies and trusted reference-data versions.
- Run syntax compilation, full `forecast/tests`, existing `tests/`, one dry-run build to a temporary output folder, and inspect generated 506 race records and web pages.
- Fix same-party seat counting, status labeling, invalid/incomplete input handling, and stale publication gate.
- Compare `git diff` to ensure `public/index.html`, FEC dataset, and history files are unchanged.
- Do not merge or enable the hourly workflow on `main` without passing these gates.

Source of this review: the complete inline patch text supplied in the chat. No claim has been made that the code has been applied or executed.
