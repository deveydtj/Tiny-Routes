# Tiny Routes Generator V2 – 10/10 Implementation Plan

## Goal

Evolve the existing Tiny Routes generator into a stricter **recipe-first, graph-first, solver-validated puzzle generator**.

The generator should create levels that feel intentionally designed, not randomly assembled.

It must support clean road layouts, no accidental loops, intentional loops/rings/revisits where appropriate, no visually confusing intersections, one valid solution, meaningful puzzle decisions, difficulty progression through mechanics rather than raw node count, and reuse of existing generator systems wherever possible.

## Core Rule

Do not ban all loops.

Tiny Routes may intentionally use loops, rings, revisits, split/rejoin paths, return paths, and multi-switch chains. These are valid medium/hard/expert mechanics.

### Correct Rule

A loop/cycle is allowed only when it is:

1. Declared by the selected recipe
2. Required or intentionally distracting
3. Validated as logically safe
4. Validated as visually readable
5. Proven uniquely solvable
6. Verified against runtime behavior when needed

### Replace This Bad Rule

    No cycles are allowed.

### With This Rule

    Cycles are allowed only when the selected recipe explicitly permits them.
    Undeclared cycles are always rejected.

## Architecture Overview

The generator should follow this pipeline:

    1. Select recipe
    2. Build abstract graph
    3. Validate abstract graph
    4. Solve puzzle logic
    5. Assign layout
    6. Validate layout readability
    7. Assign road shapes and switch exits
    8. Run runtime-style simulation
    9. Score quality
    10. Accept/reject candidate

Important principle:

    Puzzle logic must be valid before visual layout is attempted.
    Visual layout must not be allowed to create new gameplay ambiguity.

## Phase 1 – Recipe Topology Rules

### Purpose

Every recipe must declare what graph structures it is allowed to create.

Create or extend:

    RecipeTopologyRules

Fields:

    allowsCycles: Bool
    allowsRejoin: Bool
    allowsRevisit: Bool
    allowsReturnPath: Bool
    allowsRing: Bool
    allowedCycleCount: Int
    requiresPackageGate: Bool
    requiresUniqueSolution: Bool
    requiresSwiftRuntimeValidation: Bool

Optional metadata:

    topologyClass: String
    primaryMechanicTag: String
    difficultyBands: [Difficulty]
    minimumRouteLength: Int
    maximumRouteLength: Int
    minimumTapCount: Int
    maximumTapCount: Int

### Acceptance Criteria

- Every recipe/family defines topology rules.
- Easy recipes do not allow cycles by default.
- Medium may allow split/rejoin or small return paths.
- Hard may allow rings, revisits, and multi-switch chains.
- Expert may allow larger intentional loops and repeated revisits.
- Missing topology rules should fail validation.

## Phase 2 – Recipe Selection

### Purpose

Select recipes based on difficulty, recent pacing, and topology diversity.

### Difficulty Rules

#### Tutorial

Allowed:

- Straight path
- Single simple switch
- No cycles
- No revisits
- No rejoin

Target:

    3–5 nodes
    0–1 switches
    0–1 taps

#### Easy

Allowed:

- Straight path
- Fork
- Dead-end branches
- Simple package gate

Avoid:

- Cycles
- Rejoins
- Revisits
- Rings

Target:

    5–7 nodes
    1–2 switches
    1–2 taps

#### Medium

Allowed:

- Split/rejoin
- Fake shortcut
- Small return path
- Package-before-destination tension
- Short detour gate

Target:

    7–10 nodes
    2–3 switches
    2–3 taps

#### Hard

Allowed:

- Ring break
- Revisit path
- Multi-switch chain
- Branch/rejoin wrong order
- Package inside loop
- Two-phase route

Target:

    9–13 nodes
    3–5 switches
    3–5 taps

#### Expert

Allowed:

- Larger intentional loops
- Multi-switch revisits
- Four-way package gates
- Ring + switch interaction
- Controlled repeated taps
- Multi-hub decisions

Target:

    10–15 nodes
    3–6 switches
    4–6 taps

### Acceptance Criteria

- Lower difficulties avoid loop mechanics.
- Higher difficulties can use loops safely.
- Recipe selection avoids repeating the same topology too often.
- Recipe metadata matches actual graph behavior.

## Phase 3 – Abstract Graph Generation

### Purpose

Build puzzle logic before coordinates, road shapes, or visuals.

Create or strengthen:

    AbstractGraphBuilder
    RecipeGraphBuilder

The abstract graph should include:

    nodes
    edges
    start node
    goal node
    package node, if applicable
    switch nodes
    required path
    wrong branches
    declared loops
    declared rejoins
    declared revisits

### Rules

- Every new graph feature must be created intentionally.
- Branches cannot accidentally reconnect.
- Rejoins are allowed only if recipe permits rejoin.
- Cycles are allowed only if recipe permits cycles.
- Revisit paths are allowed only if recipe permits revisit.
- Package gates must enforce package-before-goal behavior.
- Switch count and tap count must fit difficulty.

### Acceptance Criteria

- Abstract graph can be generated without layout data.
- Graph metadata identifies intentional loops/rejoins/revisits.
- Undeclared graph structures are rejected.
- Graph structure matches the selected recipe's rules.

## Phase 4 – Abstract Graph Validation

### Validation 1 – Single Start

    validateSingleStart()

Expected:

    startCount == 1

### Validation 2 – Single Goal

    validateSingleGoal()

Expected:

    goalCount == 1

### Validation 3 – No Orphans

    validateNoOrphans()

Rule:

    Every node must be reachable from start.

### Validation 4 – No Undeclared Cycles

Replace:

    validateNoCycles()

With:

    validateNoUndeclaredCycles()

Rules:

    If recipe.allowsCycles == false:
        cycleCount must be 0

    If recipe.allowsCycles == true:
        only declared cycles may exist

### Validation 5 – Declared Loop Validation

Create:

    validateDeclaredLoops()

Check:

- Loop belongs to intended mechanic
- Loop does not create a shortcut
- Loop does not bypass package rules
- Loop does not create a second solution
- Loop has clear entry and exit
- Loop is allowed for difficulty
- Loop count does not exceed allowedCycleCount

### Validation 6 – Rejoin Validation

Create:

    validateDeclaredRejoins()

Check:

- Rejoin exists only when allowed
- Rejoin does not create unintended shortcut
- Rejoin does not bypass package
- Rejoin does not create duplicate valid paths
- Rejoin is required or intentionally distracting

### Validation 7 – Revisit Validation

Create:

    validateDeclaredRevisits()

Check:

- Revisited node is declared
- Revisit is part of intended route
- Revisit does not create infinite traversal
- Repeated switch taps are allowed for difficulty
- Revisit spacing is readable

### Acceptance Criteria

- Accidental loops fail.
- Intentional loops pass only when declared.
- Invalid loops fail before layout.
- Graph validation errors are reported clearly.

## Phase 5 – Unique Solution Solver

### Purpose

Prove the puzzle has exactly one valid solution before layout.

Implementation status: the current `UniqueSolutionValidatorService` performs bounded structural enumeration on generated concrete levels after scripted simulation succeeds. It counts package-before-destination terminal routes, rejects `solutionCount != 1` or limit-truncated searches when topology rules require uniqueness, and layers shortcut, package-before-goal, wrong-branch, rejoin, and revisit validation on the same search results. Full runtime timing parity remains future work.

Create or improve:

    UniqueSolutionValidator
    RouteSolver
    AbstractRouteSimulator

### Required Checks

    validateGoalReachable()
    validatePackageBeforeGoal()
    validateUniqueSolution()
    validateNoShortcutPath()
    validateWrongBranchesFailCorrectly()

### Unique Solution Rule

Expected:

    solutionCount == 1

### Solver Requirements

The solver must account for:

- Switch states
- Tap count
- Package collection
- Goal reachability
- Loops
- Rejoins
- Revisits
- Return paths
- Dead-end branches

### Loop-Specific Solver Rules

For declared loops:

- Loop may not create a second valid solution
- Loop may not allow goal before package
- Loop may not allow infinite valid traversal
- Loop must have bounded traversal depth
- Loop must preserve intended route order

### Acceptance Criteria

- Every accepted graph has exactly one valid solution.
- Shortcut paths through loops are rejected.
- Package bypasses are rejected.
- Infinite loop traversal is bounded and rejected if ambiguous.
- Solver failures include useful rejection reasons.

### Phase 5 Shortcut/Package Validation Status

Implemented route-safety checks:

- `validatePackageBeforeGoal()` rejects destination-before-package terminal routes, ambiguous package state, missing package/destination order in the intended route, and missing intended-route edges.
- `validateNoShortcutPath()` compares successful enumerated routes against `solutionRoute` and `requiredTapOrder`, rejects shorter valid routes, alternate valid routes, package-bypass goal reaches, and tap-order bypasses.
- `validateWrongBranchesFailCorrectly()` inspects off-route branches from the intended route and rejects branches that reach the goal, become valid solutions after package collection, or terminate only at traversal/tap limits.

Reporting now exposes `shortcutDetected`, `packageBypassDetected`, `wrongBranchReachedGoal`, `bypassPathSummary`, `intendedRouteLength`, `shortestValidRouteLength`, `packageReachabilityStatus`, rejoin diagnostics, and revisit diagnostics in the unique-solution validation payload.

Current limitations:

- The checks are structural and reuse bounded enumeration; they do not model exact Swift movement timing or ignored-tap windows.
- Wrong-branch validation infers branches from edges leaving the intended route.
- Declared loops are not rejected by default; they fail only when they create a shortcut, package bypass, extra valid solution, or ambiguous termination.

## Phase 6 – Rejoin and Revisit Validation

### Declared vs Undeclared Rejoins

A rejoin is an acyclic convergence point: two or more non-cycle incoming path segments flow into the same downstream node. Cycle-closing edges in ring or return-loop mechanics are classified by cycle/loop validation, not by rejoin validation.

A declared rejoin is valid only when `RecipeTopologyRules.allowsRejoin` is true and the concrete graph remains safe under the solver. An undeclared rejoin fails with `undeclared_rejoin`. Optional metadata such as `declaredRejoinCount`, `allowedRejoinCount`, `rejoinNodeIDs`, or `declaredRejoinNodeIDs` is honored when present and is checked against the detected graph.

`validateDeclaredRejoins()` runs after unique-solution, shortcut, wrong-branch, and package checks have produced solver evidence. It rejects rejoins that participate in package bypasses, alternate valid routes, shortcut routes, or traversal-limit ambiguity. Reporting exposes `rejoinDetected`, `rejoinCount`, `declaredRejoinCount`, `unsafeRejoinDetected`, and `unsafeRejoinReason`.

### Declared vs Undeclared Revisits

A revisit is an intended-route repeat of a node already visited earlier in that same route. Repeated switch taps are tracked separately from repeated node visits because a recipe can revisit a node without retapping it, and repeated taps require explicit recipe support through `allowsRepeatedTaps`.

A declared revisit is valid only when `RecipeTopologyRules.allowsRevisit` is true. An undeclared revisit fails with `undeclared_revisit`. Optional metadata such as `declaredRevisitCount`, `allowedRevisitCount`, `revisitNodeIDs`, `repeatedNodeIDs`, or `declaredRevisitNodeIDs` is checked when present.

`validateDeclaredRevisits()` reuses `UniqueSolutionValidatorService` enumeration output. It rejects revisits that create package bypasses, alternate valid routes, shortcut routes, repeated taps when the recipe disallows them, or traversal-limit paths that indicate unbounded loop risk. Reporting exposes `revisitDetected`, `revisitCount`, `declaredRevisitCount`, `unsafeRevisitDetected`, `unsafeRevisitReason`, `repeatedNodeIDs`, `repeatedSwitchIDs`, and `maxVisitCountByNode`.

### Relationship To Topology Rules

`GraphRecipe.validate()` now runs this logic in recipe order:

    topology rules present
    validateNoUndeclaredCycles()
    validateDeclaredLoops()
    validateDeclaredRejoins()
    validateDeclaredRevisits()

Generated-level validation preserves the existing concrete order: scripted simulation must pass first, then `UniqueSolutionValidatorService` performs unique-solution enumeration, package/shortcut/wrong-branch checks, rejoin checks, and revisit checks. This keeps rejoin/revisit safety tied to the same route evidence used for solution counting.

### Current Limitations

- Rejoin detection is graph-structural and intentionally excludes cycle-closing incoming edges so ring and return-loop mechanics stay under loop validation.
- Revisit validation proves bounded behavior only through the current bounded structural enumerator. Swift runtime timing, missed-tap windows, and time-limit parity remain pending runtime validation work.
- Layout readability for rejoins and revisits remains a later phase; these checks validate topology and route correctness only.

## Phase 7 – Layout Generation

### Purpose

Place a valid graph visually without creating confusion.

Create or strengthen:

    LayeredLayoutGenerator
    PortraitLayoutGenerator
    LayoutCandidateBuilder

### Layout Strategy

Use difficulty-aware layout profiles:

    standardPortrait
    largePortrait
    hubAndSpoke
    splitLane
    ringReadable
    returnPathReadable

### Layout Rules

Layout must preserve graph intent.

It must not create:

- Node overlap
- Edge overlap
- Hidden intersections
- Accidental crossings
- Roads too close together
- Switch exits that visually overlap
- Important nodes blocked by roads
- Start/goal too close together
- Package/goal visual ambiguity
- First road segments that point in confusing directions

### Acceptance Criteria

- Layout does not change puzzle logic.
- Layout is readable on phone screen.
- Hard/expert layouts may use large portrait only when useful.
- Layout failure rejects candidate, not recipe.
- Layout reports include rejection reasons.

## Phase 8 – Layout Readability Validation

Create:

    LayoutReadabilityValidator

Implemented location:

    Tools/LevelGenerator/app/services/layout_readability_validator.py

The validator emits a `LayoutReadabilityReport` and stores the latest report on each generated candidate as `layout_readability_validation_result`. JSON/Markdown generation reports expose the result under `layoutReadability`.

Checks:

    validateNoNodeOverlap()
    validateNoImplicitIntersectionWithoutNode()
    validateRoadsNotTooClose()
    validateSwitchExitSeparation()
    validateNoOverlappingFirstSegments()
    validateImportantNodeVisibility()
    validatePortraitSafety()
    validateStartGoalSeparation()

### Specific Rules

#### Implicit Intersection

Reject when two roads visually cross without a node.

    implicitIntersectionWithoutNode == true -> reject

#### Roads Too Close

Reject when unrelated roads run close enough to look connected.

    roadDistance < minimumReadableSpacing -> reject

#### Switch Exit Overlap

Reject when two exits from the same switch begin in nearly the same visual direction.

    duplicateExitDirectionBucket == true -> reject

#### Important Node Blocked

Reject when package, switch, start, or goal is visually obscured.

    importantNodeBlocked == true -> reject

### Acceptance Criteria

- Logically valid but visually confusing puzzles are rejected.
- Switch exits are visually distinct.
- Road crossings are intentional only if represented by a node.
- Readability checks run before candidate scoring.

### Reporting Metadata

The report exposes:

- `nodeOverlapDetected`
- `implicitIntersectionDetected`
- `roadsTooCloseDetected`
- `switchExitOverlapDetected`
- `importantNodeBlocked`
- `startGoalTooClose`
- `portraitSafetyFailure`
- `offendingNodes`
- `offendingRoads`
- `measuredDistances`
- `measuredAngles`
- `thresholds`

Primary rejection codes:

- `implicit_intersection_without_node`
- `switch_exit_overlap`
- `node_spacing_failure`
- `start_goal_separation_failure`
- `road_proximity_failure`
- `important_node_visibility_failure`
- `portrait_safety_failure`

Current limitations:

- Uses generator road geometry rather than Swift-rendered rounded-corner paths.
- Approximates artwork and label visibility with board-unit clearance thresholds.
- Treats all switchable nodes as important nodes until recipe metadata distinguishes major/minor switches.

## Phase 9 – Road Shape and Direction Assignment

### Purpose

Assign road shapes, switch exits, arrows, and traversal behavior after graph and layout are valid.

Create or strengthen:

    RoadShapeAssignmentService
    SwitchDirectionAssignmentService
    SwitchVisualClarityService

Implemented locations:

    Tools/LevelGenerator/app/services/road_shape_service.py
    Tools/LevelGenerator/app/services/switch_direction_assignment_service.py
    Tools/LevelGenerator/app/services/switch_visual_clarity_service.py

### Rules

- Solution path must remain valid.
- Switch arrows must match actual road-path start tangents.
- Road shape must not introduce accidental visual ambiguity.
- Branches should look tempting but not misleading in an unfair way.
- Direction buckets must be distinct for switch exits.
- Runtime simulation must match generated solution sidecar.

### Direction Buckets

Switch choices are bucketed by the rendered road-path start tangent, not by the target-node vector. This matches gameplay arrows: an L-shaped road that starts horizontally is an east/west choice even if the target node is diagonally placed.

The assignment layer rejects or penalizes:

- `ambiguous_switch_exit`: the exit has no readable first segment or cannot resolve to a valid rendered direction.
- `conflicting_direction_bucket`: two exits from the same switch occupy the same visual bucket.
- `insufficient_exit_separation`: exit buckets are too close to communicate distinct choices at gameplay scale.
- `unreadable_road_geometry`: the final road-shape plan scores below the readable-geometry threshold.

Tiny coordinate differences are not treated as meaningful choices. If two exits only differ by a small first segment or collapse into the same cardinal direction, the candidate is considered visually ambiguous even if the abstract graph is logically valid.

### Road-Shape Readability Goals

Road-shape planning optimizes `horizontalFirst` and `verticalFirst` choices after layout. It favors assignments that:

- keep switch exits in distinct buckets
- avoid overlapping first segments from the same switch
- keep wrong branches visually distinct from the required route
- reduce accidental crossings, parallel merges, and unconnected endpoint touches
- keep return-loop/revisit geometry from reading as a shortcut
- preserve ring and rejoin mechanics without hiding the intended route flow

Revisit-specific overrides are re-evaluated after assignment so metadata describes the actual road shapes written to the level.

### Relationship to Layout Readability

Layout readability validates node placement, implicit intersections, spacing, portrait safety, and important-node visibility before candidate scoring. Road-shape assignment runs on top of that layout and decides how each edge bends and which visual bucket each switch exit occupies.

Layout readability can reject a candidate whose coordinates are unclear. Road-shape validation can still reject a coordinate-valid candidate if the selected bends make switch arrows, loops, rejoins, or revisits visually confusing.

### Reporting Metadata

Road-shape and visual-clarity reports expose:

- `switchDirectionQuality`
- `switchExitAngleSeparation`
- `ambiguousSwitchDetected`
- `roadShapeWarnings`
- `readabilityAdjustments`
- `directionBucketAssignments`
- `switchDirectionBuckets`

### Acceptance Criteria

- Assigned road shapes preserve unique solution.
- No duplicate switch direction buckets.
- No ambiguous switch arrows.
- Python simulation passes.
- Swift runtime validation passes for risky mechanics.

### Current Limitations

- Buckets are cardinal because generated roads currently use orthogonal first segments.
- The generator approximates arrow readability from board-unit geometry; it does not perform Swift-rendered pixel inspection in this phase.
- Rounded road corners are approximated by straight planning segments for validation.
- Runtime parity is implemented as a production gate in Phase 10. Swift execution still runs through the existing xcodebuild test harness rather than an in-memory simulator bridge.

## Phase 10 – Runtime Parity Validation

### Purpose

Ensure Python generator behavior matches actual Tiny Routes gameplay.

Create or strengthen:

    RuntimeParityValidator
    SwiftValidationGate

Implementation status: `SwiftValidationGate` now classifies runtime-risk from recipe topology rules, candidate flags, mechanic metadata, topology class, mechanic tags, and concrete graph evidence such as four-way fanout, cycles, repeated route nodes, repeated taps, rejoins, and package-inside-loop. `RuntimeParityValidator` records whether Swift validation is not required, skipped for dry-run reporting, pending for a production `--swift-tests` run, passed, failed, or missing.

### Required For

Swift validation should be required for recipes with:

    requiresSwiftRuntimeValidation == true

Examples:

- Four-way intersections
- Rings
- Revisits
- Repeated taps
- Complex switch loops
- Package-inside-loop
- Multi-phase routes

### Checks

- Generated level loads in Swift.
- Solution sidecar matches runtime route.
- Switch arrows match runtime direction.
- Package collection order works.
- Goal is reachable only after package when required.
- Repeated taps behave correctly.
- Four-way behavior matches Python simulation.

### Acceptance Criteria

- Risky recipes cannot be accepted into production without runtime validation.
- Python-only validation is allowed only for low-risk dry-run experiments.
- Swift validation failures include candidate seed and recipe metadata.

Production behavior: dry runs may report risky candidates with `runtimeValidationStatus: skipped_required_for_production`. Production generation without `--swift-tests` rejects risky candidates with `missing_required_swift_validation`. Production generation with `--swift-tests` writes the generated level and solution sidecar, then runs the existing `LevelSolvabilityTests/testRequestedGeneratedLevelsCompleteFromEnvironmentDirectories` xcodebuild hook with generated directories supplied through environment variables.

Reporting now exposes `runtimeValidationRequired`, `runtimeValidationStatus`, `runtimeValidationReason`, `swiftValidationCommand`, `swiftValidationPassed`, `swiftValidationSkippedReason`, `riskyMechanicTags`, and `requiresSwiftRuntimeValidation` for accepted candidates and candidate-selection summaries.

Current limitations:

- Swift runtime parity uses the existing xcodebuild test harness and therefore validates files on disk after write, not in-memory candidates before write.
- Failure classification is inferred from xcodebuild output and may fall back to `swift_runtime_parity_failed`.
- Road-shape parity is validated through RouteEngine replay and generator switch-preview metadata; there is no Swift-rendered pixel comparison in this phase.

## Phase 11 – Quality Scoring V2

Create or improve:

    PuzzleQualityScorer

Output:

    0...100

Quality scoring is a selection layer, not a validation layer. Hard validation runs first and rejects invalid graph, solution, package, topology, layout-readability, and runtime-risk candidates. The scorer only ranks and rejects candidates that already passed validation, so scoring can never override a validation failure.

The V2 scorer preserves existing route-interest, difficulty-fit, readability, visual-clarity, campaign-pacing, and signature-diversity signals, then exposes them through a smaller explainable category model:

    totalScore
    categoryScores.logicScore
    categoryScores.routeInterestScore
    categoryScores.layoutScore
    categoryScores.difficultyFitScore
    categoryScores.diversityScore
    topPositiveFactors
    topNegativeFactors

Candidate comparison is deterministic. It sorts by `totalScore`, then route interest, layout, difficulty fit, diversity, logic, and seed. This makes interesting, readable, difficulty-appropriate candidates beat merely valid candidates.

### Score Categories

#### Logic Score

Rewards:

- Unique solution
- No shortcut
- Correct package order
- Clean branch behavior
- Safe declared rejoin/revisit behavior
- Runtime confidence

#### Route-Interest Score

Rewards:

- Meaningful decisions
- Fake shortcuts
- Split/rejoin structure
- Package tension
- Intentional revisits
- Multi-exit hub choices
- Correct longer detours

Penalizes:

- Straight filler chains
- Extra switches without decisions
- Repeated topology
- Branches that do not matter
- Difficulty inflated by node, switch, or branch count alone

#### Layout Score

Rewards:

- Clean spacing
- Clear start/goal separation
- Readable branches
- No visual intersections
- Good portrait composition

Penalizes:

- Crowding
- Crossings
- Ambiguous switch exits
- Dead space
- Overly compressed routes

#### Difficulty Fit Score

Rewards:

- Correct node count
- Correct switch count
- Correct tap count
- Correct mechanic complexity
- Appropriate route length
- Estimated difficulty band matching the target preset
- Tap pacing appropriate to the target preset

Penalizes:

- Difficulty mismatch
- Inflated complexity
- Excess visual complexity for the preset

#### Diversity/Pacing Score

Rewards:

- Different topology from nearby levels
- Different mechanic tag from nearby levels
- Different route shape from previous accepted levels

Penalizes:

- Repeated family
- Repeated topology class
- Repeated mechanic tag
- Repeated switch/tap pattern

### Difficulty Minimums

    tutorial: 65+
    easy: 70+
    medium: 75+
    hard: 80+
    expert: 85+

These thresholds are quality gates for already-valid candidates:

    tutorial: totalScore >= 65
    easy: totalScore >= 70
    medium: totalScore >= 75
    hard: totalScore >= 80
    expert: totalScore >= 85

### Acceptance Criteria

- Hard validation runs before scoring.
- Scoring never allows invalid puzzles.
- Candidate reports explain why the winning candidate was selected.
- Weak but technically valid puzzles are rejected.
- Reports include total score, category scores, top positive factors, and top negative factors.

## Phase 12 – Reporting and Debuggability

Every generated candidate report should include:

    seed
    difficulty
    recipe family
    recipe variant
    topology rules
    allowed cycles
    actual cycle count
    declared loops
    declared rejoins
    declared revisits
    solution count
    route length
    switch count
    tap count
    package order result
    layout profile
    readability result
    quality score
    rejection reason
    runtime validation result

### Acceptance Criteria

- Every rejection has a specific reason.
- Every accepted candidate has enough metadata to reproduce it.
- Reports make starvation issues visible.
- Reports separate logic failure, layout failure, runtime failure, and quality failure.

## Phase 13 – Testing Plan

### Unit Tests

#### Recipe Rules

    testEveryRecipeDefinesTopologyRules()
    testEasyRecipesDoNotAllowCyclesByDefault()
    testHardRecipesCanDeclareCycles()
    testMissingTopologyRulesFails()

#### Cycle Validation

    testUndeclaredCycleFails()
    testDeclaredCyclePasses()
    testDeclaredCycleShortcutFails()
    testDeclaredCyclePackageBypassFails()
    testDeclaredCycleExtraSolutionFails()

#### Unique Solution

    testSolutionExists()
    testUniqueSolution()
    testMultipleSolutionsRejected()
    testShortcutRejected()
    testPackageBypassRejected()

#### Rejoin/Revisit

    testDeclaredRejoinPasses()
    testUndeclaredRejoinFails()
    testRejoinShortcutFails()
    testDeclaredRevisitPasses()
    testUndeclaredRevisitFails()
    testInfiniteRevisitRejected()

#### Layout Readability

    testImplicitIntersectionRejected()
    testRoadsTooCloseRejected()
    testSwitchExitOverlapRejected()
    testImportantNodeBlockedRejected()
    testPortraitLayoutBoundsPass()

#### Difficulty Progression

    testDifficultyScaling()
    testEasyAvoidsLoops()
    testMediumAllowsSplitRejoin()
    testHardAllowsRingBreak()
    testExpertAllowsComplexRevisit()

#### Runtime Parity

    testGeneratedSolutionMatchesRuntime()
    testSwitchArrowUsesRoadStartTangent()
    testFourWayRuntimeParity()
    testRepeatedTapRuntimeParity()
    testPackageInsideLoopRuntimeParity()

## Phase 14 – Stress Testing

### Bounded Stress Tests

Run deterministic dry-run batches:

    100 tutorial candidates
    100 easy candidates
    100 medium candidates
    50 hard candidates
    25 expert candidates

Expected:

    zero accepted invalid puzzles
    clear rejection reasons
    reasonable acceptance rate
    no crash
    no infinite generation loop

### Acceptance Rate Targets

Initial target:

    tutorial: 95%+
    easy: 95%+
    medium: 90%+
    hard: 80%+
    expert: 70%+

Final target:

    tutorial: 98%+
    easy: 95%+
    medium: 90%+
    hard: 85%+
    expert: 80%+

### Full Stress Test

Final validation:

    Generate 1000 accepted puzzles across seeded dry-runs.

Requirements:

- Zero invalid accepted puzzles
- Zero missing solution sidecars
- Zero runtime parity failures for required recipes
- No unbounded generation attempts
- Rejection reasons are categorized

## Implementation Order

### Step 1

Add `RecipeTopologyRules`.

Do not change generation behavior yet.

### Step 2

Attach topology rules to every existing recipe/family.

Fail if any recipe lacks rules.

### Step 3

Replace strict `validateNoCycles()` with:

    validateNoUndeclaredCycles()
    validateDeclaredLoops()

### Step 4

Strengthen abstract solver:

    validateUniqueSolution()
    validateNoShortcutPath()
    validatePackageBeforeGoal()

### Step 5

Add rejoin and revisit validation.

    validateDeclaredRejoins()
    validateDeclaredRevisits()

### Step 6

Add layout readability validation.

    implicit intersections
    road closeness
    switch exit overlap
    important node visibility
    portrait safety

### Step 7

Integrate scoring.

Hard validation first, scoring second.

### Step 8

Add reporting fields.

Make every rejection reproducible.

### Step 9

Add stress tests.

Start with bounded tests, then expand.

### Step 10

Tune recipe selection and difficulty pacing.

Do not weaken validation to increase acceptance.

## Non-Negotiable Rules

Do:

- Reuse existing generator architecture.
- Keep recipe-first generation.
- Keep strict validation.
- Keep deterministic seeds.
- Keep solution sidecars.
- Keep Swift runtime validation for risky mechanics.
- Reject visually confusing layouts.
- Make hard/expert harder through mechanic interaction.

Do not:

- Rewrite the whole generator unnecessarily.
- Ban all loops.
- Accept undeclared cycles.
- Let layout create hidden gameplay behavior.
- Make levels harder only by adding switches.
- Weaken validation to make generation pass.
- Commit generated production levels without matching solution files.
- Trust Python-only validation for risky hard/expert mechanics.

## Final Definition of Done

Generator V2 is complete when:

- Existing generator features are reused, not rewritten unnecessarily.
- Every recipe declares topology rules.
- Accidental loops are rejected.
- Intentional loops are supported.
- Every loop is recipe-declared.
- Rejoins and revisits are recipe-declared.
- Every accepted puzzle has exactly one valid solution.
- Package rules cannot be bypassed.
- Shortcut paths are rejected.
- Layout is readable.
- Switch exits are visually distinct.
- Road crossings are not visually misleading.
- Hard and expert puzzles can include loops safely.
- Risky mechanics pass runtime parity validation.
- Quality score meets difficulty threshold.
- Reports explain every accepted/rejected candidate.
- Stress tests generate large batches with zero accepted invalid puzzles.

## Expected Player Outcome

Players should feel like each Tiny Routes level was hand-designed.

Good generated levels should have:

- A clear goal
- One correct route
- Tempting wrong choices
- Readable roads
- Fair switch decisions
- Difficulty that grows naturally
- No "random generator junk" feel
