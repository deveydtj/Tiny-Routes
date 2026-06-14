# Unique Solution Validator

Phase 5 extends the generated-level unique-solution enumerator with shortcut, package-before-goal, and wrong-branch classification. The validator is intentionally structural and bounded: it counts route/tap outcomes on the concrete generated graph, labels representative terminal paths, and rejects package bypasses or shortcut solutions, but it does not yet model exact tap timing, ignored-tap windows, or Swift runtime movement transitions.

## Existing Systems

- Route simulation: `PythonSolutionSimulatorService` executes the scripted sidecar against generated level data. It initializes every node's active outgoing edge to the first valid outgoing edge, rotates switches in `outgoingEdgeIDs` order, tracks package collection, blocks taps on the edge currently being departed, and fails on dead ends, package-missing destination arrival, time expiry, and simulation guard limits.
- Runtime parity reference: `RouteEngine`, `RuntimeRouteGraph`, and `NodeSwitchController` use the same first-valid-edge default and switch rotation order. Runtime also ignores taps while the dot is leaving a tapped node or transitioning through that node.
- Solution generation: `SolutionBuilderService` writes timed taps, expected edge/route metadata, `solutionRoute`, and `requiredTapOrder`. The validator compares enumerated successful paths against this intended route and tap order.
- Graph traversal: `AbstractPuzzleSolverService` performs recipe-level breadth-first traversal over current node, switch indices, package state, path, and taps. The unique-solution validator ports that state shape to concrete generated levels.
- Package validation: editor validation proves package and destination node references plus coarse reachability. Simulation proves the scripted route collects the package before destination. The unique-solution validator now rejects any enumerated destination arrival before package collection and reports package reachability status for the intended route.
- Candidate validation flow: `GeneratedLevelValidationService.validate()` is the generator acceptance gate before duplicate and quality scoring. The validator runs after scripted simulation succeeds and can reject generated candidates through normal validation messages.

## Integration Point

`UniqueSolutionValidatorService.validate_unique_solution()` is the dedicated entry point. The camel-case alias `validateUniqueSolution()` exists for parity with the Generator V2 plan language.

The validator reads `mechanicMetadata.topologyRules.requiresUniqueSolution`. If unique-solution validation is required, the accepted result is:

- `solutionCount == 1`
- the bounded search completed exhaustively within configured traversal limits

Generated candidates are rejected when the search finds zero solutions, more than one solution, or hits a traversal/state limit before uniqueness is proven. If more than one success is found, that is reported as `unique_solution_multiple_solutions` even when another branch later reaches a search limit, because two successes are already enough to reject the candidate.

Route-safety validation also runs when package or intended-route metadata exists, even if topology rules do not require full unique-solution counting. In that case the validator can still reject package bypasses, shortcut paths, and wrong-branch goal reaches without requiring `solutionCount == 1`.

## Search Strategy

The validator performs breadth-first structural enumeration. Each state represents a node arrival with the active switch configuration that will be used for future departures.

At each non-terminal node:

1. The validator reads valid outgoing edges in `outgoingEdgeIDs` order.
2. For plain route nodes, it follows the only outgoing edge.
3. For switch nodes, it enumerates every meaningful rotation count from the current active edge, excluding full-cycle no-op rotations.
4. It updates the active edge for the tapped node, appends tap history, traverses the selected edge, and records package collection if the next node is the package.
5. It treats reaching the destination with package collected as a valid solution and reaching destination before package collection as a failed terminal route.

Branches and rejoins are counted by path history, not collapsed by node alone. This means a shortcut branch that reaches the destination as a second valid package-before-destination route naturally produces `solutionCount > 1`.

The enumerator now preserves compact `UniqueSolutionPathSummary` samples for successful routes, destination-before-package routes, and failed terminal routes. Each summary includes node IDs, edge IDs, tap history, package/destination indexes, terminal reason, and route length. These summaries power the shortcut and wrong-branch checks without a second traversal.

## Shortcut and Package Checks

`validatePackageBeforeGoal()` rejects candidates when:

- the intended route metadata is missing, ambiguous, missing the package, reaches destination before package, or references missing route edges
- the search finds any `destination_before_package` terminal route
- package-gate metadata exists but the level cannot represent a distinct package before destination

`validateNoShortcutPath()` rejects candidates when:

- any route reaches destination before package collection
- more than one valid package-before-destination route exists
- the only valid route differs from `solutionRoute`
- the only valid route uses fewer route phases or fewer taps than `requiredTapOrder`
- the tap history reaches the goal with a different required switch/tap order

`validateWrongBranchesFailCorrectly()` inspects off-route edges that leave the intended route. Wrong branches are accepted when they clearly dead-end or fail before reaching destination. They are rejected when they reach destination as a valid solution, reach destination before package collection, or terminate only because the search hit a tap/depth limit.

Declared loops remain valid when the enumerated successful route matches the intended route, package order is unambiguous, and no off-route loop exit creates a valid route or package bypass.

## State Model

The current search state records:

- `current_node_id`
- `current_edge_id`, currently the edge most recently traversed
- active outgoing edge per node (`active_edge_by_node_id`)
- package-collected flag (`has_collected_package`)
- visited node history (`visited_node_ids`)
- revisit counts per node (`revisit_counts`)
- tap history (`tap_history`)
- traversal depth
- an elapsed-time placeholder for later runtime parity

The validation result records:

- `solutionCount`
- `exploredStates`
- `maxDepthReached`
- `terminationReason`
- `terminalReasonCounts`
- `isExhaustive`
- `shortcutDetected`
- `packageBypassDetected`
- `wrongBranchReachedGoal`
- `bypassPathSummary`
- `intendedRouteLength`
- `shortestValidRouteLength`
- `packageReachabilityStatus`
- representative success, package-bypass, and failure path summaries

## Traversal Limits

The implementation uses explicit bounds:

- `maxTraversalDepth`: at least `nodes * 4`, increased to `nodes * 8` for declared cycle/revisit topologies.
- `maxTaps`: at least the level/script tap count and large enough to allow every meaningful switch rotation at each traversal-depth step.
- `maxExploredStates`: at least `50000`, scaled by node and edge count for larger graphs.

Declared loops are traversable, but the search does not recurse forever. If a loop or broad branch space exceeds the depth or explored-state budget before uniqueness is proven, the candidate is rejected with `unique_solution_search_limit_reached`.

## Current Limitations

This phase is deliberately not a runtime-parity solver:

- It does not model exact tap timing, edge progress, smooth transitions, or ignored taps.
- It treats switch choices structurally at node arrival/departure time.
- It classifies structural shortcuts against `solutionRoute` and `requiredTapOrder`, but does not yet prove all visual or timing-based shortcut possibilities.
- It does not validate layout readability, visual route ambiguity, or scoring.
- It does not collapse semantically equivalent routes beyond excluding full-cycle no-op rotations at a single switch decision.
- It can reject a candidate when traversal limits prevent a proof, even if a deeper optimized solver might later prove uniqueness.
- It treats off-route branch behavior structurally. Full rejoin-specific and revisit-specific proof logic remains separate future work.

## Future Validation Requirements

The complete validator must eventually support:

- optimized loop and declared return-path proofs
- revisit-specific validation for switches and non-switch nodes
- rejoin-specific validation for multiple incoming branches
- repeated taps on the same switch
- multi-phase routes where a later switch state changes a previously visited area
- runtime parity for ignored taps and smooth pass-through transitions

## Recommended Next Phase

The next phase should add dedicated rejoin/revisit validators and runtime parity checks. Runtime parity should remain separate until structural classification is reliable.
