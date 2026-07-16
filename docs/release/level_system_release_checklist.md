# Level System Release Checklist

Use this checklist for any release that changes the level generator, level
editor, runtime routing rules, production levels, solution sidecars, or the
production manifest. Record the release identifier, commit, reviewer, and date
with the completed checklist in the release record.

## Release Candidate

- [ ] Release/version:
- [ ] Commit SHA:
- [ ] Candidate owner:
- [ ] Reviewer:
- [ ] Date:
- [ ] Working tree is clean and the candidate commit is the exact commit being released.
- [ ] Required Python dependencies, Xcode 16.4, and the supported iOS 18.5 simulator are installed.

## Automated Release Gate

From the repository root, run the complete local gate and retain its reports:

```bash
python scripts/run_all_checks.py --swift-tests \
  --destination 'platform=iOS Simulator,name=iPhone 16 Pro,OS=18.5' \
  --reports-dir artifacts/level-system-release
```

The command must exit zero. It runs the shared-core, generator, and headless
editor tests (including the editor authoring smoke workflow), deterministic
generator smoke and fixed-seed suites, production corpus and manifest gates,
and the Swift domain/runtime/parity/solvability/UI suite. On a platform without
Xcode, omit `--swift-tests`, retain the reports, and require the macOS Swift CI
job before signing off Swift parity.

- [ ] Generator checks passed.
- [ ] Editor checks passed, including the headless smoke workflow.
- [ ] Swift parity and runtime tests passed locally or in macOS CI.
- [ ] Production corpus verification passed.
- [ ] Python CI and macOS Swift CI passed for the candidate commit.

Do not waive a failed check by rerunning until it happens to pass. Fix the
failure or document an approved baseline change, then rerun the complete gate.

## Reports and Content Review

- [ ] `artifacts/level-system-release/fixed_seed_regressions.json` was reviewed; accepted counts, hashes, quality thresholds, and rejection health are expected.
- [ ] `artifacts/level-system-release/production_corpus_verification.md` was reviewed; every level passes and no debug candidate directory is packaged.
- [ ] Any intentional fixed-seed hash update was reviewed separately and committed with an explanation.
- [ ] Every shipped level has exactly one matching solution sidecar.
- [ ] The production manifest contains every shipped level exactly once and has no extra entries.
- [ ] Level IDs, sidecar `levelID` values, filenames, and manifest entries agree.
- [ ] Generated reports contain no unexpected warnings or unexplained quality regressions.

## Human Playtest Sample

Select at least one changed level from each affected difficulty plus the first,
middle, and last changed campaign levels. Include a revisit, a three-/four-way
switch, and a conditional road when those mechanics are affected.

For every sampled level:

- [ ] The active switch highlight is clear and changes at the expected time.
- [ ] Early, eligible, cooldown, and post-commit tap behavior feels correct.
- [ ] Package collection and destination completion occur in the intended order.
- [ ] Road geometry, labels, overlays, and switch states remain readable on the supported device size.
- [ ] The recorded or shipped solution completes within the limit and matches the intended difficulty.
- [ ] No stall, crash, debug overlay, or placeholder content is visible.

- [ ] Human playtest sample passed.
- [ ] Playtester names, devices, simulator/runtime versions, sampled level IDs, and findings are attached to the release record.

## Required Signoff

All rows require a named owner and evidence before release.

| Gate | Owner | Evidence | Signoff |
| --- | --- | --- | --- |
| Generator checks passed |  | Combined command log and fixed-seed report | [ ] |
| Editor checks passed |  | Combined command log, including smoke test | [ ] |
| Swift parity passed |  | Local log or macOS CI run | [ ] |
| Production corpus passed |  | Production corpus report | [ ] |
| Human playtest sample passed |  | Playtest record | [ ] |
| Reports reviewed |  | Review notes/approval | [ ] |
| Manifest synchronized |  | Corpus report and manifest diff | [ ] |

## Release and Rollback Readiness

- [ ] The final release diff contains no temporary report directory, generated debug candidate, autosave recovery file, or local environment artifact.
- [ ] Production levels, sidecars, and manifest are committed together.
- [ ] The previous known-good level corpus and app build are identifiable for rollback.
- [ ] If a post-release level-system failure is found, stop rollout, restore the known-good corpus/build, and preserve the failing fixtures and reports for diagnosis.
