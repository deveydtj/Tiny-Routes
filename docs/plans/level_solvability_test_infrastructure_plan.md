# Tiny Routes Level Solvability Test Infrastructure Plan

## Purpose

Create a reliable, engineer-friendly test infrastructure that proves every production `level_###.json` file is structurally valid, playable through the real `RouteEngine`, and completable within its time limit and tap budget.

This plan intentionally starts from the current Tiny Routes architecture instead of redesigning the entire level format up front. The current level JSON is already usable. The missing piece is a stronger validation and simulation layer that turns each level file into a provable gameplay contract.

## Recommended Direction

Use the following decisions as the baseline implementation strategy:

1. **Every shipped production level must have at least one proven winning solution.**
2. **Keep the current level JSON format for now.** Add validation and solution sidecar files before changing the core schema.
3. **Use the real `RouteEngine` for solvability proof.** Do not create a separate fake gameplay simulator that can drift away from game behavior.
4. **Support hand-authored solution scripts first.** Add automated solver/search behavior later.
5. **Allow dead ends only when a valid winning path still exists.** Dead ends are valid puzzle mechanics, not automatic level failures.
6. **Start with engine-solvable tests, then add human-playability guardrails.**
7. **Make solution scripts high-level enough that test engineers do not need to calculate exact timings by hand.**

## Current Repository Context

Relevant current files:

```text
TinyRoutes/Domain/LevelData.swift
TinyRoutes/Domain/RouteGraph.swift
TinyRoutes/Domain/RouteNode.swift
TinyRoutes/Domain/RouteEdge.swift
TinyRoutes/Gameplay/RouteEngine.swift
TinyRoutes/Infrastructure/LevelRepository.swift
TinyRoutes/Resources/Levels/level_001.json ... level_010.json
TinyRoutesTests/RouteEngineTests.swift
TinyRoutesTests/LevelRepositoryTests.swift
```

Current level shape:

```swift
struct LevelData: Identifiable, Codable {
    let id: String
    var name: String
    var graph: RouteGraph
    var startNodeID: String
    var packageNodeID: String
    var destinationNodeID: String
    var timeLimitSeconds: Int
    var parTaps: Int
}
```

Current engine behavior already supports:

- Building a runtime graph from `LevelData`
- Starting automatic dot movement
- Updating movement by `deltaTime`
- Rotating switch nodes
- Counting taps
- Collecting package
- Completing at destination
- Failing on dead end
- Failing on expired time
- Failing when destination is reached before package

This means the new infrastructure should primarily add:

- Level-data validation
- Solution script loading
- Deterministic route simulation helpers
- Production-level test coverage
- Human-playability checks
- Optional future automated solver support

---

# Target Architecture

## New Test/Support Files

Recommended layout:

```text
TinyRoutesTests/
  LevelValidationTests.swift
  LevelSolvabilityTests.swift
  LevelSolutionScriptTests.swift
  Support/
    LevelValidator.swift
    LevelValidationIssue.swift
    LevelSolutionScript.swift
    LevelSolutionRepository.swift
    LevelSimulationHarness.swift
    LevelSolvabilityResult.swift
    LevelHumanPlayabilityRules.swift

TinyRoutesTests/Resources/
  LevelSolutions/
    level_001.solution.json
    level_002.solution.json
    level_003.solution.json
    ...
```

If Xcode project file setup makes `TinyRoutesTests/Resources` difficult at first, place solution JSON files in a test-readable folder and add a small repository abstraction so the path can be changed later without touching tests.

## Validation Layers

Use layered validation so failures are easier for entry-level engineers to understand.

### Layer 1: Decode Validation

Goal: prove every level file can decode into `LevelData`.

Checks:

- JSON is valid.
- File name matches level ID.
- Required properties exist.
- `timeLimitSeconds` is positive.
- `parTaps` is zero or positive.

Failure example:

```text
level_004.json failed decode validation: missing destinationNodeID
```

### Layer 2: Graph Structure Validation

Goal: prove the level graph is internally consistent before gameplay simulation.

Checks:

- Node IDs are unique.
- Edge IDs are unique.
- `startNodeID` exists.
- `packageNodeID` exists.
- `destinationNodeID` exists.
- Every edge `fromNodeID` exists.
- Every edge `toNodeID` exists.
- Every node `outgoingEdgeIDs` list matches the real edges that originate from that node.
- No duplicate IDs inside a node's `outgoingEdgeIDs`.
- No edge has the same `fromNodeID` and `toNodeID` unless intentionally allowed later.
- No zero-length edge unless intentionally allowed for a special mechanic.

Failure example:

```text
level_006 graph validation failed: node switch_a lists outgoing edge e_missing, but no edge with that ID exists.
```

### Layer 3: Route Intent Validation

Goal: prove the level has the required puzzle pieces.

Checks:

- Start, package, and destination are not accidentally all the same node unless explicitly allowed.
- Package is reachable from start by at least one graph path ignoring switch state.
- Destination is reachable from package by at least one graph path ignoring switch state.
- At least one path from start to destination passes through the package.
- Dead ends are allowed, but they must not be the only reachable outcome.
- Unreachable nodes should be warnings at first, then errors later.

Failure example:

```text
level_009 intent validation failed: destination is not reachable from package by any directed path.
```

### Layer 4: Engine Build Validation

Goal: prove the real `RouteEngine` accepts the level.

Checks:

- `RouteEngine.buildGraph(from:)` succeeds.
- Runtime graph has same node count as source graph.
- Runtime graph has same edge count as source graph.
- Initial dot state is valid.
- Initial timer matches `timeLimitSeconds`.

Failure example:

```text
level_003 engine build validation failed: RouteEngine threw missingStartNode(id: "start")
```

### Layer 5: Scripted Solvability Validation

Goal: prove the level can be completed using the real `RouteEngine`.

Checks:

- Matching solution script exists for every production level.
- Script loads and decodes.
- Script references valid node IDs.
- Script only taps switch nodes.
- Script completes the level.
- Completion happens before time expires.
- Tap count is less than or equal to script max taps.
- Tap count is less than or equal to level `parTaps` when the script is marked as a par solution.

Failure example:

```text
level_007 solvability failed: script completed package pickup but reached dead_end before destination.
```

### Layer 6: Human-Playability Validation

Goal: prevent technically solvable but unfair levels.

Checks:

- Required taps are not too close together.
- Required switches have a reasonable reaction window before the dot arrives.
- A solution does not require frame-perfect timing.
- A solution does not require tapping a node while the dot is already leaving that node, because `RouteEngine.rotateSwitchNode(nodeID:)` intentionally blocks this.
- Total solution time leaves a small buffer before `timeLimitSeconds`.

Initial recommended constants:

```swift
enum LevelHumanPlayabilityRules {
    static let minimumTapSpacingSeconds: TimeInterval = 0.30
    static let minimumReactionWindowSeconds: TimeInterval = 0.35
    static let minimumCompletionBufferSeconds: TimeInterval = 0.50
}
```

These constants can be tuned later after playtesting.

---

# Solution Script Design

## Recommended File Naming

```text
TinyRoutesTests/Resources/LevelSolutions/level_001.solution.json
TinyRoutesTests/Resources/LevelSolutions/level_002.solution.json
TinyRoutesTests/Resources/LevelSolutions/level_003.solution.json
```

Each production `level_###.json` should have a matching `level_###.solution.json`.

## Phase 1 Script Format: Timed Actions

This is the simplest version and should be implemented first.

```json
{
  "levelID": "level_002",
  "description": "Known-good completion path for level_002.",
  "expectedOutcome": "completed",
  "maxTaps": 1,
  "requiresWithinTimeLimit": true,
  "actions": [
    {
      "timeSeconds": 0.25,
      "tapNodeID": "switch_a"
    }
  ]
}
```

Recommended Swift model:

```swift
struct LevelSolutionScript: Codable {
    let levelID: String
    var description: String?
    var expectedOutcome: ExpectedOutcome
    var maxTaps: Int
    var requiresWithinTimeLimit: Bool
    var actions: [LevelSolutionAction]
}

struct LevelSolutionAction: Codable {
    var timeSeconds: TimeInterval
    var tapNodeID: String
}

enum ExpectedOutcome: String, Codable {
    case completed
}
```

## Phase 2 Script Format: Intent-Based Steps

Timed actions are useful but can become tedious. The stronger version should let test engineers describe intent.

Example future format:

```json
{
  "levelID": "level_007",
  "description": "Pick package, return to switch, then route to destination.",
  "expectedOutcome": "completed",
  "maxTaps": 3,
  "steps": [
    {
      "type": "beforeDotReachesNode",
      "targetNodeID": "switch_a",
      "tapNodeID": "switch_a",
      "rotateCount": 1
    },
    {
      "type": "beforeDotReachesNode",
      "targetNodeID": "switch_b",
      "tapNodeID": "switch_b",
      "rotateCount": 2
    }
  ]
}
```

The infrastructure would translate intent steps into timed actions by using graph distance and engine speed.

Do not start here. Implement timed actions first, then add intent-based steps once the harness is stable.

---

# Simulation Harness Design

## Responsibility

`LevelSimulationHarness` should provide one clean API for tests:

```swift
let result = try harness.run(level: level, script: script)
XCTAssertEqual(result.outcome, .completed)
```

## Recommended Public API

```swift
struct LevelSolvabilityResult {
    let levelID: String
    let outcome: LevelOutcome?
    let elapsedTime: TimeInterval
    let timeRemaining: TimeInterval?
    let tapCount: Int
    let finalNodeID: String?
    let didCollectPackage: Bool
    let executedActions: [ExecutedLevelSolutionAction]
}

struct ExecutedLevelSolutionAction {
    let requestedTime: TimeInterval
    let nodeID: String
    let didRotate: Bool
    let actualTapCountAfterAction: Int
}

final class LevelSimulationHarness {
    private let engineFactory: () -> RouteEngine
    private let frameStep: TimeInterval

    init(
        engineFactory: @escaping () -> RouteEngine = { RouteEngine() },
        frameStep: TimeInterval = 1.0 / 60.0
    )

    func run(level: LevelData, script: LevelSolutionScript) throws -> LevelSolvabilityResult
}
```

## Simulation Rules

The harness should:

1. Build the engine from real `LevelData`.
2. Call `startDotMovement()`.
3. Sort script actions by `timeSeconds`.
4. Advance the engine in deterministic time steps.
5. Apply each tap when simulation time reaches the action time.
6. Continue until the engine reaches a terminal outcome or time expires.
7. Return a detailed result object.

Important rule: **do not duplicate gameplay rules in the harness**. The harness should drive `RouteEngine`, not replace it.

## Timing Precision

Use a fixed step to avoid frame-rate-dependent tests:

```swift
frameStep = 1.0 / 60.0
```

For tests that need exact action timing, allow the harness to update in smaller slices so taps occur exactly at the requested script time:

```text
advance to next action time
perform tap
continue fixed-step updates
```

This avoids a tap at `0.25` being accidentally applied at `0.2667` because of frame rounding.

---

# Level Validator Design

## Responsibility

`LevelValidator` should return all issues instead of throwing on the first issue. This makes it more useful for level designers.

Recommended API:

```swift
struct LevelValidationIssue: Equatable {
    enum Severity: Equatable {
        case error
        case warning
    }

    let severity: Severity
    let levelID: String
    let message: String
}

final class LevelValidator {
    func validate(level: LevelData) -> [LevelValidationIssue]
}
```

## Error vs Warning Policy

Errors should fail tests immediately.

Warnings should be allowed at first but should be visible in test output. After the level format stabilizes, warnings can be promoted to errors.

Recommended initial errors:

- Duplicate node IDs
- Duplicate edge IDs
- Missing start/package/destination node
- Edge references unknown node
- Node outgoing edges mismatch graph edges
- Duplicate outgoing edge IDs
- Non-positive time limit
- Negative par taps
- Package unreachable from start
- Destination unreachable from package
- No possible directed path from start to package to destination

Recommended initial warnings:

- Unreachable non-critical nodes
- Dead-end nodes
- Very short edge length
- Very long edge length
- Level has no switch nodes
- `parTaps` is much larger than solution tap count

---

# Test Layout

## `LevelValidationTests.swift`

Purpose: validate every production level JSON structurally.

Tests:

```swift
func testAllProductionLevelsDecodeSuccessfully()
func testAllProductionLevelFileNamesMatchLevelIDs()
func testAllProductionLevelsPassGraphValidation()
func testAllProductionLevelsHaveReachablePackageAndDestination()
func testAllProductionLevelsBuildInRouteEngine()
```

Expected behavior:

- These tests should run against every `level_###.json` file.
- Failures should clearly print the level ID and issue list.

## `LevelSolutionScriptTests.swift`

Purpose: validate the solution scripts themselves before simulation.

Tests:

```swift
func testEveryProductionLevelHasMatchingSolutionScript()
func testEverySolutionScriptReferencesExistingLevel()
func testEverySolutionScriptHasSortedNonNegativeActionTimes()
func testEverySolutionScriptReferencesKnownNodes()
func testEverySolutionScriptOnlyTapsSwitchNodes()
func testEverySolutionScriptMaxTapsIsNonNegative()
```

## `LevelSolvabilityTests.swift`

Purpose: prove real levels are completable with real engine behavior.

Tests:

```swift
func testEveryProductionLevelCanBeCompletedByItsSolutionScript()
func testEveryProductionLevelCompletesWithinTimeLimit()
func testEveryProductionLevelCompletesWithinDeclaredMaxTaps()
func testParSolutionScriptsDoNotExceedLevelParTaps()
func testSolutionsLeaveMinimumCompletionBuffer()
func testSolutionsDoNotRequireFramePerfectTapSpacing()
```

## Future `LevelSolverTests.swift`

Purpose: optional automated discovery of solutions.

Tests:

```swift
func testSolverCanFindACompletionPathForSmallLevels()
func testSolverFindsKnownSolutionForTrainingLevels()
func testSolverReportsUnsolvableForBrokenFixtureLevel()
```

Do not implement this until scripted solvability is stable.

---

# What Should Change in the Test Infrastructure

## Add Test Resource Loading

Add helper code that can discover all production levels and matching solution files.

Recommended helper:

```swift
enum TestLevelCatalog {
    static func loadProductionLevels() throws -> [LevelData]
    static func loadSolutionScripts() throws -> [LevelSolutionScript]
    static func solutionScript(for levelID: String) throws -> LevelSolutionScript
}
```

This prevents every test file from repeating bundle/path logic.

## Add Validation Issue Reporting

Create a formatting helper so failures are readable:

```swift
func formatIssues(_ issues: [LevelValidationIssue]) -> String
```

Output should look like:

```text
level_004 validation failed with 2 error(s):
- [error] Edge e_12 references unknown toNodeID package_missing.
- [error] Destination is not reachable from package.
```

## Add Deterministic Engine Harness

The harness should be the only place that manually loops over `updateDot(deltaTime:)`.

Tests should not contain low-level simulation loops.

Good:

```swift
let result = try harness.run(level: level, script: script)
XCTAssertEqual(result.outcome, .completed)
```

Avoid:

```swift
engine.updateDot(deltaTime: 0.016)
engine.updateDot(deltaTime: 0.016)
engine.rotateSwitchNode(nodeID: "switch_a")
```

## Add Broken Fixture Levels

Add intentionally broken test fixtures for validator tests.

Recommended layout:

```text
TinyRoutesTests/Fixtures/BrokenLevels/
  duplicate_node_ids.json
  duplicate_edge_ids.json
  missing_start_node.json
  missing_package_node.json
  edge_unknown_from_node.json
  edge_unknown_to_node.json
  package_unreachable.json
  destination_unreachable_from_package.json
  outgoing_edges_mismatch.json
```

These are not production levels. They exist only to prove the validator catches bad data.

---

# What Should Not Change Yet

Do not redesign these yet:

- `LevelData`
- `RouteGraph`
- `RouteNode`
- `RouteEdge`
- Production level JSON schema
- `RouteEngine` gameplay rules

Only change them if the new tests expose a real limitation.

This keeps the work safer and easier for entry-level engineers.

---

# Future Level Infrastructure Improvements

After the testing system is stable, consider these improvements.

## Optional Level Metadata

Add optional fields later:

```swift
var difficulty: Int?
var tags: [String]?
var solutionID: String?
```

Example JSON:

```json
{
  "id": "level_007",
  "name": "Return Route",
  "difficulty": 2,
  "tags": ["switch", "package", "dead_end"],
  "solutionID": "level_007.solution"
}
```

## Level Authoring Rules

Create a small guide for designers/test engineers:

```text
A valid Tiny Routes level must:
1. Start at a valid node.
2. Have one package node.
3. Have one destination node.
4. Have at least one directed path from start to package.
5. Have at least one directed path from package to destination.
6. Have a solution script that completes with real RouteEngine rules.
7. Avoid frame-perfect required taps.
8. Use dead ends only as optional wrong paths.
```

## Automated Solver

A future solver can search possible switch rotations and tap timings.

Recommended solver strategy:

- Treat switch nodes as discrete state.
- Treat active outgoing edge indices as route state.
- Simulate path from start.
- At each switch decision point, branch possible rotations before arrival.
- Search breadth-first by tap count first.
- Reject branches that exceed time limit or tap budget.
- Stop when destination is reached with package.

This is valuable later, but it should not block the first test infrastructure milestone.

---

# Entry-Level Engineering Tasks

## Task 001: Create the Level Test Support Folder Structure

### Goal

Create the test support folders that future tasks will use.

### Files to Create

```text
TinyRoutesTests/Support/.gitkeep
TinyRoutesTests/Resources/LevelSolutions/.gitkeep
TinyRoutesTests/Fixtures/BrokenLevels/.gitkeep
```

### To Do

- [x] Create `TinyRoutesTests/Support/`.
- [x] Create `TinyRoutesTests/Resources/`.
- [x] Create `TinyRoutesTests/Resources/LevelSolutions/`.
- [x] Create `TinyRoutesTests/Fixtures/`.
- [x] Create `TinyRoutesTests/Fixtures/BrokenLevels/`.
- [x] Add `.gitkeep` files where needed so empty folders are committed.

### Definition of Done

- [x] Folder structure exists.
- [x] No production code changed.

---

## Task 002: Add `LevelValidationIssue`

### Goal

Create a simple model for validation warnings and errors.

### File to Create

```text
TinyRoutesTests/Support/LevelValidationIssue.swift
```

### To Do

- [x] Create `LevelValidationIssue`.
- [x] Add nested `Severity` enum with `error` and `warning`.
- [x] Add `levelID` property.
- [x] Add `message` property.
- [x] Make the type `Equatable`.
- [x] Add a helper computed property or function for display text.

### Suggested Shape

```swift
struct LevelValidationIssue: Equatable {
    enum Severity: Equatable {
        case error
        case warning
    }

    let severity: Severity
    let levelID: String
    let message: String
}
```

### Definition of Done

- [x] File compiles.
- [x] Type is available to tests.
- [x] No production code changed.

---

## Task 003: Add `LevelValidator` Skeleton

### Goal

Create the validator entry point without implementing all rules yet.

### File to Create

```text
TinyRoutesTests/Support/LevelValidator.swift
```

### To Do

- [x] Create `final class LevelValidator`.
- [x] Add `func validate(level: LevelData) -> [LevelValidationIssue]`.
- [x] Return an empty issue list for now.
- [x] Add private helper placeholder sections for identity, graph, intent, and playability validation.
- [x] Ensure the file imports `Foundation` and can access `@testable import TinyRoutes` from tests as needed.

### Definition of Done

- [x] Validator compiles.
- [x] No validation rules are implemented yet except the empty result.

---

## Task 004: Add Duplicate ID Validation

### Goal

Catch duplicate node IDs and duplicate edge IDs.

### Files to Modify

```text
TinyRoutesTests/Support/LevelValidator.swift
TinyRoutesTests/LevelValidationTests.swift
```

### To Do

- [x] Add validation for duplicate node IDs.
- [x] Add validation for duplicate edge IDs.
- [x] Add test fixture for duplicate node IDs.
- [x] Add test fixture for duplicate edge IDs.
- [x] Add test that duplicate node IDs produce an error.
- [x] Add test that duplicate edge IDs produce an error.
- [x] Confirm validation returns all duplicate issues, not just the first one.

### Definition of Done

- [x] Duplicate node IDs fail validation.
- [x] Duplicate edge IDs fail validation.
- [x] Tests prove both cases.

---

## Task 005: Add Required Node Validation

### Goal

Verify start, package, and destination node IDs exist in the graph.

### Files to Modify

```text
TinyRoutesTests/Support/LevelValidator.swift
TinyRoutesTests/LevelValidationTests.swift
```

### To Do

- [x] Validate `startNodeID` exists.
- [x] Validate `packageNodeID` exists.
- [x] Validate `destinationNodeID` exists.
- [x] Add broken fixture for missing start node.
- [x] Add broken fixture for missing package node.
- [x] Add broken fixture for missing destination node.
- [x] Add tests for all three cases.

### Definition of Done

- [x] Missing start node fails validation.
- [x] Missing package node fails validation.
- [x] Missing destination node fails validation.
- [x] Failure messages include the missing ID.

---

## Task 006: Add Edge Reference Validation

### Goal

Verify every edge references known `fromNodeID` and `toNodeID` values.

### Files to Modify

```text
TinyRoutesTests/Support/LevelValidator.swift
TinyRoutesTests/LevelValidationTests.swift
```

### To Do

- [x] Validate every edge `fromNodeID` exists in the graph node set.
- [x] Validate every edge `toNodeID` exists in the graph node set.
- [x] Add broken fixture for unknown `fromNodeID`.
- [x] Add broken fixture for unknown `toNodeID`.
- [x] Add tests for both cases.

### Definition of Done

- [x] Unknown edge source node fails validation.
- [x] Unknown edge target node fails validation.
- [x] Failure messages include edge ID and bad node ID.

---

## Task 007: Add Outgoing Edge Consistency Validation

### Goal

Verify each node's `outgoingEdgeIDs` matches actual graph edges from that node.

### Files to Modify

```text
TinyRoutesTests/Support/LevelValidator.swift
TinyRoutesTests/LevelValidationTests.swift
```

### To Do

- [x] Validate duplicate values inside each node's `outgoingEdgeIDs`.
- [x] Validate every outgoing edge ID exists.
- [x] Validate every listed outgoing edge starts from that node.
- [x] Validate every graph edge appears in the source node's `outgoingEdgeIDs`.
- [x] Add broken fixture for duplicate outgoing edge IDs.
- [x] Add broken fixture for missing outgoing edge ID.
- [x] Add broken fixture where node omits one of its outgoing graph edges.
- [x] Add tests for each fixture.

### Definition of Done

- [x] Outgoing edge mismatch fails validation.
- [x] Duplicate outgoing edge IDs fail validation.
- [x] Missing outgoing edge references fail validation.

---

## Task 008: Add Basic Level Property Validation

### Goal

Validate simple non-graph level fields.

### Files to Modify

```text
TinyRoutesTests/Support/LevelValidator.swift
TinyRoutesTests/LevelValidationTests.swift
```

### To Do

- [x] Validate `id` is not empty.
- [x] Validate `name` is not empty.
- [x] Validate `timeLimitSeconds > 0`.
- [x] Validate `parTaps >= 0`.
- [x] Add tests for invalid values.

### Definition of Done

- [x] Empty ID fails validation.
- [x] Empty name fails validation.
- [x] Non-positive time limit fails validation.
- [x] Negative par taps fail validation.

---

## Task 009: Add Reachability Validation

### Goal

Prove the graph has a possible directed path from start to package and from package to destination.

### Files to Modify

```text
TinyRoutesTests/Support/LevelValidator.swift
TinyRoutesTests/LevelValidationTests.swift
```

### To Do

- [x] Add helper that computes reachable node IDs from a starting node using directed edges.
- [x] Validate package is reachable from start.
- [x] Validate destination is reachable from package.
- [x] Validate at least one directed path can go start → package → destination.
- [x] Add broken fixture where package is unreachable.
- [x] Add broken fixture where destination is unreachable from package.
- [x] Add tests for both fixtures.

### Definition of Done

- [x] Unreachable package fails validation.
- [x] Unreachable destination after package fails validation.
- [x] Valid production levels pass this validation.

---

## Task 010: Add Production Level Validation Test

### Goal

Run the validator against every production `level_###.json`.

### Files to Create or Modify

```text
TinyRoutesTests/LevelValidationTests.swift
TinyRoutesTests/Support/TestLevelCatalog.swift
```

### To Do

- [x] Create `TestLevelCatalog` helper.
- [x] Add method to load all production levels.
- [x] Add test that loops through every production level.
- [x] Run `LevelValidator.validate(level:)` on every level.
- [x] Fail the test if any issue has severity `.error`.
- [x] Include all validation messages in the failure output.

### Definition of Done

- [x] Every production level is validated by one test.
- [x] The failure output includes level ID and issue message.
- [x] Existing production levels pass or failures are clearly documented.

---

## Task 011: Add `LevelSolutionScript` Model

### Goal

Create a codable model for hand-authored solution scripts.

### File to Create

```text
TinyRoutesTests/Support/LevelSolutionScript.swift
```

### To Do

- [x] Create `LevelSolutionScript`.
- [x] Create `LevelSolutionAction`.
- [x] Create `ExpectedOutcome` enum with `completed`.
- [x] Add `levelID`.
- [x] Add optional `description`.
- [x] Add `expectedOutcome`.
- [x] Add `maxTaps`.
- [x] Add `requiresWithinTimeLimit`.
- [x] Add `actions`.
- [x] Make all types `Codable`.

### Definition of Done

- [x] Solution script model compiles.
- [x] A sample JSON script can decode in a unit test.

---

## Task 012: Add Solution Script Repository

### Goal

Load solution scripts from test resources.

### File to Create

```text
TinyRoutesTests/Support/LevelSolutionRepository.swift
```

### To Do

- [x] Create `LevelSolutionRepository`.
- [x] Add method to load one script by level ID.
- [x] Add method to load all scripts.
- [x] Use `JSONDecoder`.
- [x] Return helpful errors when files are missing.
- [x] Return helpful errors when decoding fails.

### Definition of Done

- [x] Repository can load one script.
- [x] Repository can load all scripts.
- [x] Missing script produces a clear failure.

---

## Task 013: Add First Solution Script for `level_001`

### Goal

Create the first real solution sidecar file.

### File to Create

```text
TinyRoutesTests/Resources/LevelSolutions/level_001.solution.json
```

### Suggested Content

```json
{
  "levelID": "level_001",
  "description": "No taps required. The default route moves from start to package to destination.",
  "expectedOutcome": "completed",
  "maxTaps": 0,
  "requiresWithinTimeLimit": true,
  "actions": []
}
```

### To Do

- [x] Add `level_001.solution.json`.
- [x] Decode it with `LevelSolutionRepository`.
- [x] Verify `levelID` equals `level_001`.
- [x] Verify `actions` is empty.

### Definition of Done

- [x] `level_001` has a matching solution script.
- [x] The script decodes successfully.

---

## Task 014: Add Solution Script Validation Tests

### Goal

Validate solution script data before using it in the simulation harness.

### File to Create

```text
TinyRoutesTests/LevelSolutionScriptTests.swift
```

### To Do

- [ ] Test every production level has a matching solution script.
- [ ] Test every solution script references an existing production level.
- [ ] Test action times are non-negative.
- [ ] Test actions are sorted by time.
- [ ] Test `maxTaps >= 0`.
- [ ] Test every `tapNodeID` exists in the referenced level.
- [ ] Test every tapped node has more than one outgoing edge.

### Definition of Done

- [ ] Invalid solution scripts fail before engine simulation.
- [ ] Missing solution scripts fail clearly.
- [ ] Bad node references fail clearly.

---

## Task 015: Add `LevelSolvabilityResult`

### Goal

Create a result model for scripted gameplay runs.

### File to Create

```text
TinyRoutesTests/Support/LevelSolvabilityResult.swift
```

### To Do

- [ ] Create `LevelSolvabilityResult`.
- [ ] Add `levelID`.
- [ ] Add `outcome`.
- [ ] Add `elapsedTime`.
- [ ] Add `timeRemaining`.
- [ ] Add `tapCount`.
- [ ] Add `finalNodeID`.
- [ ] Add `didCollectPackage`.
- [ ] Add `executedActions`.
- [ ] Create `ExecutedLevelSolutionAction`.

### Definition of Done

- [ ] Result model compiles.
- [ ] Tests can inspect outcome, time, taps, and final node.

---

## Task 016: Add `LevelSimulationHarness` Skeleton

### Goal

Create the harness that will drive `RouteEngine`.

### File to Create

```text
TinyRoutesTests/Support/LevelSimulationHarness.swift
```

### To Do

- [ ] Create `final class LevelSimulationHarness`.
- [ ] Add initializer with `engineFactory` and `frameStep`.
- [ ] Add `run(level:script:)` method.
- [ ] Build the engine from the level.
- [ ] Start dot movement.
- [ ] Return a basic result without applying actions yet.

### Definition of Done

- [ ] Harness can run `level_001` with an empty action list.
- [ ] Harness returns `.completed` for `level_001`.

---

## Task 017: Implement Timed Action Execution

### Goal

Make the harness apply scripted taps at the requested times.

### Files to Modify

```text
TinyRoutesTests/Support/LevelSimulationHarness.swift
TinyRoutesTests/LevelSolvabilityTests.swift
```

### To Do

- [ ] Sort actions by `timeSeconds` or require scripts to already be sorted.
- [ ] Advance the engine to each action time.
- [ ] Call `rotateSwitchNode(nodeID:)` for each action.
- [ ] Record whether the tap rotated the switch.
- [ ] Continue simulation after the final action until terminal outcome or time expiry.
- [ ] Stop simulation once `levelOutcome` is not nil.

### Definition of Done

- [ ] Harness can execute a non-empty action list.
- [ ] Result includes executed action details.
- [ ] Tap count matches the engine tap count.

---

## Task 018: Add `LevelSolvabilityTests`

### Goal

Prove levels complete using their solution scripts.

### File to Create

```text
TinyRoutesTests/LevelSolvabilityTests.swift
```

### To Do

- [ ] Load all production levels.
- [ ] Load matching solution scripts.
- [ ] Run each level through `LevelSimulationHarness`.
- [ ] Assert outcome is `.completed`.
- [ ] Assert completion is within time limit.
- [ ] Assert tap count is less than or equal to script `maxTaps`.
- [ ] If script is intended as par solution, assert tap count is less than or equal to level `parTaps`.
- [ ] Include level ID in every failure message.

### Definition of Done

- [ ] Every level with a solution script is simulated through real `RouteEngine`.
- [ ] Failed levels report clear diagnostics.
- [ ] `level_001` passes with zero taps.

---

## Task 019: Add Solution Scripts for All Current Production Levels

### Goal

Create one known-good solution script for each existing level.

### Files to Create

```text
TinyRoutesTests/Resources/LevelSolutions/level_002.solution.json
TinyRoutesTests/Resources/LevelSolutions/level_003.solution.json
...
TinyRoutesTests/Resources/LevelSolutions/level_010.solution.json
```

### To Do

- [ ] Open each production level JSON.
- [ ] Identify the intended route.
- [ ] Run the level manually or reason through switch defaults.
- [ ] Create a solution script for each level.
- [ ] Run `LevelSolvabilityTests` after each script is added.
- [ ] Fix the script or level data if simulation fails.
- [ ] Keep scripts minimal and readable.

### Definition of Done

- [ ] Every current `level_###.json` has a matching solution script.
- [ ] Every solution completes through `RouteEngine`.
- [ ] Every solution completes within the time limit.

---

## Task 020: Add Human Playability Rules

### Goal

Add basic fairness checks to prevent frame-perfect solutions.

### File to Create

```text
TinyRoutesTests/Support/LevelHumanPlayabilityRules.swift
```

### Files to Modify

```text
TinyRoutesTests/LevelSolvabilityTests.swift
```

### To Do

- [ ] Add `minimumTapSpacingSeconds`.
- [ ] Add `minimumCompletionBufferSeconds`.
- [ ] Validate actions are at least `minimumTapSpacingSeconds` apart.
- [ ] Validate completed solution leaves at least `minimumCompletionBufferSeconds` before the time limit.
- [ ] Add tests for these rules.

### Definition of Done

- [ ] Solutions with taps too close together fail.
- [ ] Solutions that complete with no time buffer fail.
- [ ] Valid current solutions pass or failure is documented for level tuning.

---

## Task 021: Add Intent-Based Solution Step Design Document

### Goal

Document the next-generation solution DSL before coding it.

### File to Create

```text
docs/plans/level_solution_intent_dsl_plan.md
```

### To Do

- [ ] Explain why timed scripts are phase 1 only.
- [ ] Define `beforeDotReachesNode` step.
- [ ] Define `afterDotLeavesNode` step if needed.
- [ ] Define `rotateCount` behavior.
- [ ] Explain how intent steps convert to timed actions.
- [ ] Include examples for one-switch and multi-switch levels.

### Definition of Done

- [ ] Future DSL is documented.
- [ ] No production code changed.
- [ ] No test behavior changed.

---

## Task 022: Add Optional Automated Solver Spike

### Goal

Explore whether a solver can discover solutions automatically for simple levels.

### File to Create

```text
TinyRoutesTests/Support/ExperimentalLevelSolver.swift
```

### To Do

- [ ] Mark solver as experimental in comments.
- [ ] Search possible switch rotations by tap count.
- [ ] Use `RouteEngine` or a carefully isolated graph-state search.
- [ ] Test only small fixture levels first.
- [ ] Do not require the solver for production level validation yet.

### Definition of Done

- [ ] Solver can find a solution for at least one simple test fixture.
- [ ] Solver is not required for production tests.
- [ ] Results are documented.

---

# Recommended Implementation Order

Use this order to keep the work safe:

1. Task 001: folder structure
2. Task 002: validation issue model
3. Task 003: validator skeleton
4. Task 004: duplicate ID validation
5. Task 005: required node validation
6. Task 006: edge reference validation
7. Task 007: outgoing edge consistency validation
8. Task 008: basic level property validation
9. Task 009: reachability validation
10. Task 010: production level validation test
11. Task 011: solution script model
12. Task 012: solution script repository
13. Task 013: first `level_001` solution script
14. Task 014: solution script validation tests
15. Task 015: solvability result model
16. Task 016: simulation harness skeleton
17. Task 017: timed action execution
18. Task 018: solvability tests
19. Task 019: solution scripts for all current levels
20. Task 020: human-playability rules
21. Task 021: intent DSL plan
22. Task 022: optional solver spike

---

# Final Target State

When this work is done, the repo should be able to answer these questions automatically in tests:

```text
Can every level JSON decode?
Is every graph structurally valid?
Are package and destination reachable in the correct order?
Does RouteEngine accept every level?
Does every production level have a solution script?
Does every solution script reference valid nodes?
Can every level be completed by the real RouteEngine?
Does every solution finish within the level time limit?
Does every solution stay within tap limits?
Does every solution avoid unfair frame-perfect timing?
```

That is the practical definition of a full-proof level testing system for the current Tiny Routes codebase.
