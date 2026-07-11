# Tiny Routes Generator and Level Designer Implementation Plan

**Repository reviewed:** `Tiny-Routes-main`
**Plan date:** July 10, 2026
**Primary systems:** Swift gameplay runtime, Python level generator, Python/PySide6 level editor, Swift/Python validation suites
**Goal:** Make generated levels consistently playable, understandable, varied, and engaging; make the level editor intuitive enough for routine level creation and debugging; and enforce runtime parity so accepted levels work in the real app.

---

## 1. Executive Summary

The current generator has substantial infrastructure, but it is optimizing a gameplay model that does not match the real app. The Python abstract solver treats a switch decision as something made when the dot reaches that switch. The Swift game currently allows most downstream switches to be changed at almost any time. This makes many generated levels reducible to “tap every incorrect switch at the beginning,” even when generation reports describe those taps as timed reaction decisions.

The level editor has solid file models and validation, but the primary interactions are difficult to discover:

- Nodes are added to the viewport center instead of where the designer chooses.
- Roads are created through a hidden right-click sequence.
- Road shape and most object properties cannot be edited directly.
- The visible grid does not snap.
- There is no undo/redo command system.
- Solutions are typed as raw timestamps and node IDs instead of recorded through playtesting.

This plan fixes those problems in the following order:

1. Establish a single, explicit gameplay interaction contract.
2. Make the Swift runtime and Python simulator follow that contract exactly.
3. Replace proxy-based generator scoring with measured decision-quality scoring.
4. Improve topology generation, timing, layout construction, repair, and batch selection.
5. Rebuild the editor around visible tools, direct manipulation, undo/redo, live validation, and integrated playtesting.
6. Migrate production levels and require full Python and Swift verification before release.

The target gameplay model selected by this plan is **live look-ahead routing**:

- Only the first upcoming switch on the dot's currently selected route may be changed.
- That switch becomes active when it is within a configurable travel-time look-ahead window.
- The active switch is clearly highlighted.
- The player may rotate it multiple times while the window is open, subject to a short tap cooldown.
- The switch locks when the dot commits to the outgoing road.
- Taps on all other switches are rejected and provide non-disruptive feedback.

This model preserves the intended real-time routing identity while making the generator's sequential switch decisions real rather than merely reported.

---

## 2. Completion Standard

The work is not complete merely because new code compiles. It is complete only when every global acceptance condition below passes.

### 2.1 Runtime correctness

- [ ] Swift and Python use the same switch eligibility rules.
- [ ] The same level, initial state, tap sequence, and elapsed-time steps produce matching outcomes in Swift and Python.
- [ ] Taps before an activation window are rejected in both runtimes.
- [ ] Taps during an activation window are accepted in both runtimes.
- [ ] Taps after route commitment are rejected in both runtimes.
- [ ] Two-, three-, and four-way switches rotate identically in both runtimes.
- [ ] Repeated visits and repeated taps behave identically in both runtimes.
- [ ] Package collection and destination completion order match in both runtimes.
- [ ] Existing legacy JSON still decodes without crashing.

### 2.2 Generator correctness

- [ ] Every accepted candidate passes structural validation.
- [ ] Every accepted candidate passes Python runtime simulation.
- [ ] Every accepted candidate requiring runtime parity passes the Swift test harness.
- [ ] Every accepted solution tap occurs while its switch is eligible.
- [ ] Moving all required taps to time `0.0` fails for every nonzero-tap live-routing level.
- [ ] Medium, hard, and expert levels satisfy decision-dependency requirements rather than only tap-count requirements.
- [ ] Mechanic tags do not award quality points without measured graph or simulation evidence.
- [ ] The same seed and configuration produce the same accepted levels and reports.
- [ ] A full fixed-seed campaign generation produces the requested number of valid levels.

### 2.3 Editor correctness

- [ ] A new user can place a node by choosing a tool and clicking the canvas.
- [ ] A new user can connect two nodes by dragging between visible connection handles.
- [ ] Node, edge, level-rule, and switch-state properties can be edited in the inspector.
- [ ] Every destructive or mutating edit supports undo and redo.
- [ ] Grid snapping can be enabled or disabled.
- [ ] Validation updates automatically after edits.
- [ ] A designer can play a level inside the editor and record a valid solution without typing node IDs or timestamps.
- [ ] Saving and reopening a level preserves all supported fields and unknown extension fields.
- [ ] The editor can open generated candidates and display their quality analysis.

### 2.4 Repository health

- [ ] Generator and editor Python tests can run together from the repository root without test-package import collisions.
- [ ] All Python tests pass.
- [ ] All relevant Swift tests pass on the supported simulator destination.
- [ ] The combined verification command exits nonzero on any failed gate.
- [ ] Production levels, solution sidecars, and the manifest are synchronized.
- [ ] No debug generation output or failed candidate artifacts are accidentally packaged into the app.

---

## 3. Locked Product and Technical Decisions

These decisions remove ambiguity for implementation. Change them only through an explicit design change and corresponding test updates.

### 3.1 Gameplay identity

Tiny Routes will use **live look-ahead switch control**, not unrestricted global preconfiguration.

### 3.2 Eligible switch definition

At any moment, the runtime identifies at most one eligible switch:

1. Start from the dot's current position.
2. Follow the currently active route forward.
3. Continue through nodes with zero or one usable outgoing road.
4. Stop at the first switchable node with at least two usable outgoing roads.
5. Calculate travel time from the dot's current position to that switch.
6. The switch is eligible when the travel time is less than or equal to the level's look-ahead window.
7. The switch remains eligible until the dot commits to an outgoing road from that switch.

The search must have a safety limit so malformed cycles cannot loop forever.

### 3.3 Tap behavior

- Taps are ignored while paused or after completion/failure.
- A tap is accepted only for the current eligible switch.
- A tap rotates to the next currently usable outgoing road.
- A short configurable cooldown prevents accidental duplicate taps from one physical touch.
- Multiple intentional taps are allowed during one window for three- and four-way switches.
- A rejected tap does not increment the score tap count.
- A rejected tap returns a reason for tests, logging, and editor feedback.

### 3.4 Backward compatibility

Introduce a versioned level-rules object. Legacy levels without rules decode as `legacyGlobal` temporarily. Production migration will explicitly convert or regenerate levels to `liveLookahead`.

Recommended JSON addition:

```json
{
  "schemaVersion": 2,
  "rules": {
    "switchInteractionMode": "liveLookahead",
    "switchLookaheadSeconds": 1.35,
    "switchTapCooldownSeconds": 0.12
  }
}
```

Do not rely on a nonoptional synthesized Swift `Decodable` property with a default value. Implement explicit backward-compatible decoding or use an optional serialized field with a nonoptional computed effective value.

### 3.5 Generator quality policy

A generated level is not “interesting” because its recipe declares a tag. Quality must be inferred from graph structure, solver results, simulation, and layout measurements.

### 3.6 Editor interaction policy

The editor will use explicit modes:

- **Select**
- **Place Node**
- **Connect**
- **Playtest**

Hidden right-click workflows may remain as shortcuts, but they cannot be the primary workflow.

### 3.7 Source of truth

- Swift `RouteEngine` remains the production gameplay source of truth.
- Python has a parity simulator using the same written contract.
- Shared JSON parity fixtures are executed in both languages.
- Generated production levels with advanced mechanics must pass Swift runtime replay.

---

## 4. Work Organization Rules

Use these rules to keep tasks safe for entry-level contributors.

- Keep each pull request focused on one task or one tightly connected task group.
- Add or update tests in the same change as behavior.
- Do not change a JSON shape without backward-compatibility tests.
- Do not delete old APIs until callers have migrated and compatibility tests pass.
- Prefer extracting a small service over adding more responsibilities to already large files.
- Use named result types and rejection codes instead of bare booleans.
- Preserve unknown JSON fields during editor load/save round trips.
- Run the phase gate before starting the next phase.
- Keep deterministic seeds in every generator regression test.
- Do not tune quality thresholds using only one generated batch.

Recommended task labels:

- `runtime`
- `python-core`
- `generator`
- `layout`
- `editor`
- `testing`
- `migration`
- `documentation`

---

# Phase 0 — Establish a Safe Baseline

## Objective

Make the repository testable from a clean checkout and record the current behavior before modifying gameplay.

## Task 0.1 — Add root-level developer commands

**Status:** Completed

**Files to add or update**

- `README.md`
- `scripts/run_python_tests.py` or `scripts/run_python_tests.sh`
- `scripts/run_generator_smoke.py`
- `scripts/run_all_checks.py`

**Steps**

- [x] Add a root command that runs Level Generator tests in its own working directory.
- [x] Add a root command that runs Level Editor tests in its own working directory.
- [x] Add a root command that runs both suites and preserves both exit codes.
- [x] Add a deterministic generator dry-run smoke command.
- [x] Add a combined command that runs Python tests, generator smoke checks, and optional Swift tests.
- [x] Document required Python and macOS/Xcode prerequisites.

**Acceptance tests**

- [x] Running the root Python command executes both suites.
- [x] A failure in either suite makes the root command fail.
- [x] Commands work from the repository root without manual `PYTHONPATH` changes.

## Task 0.2 — Remove the Python `tests` package collision

**Status:** Completed

**Current issue**

Both tools expose a top-level package named `tests`, so collecting both suites in one Python process can import the wrong package.

**Files to update**

- `Tools/LevelGenerator/tests/__init__.py`
- `Tools/LevelEditor/tests/__init__.py`
- Tool-specific `pyproject.toml`, `pytest.ini`, or equivalent configuration

**Steps**

- [x] Choose one consistent solution: remove package markers where safe, or rename packages to `level_generator_tests` and `level_editor_tests`.
- [x] Add explicit test paths to each tool's pytest configuration.
- [x] Remove imports that depend on generic `tests.*` package names.
- [x] Verify fixture imports remain deterministic.

**Acceptance tests**

- [x] `python -m pytest Tools/LevelGenerator/tests Tools/LevelEditor/tests` collects both suites without import mismatch.
- [x] Running each suite independently still passes.

## Task 0.3 — Record the current level-corpus baseline

**Status:** Completed

**Files to add**

- `Tools/LevelGenerator/analyze_level_corpus.py`
- `docs/quality/current_level_corpus_baseline.json`
- `docs/quality/current_level_corpus_baseline.md`

**Steps**

- [x] Load every production `level_###.json` and matching solution sidecar.
- [x] Replay the original solution.
- [x] Replay the same tap sequence with all taps at `0.0`.
- [x] Replay with taps compressed into the first `0.15` seconds.
- [x] Record switch counts, outgoing-degree distribution, repeated switch taps, route length, and result.
- [x] Record levels that reach destination before package under any tested state.
- [x] Write machine-readable JSON and human-readable Markdown.

**Acceptance tests**

- [x] The analyzer fails cleanly when a sidecar is missing.
- [x] The analyzer produces deterministic output.
- [x] The report identifies front-loadable levels without modifying files.

## Task 0.4 — Create golden parity fixtures

**Status:** Completed

**Files to add**

- `SharedFixtures/RuntimeParity/`
- Fixture-level JSON files
- Fixture solution/event JSON files
- Expected-state JSON files

**Required fixtures**

- [x] Straight route with no switch.
- [x] Two-way switch tapped too early.
- [x] Two-way switch tapped inside the window.
- [x] Tap on a noneligible downstream switch.
- [x] Tap after the dot commits to the outgoing edge.
- [x] Three-way switch requiring two rotations.
- [x] Four-way switch requiring three rotations.
- [x] Revisit requiring a different state on the second visit.
- [x] Package-before-destination success.
- [x] Destination-before-package failure.
- [x] Dead-end failure.
- [x] Time-limit failure.
- [x] Cycle safety-limit behavior.

**Acceptance tests**

- [x] Fixtures are valid JSON.
- [x] Each fixture contains an explanation of the expected result.
- [x] Both Swift and Python test targets can locate the same fixture directory or a synchronized copied resource set.

## Task 0.5 — Add a behavior-change checklist

**Status:** Completed

**File to add**

- `docs/development/gameplay_behavior_change_checklist.md`

**Checklist contents**

- [x] Swift unit test added.
- [x] Python parity test added.
- [x] Shared fixture added or updated.
- [x] Generator validator updated.
- [x] Editor playtest updated.
- [x] JSON compatibility considered.
- [x] Migration impact documented.

### Phase 0 exit gate

- [ ] Both Python suites run together.
- [ ] Baseline reports are committed.
- [ ] Shared parity fixtures exist.
- [ ] Root verification commands are documented and reliable.

---

# Phase 1 — Version and Document the Gameplay Contract

## Objective

Create a precise, backward-compatible data contract before changing runtime behavior.

## Task 1.1 — Add Swift level-rule domain types

**Status:** Completed

**Files to add or update**

- `TinyRoutes/Domain/LevelData.swift`
- `TinyRoutes/Domain/LevelRules.swift` — new
- `TinyRoutesTests/DomainModelsTests.swift`

**Suggested types**

```swift
enum SwitchInteractionMode: String, Codable {
    case legacyGlobal
    case liveLookahead
}

struct LevelRules: Codable, Equatable {
    var switchInteractionMode: SwitchInteractionMode
    var switchLookaheadSeconds: Double
    var switchTapCooldownSeconds: Double
}
```

**Steps**

- [x] Add `schemaVersion` support.
- [x] Add serialized `rules` support.
- [x] Implement backward-compatible decoding for missing `schemaVersion` and `rules`.
- [x] Add an `effectiveRules` property that always returns validated values.
- [x] Clamp or reject nonfinite and invalid numeric values through validation, not silent runtime behavior.
- [x] Keep legacy levels loadable during migration.

**Acceptance tests**

- [x] Version 1 JSON loads with effective legacy rules.
- [x] Version 2 JSON loads with explicit live rules.
- [x] Encoding and decoding version 2 preserves values.
- [x] Unknown future fields do not crash decoding where the current repository's decoder permits them.
- [x] Invalid look-ahead and cooldown values produce validation issues.

## Task 1.2 — Add Python shared rule models

**Status:** Completed

**Files to add**

- `Tools/TinyRoutesCore/tiny_routes_core/__init__.py`
- `Tools/TinyRoutesCore/tiny_routes_core/models/level_rules.py`
- `Tools/TinyRoutesCore/tests/test_level_rules.py`

**Steps**

- [x] Mirror the Swift enum values exactly.
- [x] Implement `from_dict` with legacy defaults.
- [x] Implement `to_dict` for version 2.
- [x] Add validation messages for invalid numbers and unknown interaction modes.
- [x] Keep naming conversion explicit; do not spread raw dictionary access throughout the tools.

**Acceptance tests**

- [x] Python reads every existing production level.
- [x] Python round-trips version 2 rules.
- [x] Python rejects or reports invalid modes consistently.

## Task 1.3 — Write the normative interaction specification

**Status:** Completed

**File to add**

- `docs/gameplay/switch_interaction_contract.md`

**Required sections**

- [x] Definition of a switchable node.
- [x] Definition of a usable outgoing road.
- [x] Definition of the first upcoming switch.
- [x] Travel-time calculation.
- [x] Eligibility window opening condition.
- [x] Eligibility window closing condition.
- [x] Multiple tap behavior.
- [x] Cooldown behavior.
- [x] Pause behavior.
- [x] Failure/completion behavior.
- [x] Cycle and look-ahead safety limits.
- [x] Legacy mode behavior.
- [x] Expected UI feedback.
- [x] Swift/Python rounding and tolerance rules.

**Acceptance condition**

- [x] A developer can implement the algorithm from the document without guessing.

## Task 1.4 — Update JSON documentation

**Status:** Completed

**Files to update**

- `Tools/LevelEditor/docs/current_level_json_shape.md`
- `Tools/LevelGenerator/README.md`
- `docs/gameplay_mechanics.md`

**Steps**

- [x] Document schema version 2.
- [x] Document defaults for legacy files.
- [x] Include complete valid examples.
- [x] Explain that new generated production levels must use `liveLookahead`.
- [x] Explain the migration path for old files.

### Phase 1 exit gate

- [ ] Swift and Python can read legacy and version 2 files.
- [ ] Contract documentation is complete.
- [ ] No gameplay behavior has changed yet.

---

# Phase 2 — Implement Live Switch Eligibility in Swift

## Objective

Make the real app enforce the target live-routing model with clear, testable results.

## Task 2.1 — Add a switch-tap result type

**Status:** Completed

**Files to add or update**

- `TinyRoutes/Gameplay/SwitchTapResult.swift` — new
- `TinyRoutes/Gameplay/RouteEngine.swift`

**Suggested result cases**

- `accepted(nodeID:activeEdgeID:)`
- `rejectedNoLevel`
- `rejectedPaused` if pause handling is moved into the engine
- `rejectedLevelFinished`
- `rejectedNotSwitchable`
- `rejectedNotEligible(expectedNodeID:)`
- `rejectedCooldown`
- `rejectedCommitted`

**Steps**

- [x] Replace the ambiguous `Bool` return from `rotateSwitchNode` with a structured result.
- [x] Provide a compatibility computed property such as `didRotate` during caller migration.
- [x] Ensure only accepted results increment `tapCount`.

**Acceptance tests**

- [x] Every rejection path has a unit test.
- [x] Existing callers compile through a transitional compatibility layer.

## Task 2.2 — Extract route look-ahead calculation

**Status:** Completed

**Files to add**

- `TinyRoutes/Gameplay/SwitchEligibilityService.swift`
- `TinyRoutesTests/SwitchEligibilityServiceTests.swift`

**Responsibilities**

- Determine the first upcoming switch.
- Calculate remaining travel distance and time.
- Stop safely on dead ends and cycles.
- Respect currently usable and active outgoing roads.
- Return diagnostic details for tests and UI.

**Suggested output**

```swift
struct SwitchEligibilitySnapshot: Equatable {
    let eligibleNodeID: String?
    let upcomingNodeID: String?
    let travelTimeSeconds: Double?
    let reason: SwitchEligibilityReason
}
```

**Steps**

- [x] Add a deterministic function that accepts runtime graph, dot state, speed, package state, and rules.
- [x] Handle a dot partway through an edge.
- [x] Handle a dot exactly at a node.
- [x] Traverse through non-switch route nodes.
- [x] Stop at the first switchable node.
- [x] Use a visited-state set and maximum step count.
- [x] Avoid modifying graph state during the query.

**Acceptance tests**

- [x] Upcoming switch is found through a chain of route nodes.
- [x] A farther second switch is not eligible while the first upcoming switch exists.
- [x] A switch outside the time window is reported but not eligible.
- [x] A switch inside the window is eligible.
- [x] A cyclic route does not hang.

## Task 2.3 — Integrate eligibility into `RouteEngine`

**Status:** Completed

**Files to update**

- `TinyRoutes/Gameplay/RouteEngine.swift`
- `TinyRoutesTests/RouteEngineTests.swift`

**Steps**

- [x] Store or compute the current eligibility snapshot.
- [x] Expose `eligibleSwitchNodeID` and travel-time information as read-only state.
- [x] Enforce `liveLookahead` in `rotateSwitchNode`.
- [x] Preserve `legacyGlobal` behavior for unmigrated levels.
- [x] Track the last accepted tap time per active window or globally, according to the written contract.
- [x] Reset cooldown state when loading or restarting a level.
- [x] Ensure reaching and departing a switch closes the correct window.
- [x] Recompute eligibility after an accepted rotation because the selected route may change future look-ahead.

**Acceptance tests**

- [x] Early tap rejected.
- [x] In-window tap accepted.
- [x] Wrong-node tap rejected.
- [x] Duplicate tap inside cooldown rejected.
- [x] Intentional later repeated tap accepted.
- [x] Tap count remains accurate.
- [x] Legacy mode behavior remains unchanged until migration.

## Task 2.4 — Expose active-switch UI state

**Status:** Completed

**Files to update**

- `TinyRoutes/UI/GameplayScreen.swift`
- `TinyRoutes/UI/SwitchNodeView.swift`
- Related view tests

**Steps**

- [x] Pass eligibility state into each switch view.
- [x] Visually distinguish inactive, upcoming, eligible, pressed, and locked states.
- [x] Add an accessible label or value describing whether the switch can be changed.
- [x] Keep hit testing available if rejected-tap feedback is desired, but never visually imply every switch is active.
- [x] Add subtle feedback for tapping the wrong switch without incrementing score.
- [x] Avoid flashing or excessive animation.

**Acceptance tests**

- [x] Only the eligible switch uses the active visual state.
- [x] Accessibility text updates when eligibility changes.
- [x] Press animation does not play for rejected taps unless a distinct rejected animation is intentionally defined.

## Task 2.5 — Update the Swift solution replay harness

**Status:** Completed

**Files to update**

- `TinyRoutesTests/LevelSimulationHarness.swift`
- `TinyRoutesTests/LevelSolvabilityTests.swift`
- `TinyRoutesTests/LevelSolutionScript.swift` if needed

**Steps**

- [x] Record accepted and rejected scripted actions.
- [x] Fail a solution replay when an expected tap is rejected.
- [x] Include rejection reason, expected eligible switch, dot state, and time in test output.
- [x] Keep time stepping deterministic.
- [x] Add parity-fixture test coverage.

**Acceptance tests**

- [x] A sidecar with an early tap fails with an actionable message.
- [x] A correct sidecar completes.
- [x] Three- and four-way repeated taps replay correctly.

### Phase 2 exit gate

- [ ] Swift runtime enforces live look-ahead rules.
- [ ] Swift parity fixtures pass.
- [ ] Legacy files still load.
- [ ] Gameplay UI communicates the active decision.

---

# Phase 3 — Build a Shared Python Core and Runtime-Parity Simulator

## Objective

Eliminate duplicated behavior and make the generator and editor use one tested Python model and simulator.

## Task 3.1 — Create the shared Python package

**Status:** Completed

**Files to add**

```text
Tools/TinyRoutesCore/
  pyproject.toml
  tiny_routes_core/
    __init__.py
    models/
    graph/
    simulation/
    validation/
    repositories/
  tests/
```

**Steps**

- [x] Make the package importable by both tools without modifying `sys.path` at runtime.
- [x] Add editable-development installation instructions.
- [x] Keep dependencies standard-library only unless a dependency is explicitly justified.
- [x] Add a package version.

**Acceptance tests**

- [x] Generator imports the package in tests.
- [x] Editor imports the package in tests.
- [x] Root Python tests do not depend on current working directory.

## Task 3.2 — Move common level and solution models into the core

**Status:** Completed

**Source files to migrate from**

- `Tools/LevelEditor/app/models/level_document.py`
- `Tools/LevelEditor/app/models/route_node_model.py`
- `Tools/LevelEditor/app/models/route_edge_model.py`
- `Tools/LevelEditor/app/models/solution_model.py`
- Overlapping generator models

**Steps**

- [x] Create shared `LevelDocument`, `RouteGraph`, `RouteNode`, `RouteEdge`, `LevelRules`, `Solution`, and `SolutionAction` models.
- [x] Preserve unknown fields on load/save.
- [x] Add explicit clone/deep-copy helpers for editor commands.
- [x] Add compatibility imports in old modules so existing callers continue working.
- [x] Migrate one tool at a time.
- [x] Remove duplicate implementations only after both tools pass.

**Acceptance tests**

- [x] Existing level files round-trip without losing unknown fields.
- [x] Existing solution files round-trip.
- [x] Generator outputs still match the Swift JSON shape.

## Task 3.3 — Add shared graph-query utilities

**Status:** Completed

**Files to add**

- `tiny_routes_core/graph/index.py`
- `tiny_routes_core/graph/queries.py`
- `tiny_routes_core/graph/validation.py`

**Utilities**

- [x] Nodes and edges by ID.
- [x] Ordered outgoing edges.
- [x] Incoming edges.
- [x] Switchability classification.
- [x] Reachability.
- [x] Cycle detection.
- [x] Rejoin detection.
- [x] Required-route extraction helpers.
- [x] Safe active-edge normalization.

**Acceptance tests**

- [x] Duplicate IDs produce deterministic errors.
- [x] Outgoing order is preserved.
- [x] Cycle and rejoin results are stable regardless of dictionary iteration order.

## Task 3.4 — Implement the Python runtime state

**Status:** Completed

**Files to add**

- `tiny_routes_core/simulation/runtime_state.py`
- `tiny_routes_core/simulation/runtime_graph.py`
- `tiny_routes_core/simulation/results.py`

**State fields**

- Level rules.
- Current node ID.
- Current edge ID.
- Progress along edge.
- Switch active indices or edge IDs.
- Package state.
- Elapsed and remaining time.
- Accepted tap count.
- Level outcome.
- Tap cooldown state.

**Acceptance tests**

- [x] State initialization matches Swift initial active-edge behavior.
- [x] Copying a state for search does not share mutable collections.
- [x] Invalid graphs fail with validation errors instead of key errors.

## Task 3.5 — Implement Python switch eligibility

**Status:** Completed

**Files to add**

- `tiny_routes_core/simulation/switch_eligibility.py`
- Tests using shared parity fixtures

**Steps**

- [x] Port the written algorithm, not an ad hoc approximation.
- [x] Use the same safety-step limit semantics as Swift.
- [x] Use defined numeric tolerances.
- [x] Return structured reasons and travel-time details.

**Acceptance tests**

- [x] Every Swift eligibility fixture produces the expected Python result.
- [x] Boundary tests cover just before, exactly at, and just after the look-ahead threshold.

## Task 3.6 — Implement the event-driven Python simulator

**Status:** Completed

**Files to add or replace**

- `tiny_routes_core/simulation/simulator.py`
- Replace internals of `Tools/LevelGenerator/app/services/python_solution_simulator_service.py`

**Steps**

- [x] Advance the dot deterministically to the next event: tap, node arrival, time limit, or requested end time.
- [x] Apply taps through the eligibility policy.
- [x] Record accepted and rejected actions.
- [x] Record package collection, destination arrival, dead ends, and time expiration.
- [x] Preserve a detailed event trace for reports and editor debugging.
- [x] Add a thin compatibility adapter for existing generator callers.

**Acceptance tests**

- [x] Shared parity fixtures pass.
- [x] Existing valid sidecars replay where legacy rules apply.
- [x] Simulation is deterministic across repeated runs.
- [x] A malformed cycle hits a controlled safety failure.

## Task 3.7 — Add automated Swift/Python parity comparison

**Status:** Completed

**Files to add or update**

- `Tools/LevelGenerator/app/services/runtime_parity_validator.py`
- `Tools/LevelGenerator/run_runtime_parity_fixtures.py`
- Swift fixture-result exporter in the test target if needed

**Steps**

- [x] Define a compact normalized trace shape.
- [x] Compare outcome, package order, accepted taps, rejected taps, final switch states, and elapsed time within tolerance.
- [x] Print the first divergent event with surrounding context.

**Acceptance tests**

- [x] Introducing a deliberate Python rotation-order bug makes parity comparison fail.
- [x] Correct implementations produce matching normalized traces.

### Phase 3 exit gate

- [ ] Generator and editor use shared level/solution models or compatibility adapters.
- [ ] Python simulator follows live look-ahead rules.
- [ ] Shared parity fixtures pass in both languages.

---

# Phase 4 — Separate Topology Solving from Runtime Timing

## Objective

Keep abstract graph search useful while preventing it from being mistaken for a complete gameplay simulation.

## Task 4.1 — Rename abstract taps to switch decisions internally

**Status:** Completed

**Files to update**

- `Tools/LevelGenerator/app/models/abstract_puzzle_solution.py`
- `Tools/LevelGenerator/app/services/abstract_puzzle_solver_service.py`
- Generator tests and reports

**Steps**

- [x] Introduce `decision_node_ids` and `minimum_required_decisions` terminology.
- [x] Keep deprecated aliases temporarily for compatibility.
- [x] Explain that topology solving selects switch states at decision encounters but does not schedule timestamps.
- [x] Remove report language that calls abstract decisions reaction windows.

**Acceptance tests**

- [x] Existing recipes still solve after field migration.
- [x] Reports distinguish topology decisions from runtime tap actions.

## Task 4.2 — Extract `TopologySolverService`

**Status:** Completed

**Files to add or update**

- `Tools/LevelGenerator/app/services/topology_solver_service.py`
- Transitional wrapper in `abstract_puzzle_solver_service.py`

**State should include**

- Current node.
- Switch states.
- Package state.
- Route history.
- Decision history.
- Visit counts.

**Steps**

- [x] Preserve deterministic breadth-first or cost-ordered search.
- [x] Enumerate rotation counts at an encountered switch.
- [x] Track repeated visits and different required states by visit.
- [x] Record successful and failed route outcomes.
- [x] Return all minimum-cost solutions up to a configured cap.
- [x] Produce structured failure reasons.

**Acceptance tests**

- [x] Straight route solves with zero decisions.
- [x] Two-way switch solves with one decision.
- [x] Revisit fixture requires a changed second-visit state.
- [x] Destination-before-package routes are classified correctly.
- [x] Search limits produce explicit limit results.

## Task 4.3 — Add a post-layout runtime solution search

**Status:** Completed

**Files to add**

- `Tools/LevelGenerator/app/services/runtime_solution_search_service.py`
- `Tools/LevelGenerator/app/models/runtime_solution_search.py`

**Responsibilities**

- Turn topology decisions into legal tap timestamps.
- Verify enough time exists for the required number of rotations.
- Search small timing alternatives around each window.
- Reject layouts that make intended decisions impossible or unreasonably tight.

**Steps**

- [x] Ask the simulator for activation-window open and close times.
- [x] Schedule taps with a configurable safety margin.
- [x] Respect tap cooldown.
- [x] Support multiple taps within one switch window.
- [x] Replay the final action list in the parity simulator.
- [x] Return timing diagnostics for every decision.

**Acceptance tests**

- [x] A two-way switch gets one legal timestamp.
- [x] A four-way switch with a short window is rejected if three taps cannot fit.
- [x] Revisited switches get separate decision-window timestamps.
- [x] Every returned action is accepted during replay.

## Task 4.4 — Make solution sidecars derive from verified runtime solutions

**Status:** Completed

**Files to update**

- `Tools/LevelGenerator/app/services/solution_builder_service.py`
- `Tools/LevelGenerator/app/services/route_timing_service.py`

**Steps**

- [x] Stop constructing final timestamps from approximate route timing alone.
- [x] Use `RuntimeSolutionSearchResult` as the required input.
- [x] Store window-open, chosen-tap, window-close, and safety margin in reports.
- [x] Fail generation when a final replay rejects any action.

**Acceptance tests**

- [x] Sidecars are sorted by time.
- [x] `maxTaps` equals accepted scripted actions.
- [x] Final replay completes under the time limit.

### Phase 4 exit gate

- [ ] Topology solving and runtime action timing are separate stages.
- [ ] Final sidecars contain only verified legal taps.
- [ ] Timing reports no longer call deadlines “reaction windows” without an opening boundary.

---

# Phase 5 — Replace Proxy Scoring with Decision-Quality Analysis

## Objective

Measure what the player actually does and reject structurally valid but strategically trivial levels.

## Task 5.1 — Add a decision-profile model

**Status:** Completed

**Files to add**

- `Tools/LevelGenerator/app/models/decision_profile.py`
- Shared core model if the editor will display it directly

**Required fields**

- `required_decision_count`
- `unique_switch_count`
- `repeated_switch_decision_count`
- `switch_state_change_on_revisit_count`
- `ordered_dependency_count`
- `independent_decision_ratio`
- `equivalent_minimum_solution_count`
- `successful_alternate_route_count`
- `failure_route_count`
- `failure_outcome_types`
- `dead_end_choice_count`
- `destination_before_package_choice_count`
- `recoverable_mistake_count`
- `route_revisit_count`
- `package_phase_decisions_before`
- `package_phase_decisions_after`
- `minimum_window_seconds`
- `average_window_seconds`
- `minimum_decision_spacing_seconds`
- `average_decision_spacing_seconds`
- `multiple_taps_in_window_count`
- `front_loaded_legacy_solution_possible`
- `no_op_or_equivalent_choice_count`

## Task 5.2 — Implement `DecisionProfileService`

**Status:** Completed

**Files to add**

- `Tools/LevelGenerator/app/services/decision_profile_service.py`
- `Tools/LevelGenerator/tests/test_decision_profile_service.py`

**Steps**

- [x] Analyze all bounded topology solutions and failures.
- [x] Determine whether changing one decision changes the required later decision.
- [x] Count decisions whose correct state is independent of all others.
- [x] Identify revisits requiring a different state.
- [x] Classify wrong-choice outcomes.
- [x] Attach runtime window and spacing metrics after layout.
- [x] Run the legacy-global simulator as a diagnostic to measure front-loadability during migration.

**Acceptance tests**

- [x] Three independent one-tap switches produce a high independent-decision ratio.
- [x] A revisit requiring state reversal produces a dependency and revisit count.
- [x] A decorative branch that rejoins immediately is classified as equivalent/no-op.
- [x] Failure outcome classifications are deterministic.

## Task 5.3 — Define difficulty-quality thresholds

**Status:** Completed

**Files to update**

- `Tools/LevelGenerator/app/models/difficulty_preset.py`
- `Tools/LevelGenerator/app/services/difficulty_service.py`
- Documentation

**Initial target policy**

| Difficulty | Decisions | Required strategic property | Minimum recommended window | Notes |
|---|---:|---|---:|---|
| Tutorial | 0–1 | Teaches one concept | 2.0 s | No punishment for first exposure |
| Easy | 1–3 | Clear consequences; independence allowed | 1.6 s | At most one multi-tap window |
| Medium | 2–4 | At least one dependency, phase change, recovery choice, or meaningful revisit | 1.25 s | Avoid all-independent chains |
| Hard | 3–6 | At least two dependencies or one state-changing revisit plus another decision | 1.0 s | Allow tighter but readable windows |
| Expert | 4–8 | Multi-stage dependency, revisit, or complex switch state | 0.85 s | No arbitrary visual ambiguity |

These are initial defaults. Tune them only after fixed-seed regression runs and human playtesting.

**Steps**

- [x] Add threshold fields to presets instead of hardcoding difficulty names in services.
- [x] Add clear rejection codes for every failed threshold.
- [x] Allow tutorial-specific exceptions without weakening other difficulties.

## Task 5.4 — Remove tag-based quality evidence

**Status:** Completed

**Files to update**

- `Tools/LevelGenerator/app/services/generation_quality_service.py`
- `Tools/LevelGenerator/tests/test_generation_quality_service.py`
- Existing phase route-interest tests

**Steps**

- [x] Keep mechanic tags for filtering and reporting only.
- [x] Award package-gate value only when analysis proves decisions occur across package phases or availability changes.
- [x] Award revisit value only when a route actually revisits a node.
- [x] Award state-reversal value only when the required state differs between visits.
- [x] Award false-shortcut value only when geometry and outcome analysis prove the route appears attractive and leads to a distinct consequence.
- [x] Reduce or remove raw bonuses for route length and geometric turn count.
- [x] Add penalties for independent switch chains and equivalent choices.

**Acceptance tests**

- [x] Adding a mechanic tag without graph evidence does not improve score.
- [x] A real measured revisit improves the appropriate metric.
- [x] A longer but strategically identical path does not receive a large gameplay-quality bonus.

## Task 5.5 — Add actionable quality reporting

**Status:** Completed

**Files to update**

- `Tools/LevelGenerator/app/repositories/generation_report_repository.py`
- Markdown and JSON report tests

**Report additions**

- [x] Decision profile summary.
- [x] Why the level is accepted for its difficulty.
- [x] Strategic weaknesses and penalties.
- [x] Every activation window.
- [x] Accepted and rejected runtime actions.
- [x] Legacy front-load diagnostic.
- [x] Evidence source for every mechanic claim.

### Phase 5 exit gate

- [ ] Quality scoring uses measured evidence.
- [ ] Medium/hard/expert independent-tap chains are rejected.
- [ ] Reports explain player decisions rather than only graph labels.

---

# Phase 6 — Improve Topology Generation with Composable Motifs

## Objective

Move from selecting mostly complete fixed recipes toward composing small, testable puzzle mechanics.

## Task 6.1 — Define a motif interface

**Status:** Completed

**Files to add**

- `Tools/LevelGenerator/app/models/puzzle_motif.py`
- `Tools/LevelGenerator/app/motifs/base_motif.py`
- `Tools/LevelGenerator/app/motifs/motif_registry.py`

**A motif should declare**

- Entry connector.
- Exit connectors.
- Nodes and directed edges.
- Intended decision effect.
- Allowed difficulties.
- Whether it may introduce a cycle, rejoin, revisit, or dead end.
- Required compatibility constraints.
- Mechanic metadata for reporting only.

**Acceptance tests**

- [x] Motif IDs are unique.
- [x] A motif validates independently.
- [x] Connector definitions reference real nodes.

## Task 6.2 — Convert existing recipes into seed motifs

**Status:** Completed

**Source areas**

- `Tools/LevelGenerator/app/recipes/`
- `Tools/LevelGenerator/app/templates/`

**Initial motifs**

- [x] Straight segment.
- [x] Single binary choice.
- [x] Dead-end decoy.
- [x] Longer recoverable detour.
- [x] Split and rejoin.
- [x] Package branch.
- [x] Return loop.
- [x] Revisited switch.
- [x] Ring route.
- [x] Three-way hub.
- [x] Four-way hub.

**Steps**

- [x] Preserve existing recipe families through adapters.
- [x] Add independent tests for each motif.
- [x] Do not delete legacy generation mode until new fixed-seed tests are stable.

## Task 6.3 — Implement a motif composer

**Status:** Completed

**Files to add**

- `Tools/LevelGenerator/app/services/motif_composer_service.py`
- `Tools/LevelGenerator/tests/test_motif_composer_service.py`

**Steps**

- [x] Choose motif count and allowed motif categories from the difficulty preset.
- [x] Connect motif entry/exit ports deterministically from a seed.
- [x] Rename internal node IDs to avoid collisions.
- [x] Preserve ordered outgoing-road intent.
- [x] Reject invalid cycles or rejoins before layout.
- [x] Run topology solver and decision-profile checks immediately.

**Acceptance tests**

- [x] Same seed produces the same composed graph.
- [x] Composed IDs are unique.
- [x] Invalid connector combinations are rejected with specific reasons.
- [x] Generated graphs have valid start, package, and destination paths.

## Task 6.4 — Add dependency-oriented composition rules

**Steps**

- [ ] For medium and above, require at least one motif whose outcome affects a later decision.
- [ ] For hard and expert, prefer a revisit, phase split, recovery loop, or multi-state hub.
- [ ] Prevent composing several independent binary choices as the only mechanic.
- [ ] Cap dead-end-only punishment so levels do not become trial-and-error chains.
- [ ] Require a readable consequence path for decoys.

**Acceptance tests**

- [ ] A medium batch cannot contain only independent switch chains.
- [ ] Hard compositions satisfy the preset dependency threshold before layout.

## Task 6.5 — Keep recipe metadata descriptive, not authoritative

**Steps**

- [ ] Generate mechanic tags from composed motifs for search/reporting.
- [ ] Recompute actual mechanic evidence after solving.
- [ ] Report discrepancies between declared intent and detected behavior.
- [ ] Reject a candidate when a required motif effect was lost during composition.

### Phase 6 exit gate

- [ ] New generation mode can build graphs from motifs.
- [ ] Existing recipe mode remains available as fallback.
- [ ] Strategic quality is checked before layout work begins.

---

# Phase 7 — Construct Layouts Instead of Rejecting Random Layouts

## Objective

Reduce geometry rejection churn by satisfying portrait, spacing, and connection constraints during placement.

## Task 7.1 — Extract layout data structures

**Files to add**

- `Tools/LevelGenerator/app/models/layout_graph.py`
- `Tools/LevelGenerator/app/models/layout_constraints.py`
- `Tools/LevelGenerator/app/models/layout_result.py`

**Required concepts**

- Logical layer or route depth.
- Grid cell.
- Lane.
- Switch port direction.
- Node footprint.
- Reserved icon clearance.
- Candidate bend points.
- Constraint violation.
- Repair operation.

## Task 7.2 — Add topological layer assignment

**Files to add or update**

- `Tools/LevelGenerator/app/services/layout_layer_service.py`
- Extract logic from `graph_layout_service.py`

**Steps**

- [ ] Place start in lower portrait layers.
- [ ] Place destination in upper portrait layers.
- [ ] Assign primary route progression vertically.
- [ ] Place branches in adjacent horizontal lanes.
- [ ] Handle cycles and revisits with explicit return lanes.
- [ ] Reserve expanded space around three- and four-way switches.

**Acceptance tests**

- [ ] Simple paths are monotonic in primary vertical progression.
- [ ] Split/rejoin motifs receive separate lanes.
- [ ] Return loops receive a nonoverlapping return lane.

## Task 7.3 — Add switch-port assignment

**Files to add**

- `Tools/LevelGenerator/app/services/switch_port_assignment_service.py`

**Steps**

- [ ] Assign a cardinal or diagonal visual direction to each outgoing edge.
- [ ] Ensure first road segments separate by the minimum angle and distance.
- [ ] Preserve outgoing-edge order in a predictable clockwise representation.
- [ ] Reserve the most readable port for the initial route where appropriate.

**Acceptance tests**

- [ ] Two outgoing roads do not overlap at the switch.
- [ ] Four-way switches use four distinct directions.
- [ ] Outgoing order remains stable after layout.

## Task 7.4 — Build candidate road geometry during placement

**Files to update or split**

- `graph_layout_service.py`
- `road_shape_service.py`
- `road_geometry_validation_service.py`

**Steps**

- [ ] Select horizontal-first or vertical-first bends based on reserved lanes.
- [ ] Detect intersections incrementally.
- [ ] Prefer adding a graph node at intentional intersections instead of allowing implicit crossings.
- [ ] Reserve clearance from nonadjacent nodes and roads.
- [ ] Keep route arrows and switch indicators clear.

## Task 7.5 — Add local layout repair

**Files to add**

- `Tools/LevelGenerator/app/services/layout_repair_service.py`
- `Tools/LevelGenerator/tests/test_layout_repair_service.py`

**Repair operations**

- [ ] Move a node one grid cell.
- [ ] Swap sibling branch lanes.
- [ ] Change one road bend order.
- [ ] Expand vertical spacing.
- [ ] Mirror a local branch.
- [ ] Move a rejoin point.
- [ ] Insert an explicit intersection node where allowed.

**Steps**

- [ ] Rank violations by severity.
- [ ] Try bounded deterministic repairs.
- [ ] Revalidate after each repair.
- [ ] Stop after a configured limit and report attempted repairs.

**Acceptance tests**

- [ ] A known overlapping fixture is repaired.
- [ ] Repair does not change graph connectivity.
- [ ] Same seed and input produce the same repair sequence.

## Task 7.6 — Reorder generation stages

**File to refactor**

- `Tools/LevelGenerator/app/services/level_generation_service.py`

**Target order**

1. Compose or select topology.
2. Validate topology.
3. Solve topology.
4. Analyze strategic decision quality.
5. Reject weak gameplay.
6. Construct layout.
7. Repair layout.
8. Validate visual readability.
9. Search legal runtime timings.
10. Replay final solution.
11. Score final candidate.
12. Add to valid candidate pool.

**Acceptance tests**

- [ ] Strategically weak candidates never enter layout generation.
- [ ] Reports identify the exact stage of rejection.

## Task 7.7 — Add layout-efficiency regression metrics

**Metrics**

- Candidate count entering layout.
- Candidates repaired successfully.
- Geometry rejection counts by code.
- Valid-candidate rate after layout.
- Average repairs per accepted candidate.

**Initial fixed-seed target**

- [ ] A standard regression batch produces the requested accepted count.
- [ ] At least 10% of candidates entering layout become valid final-pool candidates.
- [ ] No single preventable geometry rejection dominates more than 40% of layout failures.

These are engineering health targets, not player-facing difficulty rules.

### Phase 7 exit gate

- [ ] Layout is constructive and repair-capable.
- [ ] Geometry rejection churn is materially reduced on fixed seeds.
- [ ] Accepted layouts remain portrait-safe and readable.

---

# Phase 8 — Select Complete Batches for Diversity and Pacing

## Objective

Stop selecting each level greedily without considering the composition of the full generated set.

## Task 8.1 — Expand candidate signatures

**Files to update**

- `candidate_signature.py`
- `candidate_signature_service.py`

**Signature dimensions**

- Topology structure.
- Decision dependency graph.
- Switch-degree sequence.
- Revisit/state-reversal pattern.
- Failure-outcome distribution.
- Package-phase pattern.
- Layout silhouette.
- Road-direction histogram.
- Solution decision timing pattern.

**Acceptance tests**

- [ ] Mirrored layouts can be recognized as mechanically similar while still retaining visual metadata.
- [ ] Two levels with the same topology but different dependency behavior are distinguishable.

## Task 8.2 — Build a valid candidate pool per requested batch

**Steps**

- [ ] Generate more valid candidates than requested levels.
- [ ] Store complete quality and signature data.
- [ ] Do not immediately reject a valid candidate only because an earlier candidate was selected.
- [ ] Keep bounded memory and deterministic ordering.

## Task 8.3 — Add portfolio selection

**Files to add**

- `Tools/LevelGenerator/app/services/candidate_portfolio_selection_service.py`
- Tests

**Selection objective**

Maximize a weighted combination of:

- Individual candidate quality.
- Difficulty fit.
- Mechanic progression.
- Decision-signature diversity.
- Visual diversity.
- Distance from recent production levels.
- Avoidance of adjacent-level repetition.

**Steps**

- [ ] Start with a deterministic greedy diversity algorithm.
- [ ] Add hard constraints for requested difficulty and level count.
- [ ] Report why each selected candidate was chosen over alternatives.

**Acceptance tests**

- [ ] Selected batch contains the requested count.
- [ ] Selection is deterministic.
- [ ] Duplicate or near-duplicate decision signatures are minimized.

## Task 8.4 — Update campaign pacing

**Files to update**

- `campaign_pacing_service.py`
- `difficulty_curve_service.py`

**Steps**

- [ ] Introduce one mechanic at a time in tutorials/easy levels.
- [ ] Space repeated mechanic patterns apart.
- [ ] Increase dependency and state complexity before tightening timing.
- [ ] Avoid consecutive levels with the same number and type of decisions.
- [ ] Include recovery-oriented levels between highly punitive levels.

### Phase 8 exit gate

- [ ] Batch selection happens after valid candidates are collected.
- [ ] Campaign reports show mechanic and dependency progression.
- [ ] Similarity rejection is no longer the dominant generation failure mode.

---

# Phase 9 — Refactor Generator Services Around the New Pipeline

## Objective

Reduce regression risk by dividing oversized services into clear stages after behavior is stabilized.

## Task 9.1 — Reduce `level_generation_service.py`

**Current size:** approximately 2,186 lines.

**Target responsibilities for the final orchestrator**

- Validate request.
- Resolve presets.
- Request candidate production.
- Request portfolio selection.
- Persist accepted results.
- Build reports.

**Services to extract**

- Candidate seed planning.
- Topology candidate production.
- Layout candidate production.
- Runtime solution verification.
- Final candidate assembly.
- Batch orchestration.

**Acceptance tests**

- [ ] Public CLI behavior remains compatible.
- [ ] Existing generation-service tests are split by stage.

## Task 9.2 — Split unique-solution validation

**Current size:** approximately 1,591 lines.

**Suggested components**

- `solution_state_search.py`
- `solution_equivalence_service.py`
- `failure_outcome_classifier.py`
- `unique_solution_report_builder.py`

**Steps**

- [ ] Separate search from report formatting.
- [ ] Make search limits explicit configuration.
- [ ] Use decision-profile terminology.

## Task 9.3 — Split layout services

**Current large files**

- `graph_layout_service.py`
- `visual_clarity_validation_service.py`
- `layout_readability_validator.py`
- `road_shape_service.py`

**Suggested boundaries**

- Layer assignment.
- Coordinate placement.
- Port assignment.
- Road routing.
- Repair.
- Geometric validation.
- Visual-readability validation.
- Metric reporting.

## Task 9.4 — Replace unstructured dictionaries in stage boundaries

**Steps**

- [ ] Add dataclasses for each stage result.
- [ ] Include `passed`, `stage`, `code`, `details`, and relevant metrics.
- [ ] Keep JSON-report conversion in report-specific code.
- [ ] Add type hints to all public service methods.

### Phase 9 exit gate

- [ ] Main generator orchestration is readable without scrolling through implementation details.
- [ ] Each stage can be unit tested independently.
- [ ] Existing CLI and GUI behavior remains functional.

---

# Phase 10 — Rebuild the Editor Around Explicit Tools and Commands

## Objective

Create a stable interaction architecture before adding visible UX improvements.

## Task 10.1 — Add editor tool modes

**Files to add or update**

- `Tools/LevelEditor/app/models/editor_tool.py`
- `main_window.py`
- `canvas_scene.py`
- `canvas_view.py`

**Modes**

- `SELECT`
- `PLACE_NODE`
- `CONNECT`
- `PLAYTEST`

**Steps**

- [ ] Store the active mode in one controller-owned location.
- [ ] Add mutually exclusive toolbar buttons with icons and text/tooltips.
- [ ] Change cursor and status message by mode.
- [ ] Make Escape return to Select or cancel the current operation.
- [ ] Disable editing gestures during Playtest.

**Acceptance tests**

- [ ] Exactly one primary mode is active.
- [ ] Keyboard shortcuts switch modes.
- [ ] Mode changes clear temporary previews safely.

## Task 10.2 — Add a document controller

**Files to add**

- `Tools/LevelEditor/app/controllers/document_controller.py`
- Tests

**Responsibilities**

- Own the active `LevelDocument` and solution.
- Apply mutations.
- Emit change signals.
- Manage dirty state.
- Coordinate undo/redo.
- Trigger debounced validation.

**Steps**

- [ ] Move graph mutation out of `canvas_scene.py`.
- [ ] Move save-related document changes out of ad hoc UI callbacks.
- [ ] Keep the scene focused on rendering and interaction events.

## Task 10.3 — Add undo/redo with `QUndoStack`

**Files to add**

```text
Tools/LevelEditor/app/commands/
  add_node_command.py
  move_node_command.py
  delete_items_command.py
  add_edge_command.py
  edit_node_command.py
  edit_edge_command.py
  reorder_edges_command.py
  edit_metadata_command.py
  edit_rules_command.py
  edit_solution_command.py
```

**Steps**

- [ ] Add Edit > Undo and Edit > Redo actions.
- [ ] Add standard shortcuts.
- [ ] Ensure drag movement creates one command, not one command per mouse event.
- [ ] Make node deletion restore connected edges and outgoing order on undo.
- [ ] Clear the stack when opening a new file.
- [ ] Mark the saved stack index and derive dirty state from it.

**Acceptance tests**

- [ ] Every supported edit can be undone and redone.
- [ ] Undoing node deletion restores exact edge IDs and order.
- [ ] Dirty state clears after undoing back to the saved state.

## Task 10.4 — Break up `main_window.py`

**Current size:** approximately 1,113 lines.

**Suggested extractions**

- `menu_builder.py`
- `toolbar_builder.py`
- `file_workflow_controller.py`
- `validation_controller.py`
- `playtest_controller.py`
- `production_promotion_controller.py`

**Acceptance tests**

- [ ] Existing open/save/validate workflows still pass.
- [ ] Main window primarily wires components and signals.

### Phase 10 exit gate

- [ ] Explicit editor modes exist.
- [ ] Mutations use commands.
- [ ] Undo/redo works.
- [ ] Canvas no longer directly owns document mutation logic.

---

# Phase 11 — Make Node Placement and Road Creation Intuitive

## Objective

Replace hidden workflows with direct manipulation and visible previews.

## Task 11.1 — Implement click-to-place nodes

**Files to update**

- `piece_palette.py`
- `canvas_scene.py`
- Document controller and add-node command

**Steps**

- [ ] Selecting a palette item activates Place Node mode with that node role.
- [ ] Moving over the canvas shows a ghost node at the candidate position.
- [ ] Clicking places the node at that position.
- [ ] Placement uses grid snapping when enabled.
- [ ] Right-click or Escape cancels placement.
- [ ] Optional repeated placement stays active until canceled.

**Acceptance tests**

- [ ] Node appears at the clicked model coordinate.
- [ ] Repeated additions do not stack at viewport center.
- [ ] Undo removes the placed node.

## Task 11.2 — Add drag-and-drop palette placement

**Steps**

- [ ] Make palette items draggable with node-role MIME data.
- [ ] Accept drops on the canvas.
- [ ] Display a valid/invalid placement preview.
- [ ] Route drops through the same add-node command as click placement.

**Acceptance tests**

- [ ] Drag-and-drop and click placement produce equivalent document state.

## Task 11.3 — Add grid and snapping controls

**Files to update**

- `canvas_scene.py`
- `canvas_view.py`
- Toolbar/settings

**Steps**

- [ ] Add a snap toggle.
- [ ] Add configurable grid size with a safe range.
- [ ] Snap node creation and drag completion, not every paint operation.
- [ ] Show alignment guides to nearby node centers.
- [ ] Add “Snap Selected to Grid.”

**Acceptance tests**

- [ ] Snap-on movement ends at exact grid coordinates.
- [ ] Snap-off preserves free coordinates.
- [ ] Zoom does not change model-space snap size.

## Task 11.4 — Add visible connection handles

**Files to update**

- `node_item.py`
- `canvas_scene.py`
- New `connection_handle_item.py`

**Steps**

- [ ] Show connection handles in Connect mode or on selected nodes.
- [ ] Begin a road drag from a handle.
- [ ] Show a live arrowed road preview.
- [ ] Highlight valid destination nodes.
- [ ] Reject self-loops and duplicate directed edges unless explicitly supported.
- [ ] Create the road on drop through an undoable command.

**Acceptance tests**

- [ ] Dragging source to destination creates one directed edge.
- [ ] Canceling leaves the document unchanged.
- [ ] Duplicate-edge rejection is clear.

## Task 11.5 — Make road-shape choice visible

**Steps**

- [ ] Add horizontal-first and vertical-first options to the Connect toolbar.
- [ ] Keep Tab as a shortcut.
- [ ] Show the current bend choice in the preview.
- [ ] Allow holding a modifier to temporarily swap the bend choice.

## Task 11.6 — Add optional bidirectional-road creation

**Steps**

- [ ] Add a modifier or toolbar option to create both directed edges.
- [ ] Generate unique IDs for both edges.
- [ ] Add both operations as one undoable command.
- [ ] Do not make bidirectional roads the default.

### Phase 11 exit gate

- [ ] Nodes are placed where clicked or dropped.
- [ ] Roads are created by visible drag interaction.
- [ ] Grid snapping behaves as expected.
- [ ] All actions are undoable.

---

# Phase 12 — Make the Property Inspector Fully Editable

## Objective

Allow designers to correct level data without deleting and recreating objects.

## Task 12.1 — Add safe ID rename services

**Files to add**

- `Tools/LevelEditor/app/services/reference_rename_service.py`
- Tests

**Node rename must update**

- Node ID.
- `startNodeID`.
- `packageNodeID`.
- `destinationNodeID`.
- Every edge endpoint.
- Every solution `tapNodeID`.
- Any supported metadata references.

**Edge rename must update**

- Edge ID.
- Every node's `outgoingEdgeIDs`.
- Any supported metadata references.

**Acceptance tests**

- [ ] Rename preserves referential integrity.
- [ ] Duplicate target IDs are rejected before mutation.
- [ ] Undo restores every reference.

## Task 12.2 — Add editable node properties

**Files to update**

- `properties_panel.py`
- Document commands/controller

**Fields**

- Node ID.
- Node role: route, start, package, destination.
- X and Y position.
- Ordered outgoing roads.
- Initial active road.
- Read-only derived switch classification.

**Steps**

- [ ] Replace read-only labels with validated controls.
- [ ] Make role changes update level metadata IDs safely.
- [ ] Show outgoing option number, target node, direction, and road shape.
- [ ] Add “Set as initial route.”
- [ ] Show a warning when outgoing order and initial route would change gameplay.

**Acceptance tests**

- [ ] Editing coordinates moves the canvas node.
- [ ] Changing role updates level metadata.
- [ ] Initial active road is visually reflected.

## Task 12.3 — Add editable edge properties

**Fields**

- Edge ID.
- Source node.
- Destination node.
- Road shape.
- Future availability condition if Phase 17 is implemented.

**Steps**

- [ ] Use node dropdowns rather than raw free text.
- [ ] Prevent duplicate directed edges.
- [ ] Redraw immediately after changes.
- [ ] Preserve outgoing order or ask where the changed edge should be placed.

**Acceptance tests**

- [ ] Road bend changes without delete/recreate.
- [ ] Endpoint edits update the correct outgoing lists.
- [ ] Undo restores original geometry and references.

## Task 12.4 — Add editable level rules

**Fields**

- Schema version display.
- Switch interaction mode.
- Look-ahead seconds.
- Tap cooldown seconds.

**Steps**

- [ ] Put advanced rule fields in a Level Rules dialog or inspector section.
- [ ] Default new levels to `liveLookahead`.
- [ ] Show a migration warning for legacy mode.
- [ ] Validate ranges inline.

## Task 12.5 — Improve canvas annotations

**Steps**

- [ ] Show switch option numbers near outgoing roads.
- [ ] Highlight the initial active road.
- [ ] Show node role icons independent of ID naming.
- [ ] Show warning badges for invalid nodes/edges.
- [ ] Keep labels readable at common zoom levels.

### Phase 12 exit gate

- [ ] Node and edge properties are editable.
- [ ] Renames preserve all references.
- [ ] Switch order and initial route are obvious on the canvas.

---

# Phase 13 — Add Integrated Playtest and Solution Recording

## Objective

Let designers create and verify solutions by playing the level instead of manually entering timestamps and IDs.

## Task 13.1 — Add an editor playtest controller

**Files to add**

- `Tools/LevelEditor/app/controllers/playtest_controller.py`
- `Tools/LevelEditor/app/models/playtest_state.py`
- Tests

**Responsibilities**

- Create a shared-core simulator from the current document.
- Start, pause, resume, reset, and stop.
- Advance using a timer.
- Expose dot position, package state, time, outcome, and eligible switch.
- Record accepted and rejected taps.

**Acceptance tests**

- [ ] Starting playtest does not mutate the authored document.
- [ ] Reset restores initial switch states.
- [ ] Stopping returns to edit mode safely.

## Task 13.2 — Render the simulated dot and active switch

**Files to add or update**

- `canvas_scene.py`
- New playtest overlay items

**Steps**

- [ ] Draw a distinct playtest dot.
- [ ] Interpolate along the same road geometry represented by the model.
- [ ] Highlight the active switch using the same conceptual states as the Swift UI.
- [ ] Show package collected and outcome overlays.
- [ ] Keep authored nodes and roads noneditable during playtest.

## Task 13.3 — Route canvas clicks to simulator taps

**Steps**

- [ ] In Playtest mode, clicking a switch sends a tap action to the simulator.
- [ ] Record whether the tap was accepted.
- [ ] Show a short rejected reason in the status area.
- [ ] Do not record rejected taps as solution actions.

## Task 13.4 — Record a solution from playtest

**Steps**

- [ ] Record accepted tap timestamp and node ID.
- [ ] On successful completion, enable “Use Run as Solution.”
- [ ] Build `maxTaps` from accepted actions.
- [ ] Set expected outcome and time-limit requirement correctly.
- [ ] Replace placeholder solution through an undoable solution command.
- [ ] Validate the recorded solution immediately.

**Acceptance tests**

- [ ] A successful run produces a replayable sidecar.
- [ ] A failed run cannot replace the canonical solution without an explicit advanced override.
- [ ] Replaying the recorded solution completes identically.

## Task 13.5 — Improve the solution panel

**Files to update**

- `solution_panel.py`

**Steps**

- [ ] Make recorded playtest the primary workflow.
- [ ] Replace raw tap-node text entry with a switch dropdown.
- [ ] Keep timestamp editing as an advanced option.
- [ ] Show accepted-window bounds beside each action.
- [ ] Add “Replay Solution.”
- [ ] Add “Find Verified Solution” using the runtime solution search.
- [ ] Add “Analyze Early/Late Margin.”

## Task 13.6 — Add timeline replay and scrubbing

**Steps**

- [ ] Store or recompute simulator snapshots at deterministic intervals/events.
- [ ] Add play, pause, step-event, and reset controls.
- [ ] Allow timeline scrubbing by replaying from initial state to the selected time.
- [ ] Show switch states at the selected time.

**Acceptance tests**

- [ ] Scrubbing to the same time produces the same state.
- [ ] Timeline does not modify the solution unless an explicit edit is made.

### Phase 13 exit gate

- [ ] Levels can be played in the editor.
- [ ] Successful runs become verified solutions.
- [ ] Designers no longer need to manually type normal solution scripts.

---

# Phase 14 — Add Live Validation and Puzzle Analysis to the Editor

## Objective

Surface errors and weak puzzle design during editing instead of after save or generation.

## Task 14.1 — Debounce automatic validation

**Files to update**

- `level_validation_service.py`
- `solution_validation_service.py`
- New validation controller

**Steps**

- [ ] Run lightweight validation after a short idle debounce.
- [ ] Cancel stale pending validation when a new edit occurs.
- [ ] Keep expensive Swift tests manual.
- [ ] Separate errors, warnings, and design suggestions.

## Task 14.2 — Add validation overlays

**Steps**

- [ ] Mark invalid nodes and edges on the canvas.
- [ ] Clicking a validation item selects and centers the affected object.
- [ ] Show overlap and implicit-intersection areas visually.
- [ ] Clear overlays when the issue is resolved.

## Task 14.3 — Add a Puzzle Analysis panel

**Files to add**

- `Tools/LevelEditor/app/ui/puzzle_analysis_panel.py`
- Integration with shared/generator analysis services

**Display**

- Decision count.
- Unique switches used.
- Repeated visits.
- State changes on revisit.
- Independent-decision ratio.
- Equivalent solutions.
- Failure outcomes.
- Activation-window lengths.
- Decision spacing.
- Estimated difficulty.
- Legacy front-load diagnostic.

**Steps**

- [ ] Run topology analysis on graph changes.
- [ ] Run runtime timing analysis when layout/rules/solution change.
- [ ] Explain recommendations in plain language.
- [ ] Link recommendations to affected nodes.

## Task 14.4 — Add one-click automated checks

**Actions**

- [ ] Validate structure.
- [ ] Find verified solution.
- [ ] Replay saved solution.
- [ ] Test all taps at `0.0` in legacy diagnostic mode.
- [ ] Analyze decision quality.
- [ ] Run Swift parity tests.

## Task 14.5 — Integrate generated candidates with the editor

**Steps**

- [ ] Add “Open in Level Editor” to the generator GUI or report workflow.
- [ ] Open candidate level and solution together.
- [ ] Import candidate quality data when available.
- [ ] Allow saving to a draft directory before promotion.
- [ ] Keep production overwrite confirmation.

### Phase 14 exit gate

- [ ] Validation is visible while designing.
- [ ] Puzzle-quality analysis is available in the editor.
- [ ] Generated candidates can be inspected and corrected without manual file hunting.

---

# Phase 15 — Improve Editor Quality-of-Life and Safety

## Objective

Finish the editor workflow so it is comfortable for repeated production use.

## Task 15.1 — Add selection and alignment tools

- [ ] Multi-select with Shift.
- [ ] Marquee selection.
- [ ] Align left/right/top/bottom.
- [ ] Align centers.
- [ ] Distribute horizontally/vertically.
- [ ] Nudge by keyboard.
- [ ] Larger nudge with modifier.

## Task 15.2 — Add viewport controls

- [ ] Fit level to view.
- [ ] Zoom to selection.
- [ ] Reset zoom.
- [ ] Pan with middle mouse or space-drag.
- [ ] Preserve viewport across non-layout property edits.

## Task 15.3 — Add autosave recovery

**Steps**

- [ ] Periodically write a recovery file for dirty documents.
- [ ] Never overwrite the source file automatically.
- [ ] Offer recovery after an unclean shutdown.
- [ ] Delete recovery data after a successful save/close.

## Task 15.4 — Add keyboard shortcut help

- [ ] Add Help > Keyboard Shortcuts.
- [ ] Show mode shortcuts in tooltips.
- [ ] Include Connect shape toggle and cancel behavior.

## Task 15.5 — Add manual usability test script

**File to add**

- `Tools/LevelEditor/docs/manual_usability_test.md`

**Scenario**

A tester unfamiliar with the hidden old workflow must be able to:

1. Create a new live-routing level.
2. Place start, package, destination, route nodes, and switches.
3. Connect roads.
4. Reorder switch options.
5. Set initial roads.
6. Playtest.
7. Save the successful run as the solution.
8. Resolve validation issues.
9. Save and reopen the level.
10. Run Swift tests.

**Acceptance condition**

- [ ] The tester completes the scenario without external verbal instruction.

---

# Phase 16 — Migrate Existing Production Levels

## Objective

Move the shipped corpus to the corrected interaction model without breaking IDs, progression, or saved-player references.

## Task 16.1 — Add a migration analyzer

**File to add**

- `Tools/LevelGenerator/migrate_levels_to_live_routing.py`

**For each level, report**

- Current schema/rules.
- Current solution result.
- Live-routing solution existence.
- Required window sizes.
- Repeated decision behavior.
- Decision-quality result for its campaign difficulty.
- Recommendation: automatic conversion, regenerate, or manual redesign.

## Task 16.2 — Define migration categories

- **Automatic conversion:** Existing topology works under live routing and meets quality rules.
- **Timing/layout adjustment:** Topology works, but road lengths or window settings need adjustment.
- **Manual redesign:** Topology is too trivial or cannot create legal windows.
- **Regeneration:** Level can be safely replaced while retaining stable level ID and campaign position.

## Task 16.3 — Preserve stable production identity

**Rules**

- [ ] Keep `level_###` IDs stable.
- [ ] Keep progression order stable unless a separate progression migration is intentionally implemented.
- [ ] Regenerate names only when desired and reviewed.
- [ ] Update matching solution sidecars atomically.
- [ ] Rebuild manifest after all writes.

## Task 16.4 — Migrate tutorial levels deliberately

**Steps**

- [ ] First tutorial introduces automatic movement without a switch.
- [ ] Next tutorial shows one highlighted active switch.
- [ ] Next tutorial introduces two rotations or a later second decision.
- [ ] Do not introduce tight timing before visual language is established.
- [ ] Add instructional text or visual affordances if the app currently lacks them.

## Task 16.5 — Redesign or regenerate trivial independent chains

**Steps**

- [ ] Use the corpus analyzer to identify levels whose only challenge was early global configuration.
- [ ] Add meaningful sequencing, recovery, revisit, or phase behavior.
- [ ] Keep each campaign section mechanically varied.
- [ ] Human-playtest every changed production level.

## Task 16.6 — Verify the complete corpus

**Required checks**

- [ ] JSON structural validation.
- [ ] Python solution replay.
- [ ] Swift solution replay.
- [ ] Decision-profile difficulty fit.
- [ ] Visual-readability validation.
- [ ] Editor open/save round trip on a representative sample and automated model round trip on all files.
- [ ] Manifest synchronization.

### Phase 16 exit gate

- [ ] Every shipped production level has explicit version 2 live-routing rules.
- [ ] Every shipped sidecar replays in Swift.
- [ ] No shipped nonzero-tap level accepts a complete solution at time `0.0`.
- [ ] Campaign difficulty and mechanic progression are reviewed.

---

# Phase 17 — Add a Small Stateful Mechanic for Long-Term Variety

## Objective

Expand the design space after the core interaction model is stable. This phase is required for the full long-term generator improvement, but must not begin before runtime parity and editor playtesting are reliable.

The recommended first stateful mechanic is **edge availability by package state**.

## Task 17.1 — Extend the road domain model

**Suggested JSON**

```json
{
  "id": "edge_gate",
  "fromNodeID": "switch_gate",
  "toNodeID": "destination",
  "roadShape": "horizontalFirst",
  "availability": "afterPackage"
}
```

**Availability values**

- `always`
- `beforePackage`
- `afterPackage`

**Files to update**

- Swift `RouteEdge`
- Shared Python `RouteEdge`
- Editor edge model/inspector
- Generator recipe/motif edge models
- JSON documentation

**Acceptance tests**

- [ ] Missing availability decodes as `always`.
- [ ] All values round-trip.
- [ ] Unknown values produce a validation failure.

## Task 17.2 — Enforce road availability in Swift

**Steps**

- [ ] Filter usable outgoing edges by package state.
- [ ] Rotate switches only through currently usable edges.
- [ ] Normalize an unavailable active edge deterministically before departure.
- [ ] Update visual arrows when availability changes.
- [ ] Prevent a node from becoming an unintended dead end unless authored and validated.

## Task 17.3 — Add exact Python parity behavior

- [ ] Update graph queries.
- [ ] Update simulator.
- [ ] Update topology solver state transitions.
- [ ] Add shared fixtures.
- [ ] Compare Swift/Python traces.

## Task 17.4 — Add editor controls and visualization

- [ ] Edge availability dropdown.
- [ ] Distinct preview for currently unavailable roads during playtest.
- [ ] Validation for impossible package gates.
- [ ] Tooltip explaining the condition.

## Task 17.5 — Add package-state motifs

- [ ] Road opens after package.
- [ ] Shortcut closes after package.
- [ ] Return route changes after package.
- [ ] Package collection changes the correct state of a revisited switch.

## Task 17.6 — Update decision analysis

- [ ] Count true before/after-package phase transitions.
- [ ] Require measured state-dependent route changes before awarding package-gate quality.
- [ ] Detect impossible or irrelevant availability conditions.

### Phase 17 exit gate

- [ ] Conditional roads work identically in Swift, generator, simulator, and editor.
- [ ] Package-gate levels represent actual state changes, not only labels.

---

# Phase 18 — Continuous Integration and Release Gates

## Objective

Prevent future changes from reintroducing runtime mismatch, weak levels, or editor regressions.

## Task 18.1 — Add Python CI

**Checks**

- [ ] Shared core tests.
- [ ] Generator tests.
- [ ] Editor tests with a headless Qt platform.
- [ ] Root combined collection test.
- [ ] Deterministic generator smoke test.
- [ ] Corpus structural validation.

## Task 18.2 — Add macOS Swift CI

**Checks**

- [ ] Domain and RouteEngine tests.
- [ ] Shared runtime parity fixtures.
- [ ] Production level solvability tests.
- [ ] Selected UI component tests.

Use a pinned supported Xcode and simulator destination. Keep the local command synchronized with CI.

## Task 18.3 — Add fixed-seed generator regression suites

**Suites**

- Tutorial fixed seeds.
- Easy fixed seeds.
- Medium fixed seeds.
- Hard fixed seeds.
- Expert fixed seeds.
- Mixed 30-level campaign.
- Revisit-heavy batch.
- Three-/four-way switch batch.
- Conditional-road batch after Phase 17.

**Assertions**

- [ ] Requested accepted count is produced.
- [ ] No accepted action is rejected during replay.
- [ ] Quality thresholds pass.
- [ ] Deterministic output hashes match unless intentionally updated.
- [ ] Rejection-code distribution remains within broad health limits.

## Task 18.4 — Add production-content gates

**Checks**

- [ ] Every level has a sidecar.
- [ ] Every sidecar level ID matches.
- [ ] Every solution completes in Swift.
- [ ] Every level is in the manifest exactly once.
- [ ] No duplicate node/edge IDs.
- [ ] No legacy-global production rules remain after migration.
- [ ] No debug candidate directories are in app resources.

## Task 18.5 — Add editor smoke tests

Automate where practical:

- [ ] New level creation.
- [ ] Node placement command.
- [ ] Edge creation command.
- [ ] Undo/redo.
- [ ] Property edit.
- [ ] Save/reopen.
- [ ] Playtest recorded solution.
- [ ] Validation focus navigation.

## Task 18.6 — Add a release checklist

**File to add**

- `docs/release/level_system_release_checklist.md`

**Required signoffs**

- Generator checks passed.
- Editor checks passed.
- Swift parity passed.
- Production corpus passed.
- Human playtest sample passed.
- Reports reviewed.
- Manifest synchronized.

### Phase 18 exit gate

- [ ] CI blocks merges on any required failure.
- [ ] One documented local command reproduces release checks where platform support permits.

---

# Phase 19 — Documentation and Maintenance

## Objective

Make the corrected system maintainable by developers who did not implement it.

## Task 19.1 — Update architecture documentation

**Files to add**

- `docs/architecture/level_runtime.md`
- `docs/architecture/generator_pipeline.md`
- `docs/architecture/editor_architecture.md`
- `docs/architecture/runtime_parity.md`

## Task 19.2 — Document rejection and validation codes

**File to add**

- `docs/reference/level_validation_and_rejection_codes.md`

For every code include:

- Stage.
- Meaning.
- Typical cause.
- How to fix it.
- Whether it blocks production.

## Task 19.3 — Add generator tuning guidance

**File to add**

- `Tools/LevelGenerator/docs/difficulty_and_quality_tuning.md`

Explain:

- Decision thresholds.
- Timing windows.
- Layout profiles.
- Candidate pool sizing.
- Diversity weights.
- How to update golden seeds safely.

## Task 19.4 — Add editor user guide

**File to add**

- `Tools/LevelEditor/docs/user_guide.md`

Include screenshots after implementation for:

- Placing nodes.
- Connecting roads.
- Setting switch order.
- Setting initial route.
- Playtesting.
- Recording a solution.
- Resolving validation issues.
- Promoting a draft.

## Task 19.5 — Remove deprecated compatibility code

Only after production migration and stable releases:

- [ ] Remove deprecated abstract tap names.
- [ ] Remove duplicate Python models.
- [ ] Remove legacy hidden editor workflows that no longer add value.
- [ ] Decide whether `legacyGlobal` remains supported for archival files or is moved to a migration-only decoder.
- [ ] Remove unused legacy generator mode only after equivalent coverage exists.

---

# 20. Recommended Implementation Order

Do not parallelize tasks that change the same behavior contract. Use the sequence below.

1. Phase 0 — Baseline and test reliability.
2. Phase 1 — Versioned rules and written contract.
3. Phase 2 — Swift runtime behavior.
4. Phase 3 — Shared Python core and parity simulator.
5. Phase 4 — Topology/runtime solution separation.
6. Phase 5 — Decision-quality analysis.
7. Phase 10 — Editor command/mode foundation can begin after shared models stabilize.
8. Phase 6 — Motif generation.
9. Phase 7 — Constructive layout and repair.
10. Phase 8 — Portfolio selection and pacing.
11. Phase 9 — Generator service refactoring.
12. Phases 11–15 — Editor direct manipulation, inspector, playtest, validation, quality-of-life.
13. Phase 16 — Production level migration.
14. Phase 17 — Conditional-road mechanic.
15. Phase 18 — Final CI/release enforcement.
16. Phase 19 — Cleanup and final documentation.

Safe parallel work after Phase 3:

- Generator decision analysis and editor command architecture may proceed in parallel.
- Layout work and editor inspector work may proceed in parallel.
- Documentation may accompany every phase.

Do not begin production migration before Swift/Python parity and editor playtest recording are reliable.

---

# 21. Pull Request Breakdown for Entry-Level Contributors

The following is a suggested issue/PR sequence. Each item should be independently reviewable and should include tests.

## Foundation PRs

- [ ] **PR-001:** Add root Python test runner.
- [ ] **PR-002:** Fix generator/editor test package collision.
- [ ] **PR-003:** Add corpus-analysis command and baseline report.
- [ ] **PR-004:** Add shared parity fixture directory and no-switch fixture.
- [ ] **PR-005:** Add remaining early/in-window/late switch fixtures.
- [ ] **PR-006:** Add Swift `LevelRules` types and legacy decode tests.
- [ ] **PR-007:** Add shared Python `LevelRules` model and tests.
- [ ] **PR-008:** Write switch interaction contract and JSON docs.

## Swift runtime PRs

- [ ] **PR-009:** Add structured switch-tap result.
- [ ] **PR-010:** Add basic upcoming-switch query for a straight approach.
- [ ] **PR-011:** Extend upcoming-switch query through route-node chains.
- [ ] **PR-012:** Add cycle safety and boundary tests.
- [ ] **PR-013:** Enforce live eligibility in `RouteEngine`.
- [ ] **PR-014:** Add tap cooldown behavior.
- [ ] **PR-015:** Expose eligible switch state to `GameplayScreen`.
- [ ] **PR-016:** Add eligible/inactive switch visuals and accessibility.
- [ ] **PR-017:** Update Swift solution replay diagnostics.

## Shared Python/parity PRs

- [ ] **PR-018:** Scaffold `TinyRoutesCore` package.
- [ ] **PR-019:** Move shared level models with compatibility imports.
- [ ] **PR-020:** Move shared solution models with compatibility imports.
- [ ] **PR-021:** Add graph index and ordered outgoing query.
- [ ] **PR-022:** Add Python runtime-state model.
- [ ] **PR-023:** Add Python switch eligibility for straight approach.
- [ ] **PR-024:** Add chained-node and cycle eligibility behavior.
- [ ] **PR-025:** Add event-driven movement without taps.
- [ ] **PR-026:** Add simulator tap handling and traces.
- [ ] **PR-027:** Convert generator simulator service to the shared simulator.
- [ ] **PR-028:** Add Swift/Python normalized parity comparison.

## Solver and quality PRs

- [ ] **PR-029:** Rename abstract taps to decisions with aliases.
- [ ] **PR-030:** Extract topology solver wrapper.
- [ ] **PR-031:** Add revisit-state analysis.
- [ ] **PR-032:** Add runtime activation-window extraction.
- [ ] **PR-033:** Add legal timestamp scheduler for one-tap windows.
- [ ] **PR-034:** Add multi-tap window scheduler.
- [ ] **PR-035:** Build sidecars only from verified runtime solutions.
- [ ] **PR-036:** Add decision-profile model.
- [ ] **PR-037:** Add independent-decision analysis.
- [ ] **PR-038:** Add failure-outcome and equivalent-choice analysis.
- [ ] **PR-039:** Add timing/spacing metrics.
- [ ] **PR-040:** Add difficulty thresholds.
- [ ] **PR-041:** Remove tag-only quality bonuses.
- [ ] **PR-042:** Add decision-profile report output.

## Topology and layout PRs

- [ ] **PR-043:** Add motif base types and registry.
- [ ] **PR-044:** Convert straight and binary-choice motifs.
- [ ] **PR-045:** Add detour and dead-end motifs.
- [ ] **PR-046:** Add split/rejoin and package-branch motifs.
- [ ] **PR-047:** Add revisit and return-loop motifs.
- [ ] **PR-048:** Add motif composer with ID remapping.
- [ ] **PR-049:** Add dependency composition constraints.
- [ ] **PR-050:** Add layout constraint/result models.
- [ ] **PR-051:** Add vertical layer assignment.
- [ ] **PR-052:** Add branch lane assignment.
- [ ] **PR-053:** Add switch-port assignment.
- [ ] **PR-054:** Add incremental road routing.
- [ ] **PR-055:** Add one-cell node-move repair.
- [ ] **PR-056:** Add bend-swap and branch-lane repair.
- [ ] **PR-057:** Reorder generator validation stages.
- [ ] **PR-058:** Add layout efficiency metrics.
- [ ] **PR-059:** Expand candidate decision signatures.
- [ ] **PR-060:** Add valid candidate pool.
- [ ] **PR-061:** Add deterministic portfolio selection.

## Editor foundation PRs

- [ ] **PR-062:** Add editor tool-mode enum and toolbar actions.
- [ ] **PR-063:** Add document controller and dirty-state signal.
- [ ] **PR-064:** Add undo stack and add-node command.
- [ ] **PR-065:** Add move-node command.
- [ ] **PR-066:** Add add-edge command.
- [ ] **PR-067:** Add delete-items command with restoration tests.
- [ ] **PR-068:** Move canvas mutations through controller.
- [ ] **PR-069:** Add click-to-place ghost preview.
- [ ] **PR-070:** Add drag-and-drop palette placement.
- [ ] **PR-071:** Add grid snap toggle.
- [ ] **PR-072:** Add visible connection handles.
- [ ] **PR-073:** Add drag-to-connect preview.
- [ ] **PR-074:** Add visible road-shape selector.
- [ ] **PR-075:** Add optional bidirectional connect action.

## Editor inspector and playtest PRs

- [ ] **PR-076:** Add safe node-reference rename service.
- [ ] **PR-077:** Add safe edge-reference rename service.
- [ ] **PR-078:** Make node coordinates and role editable.
- [ ] **PR-079:** Make outgoing order and initial edge editable.
- [ ] **PR-080:** Make edge endpoints and shape editable.
- [ ] **PR-081:** Add level-rules editor.
- [ ] **PR-082:** Add switch-option annotations to canvas.
- [ ] **PR-083:** Add playtest controller start/reset behavior.
- [ ] **PR-084:** Render simulator dot and eligible switch.
- [ ] **PR-085:** Route playtest clicks to simulator taps.
- [ ] **PR-086:** Record accepted actions.
- [ ] **PR-087:** Add “Use Run as Solution.”
- [ ] **PR-088:** Add solution replay controls.
- [ ] **PR-089:** Replace raw tap-node entry with dropdown.
- [ ] **PR-090:** Add automatic/debounced validation.
- [ ] **PR-091:** Add canvas validation overlays.
- [ ] **PR-092:** Add Puzzle Analysis panel.
- [ ] **PR-093:** Add generator candidate open-in-editor workflow.

## Migration and release PRs

- [ ] **PR-094:** Add live-routing migration analyzer.
- [ ] **PR-095:** Migrate tutorial levels.
- [ ] **PR-096:** Migrate easy levels.
- [ ] **PR-097:** Migrate medium levels.
- [ ] **PR-098:** Migrate hard/expert levels.
- [ ] **PR-099:** Rebuild and verify manifest/sidecars.
- [ ] **PR-100:** Add Python CI.
- [ ] **PR-101:** Add macOS Swift parity CI.
- [ ] **PR-102:** Add fixed-seed generator regression CI.
- [ ] **PR-103:** Add production-content release gate.
- [ ] **PR-104:** Add editor manual usability guide and final architecture docs.

Phase 17 conditional-road work should be issued as a separate labeled epic after PR-104 or after the core system is stable enough to support it safely.

---

# 22. Required Test Matrix

## 22.1 Swift unit tests

- Level-rule decoding and encoding.
- Legacy defaults.
- Switch eligibility lookup.
- Eligibility boundaries.
- Tap result reasons.
- Cooldown.
- Rotation order.
- Repeated visits.
- Package order.
- Dead ends and timeouts.
- UI active/inactive state.

## 22.2 Python shared-core tests

- Model round trips.
- Unknown-field preservation.
- Graph indexing and validation.
- Eligibility parity.
- Simulator movement.
- Accepted/rejected taps.
- Trace determinism.
- Safety limits.

## 22.3 Generator tests

- Topology solver.
- Runtime timestamp search.
- Decision profile.
- Difficulty thresholds.
- Motif validation/composition.
- Layout construction and repair.
- Candidate signature and portfolio selection.
- Sidecar replay.
- Report schema.
- Determinism.

## 22.4 Editor tests

- Tool mode transitions.
- Add/move/delete/connect commands.
- Undo/redo.
- Reference-safe rename.
- Inspector edits.
- Grid snapping.
- Playtest lifecycle.
- Solution recording and replay.
- Debounced validation.
- File round trip.

## 22.5 Integration tests

- Generator output opens in editor.
- Editor-recorded solution replays in Python.
- Editor-recorded solution replays in Swift.
- Generator sidecar replays in editor.
- Migrated production corpus passes all gates.

---

# 23. Final Verification Commands

Exact commands may change when root scripts are implemented, but the repository must end with a documented equivalent of the following:

```bash
# All Python tests in one invocation
python -m pytest \
  Tools/TinyRoutesCore/tests \
  Tools/LevelGenerator/tests \
  Tools/LevelEditor/tests

# Deterministic generator smoke and regression checks
python Tools/LevelGenerator/run_all_generator_checks.py
python Tools/LevelGenerator/stress_test_generation.py --preset fixed-regression

# Validate production level and sidecar corpus
python Tools/LevelGenerator/validate_generated_levels.py --all-production
python Tools/LevelGenerator/analyze_level_corpus.py --fail-on-quality-regression

# Swift tests on the supported simulator
xcodebuild test \
  -project TinyRoutes.xcodeproj \
  -scheme TinyRoutes \
  -destination 'platform=iOS Simulator,name=iPhone 16,OS=18.5'

# One final wrapper
python scripts/run_all_checks.py --include-swift --production-content
```

The final wrapper must:

- Return zero only when every required gate passes.
- Print a concise summary grouped by runtime, generator, editor, and content.
- Preserve detailed logs for failures.

---

# 24. Final Manual Acceptance Scenarios

Automated tests are necessary but not sufficient for puzzle quality and editor usability.

## Scenario A — First-time editor user

- [ ] Create a new level without reading source code.
- [ ] Place five nodes at intended positions.
- [ ] Connect directed roads.
- [ ] Change one road bend.
- [ ] Reorder a switch.
- [ ] Set its initial route.
- [ ] Undo and redo the edits.
- [ ] Play the level.
- [ ] Save the successful run as a solution.
- [ ] Fix a validation warning.
- [ ] Save and reopen with identical state.

## Scenario B — Generated candidate review

- [ ] Generate a medium candidate batch.
- [ ] Open a selected candidate in the editor.
- [ ] Review its decision profile.
- [ ] Replay the generated solution.
- [ ] Make a layout adjustment.
- [ ] Confirm the solution and timing remain valid or are clearly invalidated.
- [ ] Record a replacement solution if needed.
- [ ] Run Swift parity.

## Scenario C — Live-routing gameplay

- [ ] Tap a downstream inactive switch and confirm no score increment.
- [ ] Watch the upcoming switch become visually active.
- [ ] Tap it successfully.
- [ ] Use multiple taps on a three-way switch.
- [ ] Miss a decision and receive an understandable consequence.
- [ ] Complete a revisit level that requires changing a switch on the second visit.

## Scenario D — Campaign generation

- [ ] Generate a fixed-seed 30-level campaign.
- [ ] Confirm all requested levels are produced.
- [ ] Confirm mechanic and decision profiles vary.
- [ ] Confirm no nonzero-tap solution can be moved entirely to time zero.
- [ ] Confirm all sidecars replay in Swift.
- [ ] Human-review a representative sample from every difficulty band.

---

# 25. Risks and Mitigations

## Risk: Gameplay change invalidates existing levels

**Mitigation**

- Preserve legacy decoding.
- Add migration analysis before rewriting production files.
- Keep stable level IDs.
- Migrate by difficulty group with full replay tests.

## Risk: Swift and Python diverge again

**Mitigation**

- Maintain a written normative contract.
- Execute shared fixtures in both languages.
- Compare normalized traces.
- Require parity tests for every behavior change.

## Risk: Live windows feel too difficult

**Mitigation**

- Use generous initial windows.
- Highlight only the active switch.
- Increase complexity before reducing time.
- Store window thresholds in difficulty presets and level rules.
- Human-playtest before tuning tighter.

## Risk: Generator refactor becomes too large

**Mitigation**

- Add compatibility wrappers.
- Separate behavior changes from structural refactors.
- Keep deterministic golden seeds.
- Extract one stage at a time.

## Risk: Editor command migration introduces data loss

**Mitigation**

- Preserve unknown JSON fields.
- Add command-specific restoration tests.
- Add save/reopen round-trip tests.
- Keep source files untouched until explicit save.
- Add recovery autosaves.

## Risk: Quality score is overfit to hand-authored fixtures

**Mitigation**

- Use multiple fixed-seed batches.
- Test adversarial trivial graphs.
- Keep raw metrics visible in reports.
- Require human playtest samples.
- Tune thresholds separately from core metric calculations.

---

# 26. Definition of Done

The generator and editor improvement project is complete when all of the following are true:

- [ ] Production gameplay uses documented live look-ahead switch control.
- [ ] Swift and Python runtime-parity suites pass.
- [ ] Generated solution actions are legal under the real interaction policy.
- [ ] Generator quality is based on measured decision structure and runtime behavior.
- [ ] Medium and harder levels cannot pass solely as independent one-tap switch chains.
- [ ] Generator layout uses constructive placement and bounded repair.
- [ ] Candidate batches are selected for campaign-level diversity.
- [ ] The level editor has explicit Select, Place, Connect, and Playtest modes.
- [ ] The editor supports direct node/road manipulation, editable properties, grid snapping, and undo/redo.
- [ ] The editor records and replays solutions through the shared simulator.
- [ ] Live validation and decision analysis are visible in the editor.
- [ ] All production levels are migrated and pass Python and Swift replay.
- [ ] All Python suites run together and pass.
- [ ] Required Swift tests pass.
- [ ] CI and release gates prevent invalid levels or runtime mismatches from shipping.
- [ ] Architecture, user, tuning, and release documentation is current.

When these conditions pass, the system has an enforceable basis for generating functional levels, detecting strategically weak levels before acceptance, and authoring/debugging levels through an intuitive tool rather than fragile manual JSON and hidden interactions.
