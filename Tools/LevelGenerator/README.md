# Tiny Routes Level Generator

Procedural generation tool for creating Tiny Routes production level JSON and matching solution sidecar files. The generator writes the same shapes used by the Swift runtime and the Python Level Editor, then validates candidates before saving them.

## Install

The generator runtime uses only the Python standard library:

```bash
python Tools/LevelGenerator/generate_levels.py --help
```

On macOS setups without a `python` shim, use `python3` for the same commands.

Tests use `pytest`, matching the existing tool tests:

```bash
python -m pytest Tools/LevelGenerator/tests
```

Map-inspired generation is optional and intentionally separate. Normal generation does not require network access. See `app/map_import/README.md`.

## Quick Start

Dry-run one tutorial level:

```bash
python Tools/LevelGenerator/generate_levels.py --start 12 --count 1 --difficulty tutorial --template straight_delivery --seed 1 --dry-run
```

## Smoke Test

Start with this deterministic dry run when setting up or changing the generator:

```bash
python Tools/LevelGenerator/generate_levels.py --start 99 --count 2 --difficulty easy --template mixed --seed 123 --dry-run
```

Expected behavior:

- The command exits successfully.
- It prints accepted candidates.
- It writes reports if report paths are configured.
- It does not write level or solution files in dry-run mode.

Write one tutorial level and matching solution:

```bash
python Tools/LevelGenerator/generate_levels.py --start 12 --count 1 --difficulty tutorial --template straight_delivery --seed 1
```

Generate multiple levels:

```bash
python Tools/LevelGenerator/generate_levels.py --start 12 --count 5 --difficulty easy --template mixed --seed 1234
```

Generate along the default campaign curve:

```bash
python Tools/LevelGenerator/generate_levels.py --start 1 --count 30 --difficulty auto --template mixed --seed 1234 --dry-run
```

Validate generated files:

```bash
python Tools/LevelGenerator/validate_generated_levels.py --levels level_012 level_013
```

Delete generated levels and matching solution sidecars:

```bash
python Tools/LevelGenerator/delete_levels.py 31-35 --dry-run
```

Rebuild the production manifest:

```bash
python Tools/LevelGenerator/rebuild_manifest.py
```

Run the local generator check suite:

```bash
python Tools/LevelGenerator/run_all_generator_checks.py
```

## Simple GUI

Run:

```bash
python Tools/LevelGenerator/launch_gui.py
```

The GUI is a thin wrapper around the same generation and validation services used by the CLI. Use dry-run first, then write to a temporary output folder before writing production levels. The GUI writes the same markdown and JSON reports as the CLI.

Use a Python 3.10+ interpreter with Tkinter enabled.

## Options

`--overwrite` allows replacing existing level and solution files. Without it, the generator refuses to overwrite anything.

`--dry-run` generates and validates candidates without writing level or solution files. Reports are still written when report paths are configured.

`--seed` makes generation reproducible. Candidate seeds are recorded in the markdown and JSON reports.

`--swift-tests` runs the real Swift solvability tests after files are written. `--no-swift-tests` skips them.

### Runtime Parity Validation

Runtime parity means the Python generator and the real Tiny Routes Swift runtime agree about a generated level. Python validation checks graph structure, solution sidecars, unique-solution evidence, road geometry, and tap timing before a candidate can be selected. Runtime parity is the extra gate for mechanics where the exact `RouteEngine` behavior matters: the generated level must load in Swift, the solution sidecar must replay through the runtime, switch taps must rotate to the expected runtime edge, package collection must happen before completion, repeated taps must behave correctly, and the road-shape choices must be interpreted by gameplay in the same way the generator expected.

The generator marks runtime parity as required when any of these are present:

- `RecipeTopologyRules.requiresSwiftRuntimeValidation`
- candidate-level `requires_swift_validation`
- four-way switches
- rings, loops, return paths, revisits, repeated taps, or route reversal
- split/rejoin or declared rejoin mechanics
- package-inside-loop or multi-phase/two-phase route mechanics
- concrete graph evidence of four-way fanout, cycles, repeated route nodes, repeated tap nodes, rejoins, or package nodes inside a detected cycle

Dry runs may skip Swift validation so iteration stays fast. Reports still show the production requirement with fields such as `runtimeValidationRequired`, `runtimeValidationStatus`, `runtimeValidationReason`, `swiftValidationCommand`, `swiftValidationPassed`, `swiftValidationSkippedReason`, `riskyMechanicTags`, and `requiresSwiftRuntimeValidation`. For a dry run that finds a risky candidate, expect `runtimeValidationStatus: skipped_required_for_production`.

Production writes are stricter. If a candidate requires runtime parity and `--swift-tests` is not enabled, the candidate is rejected with `missing_required_swift_validation`. With `--swift-tests`, the candidate is marked pending while files are written, then the generator runs:

```bash
xcodebuild test -project TinyRoutes.xcodeproj -scheme TinyRoutes -destination 'platform=iOS Simulator,name=iPhone 16,OS=18.5' -only-testing:TinyRoutesTests/LevelSolvabilityTests/testRequestedGeneratedLevelsCompleteFromEnvironmentDirectories
```

The command receives `TINY_ROUTES_VALIDATION_LEVEL_IDS`, `TINY_ROUTES_LEVELS_DIR`, and `TINY_ROUTES_SOLUTIONS_DIR` so Swift replays only the generated level and solution sidecar files for that batch. Swift failures are surfaced as `swift_runtime_parity_failed`, `solution_sidecar_runtime_mismatch`, `switch_tap_runtime_mismatch`, or `package_order_runtime_mismatch` when the xcodebuild output contains enough detail to classify them.

Current limitations:

- Swift parity runs after generated files are written because the existing Swift test harness loads level and solution sidecar directories from disk.
- Failure attribution is batch-level when xcodebuild fails; inspect the Swift failure details for the exact level.
- Road-shape parity is covered through RouteEngine movement and switch-direction metadata in reports, not by Swift-rendered pixel inspection.
- Dry-run reports are advisory for runtime parity; run production generation with `--swift-tests` before committing risky mechanics.

`--compare-existing` rejects candidates that are too similar to existing level files in the configured output folders. This is enabled by default; use `--no-compare-existing` for scratch experiments.

`--generation-mode` controls the generation architecture. `recipe-first` is the default and preferred path; `legacy-template` and `hybrid` remain available for comparison and fallback runs.

Recipe-first generation solves multiple abstract recipes before layout, then tries layout and road-shape variants. The default breadth is 4 recipes, 2 layouts per recipe, 2 road-shape strategies per layout, and 4 valid candidates scored before accepting the best one.

`--layout-orientation` defaults to `portrait_vertical`. This profile asks recipe-first layouts to compose routes for mobile portrait play: the generated map should be taller than wide, the start should sit in the lower portion of the layout, and the destination should sit in the upper portion. Horizontal branches, detours, and side movement are still allowed when the overall composition passes the portrait safety checks.

`--layout-size-profile` defaults to `difficulty_curve`. That resolver keeps tutorial and easy levels on `standard_portrait`, introduces occasional `large_portrait` candidates for medium route-interest layouts, and offers more large portrait candidates for hard/expert routes that benefit from extra vertical room. Use explicit `standard_portrait` or `large_portrait` only for targeted experiments. Large portrait keeps the same recipe families and validation rules, but expands the vertical coordinate bounds and asks vertical/portrait layouts to preserve more space between route nodes. It does not automatically convert every generated level to a large map.

Generation reports include the selected layout profile, layout size profile, and lightweight portrait metrics: width, height, aspect ratio, start-to-destination vertical separation, and whether portrait checks passed. The Swift gameplay camera uses runtime level extents to decide whether a generated large portrait level should scroll instead of being scaled down to one screen.

`--candidate-pool-size` scores multiple valid candidates for each level and accepts the highest-scoring one. Reports include quality, pacing, route-interest, difficulty-fit, and simulation details.

### Generation Reports

The CLI and GUI write the same Markdown and JSON reports when report paths are configured. The JSON report is the audit source of truth; the Markdown report is optimized for quick human review.

Each accepted level and candidate-selection summary uses standardized candidate status fields:

- `candidateID`, `levelID`, `seed`, `difficulty`
- `recipeFamily`, `recipeVariant`, `topologyClass`, `mechanicTags`
- `status`
- `acceptedOrRejectedReason`
- `validationStage`
- `rejectionCode`
- `rejectionDetails`

`status` is `accepted`, `rejected`, or `not_selected`. `validationStage` identifies the gate that accepted or rejected the candidate:

- `topology_validation`
- `unique_solution_validation`
- `shortcut_validation`
- `package_validation`
- `rejoin_validation`
- `revisit_validation`
- `layout_readability_validation`
- `road_shape_validation`
- `runtime_parity_validation`
- `quality_scoring`
- `candidate_selection`

Accepted candidates expose nested reports for `topologyReport`, `solverReport`, `layoutReadabilityReport`, `roadShapeReport`, `runtimeParityReport`, and `qualityScoreBreakdown`. Rejected candidates are recorded in `rejectedCandidateSummaries` with the same status fields plus any available topology, solver, layout, road-shape, runtime, and quality metadata. Valid candidates that pass all hard gates but lose candidate selection are listed under `candidateSelection[].notSelectedCandidates`; they are not counted as hard rejections.

Use these aggregate fields first when debugging a failed or starved batch:

- `rejectionReasonCounts`
- `rejectionStageCounts`
- `topRejectedNearMisses`
- `acceptedDifficultyDistribution`
- `acceptedRecipeDistribution`
- `acceptedTopologyDistribution`
- `acceptedMechanicDistribution`
- `acceptedMapSizeDistribution`

Common rejection-code families map directly to stages. `quality_*`, `route_interest_below_*`, `boring_topology_for_difficulty`, and `large_portrait_without_puzzle_need` are quality-scoring rejections. `candidate_too_similar_to_batch`, `candidate_too_similar_to_existing`, and `not_selected` are candidate-selection outcomes. `missing_required_swift_validation` and `swift_runtime_parity_failed` are runtime-parity failures. Layout readability codes include `node_spacing_failure`, `implicit_intersection_without_node`, `road_proximity_failure`, `switch_exit_overlap`, `important_node_visibility_failure`, `start_goal_separation_failure`, and `portrait_safety_failure`. Road-shape codes include `ambiguous_switch_exit`, `conflicting_direction_bucket`, `insufficient_exit_separation`, and crossing/proximity road-shape issues.

Debug a rejected candidate by starting with `candidateID`, `seed`, `recipeFamily`, `recipeVariant`, `validationStage`, `rejectionCode`, and `rejectionDetails`. Then inspect the stage-specific nested report. For example, use `solverReport` for solution count, package bypass, wrong-branch, shortcut, and traversal-limit questions; use `layoutReadabilityReport` for offending nodes/roads and measured distances; use `roadShapeReport` for switch direction buckets and exit-angle separation; use `qualityScoreBreakdown`, `difficultyFit`, `routeInterestFit`, and `pacingPenalties` for technically valid candidates rejected by scoring.

Run a safe stress dry-run into a scratch folder when tuning the curve:

```bash
python Tools/LevelGenerator/stress_test_generation.py --start 1 --count 20 --difficulty auto --seed 9001 --output-dir /tmp/tiny-routes-phase4-stress
```

The stress command forces `dry_run=True`, disables existing-production similarity checks, and writes only scratch reports. It prints and writes `stress_summary.json` with pass/fail rate, accepted difficulty distribution, recipe distribution, topology distribution, map-size distribution, and rejection reasons.

### Route-Interest Scoring

Recipe-first generation now includes route-interest scoring so accepted candidates are not chosen only because they validate cleanly. The score rewards small maze-like route decisions:

- fake shortcuts or visually tempting invalid branches
- split paths that rejoin later
- correct longer detours over obvious direct-looking paths
- package-before-destination tension
- loops or revisit-style paths on difficulties that support them
- multi-exit hub choices
- meaningful route turns instead of straight switch chains

It also penalizes boring topology:

- mostly straight switch chains
- route nodes that only pad length without adding a decision
- nearby repetition of the same topology class or mechanic tags
- candidates that become harder only by adding more switches
- recipe families whose graph shape collapses into the same underlying chain

Reports expose the selected recipe family, topology class, route-interest score, route-interest tags, bonuses, penalties, fake-shortcut/branch-rejoin/package-tension/loop flags, meaningful turn count, and repeated-topology penalty. Rejected near-misses include the same quality summary so it is clear why the accepted candidate won.

Phase 2 upgraded these recipe families first:

- `fake_shortcut`
- `split_path_rejoin`
- `long_detour_gate`
- `hub_choice`
- `package_inside_loop`
- `two_phase_route`

An interesting generated topology is one where the shortest-looking branch can be wrong, branches can rejoin, package collection changes the valid route, or a loop/revisit changes the exit decision. A boring topology is a straight line of switches with renamed dead ends or filler nodes that only increase travel time.

Large portrait generation is intentionally limited to layout scale and coordinate bounds. It does not create new recipe families, weaken validation, add hidden map areas, or modify production level JSON by itself.

`--difficulty auto` uses the default campaign curve: levels 1-3 tutorial, 4-10 easy, 11-25 medium, 26-40 hard, and 41+ expert.

`--map-seed-path` applies a saved map seed JSON to generated node positions. Map import is separate from production generation:

```bash
python Tools/LevelGenerator/import_map_seed.py --place "Imperial, Missouri, USA" --output /tmp/imperial-seed.json --cache-dir /tmp/tiny-routes-map-cache
```

## Difficulty and Templates

Supported difficulty presets:

- `tutorial`: 3-5 nodes, 0-1 switches, 0-1 taps, route length 2-4, standard portrait only, straight-line or single-branch topology, very low route-interest target, max visual complexity 0.34.
- `easy`: 5-7 nodes, 1-2 switches, 1-2 taps, route length 3-5, standard portrait only, single-branch/two-switch/detour/package-gate topology, mild optional detour/package tension, max visual complexity 0.44.
- `medium`: 7-9 nodes, 2-3 switches, 2-3 taps, route length 5-7, mostly standard portrait with occasional large portrait candidates, optional split/rejoin, fake shortcut, package tension, detour, or meaningful-turn tags, max visual complexity 0.62.
- `hard`: 9-12 nodes, 3-5 switches, 3-5 taps, route length 7-10, frequent large portrait candidates for route structures that need room, stronger detour, loop/revisit, hub, two-phase, split/rejoin, and fake-shortcut tags, max visual complexity 0.76.
- `expert`: 8-13 nodes, 1-5 switches, 2-6 taps, route length 6-11, standard and large portrait candidates allowed when four-way, ring, revisit, or route-phase structures benefit, max visual complexity 0.86.
- `auto`

Quality scoring runs after strict validation. Validation decides whether a candidate is legal; scoring decides whether a legal candidate is worth selecting. A score can reject a weak candidate, but it cannot make an invalid candidate acceptable.

`PuzzleQualityScorer` reports a deterministic `0...100` `totalScore` plus five category scores:

- `logicScore`: unique-solution confidence, package order, shortcut absence, runtime confidence, and safe branch/rejoin/revisit behavior.
- `routeInterestScore`: meaningful decisions, fake shortcuts, split/rejoin structure, package tension, revisit/ring behavior, hubs, and meaningful turns. It caps candidates that get harder only by adding switches, nodes, or repetitive branches.
- `layoutScore`: readability, switch-exit clarity, road shape, visual clarity, spacing, and composition.
- `difficultyFitScore`: node/switch/tap counts, route length, estimated difficulty band, visual complexity, and tap pacing against the target preset.
- `diversityScore`: topology/mechanic difference from nearby accepted levels, campaign pacing, and signature uniqueness.

The generator prefers the highest `totalScore`, then route interest, layout, difficulty fit, diversity, logic, and finally the lower seed for deterministic tie-breaking. Difficulty minimums are tutorial `65`, easy `70`, medium `75`, hard `80`, and expert `85`. Reports include `categoryScores`, `topPositiveFactors`, and `topNegativeFactors` for accepted candidates and near misses.

Pacing rules compare each accepted candidate to nearby accepted signatures. They penalize adjacent recipe-family repeats, topology-class repeats, repeated fake shortcuts, repeated hubs, repeated loop/revisit usage, repeated switch-count/tap-count patterns, nearby mechanic-tag overlap, difficulty cliffs, and consecutive large portrait profiles. The scorer can still accept a repeated element when the rest of the candidate is clearly better, but the report shows the pacing penalty.

Supported templates:

- `straight_delivery`
- `single_switch`
- `package_gate`
- `return_loop`
- `multi_switch_chain`
- `ring_route`
- `four_way_intersection`
- `mixed`

`mixed` filters templates by difficulty and prefers safer templates for beginner presets.

## Xcode Troubleshooting

The repository uses `project.yml` as the XcodeGen source of truth and the checked-in `.xcodeproj` has explicit JSON resource references. When generation writes to the default production folders, the generator runs XcodeGen automatically before optional Swift tests:

```bash
python Tools/LevelGenerator/generate_levels.py --start 31 --count 5 --difficulty hard --template mixed --swift-tests
```

Use `--no-xcodegen` only when writing to a scratch folder or when you intentionally want to defer project regeneration. To sync manually:

```bash
xcodegen generate
```

If Xcode reports missing level JSON inputs after deleting or regenerating only part of a batch, run `xcodegen generate` so stale file references are removed from `TinyRoutes.xcodeproj`.

If `xcodebuild` is missing, install Xcode or run generation with `--no-swift-tests`, then validate on a Mac with Xcode before committing generated production levels.

## Generated-Level Review Checklist

- Dry-run generation works.
- Write generation works.
- Reports open correctly.
- Open generated level in the Level Editor.
- Confirm nodes are visually readable.
- Confirm route lines do not overlap badly.
- Confirm package and destination are obvious.
- Confirm dead ends look intentional.
- Run Python validation.
- Run Swift solvability tests when available.
- Play the level manually in simulator before committing.
- Commit level JSON and solution JSON together.

## Developer Workflow

- Work one task at a time and keep generated production files out of tests.
- Use scratch directories or `--dry-run` for experiments.
- Add or update tests with every service change.
- Keep `completion_status.md` current when finishing generator work.
- Run `python Tools/LevelGenerator/run_all_generator_checks.py` before relying on a production batch.

Good generated levels have readable routes, clear start/package/destination placement, intentional dead ends, difficulty-appropriate decision counts, and a non-placeholder solution sidecar. Confusing levels usually have crossing-heavy routes, clustered important nodes, or tap timing that only works by accident; reject those during review even when validation passes.
