# Tiny Routes Generation Report

- Generated: `2026-06-06T22:30:17.502164+00:00`
- Repo root: `/Users/jake/Developer/Tiny-Routes`
- Difficulty: `tutorial`
- Template mode: `mixed`
- Generation profile: `production`
- Generation mode: `recipe_first`
- Base seed: `None`
- Dry run: `False`
- Dry-run pass rate: `0.0302`
- Compare existing levels: `True`
- Candidate pool size: `4`
- Candidate generation count: `288`
- Candidate validation count: `232`
- Rejection phases: `{'generationErrors': 0, 'validationFailures': 37, 'selectionFilters': 177}`
- Recipe pool size: `6`
- Layouts per recipe: `3`
- Road shapes per layout: `2`
- Playtest uniqueness window: `6`
- Layout orientation preference: `portrait_vertical`
- Layout profile: `portrait_vertical`
- Layout size profile: `difficulty_curve`
- Vertical route probability: `0.35`
- Prefer vertical for long routes: `True`
- Xcode project sync: `True`
- Swift tests: `Swift tests were not run.`

## Distributions

- Difficulty: `{'tutorial': 7}`
- Recipe: `{'package_before_destination_intro': 1, 'single_switch': 1, 'single_switch_intro': 1, 'single_switch_wrong_dead_end': 1, 'straight_delivery': 2, 'straight_delivery_intro': 1}`
- Topology: `{'single_branch': 3, 'straight_line': 4}`
- Family streaks: `{'longest': {'value': 'package_before_destination_intro', 'length': 1}, 'repeatedStreaks': []}`
- Topology streaks: `{'longest': {'value': 'straight_line', 'length': 1}, 'repeatedStreaks': []}`
- Map size: `{'standard_portrait': 7}`
- Route interest score: `{'below_medium': 7}`
- Route interest by difficulty: `{'tutorial': {'minimum': 0.0, 'average': 0.0831, 'maximum': 0.345, 'count': 7, 'distribution': {'below_medium': 7}}}`
- Candidate generation by difficulty: `{'tutorial': 288}`
- Candidate validation by difficulty: `{'tutorial': 232}`
- Accepted vs rejected by difficulty: `{'tutorial': {'accepted': 7, 'rejected': 214}}`
- Similarity rejections by difficulty: `{'tutorial': 176}`
- Starvation causes: `{'totalRejections': 214, 'phaseCounts': {'generationErrors': 0, 'validationFailures': 37, 'selectionFilters': 177}, 'topCategories': [{'category': 'batchSimilarity', 'count': 177, 'share': 0.8271}], 'topReasons': [{'reason': 'candidate_too_similar_to_batch', 'count': 176, 'share': 0.8224}, {'reason': 'portrait_start_destination_not_vertically_separated', 'count': 37, 'share': 0.1729}, {'reason': 'quality_similarity_above_threshold', 'count': 1, 'share': 0.0047}]}`

## Accepted Levels

| Level | Source | Mechanics | Topology | Path | Orientation | Diversity | Seed | Difficulty | Nodes | Edges | Switches | Par Taps | Time Limit | Quality | Preview | Signatures | Status |
|---|---|---|---|---:|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|---|
| `level_001` | `package_before_destination_intro / package_before_destination_intro_alternate` | `straight_delivery: straight_delivery, long_route, package_order` | `straight_line` | 4 | `vertical` | `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0` | 1878254907 | tutorial | 5 | 4 | 0 | 0 | 30 | 0.8886 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_001.svg) | `T:1a988a48 L:752cf628 S:4ea3c0eb` | passed |
| `level_002` | `single_switch / single_switch_classic` | `single_switch: single_switch, dead_end` | `single_branch` | 3 | `vertical` | `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0` | 2962776876 | tutorial | 5 | 4 | 1 | 1 | 30 | 0.8462 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_002.svg) | `T:9e8f40a4 L:ce1bb14a S:fc75f4b5` | passed |
| `level_003` | `straight_delivery_intro / straight_delivery_intro_primary` | `straight_delivery: straight_delivery, intro` | `straight_line` | 2 | `vertical` | `topology 0.92, mechanic penalty 0.045, topology penalty 0.08, score 0.9358` | 4047298845 | tutorial | 3 | 2 | 0 | 0 | 30 | 0.8229 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_003.svg) | `T:2a12d2df L:ca3e45f9 S:4ea3c0eb` | passed |
| `level_004` | `single_switch_wrong_dead_end / single_switch_wrong_dead_end_primary` | `single_switch: single_switch, dead_end, switch` | `single_branch` | 3 | `vertical` | `topology 0.92, mechanic penalty 0.06, topology penalty 0.08, score 0.929` | 2014853202 | tutorial | 5 | 4 | 1 | 1 | 30 | 0.8118 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_004.svg) | `T:43bcc0ec L:91cf31d9 S:fc75f4b5` | passed |
| `level_005` | `straight_delivery / straight_delivery_0_intermediate` | `straight_delivery: straight_delivery` | `straight_line` | 2 | `vertical` | `topology 0.92, mechanic penalty 0.14, topology penalty 0.08, score 0.893` | 2218123499 | tutorial | 3 | 2 | 0 | 0 | 30 | 0.805 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_005.svg) | `T:2a12d2df L:c763c629 S:4ea3c0eb` | passed |
| `level_006` | `single_switch_intro / single_switch_intro_primary` | `single_switch: single_switch, dead_end, switch, intro` | `single_branch` | 3 | `vertical` | `topology 0.92, mechanic penalty 0.11, topology penalty 0.08, score 0.9065` | 3008145547 | tutorial | 5 | 4 | 1 | 1 | 30 | 0.8002 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_006.svg) | `T:9e8f40a4 L:819442f4 S:fc75f4b5` | passed |
| `level_007` | `straight_delivery / straight_delivery_1_intermediate` | `straight_delivery: straight_delivery` | `straight_line` | 3 | `vertical` | `topology 0.92, mechanic penalty 0.14, topology penalty 0.08, score 0.893` | 678951892 | tutorial | 4 | 3 | 0 | 0 | 30 | 0.8377 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_007.svg) | `T:d97fe243 L:5fbb97af S:4ea3c0eb` | passed |

## Level Details

### `level_001`
- Recipe: `package_before_destination_intro` variant `package_before_destination_intro_alternate`; abstract signature `7fd029991087`.
- Mechanics: tags `straight_delivery, long_route, package_order`; primary `straight_delivery`; topology `straight_line`; required path length `4`; layout orientation `vertical` via `portrait_profile_default`; Swift-required `False`; unlock `package objective introduced`; depends on `straight_delivery_intro`.
- Diversity audit: topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0.
- Layout: `normal`; strategy: `vertical_route_progression`; profile: `portrait_vertical`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `vertical`; road shapes: `auto` (score `0.96`).
- Portrait checks: passed `True`; width `0.7`, height `1.85`, aspect `0.3784`, start-destination vertical separation `1.85`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 0 required taps, 0 alternate paths, 0 dead ends, 0 loops.
- Difficulty model: estimated `easy`, mechanical `0.1948`, visual `0.365`, campaign pacing `1.0`, preset fit `0.9507`.
- Score breakdown: mechanic `0.69`, runtime `1.0`, readability `0.99`, route interest `0.345`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9865`, diversity `1.0` (topology `1.0`, mechanic penalty `0.0`, topology penalty `0.0`).
- Route interest: score `0.345`; tags `correct_detour, meaningful_turns`; fake shortcut `False`; branch/rejoin `False`; package tension `False`; loop/revisit `False`; turns `2`; repeated topology penalty `0.0`.
- Solution route: `start` -> `pickup_lane` -> `package` -> `exit_lane` -> `destination`.
- Required taps: none.
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.8886 vs 0.8594). Scores min/avg/max `0.8309`/`0.855`/`0.8886`.
- Accepted candidate audit: family `package_before_destination_intro`; variant `package_before_destination_intro_alternate`; tags `straight_delivery, long_route, package_order`; primary `straight_delivery`; topology `straight_line`; path `4`; orientation `vertical`; Swift-required `False`; strategy `vertical_route_progression`; variant `normal`; orientation reason `portrait_profile_default`; route interest `0.345`; diversity `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0`.
- Near miss `not_selected` seed `2172754828` score `0.8594` family `single_switch_intro` variant `single_switch_intro_primary` tags `single_switch, dead_end, switch, intro` primary `single_switch` topology `single_branch` path `3` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `normal` orientation reason `portrait_profile_default` route interest `0.035` diversity `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0`.
- Near miss `not_selected` seed `2467254749` score `0.8411` family `single_switch_wrong_dead_end` variant `single_switch_wrong_dead_end_primary` tags `single_switch, dead_end, switch` primary `single_switch` topology `single_branch` path `3` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `normal` orientation reason `portrait_profile_default` route interest `0.035` diversity `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0`.
- Near miss `not_selected` seed `2764002761` score `0.8309` family `single_switch` variant `single_switch_classic` tags `single_switch, dead_end` primary `single_switch` topology `single_branch` path `3` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `mirrored` orientation reason `portrait_profile_default` route interest `0.035` diversity `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0`.
- No switch-specific review notes.
### `level_002`
- Recipe: `single_switch` variant `single_switch_classic`; abstract signature `39f4e06795c7`.
- Mechanics: tags `single_switch, dead_end`; primary `single_switch`; topology `single_branch`; required path length `3`; layout orientation `vertical` via `portrait_profile_default`; Swift-required `False`; unlock `none`; depends on `none`.
- Diversity audit: topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0.
- Layout: `normal`; strategy: `vertical_route_progression`; profile: `portrait_vertical`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `vertical`; road shapes: `auto` (score `0.96`).
- Portrait checks: passed `True`; width `1.1`, height `1.85`, aspect `0.5946`, start-destination vertical separation `1.85`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 1 required taps, 0 alternate paths, 1 dead ends, 0 loops.
- Difficulty model: estimated `medium`, mechanical `0.4129`, visual `0.445`, campaign pacing `0.78`, preset fit `0.9265`.
- Score breakdown: mechanic `0.82`, runtime `1.0`, readability `0.99`, route interest `0.035`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9955`, diversity `1.0` (topology `1.0`, mechanic penalty `0.0`, topology penalty `0.0`).
- Route interest: score `0.035`; tags `none`; fake shortcut `False`; branch/rejoin `False`; package tension `False`; loop/revisit `False`; turns `1`; repeated topology penalty `0.0`.
- Solution route: `start` -> `choice` -> `package` -> `destination`.
- Required taps: tap `choice` at `0.31s` -> `e_choice_package` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.8462 vs 0.8279). Scores min/avg/max `0.8024`/`0.8221`/`0.8462`.
- Accepted candidate audit: family `single_switch`; variant `single_switch_classic`; tags `single_switch, dead_end`; primary `single_switch`; topology `single_branch`; path `3`; orientation `vertical`; Swift-required `False`; strategy `vertical_route_progression`; variant `normal`; orientation reason `portrait_profile_default`; route interest `0.035`; diversity `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0`.
- Near miss `not_selected` seed `140309185` score `0.8279` family `single_switch_wrong_dead_end` variant `single_switch_wrong_dead_end_alternate` tags `single_switch, dead_end, switch` primary `single_switch` topology `single_branch` path `3` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `normal` orientation reason `portrait_profile_default` route interest `0.035` diversity `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0`.
- Near miss `not_selected` seed `3551776718` score `0.812` family `straight_delivery` variant `straight_delivery_2_intermediate` tags `straight_delivery, long_route` primary `straight_delivery` topology `straight_line` path `4` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `normal` orientation reason `portrait_profile_default` route interest `0.185` diversity `topology 0.7, mechanic penalty 0.26, topology penalty 0.3, score 0.718`.
- Near miss `not_selected` seed `3257276797` score `0.8024` family `straight_delivery_intro` variant `straight_delivery_intro_alternate` tags `straight_delivery, intro` primary `straight_delivery` topology `straight_line` path `2` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `normal` orientation reason `portrait_profile_default` route interest `0.0` diversity `topology 0.7, mechanic penalty 0.2, topology penalty 0.3, score 0.745`.
- Switch `choice` starts on `e_choice_dead_end_a` (east); tap 1 @ 0.31s -> `e_choice_package` (south).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'choice' with 2 option(s).
### `level_003`
- Recipe: `straight_delivery_intro` variant `straight_delivery_intro_primary`; abstract signature `19aba4205409`.
- Mechanics: tags `straight_delivery, intro`; primary `straight_delivery`; topology `straight_line`; required path length `2`; layout orientation `vertical` via `portrait_profile_default`; Swift-required `False`; unlock `level 1`; depends on `none`.
- Diversity audit: topology 0.92, mechanic penalty 0.045, topology penalty 0.08, score 0.9358.
- Layout: `normal`; strategy: `vertical_route_progression`; profile: `portrait_vertical`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `vertical`; road shapes: `auto` (score `0.99`).
- Portrait checks: passed `True`; width `0.7`, height `1.85`, aspect `0.3784`, start-destination vertical separation `1.85`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 0 required taps, 0 alternate paths, 0 dead ends, 0 loops.
- Difficulty model: estimated `tutorial`, mechanical `0.1048`, visual `0.205`, campaign pacing `0.86`, preset fit `0.9682`.
- Score breakdown: mechanic `0.69`, runtime `1.0`, readability `0.9975`, route interest `0.0`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9989`, diversity `0.9358` (topology `0.92`, mechanic penalty `0.045`, topology penalty `0.08`).
- Route interest: score `0.0`; tags `none`; fake shortcut `False`; branch/rejoin `False`; package tension `False`; loop/revisit `False`; turns `1`; repeated topology penalty `0.08`.
- Solution route: `start` -> `package` -> `destination`.
- Required taps: none.
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.8229 vs 0.7912). Scores min/avg/max `0.777`/`0.7932`/`0.8229`.
- Accepted candidate audit: family `straight_delivery_intro`; variant `straight_delivery_intro_primary`; tags `straight_delivery, intro`; primary `straight_delivery`; topology `straight_line`; path `2`; orientation `vertical`; Swift-required `False`; strategy `vertical_route_progression`; variant `normal`; orientation reason `portrait_profile_default`; route interest `0.0`; diversity `topology 0.92, mechanic penalty 0.045, topology penalty 0.08, score 0.9358`.
- Near miss `not_selected` seed `635831312` score `0.7912` family `single_switch_wrong_dead_end` variant `single_switch_wrong_dead_end_primary` tags `single_switch, dead_end, switch` primary `single_switch` topology `single_branch` path `3` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `normal` orientation reason `portrait_profile_default` route interest `0.0` diversity `topology 0.7, mechanic penalty 0.22, topology penalty 0.3, score 0.736`.
- Near miss `not_selected` seed `49079562` score `0.7815` family `single_switch_intro` variant `single_switch_intro_primary` tags `single_switch, dead_end, switch, intro` primary `single_switch` topology `single_branch` path `3` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `mirrored` orientation reason `portrait_profile_default` route interest `0.0` diversity `topology 0.7, mechanic penalty 0.2, topology penalty 0.3, score 0.745`.
- Near miss `quality_similarity_above_threshold` seed `51327652` score `0.777` family `single_switch_intro` variant `single_switch_intro_primary` tags `single_switch, dead_end, switch, intro` primary `single_switch` topology `single_branch` path `3` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `wide` orientation reason `portrait_profile_default` route interest `0.0` diversity `topology 0.7, mechanic penalty 0.2, topology penalty 0.3, score 0.745`.
- No switch-specific review notes.
### `level_004`
- Recipe: `single_switch_wrong_dead_end` variant `single_switch_wrong_dead_end_primary`; abstract signature `a6ac65ca69c1`.
- Mechanics: tags `single_switch, dead_end, switch`; primary `single_switch`; topology `single_branch`; required path length `3`; layout orientation `vertical` via `portrait_profile_default`; Swift-required `False`; unlock `single switch introduced`; depends on `single_switch_intro`.
- Diversity audit: topology 0.92, mechanic penalty 0.06, topology penalty 0.08, score 0.929.
- Layout: `normal`; strategy: `vertical_route_progression`; profile: `portrait_vertical`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `vertical`; road shapes: `auto` (score `0.96`).
- Portrait checks: passed `True`; width `1.1`, height `1.85`, aspect `0.5946`, start-destination vertical separation `1.85`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 1 required taps, 0 alternate paths, 1 dead ends, 0 loops.
- Difficulty model: estimated `medium`, mechanical `0.4129`, visual `0.445`, campaign pacing `0.64`, preset fit `0.9265`.
- Score breakdown: mechanic `0.82`, runtime `1.0`, readability `0.99`, route interest `0.0`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9955`, diversity `0.929` (topology `0.92`, mechanic penalty `0.06`, topology penalty `0.08`).
- Route interest: score `0.0`; tags `none`; fake shortcut `False`; branch/rejoin `False`; package tension `False`; loop/revisit `False`; turns `1`; repeated topology penalty `0.08`.
- Solution route: `start` -> `choice` -> `package` -> `destination`.
- Required taps: tap `choice` at `0.31s` -> `e_choice_package` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.8118 vs 0.8012). Scores min/avg/max `0.7994`/`0.8041`/`0.8118`.
- Accepted candidate audit: family `single_switch_wrong_dead_end`; variant `single_switch_wrong_dead_end_primary`; tags `single_switch, dead_end, switch`; primary `single_switch`; topology `single_branch`; path `3`; orientation `vertical`; Swift-required `False`; strategy `vertical_route_progression`; variant `normal`; orientation reason `portrait_profile_default`; route interest `0.0`; diversity `topology 0.92, mechanic penalty 0.06, topology penalty 0.08, score 0.929`.
- Near miss `not_selected` seed `2311601214` score `0.8012` family `single_switch_intro` variant `single_switch_intro_primary` tags `single_switch, dead_end, switch, intro` primary `single_switch` topology `single_branch` path `3` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `mirrored` orientation reason `portrait_profile_default` route interest `0.0` diversity `topology 0.92, mechanic penalty 0.075, topology penalty 0.08, score 0.9223`.
- Near miss `not_selected` seed `1720353281` score `0.7994` family `straight_delivery` variant `straight_delivery_1_intermediate` tags `straight_delivery` primary `straight_delivery` topology `straight_line` path `3` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `normal` orientation reason `portrait_profile_default` route interest `0.09` diversity `topology 0.62, mechanic penalty 0.33, topology penalty 0.38, score 0.6425`.
- Switch `choice` starts on `e_choice_wrong_dead_end` (east); tap 1 @ 0.31s -> `e_choice_package` (south).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'choice' with 2 option(s).
### `level_005`
- Recipe: `straight_delivery` variant `straight_delivery_0_intermediate`; abstract signature `c3707c722388`.
- Mechanics: tags `straight_delivery`; primary `straight_delivery`; topology `straight_line`; required path length `2`; layout orientation `vertical` via `portrait_profile_default`; Swift-required `False`; unlock `none`; depends on `none`.
- Diversity audit: topology 0.92, mechanic penalty 0.14, topology penalty 0.08, score 0.893.
- Layout: `mirrored`; strategy: `vertical_route_progression`; profile: `portrait_vertical`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `vertical`; road shapes: `auto` (score `0.99`).
- Portrait checks: passed `True`; width `0.7`, height `1.85`, aspect `0.3784`, start-destination vertical separation `1.85`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 0 required taps, 0 alternate paths, 0 dead ends, 0 loops.
- Difficulty model: estimated `tutorial`, mechanical `0.1048`, visual `0.205`, campaign pacing `0.86`, preset fit `0.9682`.
- Score breakdown: mechanic `0.69`, runtime `1.0`, readability `0.9975`, route interest `0.0`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9989`, diversity `0.893` (topology `0.92`, mechanic penalty `0.14`, topology penalty `0.08`).
- Route interest: score `0.0`; tags `none`; fake shortcut `False`; branch/rejoin `False`; package tension `False`; loop/revisit `False`; turns `1`; repeated topology penalty `0.08`.
- Solution route: `start` -> `package` -> `destination`.
- Required taps: none.
- Candidate selection: Only one scored candidate passed validation and quality thresholds. Scores min/avg/max `0.805`/`0.805`/`0.805`.
- Accepted candidate audit: family `straight_delivery`; variant `straight_delivery_0_intermediate`; tags `straight_delivery`; primary `straight_delivery`; topology `straight_line`; path `2`; orientation `vertical`; Swift-required `False`; strategy `vertical_route_progression`; variant `mirrored`; orientation reason `portrait_profile_default`; route interest `0.0`; diversity `topology 0.92, mechanic penalty 0.14, topology penalty 0.08, score 0.893`.
- No switch-specific review notes.
### `level_006`
- Recipe: `single_switch_intro` variant `single_switch_intro_primary`; abstract signature `5d713e530369`.
- Mechanics: tags `single_switch, dead_end, switch, intro`; primary `single_switch`; topology `single_branch`; required path length `3`; layout orientation `vertical` via `portrait_profile_default`; Swift-required `False`; unlock `straight delivery understood`; depends on `straight_delivery_intro`.
- Diversity audit: topology 0.92, mechanic penalty 0.11, topology penalty 0.08, score 0.9065.
- Layout: `mirrored`; strategy: `vertical_route_progression`; profile: `portrait_vertical`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `vertical`; road shapes: `auto` (score `0.96`).
- Portrait checks: passed `True`; width `1.1`, height `1.85`, aspect `0.5946`, start-destination vertical separation `1.85`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 1 required taps, 0 alternate paths, 1 dead ends, 0 loops.
- Difficulty model: estimated `medium`, mechanical `0.4129`, visual `0.445`, campaign pacing `0.64`, preset fit `0.9265`.
- Score breakdown: mechanic `0.82`, runtime `1.0`, readability `0.99`, route interest `0.0`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9955`, diversity `0.9065` (topology `0.92`, mechanic penalty `0.11`, topology penalty `0.08`).
- Route interest: score `0.0`; tags `none`; fake shortcut `False`; branch/rejoin `False`; package tension `False`; loop/revisit `False`; turns `1`; repeated topology penalty `0.08`.
- Solution route: `start` -> `choice` -> `package` -> `destination`.
- Required taps: tap `choice` at `0.31s` -> `e_choice_package` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.8002 vs 0.7726). Scores min/avg/max `0.7726`/`0.7864`/`0.8002`.
- Accepted candidate audit: family `single_switch_intro`; variant `single_switch_intro_primary`; tags `single_switch, dead_end, switch, intro`; primary `single_switch`; topology `single_branch`; path `3`; orientation `vertical`; Swift-required `False`; strategy `vertical_route_progression`; variant `mirrored`; orientation reason `portrait_profile_default`; route interest `0.0`; diversity `topology 0.92, mechanic penalty 0.11, topology penalty 0.08, score 0.9065`.
- Near miss `not_selected` seed `3889397219` score `0.7726` family `straight_delivery` variant `straight_delivery_1_intermediate` tags `straight_delivery` primary `straight_delivery` topology `straight_line` path `3` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `normal` orientation reason `portrait_profile_default` route interest `0.09` diversity `topology 0.62, mechanic penalty 0.37, topology penalty 0.38, score 0.5845`.
- Switch `choice` starts on `e_choice_dead_end_a` (west); tap 1 @ 0.31s -> `e_choice_package` (south).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'choice' with 2 option(s).
### `level_007`
- Recipe: `straight_delivery` variant `straight_delivery_1_intermediate`; abstract signature `e2a667e385b6`.
- Mechanics: tags `straight_delivery`; primary `straight_delivery`; topology `straight_line`; required path length `3`; layout orientation `vertical` via `portrait_profile_default`; Swift-required `False`; unlock `none`; depends on `none`.
- Diversity audit: topology 0.92, mechanic penalty 0.14, topology penalty 0.08, score 0.893.
- Layout: `normal`; strategy: `vertical_route_progression`; profile: `portrait_vertical`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `vertical`; road shapes: `auto` (score `0.96`).
- Portrait checks: passed `True`; width `0.7`, height `1.85`, aspect `0.3784`, start-destination vertical separation `1.85`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 0 required taps, 0 alternate paths, 0 dead ends, 0 loops.
- Difficulty model: estimated `easy`, mechanical `0.1529`, visual `0.285`, campaign pacing `0.86`, preset fit `0.9682`.
- Score breakdown: mechanic `0.69`, runtime `1.0`, readability `0.99`, route interest `0.202`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9955`, diversity `0.893` (topology `0.92`, mechanic penalty `0.14`, topology penalty `0.08`).
- Route interest: score `0.202`; tags `meaningful_turns`; fake shortcut `False`; branch/rejoin `False`; package tension `False`; loop/revisit `False`; turns `2`; repeated topology penalty `0.08`.
- Solution route: `start` -> `node_a` -> `package` -> `destination`.
- Required taps: none.
- Candidate selection: Only one scored candidate passed validation and quality thresholds. Scores min/avg/max `0.8377`/`0.8377`/`0.8377`.
- Accepted candidate audit: family `straight_delivery`; variant `straight_delivery_1_intermediate`; tags `straight_delivery`; primary `straight_delivery`; topology `straight_line`; path `3`; orientation `vertical`; Swift-required `False`; strategy `vertical_route_progression`; variant `normal`; orientation reason `portrait_profile_default`; route interest `0.202`; diversity `topology 0.92, mechanic penalty 0.14, topology penalty 0.08, score 0.893`.
- No switch-specific review notes.

## Rejections

- Rejected candidates: `214`
- `candidate_too_similar_to_batch`: 176
- `portrait_start_destination_not_vertically_separated`: 37
- `quality_similarity_above_threshold`: 1

## Messages

- Rejected candidate level_001 seed=2761754670 template=single_switch reason=candidate_too_similar_to_batch detail=matches level_001: same topology, solution, and layout (9e8f40a4/fc75f4b5)
- Rejected candidate level_001 seed=3056254591 template=single_switch_wrong_dead_end reason=candidate_too_similar_to_batch detail=matches level_001: same topology, solution, and layout (43bcc0ec/fc75f4b5)
- Rejected candidate level_001 seed=3350754512 template=single_switch_intro reason=candidate_too_similar_to_batch detail=matches level_001: same topology, solution, and layout (9e8f40a4/fc75f4b5)
- Rejected candidate level_001 seed=2175002919 template=single_switch_intro reason=candidate_too_similar_to_batch detail=matches level_001: similarity 0.91 >= 0.88
- Rejected candidate level_002 seed=3846276639 template=package_before_destination_intro reason=candidate_too_similar_to_batch detail=matches level_001: same topology, solution, and layout (1a988a48/4ea3c0eb)
- Rejected candidate level_002 seed=4140776560 template=single_switch reason=candidate_too_similar_to_batch detail=matches level_002: same topology, solution, and layout (9e8f40a4/fc75f4b5)
- Rejected candidate level_003 seed=46831470 template=single_switch_intro reason=candidate_too_similar_to_batch detail=matches level_002: same topology, solution, and layout (9e8f40a4/fc75f4b5)
- Rejected candidate level_003 seed=341331391 template=single_switch reason=candidate_too_similar_to_batch detail=matches level_002: same topology, solution, and layout (9e8f40a4/fc75f4b5)
- Rejected candidate level_003 seed=930331233 template=straight_delivery_intro reason=candidate_too_similar_to_batch detail=matches level_003: same topology, solution, and layout (2a12d2df/4ea3c0eb)
- Rejected candidate level_003 seed=1224831154 template=single_switch_wrong_dead_end reason=candidate_too_similar_to_batch detail=matches level_003: same topology, solution, and layout (43bcc0ec/fc75f4b5)
- Rejected candidate level_003 seed=343579482 template=single_switch reason=candidate_too_similar_to_batch detail=matches level_002: similarity 0.91 >= 0.88
- Rejected candidate level_003 seed=932579324 template=straight_delivery_intro reason=candidate_too_similar_to_batch detail=matches level_003: similarity 0.88 >= 0.88
- Rejected candidate level_003 seed=1227079245 template=single_switch_wrong_dead_end reason=candidate_too_similar_to_batch detail=matches level_003: similarity 0.91 >= 0.88
- Rejected candidate level_003 seed=4051795027 template=straight_delivery_intro reason=candidate_too_similar_to_batch detail=matches level_003: same template/topology and layout similarity 0.99
- Rejected candidate level_003 seed=51327652 template=single_switch_intro reason=quality_similarity_above_threshold detail=similarity 0.88 > 0.87
- Rejected candidate level_003 seed=345827573 template=single_switch reason=candidate_too_similar_to_batch detail=matches level_002: same template/topology and layout similarity 0.99
- Rejected candidate level_003 seed=640327494 template=single_switch_wrong_dead_end reason=candidate_too_similar_to_batch detail=matches level_003: same template/topology and layout similarity 0.99
- Rejected candidate level_003 seed=934827415 template=straight_delivery_intro reason=candidate_too_similar_to_batch detail=matches level_003: same template/topology and layout similarity 0.99
- Rejected candidate level_003 seed=1229327336 template=single_switch_wrong_dead_end reason=candidate_too_similar_to_batch detail=matches level_003: same template/topology and layout similarity 0.99
- Rejected candidate level_003 seed=4047298846 template=straight_delivery_intro reason=candidate_too_similar_to_batch detail=matches level_003: same topology, solution, and layout (2a12d2df/4ea3c0eb)
- Rejected candidate level_003 seed=46831471 template=single_switch_intro reason=candidate_too_similar_to_batch detail=matches level_002: same topology, solution, and layout (9e8f40a4/fc75f4b5)
- Rejected candidate level_003 seed=341331392 template=single_switch reason=candidate_too_similar_to_batch detail=matches level_002: same topology, solution, and layout (9e8f40a4/fc75f4b5)
- Rejected candidate level_003 seed=635831313 template=single_switch_wrong_dead_end reason=candidate_too_similar_to_batch detail=matches level_003: same topology, solution, and layout (43bcc0ec/fc75f4b5)
- Rejected candidate level_003 seed=930331234 template=straight_delivery_intro reason=candidate_too_similar_to_batch detail=matches level_003: same topology, solution, and layout (2a12d2df/4ea3c0eb)
- Rejected candidate level_003 seed=1224831155 template=single_switch_wrong_dead_end reason=candidate_too_similar_to_batch detail=matches level_003: same topology, solution, and layout (43bcc0ec/fc75f4b5)
- Rejected candidate level_003 seed=343579483 template=single_switch reason=candidate_too_similar_to_batch detail=matches level_002: similarity 0.91 >= 0.88
- Rejected candidate level_003 seed=932579325 template=straight_delivery_intro reason=candidate_too_similar_to_batch detail=matches level_003: similarity 0.88 >= 0.88
- Rejected candidate level_003 seed=4051795028 template=straight_delivery_intro reason=candidate_too_similar_to_batch detail=matches level_003: same template/topology and layout similarity 0.99
- Rejected candidate level_003 seed=51327653 template=single_switch_intro reason=candidate_too_similar_to_batch detail=matches level_003: similarity 0.91 >= 0.88
- Rejected candidate level_003 seed=345827574 template=single_switch reason=candidate_too_similar_to_batch detail=matches level_002: same template/topology and layout similarity 0.99
- Rejected candidate level_003 seed=640327495 template=single_switch_wrong_dead_end reason=candidate_too_similar_to_batch detail=matches level_003: same template/topology and layout similarity 0.99
- Rejected candidate level_003 seed=934827416 template=straight_delivery_intro reason=candidate_too_similar_to_batch detail=matches level_003: same template/topology and layout similarity 0.99
- Rejected candidate level_003 seed=1229327337 template=single_switch_wrong_dead_end reason=candidate_too_similar_to_batch detail=matches level_003: same template/topology and layout similarity 0.99
- Rejected candidate level_004 seed=836853518 template=single_switch reason=candidate_too_similar_to_batch detail=matches level_002: same topology, solution, and layout (9e8f40a4/fc75f4b5)
- Rejected candidate level_004 seed=1131353439 template=package_before_destination_intro reason=candidate_too_similar_to_batch detail=matches level_001: same topology, solution, and layout (1a988a48/4ea3c0eb)
- Rejected candidate level_004 seed=1425853360 template=straight_delivery_intro reason=candidate_too_similar_to_batch detail=matches level_003: same topology, solution, and layout (2a12d2df/4ea3c0eb)
- Rejected candidate level_004 seed=2309353123 template=single_switch_intro reason=candidate_too_similar_to_batch detail=matches level_002: same topology, solution, and layout (9e8f40a4/fc75f4b5)
- Rejected candidate level_004 seed=839101609 template=single_switch reason=candidate_too_similar_to_batch detail=matches level_002: similarity 0.91 >= 0.88
- Rejected candidate level_004 seed=1133601530 template=package_before_destination_intro reason=candidate_too_similar_to_batch detail=matches level_001: similarity 0.92 >= 0.88
- Rejected candidate level_004 seed=1428101451 template=straight_delivery_intro reason=candidate_too_similar_to_batch detail=matches level_003: similarity 0.88 >= 0.88
- Rejected candidate level_004 seed=2017101293 template=single_switch_wrong_dead_end reason=candidate_too_similar_to_batch detail=matches level_004: similarity 0.91 >= 0.88
- Rejected candidate level_004 seed=841349700 template=single_switch reason=candidate_too_similar_to_batch detail=matches level_002: same template/topology and layout similarity 0.99
- Rejected candidate level_004 seed=1135849621 template=package_before_destination_intro reason=candidate_too_similar_to_batch detail=matches level_001: same template/topology and layout similarity 0.99
- Rejected candidate level_004 seed=1430349542 template=straight_delivery_intro reason=candidate_too_similar_to_batch detail=matches level_003: same template/topology and layout similarity 0.99
- Rejected candidate level_004 seed=1724849463 template=straight_delivery reason=candidate_too_similar_to_batch detail=matches level_004: same template/topology and layout similarity 0.99
- Rejected candidate level_004 seed=2019349384 template=single_switch_wrong_dead_end reason=candidate_too_similar_to_batch detail=matches level_004: same template/topology and layout similarity 0.99
- Rejected candidate level_004 seed=2313849305 template=single_switch_intro reason=candidate_too_similar_to_batch detail=matches level_004: similarity 0.91 >= 0.88
- Rejected candidate level_004 seed=836853519 template=single_switch reason=candidate_too_similar_to_batch detail=matches level_002: same topology, solution, and layout (9e8f40a4/fc75f4b5)
- Rejected candidate level_004 seed=1131353440 template=package_before_destination_intro reason=candidate_too_similar_to_batch detail=matches level_001: same topology, solution, and layout (1a988a48/4ea3c0eb)
- Rejected candidate level_004 seed=1425853361 template=straight_delivery_intro reason=candidate_too_similar_to_batch detail=matches level_003: same topology, solution, and layout (2a12d2df/4ea3c0eb)
- Additional candidate rejection messages suppressed after 50; see rejectionReasonCounts and candidateSelection in the report.
- Could not generate valid level_008 after 1 attempts.

## Recommendations

- Most common rejection: `candidate_too_similar_to_batch`.
- For playtest batches, rerun with `--playtest-mode`.
- Increase `--candidate-pool-size`.
- Enable more hard templates with `--swift-tests`.
- Use `--difficulty auto` instead of hard-only.
- Generate fewer levels per batch.
- Add a new hard template variant.

## Swift Test Summary

- Command: `not run`
- Result: `Swift tests were not run.`

## Next Steps

- Open generated levels in the Level Editor.
- Run Python validation and Swift solvability before committing production levels.
- `xcodegen generate` runs automatically for default production output; rerun it manually if resources were deleted outside the generator.
