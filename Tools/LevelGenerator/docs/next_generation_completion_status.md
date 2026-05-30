# Next Generation Plan Completion Status

This file tracks progress against `Tools/LevelGenerator/docs/next_generation_master_plan.md`.

## Phase 0 - Baseline, Safety, and Bug Reproduction

- [x] Created `Tools/LevelGenerator/docs/next_generation_master_plan.md`.
- [x] Created `Tools/LevelGenerator/docs/next_generation_completion_status.md`.
- [x] Added a current-state baseline summary to the master plan.
- [x] Documented current templates.
- [x] Documented current validators.
- [x] Documented current simulation behavior.
- [x] Documented current report and preview behavior.
- [x] Documented known limitations.
- [x] Saved a level-028-style switch arrow bug fixture:
  - [x] `TinyRoutesTests/Fixtures/SwitchArrowBug/level_028_style_switch_arrow_mismatch.json`
  - [x] `TinyRoutesTests/Fixtures/SwitchArrowBug/level_028_style_switch_arrow_mismatch.solution.json`
  - [x] `TinyRoutesTests/Fixtures/SwitchArrowBug/README.md`
- [x] Documented the legacy displayed arrow direction and actual first travel direction.
- [x] Added regression coverage that fixture edges use the road-path start tangent instead of the diagonal target-node vector.
- [x] Confirmed existing horizontal-first and vertical-first switch arrow tangent tests are present in `TinyRoutesTests/RouteEngineTests.swift`.

## Baseline Verification

The repo does not have a `python` shim on this machine, and `/opt/homebrew/bin/python3` does not have `pytest` installed. Baseline generator verification was run before the Phase 0 artifact changes and repeated afterward with Python 3.13:

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests
```

Result: `143 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 Tools/LevelGenerator/run_all_generator_checks.py --python /Library/Frameworks/Python.framework/Versions/3.13/bin/python3
```

Result: passed. The check suite ran Python tests, smoke dry-run generation, and validation for production levels `level_001` through `level_030` with Swift tests disabled by the script.

Xcode is available:

```bash
xcodebuild -version
```

Result: Xcode 26.5, build 17F42.

Focused Swift regression verification:

```bash
xcodebuild test -scheme TinyRoutes -destination 'platform=iOS Simulator,id=CE7E87CB-2EDB-4E6B-AC65-AA1BDCA416AD' -only-testing:TinyRoutesTests/RouteEngineTests
```

Result: `TEST SUCCEEDED`; 88 `RouteEngineTests` passed, including `testLevel028StyleFixtureSwitchArrowsUseRoadStartTangents`.

## Phase 1 - Runtime-Parity Switch Direction and Arrow Correctness

Not started as part of this phase. Some runtime arrow direction fixes and Swift tests were already present when Phase 0 began; Python-side switch visual clarity validation and generator rejection remain future work.
