# Tiny Routes Level Solvability Hang/Test-Health Fix Plan

## Purpose

Fix the test-health issue where `LevelSolvabilityTests` can hang at 100% CPU inside the real `RouteEngine` simulation path. The goal is not to redesign solvability. The goal is to make the harness deterministic, bounded, diagnostic, and capable of identifying whether a failure belongs to a solution script, level graph, or engine progression bug.

## Current Risk

`LevelSimulationHarness` currently advances time in two unbounded loops. A healthy level should complete, fail, or consume time until `.failed(reason: .timeExpired)`, but test infrastructure cannot assume that invariant. If the engine stops producing terminal outcomes or stops making progress, the test process can spin indefinitely.

The cache in `LevelSolvabilityTests` also holds a static lock while all simulations run. If one simulation hangs, other solvability test methods can block behind that lock.

## Target Outcome

- Running all tests never hangs indefinitely because of `LevelSolvabilityTests`.
- Bad simulations fail fast with clear XCTest messages.
- Failure messages identify level ID, script ID, expected and actual outcome, elapsed time, remaining time, tap count, step count, current node, current edge, package state, and last action.
- `LevelSimulationHarnessTests` proves guard behavior.
- `RouteEngine` internal safety-limit trips are observable by tests.
- Solvability tests still prove production levels complete with valid scripts.

## Implementation Tasks

1. Add `LevelSimulationLimits` with production and fast-test defaults.
2. Add typed `LevelSimulationHarnessError` values and `LevelSimulationDiagnostics`.
3. Add an `EngineProgressSnapshot` helper to detect repeated no-progress updates.
4. Centralize all simulation advancement into a single guarded helper.
5. Validate script action times and tap node IDs before simulation.
6. Expose `RouteEngine.didHitUpdateSafetyStepLimit` and have the harness fail when it trips.
7. Extend `LevelSolvabilityResult` with step-count metadata.
8. Add harness guard unit tests for max steps, invalid times, normal completion, and bounded cycle behavior.
9. Improve `LevelSolvabilityTests` diagnostics.
10. Avoid running simulations while holding `cacheLock`.
11. Add focused solution-script structure health tests.
12. Run targeted harness and solvability tests to capture the first bounded failure.
13. Fix the root cause in the correct layer: script, graph, or `RouteEngine`.
14. Add the smallest regression test for the exact hang mode.
15. Run the full suite without skipping solvability tests.

## Guard Defaults

Production solvability uses:

```swift
LevelSimulationLimits(
    maxStepCount: 20_000,
    maxSimulatedTimeSeconds: nil,
    maxNoProgressStepCount: 120
)
```

`nil` simulated-time limit means the harness uses the level time limit plus a small buffer. Current production levels are short enough that 20,000 steps leaves substantial headroom while still making indefinite CPU spin impossible.

## Non-Goals

- Do not change menu header UI behavior.
- Do not rewrite the level JSON structure.
- Do not replace `RouteEngine` with a fake simulator.
- Do not permanently skip `LevelSolvabilityTests`.
- Do not hide failing levels to make CI pass.
- Do not rely on `assertionFailure` as the only simulation failure signal.

## Acceptance Checklist

- [x] `LevelSimulationHarness` has no unbounded advancement loop.
- [x] Harness guard failures throw typed errors.
- [x] Harness errors include level ID and runtime diagnostics.
- [x] `RouteEngine` internal safety limit is observable by tests.
- [x] Harness tests cover max-step and invalid-action failures.
- [x] `LevelSolvabilityTests` no longer runs simulations while holding `cacheLock`.
- [x] Solvability failures include useful per-level details.
- [x] The original hanging run becomes a bounded pass or bounded failure.
- [x] The root cause is fixed in the correct layer.
- [x] A focused regression test prevents recurrence.
- [x] Full test suite passes without skipping `LevelSolvabilityTests`.

## Verification Notes

Verified on May 24, 2026 with the available `iPhone 16, OS=18.5` simulator. The generic `iPhone 16` destination did not resolve on this machine because multiple runtimes are installed.

Commands run:

```bash
xcodebuild test -scheme TinyRoutes -destination 'platform=iOS Simulator,name=iPhone 16,OS=18.5' -only-testing:TinyRoutesTests/LevelSimulationHarnessTests
xcodebuild test -scheme TinyRoutes -destination 'platform=iOS Simulator,name=iPhone 16,OS=18.5' -only-testing:TinyRoutesTests/LevelSolutionScriptTests
xcodebuild test -scheme TinyRoutes -destination 'platform=iOS Simulator,name=iPhone 16,OS=18.5' -only-testing:TinyRoutesTests/LevelSolvabilityTests
xcodebuild test -scheme TinyRoutes -destination 'platform=iOS Simulator,name=iPhone 16,OS=18.5' -only-testing:TinyRoutesTests/TRMenuHeaderTests
xcodebuild test -scheme TinyRoutes -destination 'platform=iOS Simulator,name=iPhone 16,OS=18.5'
```

Results:

- `LevelSimulationHarnessTests`: 7 tests, 0 failures.
- `LevelSolutionScriptTests`: 12 tests, 0 failures.
- `LevelSolvabilityTests`: 7 tests, 0 failures.
- `TRMenuHeaderTests`: 2 tests, 0 failures.
- Full suite: 242 tests, 0 failures.

The current production catalog did not trip the new guard after bounded advancement landed. The reliability fix is therefore in the harness layer: every simulation now has step, time, no-progress, and `RouteEngine` internal-safety guards, and the small-cycle regression proves a non-terminal route drains to `.timeExpired` instead of spinning indefinitely.
