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

- [x] Updated `SwitchArrowDirectionResolver` to expose `directionAngleForRoadPathStart(_:)` and use the road-path start tangent before falling back to target-node vectors.
- [x] Added focused Swift tests for straight horizontal roads, straight vertical roads, horizontal-first L-roads, vertical-first L-roads, the level-028-style fixture, and active outgoing edge arrow changes.
- [x] Added `SwitchVisualClarityService` for Python-side generator validation.
- [x] Added generator validation errors for ambiguous switch visual directions, duplicate switch direction buckets, and solution taps that cycle to visually confusing edges.
- [x] Updated `GraphBuilderService` to choose distinct switch outgoing road-shape buckets where a clear assignment exists, while preserving explicit road-shape overrides for validation to judge.
- [x] Added generator tests for duplicate right-exit rejection, distinct up/right/down/left exits, and L-shaped first-segment direction bucketing.
- [x] Added switch visual direction bucket details to JSON generation reports under each switch preview.
- [x] Confirmed rejection reason counts include visual switch failures through the existing validation/rejection path.
- [x] Updated affected checked-in production level `roadShape` fields so existing levels pass the stricter visual-clarity gate without changing topology or solution timings.

Verification:

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests
```

Result: `147 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 Tools/LevelGenerator/run_all_generator_checks.py --python /Library/Frameworks/Python.framework/Versions/3.13/bin/python3
```

Result: passed. The check suite ran Python tests, smoke dry-run generation, and validation for production levels `level_001` through `level_030` with Swift tests disabled by the script.

```bash
xcodebuild test -scheme TinyRoutes -destination 'platform=iOS Simulator,id=CE7E87CB-2EDB-4E6B-AC65-AA1BDCA416AD' -only-testing:TinyRoutesTests/RouteEngineTests
```

Result: `TEST SUCCEEDED`; 91 `RouteEngineTests` passed.

```bash
xcodebuild test -scheme TinyRoutes -destination 'platform=iOS Simulator,id=CE7E87CB-2EDB-4E6B-AC65-AA1BDCA416AD' -only-testing:TinyRoutesTests/LevelRepositoryTests
```

Result: `TEST SUCCEEDED`; 30 `LevelRepositoryTests` passed.

## Phase 2 - Move From Template-First to Recipe-First Generation

Completed:

- [x] Added the recipe-generation contract surface:
  - [x] `MechanicRecipeGenerator`
  - [x] `RecipeFamily`
  - [x] `RecipeVariantSpec`
- [x] Added `RecipeFamilyRegistry` as the recipe-family selection boundary.
- [x] Added legacy-compatible recipe-family placeholders for the current template families:
  - [x] `straight_delivery`
  - [x] `single_switch`
  - [x] `package_gate`
  - [x] `return_loop`
  - [x] `multi_switch_chain`
  - [x] `ring_route`
  - [x] `four_way_intersection`
- [x] Marked existing `LevelTemplate` classes as legacy-compatible through the shared base class.
- [x] Added generation architecture config fields:
  - [x] `generation_mode`: `legacy_template`, `recipe_first`, `hybrid`
  - [x] `recipe_pool_size`
  - [x] `layouts_per_recipe`
  - [x] `road_shapes_per_layout`
- [x] Added CLI options:
  - [x] `--generation-mode`
  - [x] `--recipe-pool-size`
  - [x] `--layouts-per-recipe`
  - [x] `--road-shapes-per-layout`
- [x] Added report payload fields for the new architecture config values.
- [x] Implemented recipe-family graph production for each current template family:
  - [x] `straight_delivery`
  - [x] `single_switch`
  - [x] `package_gate`
  - [x] `return_loop`
  - [x] `multi_switch_chain`
  - [x] `ring_route`
  - [x] `four_way_intersection`
- [x] Updated `LevelGenerationService` to choose recipe families in `recipe_first` and `hybrid` mode.
- [x] Added abstract recipe validation before layout generation.
- [x] Added recipe candidate pool, layout-per-recipe, and road-shape-per-layout expansion.
- [x] Added recipe-first metadata to generated candidates:
  - [x] recipe family
  - [x] recipe variant
  - [x] abstract graph signature
  - [x] selected layout variant
  - [x] selected road-shape strategy
- [x] Added GUI state and controls for the new options.
- [x] Updated reports to show recipe source metadata.
- [x] Fixed the initial recipe-first return-loop layout failure by moving handcrafted family layout seeds into the layout builder rather than storing coordinates in recipe objects.

Verification:

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests/test_recipe_family_registry.py Tools/LevelGenerator/tests/test_generation_service.py Tools/LevelGenerator/tests/test_cli.py
```

Result: `25 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests
```

Result: `153 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests
```

Result: `156 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 Tools/LevelGenerator/run_all_generator_checks.py --python /Library/Frameworks/Python.framework/Versions/3.13/bin/python3
```

Result: passed. The check suite ran Python tests, smoke dry-run generation, and validation for production levels `level_001` through `level_030` with Swift tests disabled by the script.

```bash
xcodebuild test -scheme TinyRoutes -destination 'platform=iOS Simulator,id=CE7E87CB-2EDB-4E6B-AC65-AA1BDCA416AD' -only-testing:TinyRoutesTests/RouteEngineTests -only-testing:TinyRoutesTests/LevelRepositoryTests
```

Result: `TEST SUCCEEDED`; 121 selected Swift tests passed.

## Phase 3 - Abstract Puzzle Solver

Completed:

- [x] Added `AbstractPuzzleSolverService`.
- [x] Added explicit switch-state search over recipe graphs:
  - [x] default active outgoing edge is index `0`
  - [x] tap order rotates through outgoing edges in recipe/build order
  - [x] two-way, three-way, and four-way switches are supported through bounded outgoing-edge counts
  - [x] repeated switch taps are rejected when the difficulty preset has not unlocked them
- [x] Added bounded breadth-first exploration with max tap, state, and path-step guards.
- [x] Added solved recipe metadata:
  - [x] `solutionTapNodeIDs`
  - [x] `solutionSwitchStates`
  - [x] `requiredPath`
  - [x] `alternatePathCount`
  - [x] `deadEndCount`
  - [x] `loopCount`
  - [x] additional failure/false-route/repeated-tap metadata for reports
- [x] Updated recipe-first generation to solve every recipe before layout.
- [x] Added clear abstract solver rejection codes for invalid recipes, no-solution graphs, destination-before-package routes, repeated taps before unlock, excessive taps, too many equivalent solutions, too many outgoing switch edges, and no meaningful switch choices.
- [x] Added abstract solution metadata to JSON generation reports and a short summary to Markdown reports.
- [x] Added solver tests for:
  - [x] no-switch tutorial route
  - [x] single switch with wrong branch
  - [x] package gate
  - [x] return loop
  - [x] ring route
  - [x] four-way intersection
  - [x] unsolvable graph
  - [x] destination-before-package graph

Verification:

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests/test_abstract_puzzle_solver_service.py Tools/LevelGenerator/tests/test_generation_service.py::test_generation_service_recipe_first_supports_current_recipe_families Tools/LevelGenerator/tests/test_generation_service.py::test_generation_service_recipe_first_mode_generates_recipe_metadata
```

Result: `10 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests
```

Result: `164 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 Tools/LevelGenerator/run_all_generator_checks.py --python /Library/Frameworks/Python.framework/Versions/3.13/bin/python3
```

Result: passed. The check suite ran Python tests, smoke dry-run generation, and validation for production levels `level_001` through `level_030` with Swift tests disabled by the script.

## Phase 4 - Layout Planner

Completed:

- [x] Added `GraphLayoutPlannerService` as the recipe-first layout planning boundary.
- [x] Planner input is a solved abstract `GraphRecipe`; output includes node coordinates, strategy/variant metadata, layout hash, and validation issue codes.
- [x] Added layout strategies:
  - [x] horizontal route progression
  - [x] vertical route progression
  - [x] hub-and-spoke
  - [x] ring/loop
  - [x] package-inside-loop
  - [x] split-lane
  - [x] four-way intersection
- [x] Added layout spacing and composition checks:
  - [x] minimum node distance
  - [x] larger important-node distance
  - [x] board-edge margins
  - [x] switch-to-switch spacing
  - [x] package/destination separation
  - [x] dead-end readability
  - [x] switch edge/tap-target clearance
- [x] Added deterministic layout variation support for mirror, rotation, widen/narrow, route center shifting, and controlled jitter.
- [x] Wired recipe-first builds through the layout planner instead of direct recipe-position assignment.
- [x] Added layout metadata to generated candidates and JSON/Markdown reports.
- [x] Added validation rejection codes:
  - [x] `layout_node_cluster`
  - [x] `layout_important_nodes_too_close`
  - [x] `layout_switch_too_close_to_edge`
  - [x] `layout_package_destination_confusing`
  - [x] `layout_dead_end_not_readable`
- [x] Added tests for strategy bounds, important-node spacing, layout hash variation, clustered layout rejection, and recipe-family generation support.

Verification:

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests/test_graph_layout_service.py Tools/LevelGenerator/tests/test_generated_level_validation_service.py Tools/LevelGenerator/tests/test_generation_service.py::test_generation_service_recipe_first_supports_current_recipe_families Tools/LevelGenerator/tests/test_generation_service.py::test_generation_service_recipe_first_mode_generates_recipe_metadata
```

Result: `17 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests
```

Result: `168 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 Tools/LevelGenerator/run_all_generator_checks.py --python /Library/Frameworks/Python.framework/Versions/3.13/bin/python3
```

Result: passed. The check suite ran Python tests, smoke dry-run generation, and validation for production levels `level_001` through `level_030` with Swift tests disabled by the script.

## Phase 5 - Road Shape Planner

Completed:

- [x] Expanded `RoadShapeService` from single-edge shape selection into whole-graph road-shape planning.
- [x] Planner input now includes node positions, recipe edges, required path, important nodes, and outgoing switch choices inferred from graph topology.
- [x] Planner output includes per-edge road shapes, start/end direction buckets, route-edge flags, quality score, issue codes, and report-ready metadata.
- [x] Added road-shape alternatives:
  - [x] `auto`
  - [x] `all_straight`
  - [x] `horizontal_first`
  - [x] `vertical_first`
  - [x] `alternating`
  - [x] `switch_clarity_optimized`
  - [x] `crossing_minimized`
  - [x] `main_route_smoothed`
- [x] Wired recipe-first level building through the road-shape planner before constructing `RouteEdgeModel` values.
- [x] Added switch-exit scoring and validation metadata for duplicate starting tangents, overlapping same-switch first segments, required/wrong-route first-segment overlap, and four-way cardinal exit coverage.
- [x] Added crossing and overlap analysis for total crossings, crossings near important nodes, required-path crossings, long parallel segments, important-node proximity, endpoint-vector mismatch, and main-route smoothness breaks.
- [x] Added road-shape metadata to generated candidates, JSON reports, Markdown reports, and generation quality details.
- [x] Added validation messages for hard road-shape failures while leaving softer road-shape findings as quality/report warnings.
- [x] Updated recipe-first road-shape strategy expansion to include the new planner strategies.
- [x] Added tests for switch-exit separation, L-road tangent differences, crossing score penalties, overlapping first-segment failures, recipe-first metadata, and report quality details.

Verification:

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests/test_road_shape_service.py Tools/LevelGenerator/tests/test_generation_service.py::test_generation_service_recipe_first_mode_generates_recipe_metadata Tools/LevelGenerator/tests/test_generation_service.py::test_generation_service_recipe_first_supports_current_recipe_families -q
```

Result: `9 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests
```

Result: `172 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 Tools/LevelGenerator/run_all_generator_checks.py --python /Library/Frameworks/Python.framework/Versions/3.13/bin/python3
```

Result: passed. The check suite ran Python tests, smoke dry-run generation, and validation for production levels `level_001` through `level_021` with Swift tests disabled by the script.

## Phase 6 - Visual Clarity Validator

Completed:

- [x] Added standalone `VisualClarityValidationService`.
- [x] Added structured `VisualClarityIssue` and `VisualClarityReport` outputs with `error`, `warning`, and `info` severities.
- [x] Added route crossing, overlap, node spacing, switch exit direction, tap target spacing, and important-node readability rules.
- [x] Added switch-specific rule codes for duplicate start directions, ambiguous active arrows, hidden active edges, switch spacing, and missing four-way cardinal options.
- [x] Added route-specific rule codes for required-path self-crossings, wrong/required route crossings near switches, main-route-like dead ends, unclear return loops, and packages off the visual flow.
- [x] Added mobile-readability rule codes for switch tap target spacing, arrow/icon collision risk, important-node readability, and small-device spacing.
- [x] Wired visual clarity errors into generated-level validation and candidate rejection.
- [x] Wired visual clarity warnings into generation quality readability penalties.
- [x] Added visual clarity metadata and exact node/edge IDs to JSON generation reports.
- [x] Added tests for visual clarity rejection, warning quality penalties, and report node/edge ID output.

Verification:

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests/test_generated_level_validation_service.py Tools/LevelGenerator/tests/test_generation_quality_service.py Tools/LevelGenerator/tests/test_generation_report_repository.py Tools/LevelGenerator/tests/test_switch_visual_clarity_service.py
```

Result: `18 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests
```

Result: `175 passed`.

## Phase 7 - Runtime-Parity Simulation

Completed:

- [x] Audited Swift runtime movement and switch behavior across:
  - [x] `RouteEngine.swift`
  - [x] `RuntimeRouteGraph.swift`
  - [x] `NodeSwitchController.swift`
  - [x] `RoadPath` in `RouteEdge.swift`
  - [x] gameplay switch arrow rendering behavior from Phase 1
- [x] Expanded `RouteTimingService` to build Swift-parity road paths with straight segments, rounded horizontal-first/vertical-first L-road turns, point/tangent sampling, and perpendicular connector lengths.
- [x] Updated `PythonSolutionSimulatorService` to:
  - [x] use road-path-aware edge length
  - [x] model pass-through `DeliveryDotTransition` timing with `begin_transition` and `end_transition` trace events
  - [x] keep Swift switch rotation order through valid outgoing edge order
  - [x] reject taps ignored because the dot has already committed to the current edge
  - [x] reject taps ignored while the dot is in a transition at that node
- [x] Added parity fixture coverage for:
  - [x] straight road timing
  - [x] horizontal-first L-road timing
  - [x] vertical-first L-road timing
  - [x] pass-through connector timing
  - [x] return loop completion
  - [x] ring route completion
  - [x] four-way switch completion
- [x] Improved Swift validation hooks:
  - [x] `SwiftTestService` can target specific generated level IDs
  - [x] generated-level validation can pass scratch level and solution directories to XCTest through environment variables
  - [x] Swift test summaries include validation environment and structured failure details
  - [x] `LevelSolvabilityTests` can validate externally generated levels from explicit directories
- [x] Added production policy enforcement:
  - [x] hard/expert production generation requires `--swift-tests`
  - [x] ring/four-way production generation requires Swift validation
  - [x] dry runs remain Python-only friendly
- [x] Updated `level_017.solution.json` final tap timing from `5.42s` to `5.30s` so the stricter road-path-aware Python timing leaves the required pre-arrival buffer while Swift solvability still passes.

Verification:

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests
```

Result: `185 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 Tools/LevelGenerator/run_all_generator_checks.py --python /Library/Frameworks/Python.framework/Versions/3.13/bin/python3
```

Result: passed. The check suite ran Python tests, smoke dry-run generation, and validation for production levels `level_001` through `level_021` with Swift tests disabled by the script.

```bash
xcodebuild test -project TinyRoutes.xcodeproj -scheme TinyRoutes -destination 'platform=iOS Simulator,name=iPhone 16,OS=18.5' -only-testing:TinyRoutesTests/LevelSolvabilityTests -only-testing:TinyRoutesTests/LevelSimulationHarnessTests
```

Result: `TEST SUCCEEDED`; 19 selected Swift tests ran, with the external generated-level validation test skipped because no generated level IDs were requested through environment variables.

## Phase 8 - Difficulty Model and Campaign Progression

Completed:

- [x] Added expanded `DifficultyMetrics` output for generated levels:
  - [x] required tap count
  - [x] switch count
  - [x] four-way switch count
  - [x] repeated tap count
  - [x] solution path length
  - [x] false branch count
  - [x] loop count
  - [x] average time between required taps
  - [x] minimum reaction window before a required switch
  - [x] visual complexity score
  - [x] route crossing score
  - [x] package detour complexity
- [x] Added explanatory difficulty-band estimates for tutorial, easy, medium, hard, and expert.
- [x] Updated auto campaign weights to enforce mechanic unlock order:
  - [x] movement-only level 1
  - [x] single-switch before multi-switch
  - [x] package gate before return loop
  - [x] return loop before ring-route emphasis
  - [x] two-way switch families before four-way intersection emphasis
- [x] Added `CampaignPacingService` for batch-level scoring against previous campaign levels.
- [x] Penalized tap-count spikes, adjacent duplicate mechanics, repeated recipe-family streaks, and difficulty cliffs in generation quality.
- [x] Added mechanical difficulty, visual difficulty, estimated band, campaign pacing, and full metrics to JSON reports.
- [x] Added mechanical/visual difficulty summary lines to Markdown reports.
- [x] Added tests covering auto curve bands, unlock gates, simple tutorial metrics, hard-level complexity, and adjacent duplicate mechanic penalties.

Verification:

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests/test_difficulty_curve_service.py Tools/LevelGenerator/tests/test_difficulty_service.py Tools/LevelGenerator/tests/test_generation_quality_service.py Tools/LevelGenerator/tests/test_generation_service.py::test_generation_service_recipe_first_mode_generates_recipe_metadata -q
```

Result: `14 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests -q
```

Result: `194 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 Tools/LevelGenerator/run_all_generator_checks.py --python /Library/Frameworks/Python.framework/Versions/3.13/bin/python3
```

Result: passed. The check suite ran Python tests, smoke dry-run generation, and validation for production levels `level_001` through `level_030` with Swift tests disabled by the script.

## Phase 9 - Recipe Library Expansion

Completed:

- [x] Added 27 recipe-first families across the campaign bands:
  - [x] Tutorial: `straight_delivery_intro`, `single_switch_intro`, `single_switch_wrong_dead_end`, `package_before_destination_intro`
  - [x] Easy: `single_switch_package_choice`, `two_switch_order_intro`, `short_detour_gate`, `safe_dead_end_choice`, `package_gate_simple`
  - [x] Medium: `multi_switch_order`, `package_gate_double_choice`, `return_loop_intro`, `split_path_rejoin`, `fake_shortcut`, `hub_choice`
  - [x] Hard: `return_loop_with_gate`, `ring_route_gate`, `multi_switch_revisit`, `package_inside_loop`, `two_phase_route`, `branch_then_rejoin_with_wrong_order`
  - [x] Expert: `four_way_intro`, `four_way_package_gate`, `four_way_ring`, `multi_four_way_route`, `controlled_repeated_taps`, `late_route_reversal`
- [x] Added structured recipe mechanic metadata:
  - [x] intended mechanic
  - [x] supported difficulties
  - [x] required player skill
  - [x] allowed switch and tap counts
  - [x] repeated-tap allowance
  - [x] visual layout requirements
  - [x] design/usefulness reason
  - [x] mechanic tags, unlock requirement, and prior dependency
- [x] Added expanded recipe families to `RecipeFamilyRegistry` and mixed recipe selection.
- [x] Updated campaign recipe weights by difficulty and level-number unlock progression.
- [x] Added mechanic metadata to generated candidates, candidate selection summaries, solution review notes, JSON reports, and Markdown reports.
- [x] Added tests proving every expanded family produces a valid recipe, solves through the abstract solver, builds a layout, and passes final Python validation for a deterministic seed.
- [x] Scoped the batch smoke test to a small deterministic candidate pool so it still covers all difficulty bands without running production-sized search inside the unit suite.

Verification:

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests/test_recipe_family_registry.py Tools/LevelGenerator/tests/test_difficulty_curve_service.py Tools/LevelGenerator/tests/test_generation_report_repository.py::test_generation_report_repository_writes_recipe_mechanic_metadata Tools/LevelGenerator/tests/test_generation_service.py::test_generation_service_recipe_first_supports_current_recipe_families
```

Result: `11 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests
```

Result: `219 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 Tools/LevelGenerator/run_all_generator_checks.py --python /Library/Frameworks/Python.framework/Versions/3.13/bin/python3
```

Result: passed. The check suite ran Python tests, deterministic smoke dry-run generation with scoped candidate search, and validation for production levels `level_001` through `level_030` with Swift tests disabled by the script.

## Phase 10 - Candidate Search, Scoring, and Selection

Completed:

- [x] Updated candidate-pool defaults for production-quality selection:
  - [x] default `candidate_pool_size` is now `25`
  - [x] default `max_attempts_per_level` is now `300`
  - [x] explicit `candidate_pool_size=1` remains supported for fast tests
  - [x] production generation emits a warning when pool size is `1`
- [x] Expanded `GenerationQualityScore` and report payloads with:
  - [x] abstract mechanic quality
  - [x] runtime solvability
  - [x] visual readability
  - [x] switch clarity
  - [x] difficulty fit
  - [x] uniqueness
  - [x] campaign pacing
  - [x] mobile tap comfort
  - [x] visual appeal
- [x] Added hard quality rejection thresholds for:
  - [x] minimum total quality
  - [x] minimum switch clarity
  - [x] minimum runtime confidence
  - [x] maximum similarity
- [x] Added soft quality penalties for awkward tap timing, route simplicity/complexity mismatch, crossings, tight spacing, and repeated recipe-family pacing.
- [x] Added candidate selection summaries to generation results and reports:
  - [x] accepted candidate score breakdown
  - [x] top rejected near-miss candidates
  - [x] selection rationale explaining why the accepted candidate won
  - [x] minimum, average, and maximum scored candidate totals per generated level
- [x] Added tests for expanded quality categories, clarity threshold rejection, production pool-size warnings, selection summaries, and deterministic pool selection.

Verification:

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests -q
```

Result: `198 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 Tools/LevelGenerator/run_all_generator_checks.py --python /Library/Frameworks/Python.framework/Versions/3.13/bin/python3
```

Result: passed. The check suite ran Python tests, smoke dry-run generation, and validation for production levels `level_001` through `level_030` with Swift tests disabled by the script.

## Phase 11 - Generated Solution Sidecars and Human-Friendly Timing

Completed:

- [x] Added generated solution metadata:
  - [x] per-tap reason text
  - [x] expected edge after tap
  - [x] reaction window before switch arrival
  - [x] switch state before and after tap
- [x] Added sidecar-level metadata:
  - [x] template and recipe family/variant where available
  - [x] intended solution route
  - [x] required tap order
  - [x] generated seed
  - [x] solution metadata validation version
- [x] Added generated-candidate timing validation:
  - [x] difficulty-aware minimum tap spacing
  - [x] difficulty-aware reaction window before switch arrival
  - [x] first-tap grace after level start for non-tutorial levels
  - [x] stricter repeated-tap spacing outside expert levels
- [x] Hardened generated solution validation for missing sidecars, level ID mismatches, placeholder sidecars, non-switch tap targets, tap spacing, and Python simulation failure.
- [x] Added solution route and required tap summaries to JSON and Markdown generation reports.
- [x] Added tests covering metadata output, matching level IDs, missing sidecars, early taps, rapid repeated taps, and report solution payloads.

Verification:

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests/test_solution_builder_service.py Tools/LevelGenerator/tests/test_generated_level_validation_service.py Tools/LevelGenerator/tests/test_generation_report_repository.py -q
```

Result: `21 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m pytest Tools/LevelGenerator/tests -q
```

Result: `217 passed`.

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 Tools/LevelGenerator/run_all_generator_checks.py --python /Library/Frameworks/Python.framework/Versions/3.13/bin/python3
```

Result: passed. The check suite ran Python tests, smoke dry-run generation, and validation for production levels `level_001` through `level_030` with Swift tests disabled by the script.
