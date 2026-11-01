# Tiny Routes Generation Report

- Generated: `2026-08-17T00:12:47.586825+00:00`
- Repo root: `/Users/jake/Developer/Tiny-Routes`
- Difficulty: `easy`
- Recipe family: `single_switch`
- Generation profile: `production`
- Generator architecture: `v2_legacy` (version `2`)
- Production eligible: `False`
- Warning: v2_legacy is a non-production compatibility mode. Its output cannot be promoted as new production content.
- Output schema versions: `[]`
- V2 pipeline mode: `recipe_first`
- Base seed: `101`
- Dry run: `False`
- Dry-run pass rate: `1.0`
- Compare existing levels: `False`
- Candidate pool size: `1`
- Candidate generation count: `16`
- Candidate validation count: `1`
- Rejection phases: `{'generationErrors': 0, 'validationFailures': 0, 'selectionFilters': 0}`
- Recipe pool size: `4`
- Layouts per recipe: `2`
- Road shapes per layout: `2`
- Playtest uniqueness window: `6`
- Layout orientation preference: `horizontal`
- Layout profile: `horizontal`
- Layout size profile: `difficulty_curve`
- Vertical route probability: `0.35`
- Prefer vertical for long routes: `True`
- Xcode project sync: `True`
- Swift tests: `Swift tests were not run.`

## Distributions

- Difficulty: `{'easy': 1}`
- Recipe: `{'single_switch': 1}`
- Topology: `{'single_branch': 1}`
- Mechanics: `{'dead_end': 1, 'single_switch': 1}`
- Family streaks: `{'longest': {'value': 'single_switch', 'length': 1}, 'repeatedStreaks': []}`
- Topology streaks: `{'longest': {'value': 'single_branch', 'length': 1}, 'repeatedStreaks': []}`
- Map size: `{'standard_portrait': 1}`
- Route interest score: `{'below_medium': 1}`
- Route interest by difficulty: `{'easy': {'minimum': 0.293, 'average': 0.293, 'maximum': 0.293, 'count': 1, 'distribution': {'below_medium': 1}}}`
- Candidate generation by difficulty: `{'easy': 16}`
- Candidate validation by difficulty: `{'easy': 1}`
- Accepted vs rejected by difficulty: `{'easy': {'accepted': 1, 'rejected': 0}}`
- Similarity rejections by difficulty: `{}`
- Starvation causes: `{'totalRejections': 0, 'phaseCounts': {'generationErrors': 0, 'validationFailures': 0, 'selectionFilters': 0}, 'topCategories': [], 'topReasons': []}`
- Rejection stages: `{}`

## Accepted Levels

| Level | Source | Mechanics | Topology | Path | Orientation | Diversity | Seed | Difficulty | Nodes | Edges | Switches | Par Taps | Time Limit | Quality | Preview | Signatures | Status |
|---|---|---|---|---:|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|---|
| `level_004` | `single_switch / single_switch_upper_package` | `single_switch: single_switch, dead_end` | `single_branch` | 4 | `horizontal` | `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0` | 737422275 | easy | 6 | 5 | 1 | 1 | 30 | 0.8194 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_004.svg) | `T:ccb92af3 L:4fa75257 S:69263e73` | accepted |

## Level Details

### `level_004`
- Recipe: `single_switch` variant `single_switch_upper_package`; abstract signature `c85139fbf346`.
- Mechanics: tags `single_switch, dead_end`; primary `single_switch`; topology `single_branch`; required path length `4`; layout orientation `horizontal` via `explicit_preference`; Swift-required `False`; runtime validation `not_required`; unlock `none`; depends on `none`.
- Diversity audit: topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0.
- Layout: `normal`; strategy: `horizontal_route_progression`; profile: `horizontal`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `horizontal`; road shapes: `auto` (score `0.96`).
- Portrait checks: passed `True`; width `2.0`, height `0.9`, aspect `2.2222`, start-destination vertical separation `0.3`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Layout readability: passed `True`, 0 issue(s); flags `{}`.
- Topology solution: 1 required decisions, 0 alternate paths, 1 dead ends, 0 loops.
- Topology rules: cycles `False` allowed `0` actual `0`; rejoin `False` declared `0`; revisit `False` declared `0`; return path `False`; ring `False`.
- Unique solution validation: solutions `1`, exhaustive `True`, explored states `6`, max depth `4`, traversal limit `False`, shortcut `False`, package bypass `False`, wrong branch reached goal `False`, package status `package_before_destination_on_intended_route`, shortest route `4`.
- Rejoin/revisit validation: rejoin detected `False` count `0` declared `0` unsafe `False` reason `None`; revisit detected `False` count `0` declared `0` unsafe `False` reason `None`.
- Runtime parity: required `False`; status `not_required`; requiresSwiftRuntimeValidation `False`; risky tags `none`; reason `No runtime-risk mechanics detected.`.
- Quality score: `81.94`/100; logic `95.92`, route interest `29.3`, layout `99.24`, difficulty fit `93.44`, diversity `100.0`.
- Quality factors: positives `unique solution confirmed, topology and mechanics differ from nearby accepted levels, route interest: meaningfulTurns, layout readability audit is clean, no shortcut route detected`; negatives `preset content fit penalties, estimated difficulty band differs from target, route weakness: fillerRouteNodes`.
- Difficulty model: estimated `medium`, mechanical `0.458`, visual `0.525`, campaign pacing `1.0`, preset fit `0.9405`.
- Score breakdown: mechanic `0.82`, runtime `1.0`, readability `0.99`, route interest `0.293`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9955`, diversity `1.0` (topology `1.0`, mechanic penalty `0.0`, topology penalty `0.0`).
- Route interest: score `0.293`; tags `meaningful_turns`; fake shortcut `False`; branch/rejoin `False`; package tension `False`; loop/revisit `False`; turns `2`; repeated topology penalty `0.0`.
- Decision profile: `1` decisions across `1` switches; dependencies `0`; independent ratio `1.0`; revisits `0`.
- Difficulty acceptance: required decision count 1 matches the selected easy preset.
- Strategic weaknesses: independent decision ratio is 1.000; preset content fit penalties; estimated difficulty band differs from target; route weakness: fillerRouteNodes; visual_complexity_above_preset_target; filler_route_nodes.
- Legacy front-load diagnostic: `True`.
- Activation window `upper_choice` visit `1`: `0.0`–`1.0`s; taps `[0.12]`; margin `0.12`s.
- Runtime actions: accepted `1`; rejected `0`.
- Mechanic evidence: `single_switch` from `descriptive recipe metadata`; `dead_end` from `descriptive recipe metadata`.
- Solution route: `start` -> `approach` -> `upper_choice` -> `package` -> `destination`.
- Required taps: tap `upper_choice` at `0.12s` -> `e_upper_choice_package` (unknowns window).
- Candidate selection: Selected with portfolio objective 0.9324; strongest factors: blueprintVariety=1.000, decisionDiversity=1.000, dependencyProgression=1.000. Hard campaign constraints passed; alternatives were retained and ranked with deterministic signature and seed tie-breakers. It ranked above 0 alternatives. Scores min/avg/max `81.94`/`81.94`/`81.94`.
- Accepted candidate audit: family `single_switch`; variant `single_switch_upper_package`; tags `single_switch, dead_end`; primary `single_switch`; topology `single_branch`; path `4`; orientation `horizontal`; Swift-required `False`; runtime validation `not_required`; strategy `horizontal_route_progression`; variant `normal`; orientation reason `explicit_preference`; route interest `0.293`; diversity `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0`.
- Switch `upper_choice` starts on `e_upper_choice_upper_dead_end` (north); tap 1 @ 0.12s -> `e_upper_choice_package` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'upper_choice' with 2 option(s).

## Rejections

- Rejected candidates: `0`
- Rejection stages: `{}`

## Messages

- Warning: production generation is using `candidate_pool_size=1`; use a larger pool for quality-based selection.
- Regenerated TinyRoutes.xcodeproj with xcodegen.

## Swift Test Summary

- Command: `not run`
- Result: `Swift tests were not run.`

## Next Steps

- Open generated levels in the Level Editor.
- Run Python validation and Swift solvability before committing production levels.
- `xcodegen generate` runs automatically for default production output; rerun it manually if resources were deleted outside the generator.
