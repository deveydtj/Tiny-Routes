# Layout Readability Validation

`LayoutReadabilityValidator` is the Generator V2 Phase 7 acceptance gate for layouts that are logically valid but visually unfair.

Generated-level validation invokes it after structural graph checks, unique-solution enumeration, shortcut detection, package-bypass checks, declared rejoin validation, and declared revisit validation. It runs before quality scoring and candidate acceptance. The validator does not call Swift runtime validation, gameplay simulation, or quality scoring.

## Goal

A generated puzzle can have correct graph logic and still be unacceptable if the layout invites a reasonable player to misread it. Phase 7 rejects those candidates rather than letting quality scoring trade readability away for another score.

Examples:

- Two roads cross without an actual graph node.
- Two unrelated roads are close enough to look connected.
- Two switch exits visibly leave in the same direction.
- A package, start, goal, or switch sits under or too close to unrelated roads.
- Start and goal are so close that the objective reads as accidental.
- A portrait layout fits numerically but fails the intended phone-safe composition.

## Checks

`validateNoNodeOverlap()` / `validate_no_node_overlap()`

Rejects node pairs below the configured spacing threshold. Important nodes and switches use stricter spacing than ordinary route nodes.

`validateNoImplicitIntersectionWithoutNode()` / `validate_no_implicit_intersection_without_node()`

Rejects road segment crossings or unrelated road overlaps when no graph node exists at the visual intersection.

`validateRoadsNotTooClose()` / `validate_roads_not_too_close()`

Rejects unrelated road corridors below minimum spacing. Roads that share an endpoint are allowed so declared loops, rejoins, and revisits are preserved unless the actual geometry is confusing.

`validateSwitchExitSeparation()` / `validate_switch_exit_separation()`

Rejects switch exits whose first visible segment angles are too close together.

`validateNoOverlappingFirstSegments()` / `validate_no_overlapping_first_segments()`

Rejects outgoing roads from the same switch when their first visible road segments overlap.

`validateImportantNodeVisibility()` / `validate_important_node_visibility()`

Rejects layouts where start, package, destination, or switch nodes are too close to unrelated roads.

`validateStartGoalSeparation()` / `validate_start_goal_separation()`

Rejects layouts where start and destination are visually too close.

`validatePortraitSafety()` / `validate_portrait_safety()`

Rejects nodes outside the readable portrait safe area. For `portrait_vertical` layouts it also checks portrait aspect ratio, start-goal vertical separation, start lower placement, and goal upper placement.

## Thresholds

Thresholds live in `LayoutReadabilityThresholds` and are reported with each validation result. They are expressed in generator board units and are scaled upward from the active `DifficultyPreset.minimum_node_distance` where appropriate.

Current threshold fields:

- `minimumNodeSpacing`
- `importantNodeSpacing`
- `switchNodeSpacing`
- `minimumRoadSpacing`
- `switchExitMinimumAngleDegrees`
- `overlappingFirstSegmentMinimumLength`
- `importantNodeRoadClearance`
- `startGoalMinimumDistance`
- `portraitEdgeMargin`
- `portraitMaxAspectRatio`
- `portraitMinVerticalSeparation`

Harder difficulties do not get looser readability thresholds. Large portrait layouts receive their larger bounds through the generation preset override, not through lower readability standards.

## Reporting

Accepted-level JSON reports include `layoutReadability` with:

- `passed`
- `metadata`
- `issues`

Metadata includes these phase-level flags:

- `nodeOverlapDetected`
- `implicitIntersectionDetected`
- `roadsTooCloseDetected`
- `switchExitOverlapDetected`
- `importantNodeBlocked`
- `startGoalTooClose`
- `portraitSafetyFailure`

It also includes:

- `offendingNodes`
- `offendingRoads`
- `measuredDistances`
- `measuredAngles`
- `thresholds`
- `issueCounts`

Candidate rejection reasons are explicit. Common hard-failure codes include:

- `implicit_intersection_without_node`
- `switch_exit_overlap`
- `node_spacing_failure`
- `start_goal_separation_failure`
- `road_proximity_failure`
- `important_node_visibility_failure`
- `portrait_safety_failure`

## Current Limitations

- The validator uses generator road geometry, which is axis-aligned straight/L-shaped segments from `RoadShapeService`. It does not sample Swift-rendered rounded corners.
- Portrait safety checks use generator metadata and coordinate bounds, not device-specific safe-area insets.
- Important switches currently mean all switchable nodes. If a future recipe distinguishes major/minor switches, this can be narrowed through recipe metadata.
- Road thickness, labels, package artwork, and destination artwork are approximated as geometric clearance thresholds rather than measured from rendered pixels.
- Existing Phase 6 visual-clarity warnings still feed quality scoring; Phase 7 only handles hard layout rejection.
