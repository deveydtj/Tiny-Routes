# Unique Solution Validator Framework

Phase 3 prepares Generator V2 for strict unique-solution validation without implementing exhaustive path enumeration yet.

## Existing Systems Audited

- Route simulation: `PythonSolutionSimulatorService` executes the scripted sidecar against generated level data. It initializes every node's active outgoing edge to the first valid outgoing edge, rotates switches in `outgoingEdgeIDs` order, tracks package collection, blocks taps on the edge currently being departed, and fails on dead ends, package-missing destination arrival, time expiry, and simulation guard limits.
- Runtime parity reference: `RouteEngine`, `RuntimeRouteGraph`, and `NodeSwitchController` use the same first-valid-edge default and switch rotation order. Runtime also ignores taps while the dot is leaving a tapped node or transitioning through that node.
- Solution generation: `SolutionBuilderService` writes timed taps, expected edge/route metadata, `solutionRoute`, and `requiredTapOrder`. It generates one intended script but does not prove there is no alternate script.
- Graph traversal: `AbstractPuzzleSolverService` already performs recipe-level breadth-first traversal over current node, switch indices, package state, path, and taps. It is useful prior art, but it runs before concrete level layout and does not model timed runtime details.
- Package validation: editor validation proves package and destination node references plus coarse reachability. Simulation proves the scripted route collects the package before destination. No current validator proves all successful routes must collect the package in the intended order.
- Candidate validation flow: `GeneratedLevelValidationService.validate()` is the generator acceptance gate before duplicate and quality scoring. The new validator is registered there after scripted simulation, so future unique-solution errors can reject candidates in the same flow.

## Integration Point

`UniqueSolutionValidatorService.validate_unique_solution()` is the dedicated entry point. The camel-case alias `validateUniqueSolution()` exists for parity with the Generator V2 plan language.

The Phase 3 implementation is intentionally non-rejecting:

- It reads `mechanicMetadata.topologyRules.requiresUniqueSolution`.
- It builds the initial search state and validation config.
- It stores the result on `GeneratedLevel.unique_solution_validation_result`.
- It returns no validation issues until exhaustive counting is implemented.

Future phases should add `error` issues from this service only when the validator is exhaustive enough for the topology under inspection.

## Required State Model

The validator must model at least:

- `current_node_id`
- `current_edge_id` and eventually transition state for runtime parity
- active outgoing edge per node
- package-collected flag
- visited node history
- revisit counts per node
- tap history, including repeated taps
- traversal depth
- elapsed time or abstract time windows once timed parity is added
- max tap and max traversal-depth bounds derived from level/script/topology
- topology permissions for loops, revisits, rejoins, and package gates

## Future Validation Requirements

The complete validator must eventually support:

- loops and declared return paths
- revisits to switches and non-switch nodes
- rejoin paths with multiple incoming branches
- package gates and package-bypass rejection
- repeated taps on the same switch
- multi-phase routes where a later switch state changes a previously visited area
- shortcut detection before and after package collection
- runtime parity for ignored taps and smooth pass-through transitions

## Recommended Implementation Sequence

1. Path enumeration: port the recipe-level BFS state shape to concrete generated levels, enumerating switch choices up to configured tap and traversal-depth bounds. Count only terminal states that reach destination after package collection.
2. Shortcut detection: classify successful paths that do not match the intended `solutionRoute` or that reach destination with fewer taps, fewer route steps, or a bypassed required node.
3. Package order validation: split successful/failed terminal states by package-collected state and reject any destination-before-package route that can be repaired into a valid shortcut without the intended gate.
4. Revisit support: add loop-aware seen keys that include bounded visit counts, tap history, and active switch state so declared loops are searchable without infinite traversal.
5. Rejoin support: preserve path history through branches and compare rejoined states by package/tap/switch context, not node alone.
6. Runtime parity: add optional timing and ignored-tap modeling after structural uniqueness is reliable.
