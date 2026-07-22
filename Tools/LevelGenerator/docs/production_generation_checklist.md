# Production V3 Operator Runbook

Automatic production generation is unattended: it does not require candidate
review, Level Editor repair, or per-level playtesting. Human sampling belongs to
release QA and quality-profile calibration, not to a successful generation run.

## One-command generation

From the repository root, with Python dependencies and Xcode installed:

```bash
python Tools/LevelGenerator/generate_production_campaign.py \
  --start 31 \
  --count 30 \
  --difficulty auto \
  --seed 12345 \
  --swift-tests
```

Omit `--seed` to have the command choose and report one. The same configuration,
quality-profile version, seed, worker count, and attempt budget produce the same
candidate identities, selected logic, solutions, and reports. Record the
resolved seed from the terminal report.

The command succeeds only after selecting the complete requested count,
validating staged Python/Swift evidence, and atomically promoting it. It has no
legacy template, fixed recipe, direct motif, relaxed quality, or manual-approval
fallback.

## GUI generation

Launch `python Tools/LevelGenerator/launch_gui.py`, enter start level, count,
difficulty/campaign profile, and optional seed, then choose **Generate Production
Campaign**. The activity log shows the same planning, candidate-pool, portfolio,
staging, validation, and promotion stages as the CLI and ends with the terminal
report path. Do not use legacy generation controls for production output.

## Reports and failure reproduction

The terminal JSON/Markdown report records run/configuration identity, resolved
seed, quality-profile version/fingerprint, global attempt allocations, selected
candidate proofs, rejection counts, health metrics, staged hashes, Swift parity,
and promotion status. Normal rejection churn is expected; incomplete pools,
anomaly thresholds, stage bypasses, or transaction failures are systemic.

Every retained attempt includes a reproducibility bundle. To investigate a
failure:

1. Read the terminal status, failure code/stage, constrained slots, and dominant
   rejection codes.
2. Preserve the run workspace and reproduction bundle.
3. Run its `reproduce.sh`; it targets an isolated output tree and restores the
   original request, seed, quality profile, worker count, and budgets.
4. Compare stage evidence and content hashes. Never point a reproduction command
   at production directories.

## Staging, locking, and rollback

All candidate and corpus writes occur in the run workspace. A process-wide
generation lock protects the promotion boundary. Do not delete a lock unless
the recorded owner is demonstrably stale. Validation failure yields
`failed_no_changes`; promotion failure yields `rolled_back` only after restoring
the original production snapshot. See
[Transactional Generation](transactional_generation.md).

## Extending the generator

- Adding a blueprint archetype: follow
  [Puzzle Blueprints](puzzle_blueprints.md#adding-an-archetype), then add target,
  deterministic, exact-strategy, and production-smoke coverage.
- Adding a motif: follow [Stateful Motifs](stateful_motifs.md#adding-a-motif),
  including typed contract, invalid-context, solver, and phase-layout tests.
- Updating quality thresholds: create a higher semantic version under
  `config/quality_profiles`; protected invariants cannot be weakened. Update
  blinded-playtest and fixed-seed evidence as described in
  [Quality Gates](quality_gates.md#updating-quality-profiles).

## Release QA

Run the mandatory wrapper from a clean checkout:

```bash
python scripts/run_all_checks.py --swift-tests \
  --production-content \
  --generator-v3-stress \
  --transaction-tests
```

This runs all Python suites, generator smoke/fixed seeds, production corpus
verification, 100 complete 30-level V3 campaigns, transaction failures, and the
Swift scheme. It writes `release_summary.json` and `release_summary.md` under
`artifacts/production-v3-release` unless `--reports-dir` is supplied. The
summary contains commit/configuration identity, quality profile, test and stress
totals, campaign completion, parity, corpus metrics, and non-blocking warnings.

The command returns zero only when every gate passes and all four release flags
are present. A dirty-worktree warning is recorded for traceability; run the
release signoff from a clean checkout so the commit identity describes the code
that was tested.

Optional blinded human sampling may be performed after automated gates to
calibrate a future quality-profile version. It does not select, repair, or
approve individual generated levels.
