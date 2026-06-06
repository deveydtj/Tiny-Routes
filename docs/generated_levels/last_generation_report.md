# Tiny Routes Generation Report

- Generated: `2026-06-06T13:50:56.414497+00:00`
- Repo root: `/Users/jake/Developer/Tiny-Routes`
- Difficulty: `medium`
- Template mode: `mixed`
- Generation mode: `recipe_first`
- Base seed: `None`
- Dry run: `False`
- Dry-run pass rate: `0.1235`
- Compare existing levels: `False`
- Candidate pool size: `2`
- Candidate generation count: `458`
- Candidate validation count: `81`
- Recipe pool size: `6`
- Layouts per recipe: `2`
- Road shapes per layout: `2`
- Layout orientation preference: `mixed`
- Layout profile: `mixed`
- Layout size profile: `difficulty_curve`
- Vertical route probability: `0.55`
- Prefer vertical for long routes: `True`
- Xcode project sync: `True`
- Swift tests: `Swift tests were not run.`

## Distributions

- Difficulty: `{'medium': 10}`
- Recipe: `{'fake_shortcut': 2, 'hub_choice': 1, 'long_detour_gate': 1, 'package_gate': 1, 'package_gate_double_choice': 2, 'return_loop': 1, 'return_loop_intro': 1, 'split_path_rejoin': 1}`
- Topology: `{'detour_gate': 3, 'hub_spoke': 1, 'package_gate': 3, 'return_loop': 1, 'split_rejoin': 1, 'two_switch_order': 1}`
- Family streaks: `{'longest': {'value': 'fake_shortcut', 'length': 1}, 'repeatedStreaks': []}`
- Topology streaks: `{'longest': {'value': 'package_gate', 'length': 2}, 'repeatedStreaks': [{'value': 'package_gate', 'length': 2}]}`
- Map size: `{'standard_portrait': 10}`
- Route interest score: `{'excellent': 5, 'expert_gate': 4, 'strong': 1}`
- Route interest by difficulty: `{'medium': {'minimum': 0.58, 'average': 0.8342, 'maximum': 1.0, 'count': 10, 'distribution': {'excellent': 5, 'expert_gate': 4, 'strong': 1}}}`
- Candidate generation by difficulty: `{'medium': 458}`
- Candidate validation by difficulty: `{'medium': 81}`
- Accepted vs rejected by difficulty: `{'medium': {'accepted': 10, 'rejected': 61}}`
- Similarity rejections by difficulty: `{'medium': 40}`
- Starvation causes: `{'totalRejections': 61, 'topCategories': [{'category': 'batchSimilarity', 'count': 41, 'share': 0.6721}, {'category': 'routeInterestGate', 'count': 9, 'share': 0.1475}, {'category': 'tapTiming', 'count': 4, 'share': 0.0656}, {'category': 'layoutValidity', 'count': 4, 'share': 0.0656}, {'category': 'readabilityBlockedRoads', 'count': 3, 'share': 0.0492}], 'topReasons': [{'reason': 'candidate_too_similar_to_batch', 'count': 40, 'share': 0.6557}, {'reason': 'route_interest_below_medium_gate', 'count': 9, 'share': 0.1475}, {'reason': 'solution_tap_not_before_switch_arrival', 'count': 4, 'share': 0.0656}, {'reason': 'layout_node_out_of_bounds', 'count': 4, 'share': 0.0656}, {'reason': 'important_node_readability_blocked_by_road', 'count': 3, 'share': 0.0492}]}`

## Accepted Levels

| Level | Source | Mechanics | Topology | Path | Orientation | Diversity | Seed | Difficulty | Nodes | Edges | Switches | Par Taps | Time Limit | Quality | Preview | Signatures | Status |
|---|---|---|---|---:|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|---|
| `level_091` | `fake_shortcut / fake_shortcut_primary` | `fake_shortcut: fake_shortcut, detour, package_gate, dead_end` | `detour_gate` | 6 | `horizontal` | `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0` | 999724393 | medium | 9 | 8 | 2 | 2 | 30 | 0.9687 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_091.svg) | `T:c115d191 L:43a576a0 S:547b0f2b` | passed |
| `level_092` | `package_gate_double_choice / package_gate_double_choice_alternate` | `package_gate: package_gate, multi_switch, two_switch` | `package_gate` | 4 | `horizontal` | `topology 1.0, mechanic penalty 0.04, topology penalty 0.0, score 0.982` | 2084246362 | medium | 7 | 6 | 2 | 2 | 30 | 0.918 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_092.svg) | `T:501007b5 L:942bdc73 S:22e42c17` | passed |
| `level_093` | `split_path_rejoin / split_path_rejoin_primary` | `split_path: split_path, rejoin, multi_switch, package_gate` | `split_rejoin` | 6 | `horizontal` | `topology 1.0, mechanic penalty 0.0825, topology penalty 0.0, score 0.9629` | 3463268252 | medium | 9 | 9 | 2 | 2 | 30 | 0.9222 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_093.svg) | `T:404d3c3f L:8db73392 S:22e42c17` | passed |
| `level_094` | `return_loop / return_loop_lower` | `loop: loop, repeated_tap` | `return_loop` | 6 | `horizontal` | `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0` | 841822767 | medium | 7 | 7 | 2 | 3 | 30 | 0.9083 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_094.svg) | `T:f152647c L:998cd5e3 S:50bb2282` | passed |
| `level_095` | `hub_choice / hub_choice_alternate` | `hub: hub, multi_switch, rejoin, dead_end` | `hub_spoke` | 6 | `horizontal` | `topology 1.0, mechanic penalty 0.075, topology penalty 0.0, score 0.9663` | 1337344894 | medium | 9 | 9 | 2 | 2 | 30 | 0.913 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_095.svg) | `T:02fd7ebc L:973639ef S:84ab4378` | passed |
| `level_096` | `long_detour_gate / long_detour_gate_primary` | `long_route: long_route, detour, package_gate` | `detour_gate` | 6 | `horizontal` | `topology 1.0, mechanic penalty 0.0667, topology penalty 0.0, score 0.97` | 3010866705 | medium | 9 | 9 | 2 | 2 | 30 | 0.8817 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_096.svg) | `T:eb2c3b9e L:75baa561 S:e45124c2` | passed |
| `level_097` | `return_loop_intro / return_loop_intro_primary` | `loop: loop, repeated_tap, multi_switch, return_loop` | `two_switch_order` | 4 | `horizontal` | `topology 1.0, mechanic penalty 0.08, topology penalty 0.0, score 0.964` | 3211888911 | medium | 7 | 6 | 2 | 2 | 30 | 0.8779 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_097.svg) | `T:501007b5 L:98c18977 S:22e42c17` | passed |
| `level_098` | `fake_shortcut / fake_shortcut_primary` | `fake_shortcut: fake_shortcut, detour, package_gate, dead_end` | `detour_gate` | 6 | `horizontal` | `topology 0.92, mechanic penalty 0.0725, topology penalty 0.08, score 0.9234` | 592691648 | medium | 9 | 8 | 2 | 2 | 30 | 0.8866 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_098.svg) | `T:c115d191 L:e34b8051 S:547b0f2b` | passed |
| `level_099` | `package_gate_double_choice / package_gate_double_choice_primary` | `package_gate: package_gate, multi_switch, two_switch` | `package_gate` | 4 | `horizontal` | `topology 1.0, mechanic penalty 0.11, topology penalty 0.0, score 0.9505` | 1382713565 | medium | 7 | 6 | 2 | 2 | 30 | 0.8815 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_099.svg) | `T:501007b5 L:89810884 S:22e42c17` | passed |
| `level_100` | `package_gate / package_gate_crossing_avoidance` | `package_gate: package_gate, multi_switch` | `package_gate` | 4 | `horizontal` | `topology 0.7, mechanic penalty 0.385, topology penalty 0.3, score 0.6618` | 3435771385 | medium | 7 | 6 | 2 | 2 | 30 | 0.8818 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_100.svg) | `T:b6fc1fcd L:d16e5a6d S:02f4e4f5` | passed |

## Level Details

### `level_091`
- Recipe: `fake_shortcut` variant `fake_shortcut_primary`; abstract signature `29bedea142dc`.
- Mechanics: tags `fake_shortcut, detour, package_gate, dead_end`; primary `fake_shortcut`; topology `detour_gate`; required path length `6`; layout orientation `horizontal` via `mixed_horizontal`; Swift-required `False`; unlock `medium levels unlocked`; depends on `short_detour_gate`.
- Diversity audit: topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0.
- Layout: `normal`; strategy: `split_lane`; profile: `horizontal`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `horizontal`; road shapes: `auto` (score `0.96`).
- Portrait checks: passed `True`; width `2.0`, height `0.9`, aspect `2.2222`, start-destination vertical separation `0.0`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 2 required taps, 0 alternate paths, 2 dead ends, 0 loops.
- Difficulty model: estimated `expert`, mechanical `0.7972`, visual `0.845`, campaign pacing `1.0`, preset fit `0.8425`.
- Score breakdown: mechanic `0.95`, runtime `1.0`, readability `0.99`, route interest `1.0`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9622`, diversity `1.0` (topology `1.0`, mechanic penalty `0.0`, topology penalty `0.0`).
- Route interest: score `1.0`; tags `fake_shortcut, correct_detour, package_gate_tension, meaningful_turns`; fake shortcut `True`; branch/rejoin `False`; package tension `True`; loop/revisit `False`; turns `3`; repeated topology penalty `0.0`.
- Solution route: `start` -> `choice` -> `detour_a` -> `package` -> `detour_b` -> `switch_b` -> `destination`.
- Required taps: tap `choice` at `0.10s` -> `e_choice_detour_a` (0.25s window), tap `switch_b` at `1.85s` -> `e_switch_b_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.9687 vs 0.9194). Scores min/avg/max `0.9194`/`0.9441`/`0.9687`.
- Accepted candidate audit: family `fake_shortcut`; variant `fake_shortcut_primary`; tags `fake_shortcut, detour, package_gate, dead_end`; primary `fake_shortcut`; topology `detour_gate`; path `6`; orientation `horizontal`; Swift-required `False`; strategy `split_lane`; variant `normal`; orientation reason `mixed_horizontal`; route interest `1.0`; diversity `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0`.
- Near miss `not_selected` seed `1294224314` score `0.9194` family `return_loop_intro` variant `return_loop_intro_primary` tags `loop, repeated_tap, multi_switch, return_loop` primary `loop` topology `two_switch_order` path `4` orientation `horizontal` Swift-required `False` strategy `package_inside_loop` variant `normal` orientation reason `mixed_horizontal` route interest `0.58` diversity `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0`.
- Switch `choice` starts on `e_choice_shortcut_dead_end` (north); tap 1 @ 0.10s -> `e_choice_detour_a` (east).
- Switch `switch_b` starts on `e_switch_b_dead_end_b` (north); tap 1 @ 1.85s -> `e_switch_b_destination` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'choice' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'switch_b' with 2 option(s).
### `level_092`
- Recipe: `package_gate_double_choice` variant `package_gate_double_choice_alternate`; abstract signature `370547fa090b`.
- Mechanics: tags `package_gate, multi_switch, two_switch`; primary `package_gate`; topology `package_gate`; required path length `4`; layout orientation `horizontal` via `mixed_horizontal`; Swift-required `False`; unlock `package gate learned`; depends on `package_gate_simple`.
- Diversity audit: topology 1.0, mechanic penalty 0.04, topology penalty 0.0, score 0.982.
- Layout: `normal`; strategy: `split_lane`; profile: `horizontal`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `horizontal`; road shapes: `auto` (score `0.96`).
- Portrait checks: passed `True`; width `2.0`, height `0.9`, aspect `2.2222`, start-destination vertical separation `0.0`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 2 required taps, 0 alternate paths, 2 dead ends, 0 loops.
- Difficulty model: estimated `hard`, mechanical `0.7072`, visual `0.685`, campaign pacing `0.92`, preset fit `0.8845`.
- Score breakdown: mechanic `0.95`, runtime `1.0`, readability `0.99`, route interest `0.64`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9955`, diversity `0.982` (topology `1.0`, mechanic penalty `0.04`, topology penalty `0.0`).
- Route interest: score `0.64`; tags `package_gate_tension, meaningful_turns`; fake shortcut `False`; branch/rejoin `False`; package tension `True`; loop/revisit `False`; turns `3`; repeated topology penalty `0.0`.
- Solution route: `start` -> `switch_a` -> `package` -> `switch_b` -> `destination`.
- Required taps: tap `switch_a` at `0.10s` -> `e_switch_a_package` (0.4s window), tap `switch_b` at `1.70s` -> `e_switch_b_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.9180 vs 0.8884). Scores min/avg/max `0.8884`/`0.9032`/`0.918`.
- Accepted candidate audit: family `package_gate_double_choice`; variant `package_gate_double_choice_alternate`; tags `package_gate, multi_switch, two_switch`; primary `package_gate`; topology `package_gate`; path `4`; orientation `horizontal`; Swift-required `False`; strategy `split_lane`; variant `normal`; orientation reason `mixed_horizontal`; route interest `0.64`; diversity `topology 1.0, mechanic penalty 0.04, topology penalty 0.0, score 0.982`.
- Near miss `not_selected` seed `2378746283` score `0.8884` family `return_loop_intro` variant `return_loop_intro_primary` tags `loop, repeated_tap, multi_switch, return_loop` primary `loop` topology `two_switch_order` path `4` orientation `horizontal` Swift-required `False` strategy `package_inside_loop` variant `normal` orientation reason `mixed_horizontal` route interest `0.58` diversity `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0`.
- Switch `switch_a` starts on `e_switch_a_dead_end_a` (north); tap 1 @ 0.10s -> `e_switch_a_package` (east).
- Switch `switch_b` starts on `e_switch_b_dead_end_b` (north); tap 1 @ 1.70s -> `e_switch_b_destination` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'switch_a' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'switch_b' with 2 option(s).
### `level_093`
- Recipe: `split_path_rejoin` variant `split_path_rejoin_primary`; abstract signature `8b78612583fa`.
- Mechanics: tags `split_path, rejoin, multi_switch, package_gate`; primary `split_path`; topology `split_rejoin`; required path length `6`; layout orientation `horizontal` via `mixed_horizontal`; Swift-required `False`; unlock `medium levels unlocked`; depends on `two_switch_order_intro`.
- Diversity audit: topology 1.0, mechanic penalty 0.0825, topology penalty 0.0, score 0.9629.
- Layout: `normal`; strategy: `split_lane`; profile: `horizontal`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `horizontal`; road shapes: `auto` (score `0.91`).
- Portrait checks: passed `True`; width `2.1`, height `1.7`, aspect `1.2353`, start-destination vertical separation `0.55`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 2 required taps, 0 alternate paths, 1 dead ends, 0 loops.
- Difficulty model: estimated `expert`, mechanical `0.8766`, visual `0.88`, campaign pacing `0.62`, preset fit `0.818`.
- Score breakdown: mechanic `0.96`, runtime `1.0`, readability `0.9775`, route interest `1.0`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9444`, diversity `0.9629` (topology `1.0`, mechanic penalty `0.0825`, topology penalty `0.0`).
- Route interest: score `1.0`; tags `fake_shortcut, split_rejoin, package_gate_tension, tempting_wrong_branch, meaningful_turns`; fake shortcut `True`; branch/rejoin `True`; package tension `True`; loop/revisit `False`; turns `4`; repeated topology penalty `0.0`.
- Solution route: `start` -> `switch_a` -> `upper_branch` -> `package` -> `rejoin` -> `switch_b` -> `destination`.
- Required taps: tap `switch_a` at `0.10s` -> `e_switch_a_upper_branch` (0.4s window), tap `switch_b` at `4.55s` -> `e_switch_b_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.9222 vs 0.8844). Scores min/avg/max `0.8782`/`0.8949`/`0.9222`.
- Accepted candidate audit: family `split_path_rejoin`; variant `split_path_rejoin_primary`; tags `split_path, rejoin, multi_switch, package_gate`; primary `split_path`; topology `split_rejoin`; path `6`; orientation `horizontal`; Swift-required `False`; strategy `split_lane`; variant `normal`; orientation reason `mixed_horizontal`; route interest `1.0`; diversity `topology 1.0, mechanic penalty 0.0825, topology penalty 0.0, score 0.9629`.
- Near miss `route_interest_below_medium_gate` seed `3168768331` score `0.8844` family `multi_switch_chain` variant `multi_switch_chain_stair_step` tags `multi_switch` primary `multi_switch` topology `two_switch_order` path `4` orientation `horizontal` Swift-required `False` strategy `horizontal_route_progression` variant `normal` orientation reason `mixed_horizontal` route interest `0.405` diversity `topology 1.0, mechanic penalty 0.12, topology penalty 0.0, score 0.946`.
- Near miss `not_selected` seed `3757768173` score `0.8782` family `long_detour_gate` variant `long_detour_gate_alternate` tags `long_route, detour, package_gate` primary `long_route` topology `detour_gate` path `6` orientation `horizontal` Swift-required `False` strategy `split_lane` variant `normal` orientation reason `mixed_horizontal` route interest `1.0` diversity `topology 0.92, mechanic penalty 0.1, topology penalty 0.08, score 0.911`.
- Switch `switch_a` starts on `e_switch_a_lower_shortcut` (south); tap 1 @ 0.10s -> `e_switch_a_upper_branch` (east).
- Switch `switch_b` starts on `e_switch_b_dead_end_b` (west); tap 1 @ 4.55s -> `e_switch_b_destination` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'switch_a' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'switch_b' with 2 option(s).
### `level_094`
- Recipe: `return_loop` variant `return_loop_lower`; abstract signature `eb4ba72e54fa`.
- Mechanics: tags `loop, repeated_tap`; primary `loop`; topology `return_loop`; required path length `6`; layout orientation `horizontal` via `mixed_horizontal`; Swift-required `False`; unlock `none`; depends on `none`.
- Diversity audit: topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0.
- Layout: `normal`; strategy: `package_inside_loop`; profile: `horizontal`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `horizontal`; road shapes: `auto` (score `0.92`).
- Portrait checks: passed `True`; width `2.0`, height `1.0`, aspect `2.0`, start-destination vertical separation `-0.05`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `0.92`, 1 issue(s).
- Abstract solution: 3 required taps, 1 alternate paths, 1 dead ends, 9 loops.
- Difficulty model: estimated `expert`, mechanical `1.0`, visual `0.78`, campaign pacing `0.72`, preset fit `0.888`.
- Score breakdown: mechanic `1.0`, runtime `1.0`, readability `0.74`, route interest `0.87`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.8365`, diversity `1.0` (topology `1.0`, mechanic penalty `0.0`, topology penalty `0.0`).
- Route interest: score `0.87`; tags `split_rejoin, loop_or_revisit, meaningful_turns`; fake shortcut `False`; branch/rejoin `True`; package tension `False`; loop/revisit `True`; turns `5`; repeated topology penalty `0.0`.
- Solution route: `start` -> `lower_alpha_switch` -> `package` -> `lower_beta_switch` -> `lower_return` -> `lower_alpha_switch` -> `destination`.
- Required taps: tap `lower_alpha_switch` at `1.36s` -> `e_lower_alpha_switch_package` (0.45s window), tap `lower_beta_switch` at `3.22s` -> `e_lower_beta_switch_lower_return` (0.45s window), tap `lower_alpha_switch` at `4.46s` -> `e_lower_alpha_switch_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.9083 vs 0.9075). Scores min/avg/max `0.8569`/`0.8909`/`0.9083`.
- Accepted candidate audit: family `return_loop`; variant `return_loop_lower`; tags `loop, repeated_tap`; primary `loop`; topology `return_loop`; path `6`; orientation `horizontal`; Swift-required `False`; strategy `package_inside_loop`; variant `normal`; orientation reason `mixed_horizontal`; route interest `0.87`; diversity `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0`.
- Near miss `not_selected` seed `547322846` score `0.9075` family `hub_choice` variant `hub_choice_primary` tags `hub, multi_switch, rejoin, dead_end` primary `hub` topology `hub_spoke` path `6` orientation `horizontal` Swift-required `False` strategy `hub_and_spoke` variant `normal` orientation reason `mixed_horizontal` route interest `1.0` diversity `topology 1.0, mechanic penalty 0.1, topology penalty 0.0, score 0.955`.
- Near miss `route_interest_below_medium_gate` seed `4253290300` score `0.8569` family `multi_switch_order` variant `multi_switch_order_alternate` tags `multi_switch, switch_order` primary `multi_switch` topology `two_switch_order` path `4` orientation `horizontal` Swift-required `False` strategy `horizontal_route_progression` variant `normal` orientation reason `mixed_horizontal` route interest `0.405` diversity `topology 1.0, mechanic penalty 0.105, topology penalty 0.0, score 0.9527`.
- Switch `lower_alpha_switch` starts on `e_lower_alpha_switch_destination` (south); tap 1 @ 1.36s -> `e_lower_alpha_switch_package` (west), tap 2 @ 4.46s -> `e_lower_alpha_switch_destination` (south).
- Switch `lower_beta_switch` starts on `e_lower_beta_switch_lower_dead_end` (south); tap 1 @ 3.22s -> `e_lower_beta_switch_lower_return` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'lower_alpha_switch' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'lower_beta_switch' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 3 taps 2-way switch 'lower_alpha_switch' with 2 option(s).
- Warning: return_loop_visually_unclear: Return loop revisits switch 'lower_alpha_switch', which can obscure the intended route flow.
- Visual clarity warning: `return_loop_visually_unclear` node `lower_alpha_switch` edge `None`.
### `level_095`
- Recipe: `hub_choice` variant `hub_choice_alternate`; abstract signature `c31dda0c916a`.
- Mechanics: tags `hub, multi_switch, rejoin, dead_end`; primary `hub`; topology `hub_spoke`; required path length `6`; layout orientation `horizontal` via `mixed_horizontal`; Swift-required `False`; unlock `three-way switches unlocked`; depends on `multi_switch_order`.
- Diversity audit: topology 1.0, mechanic penalty 0.075, topology penalty 0.0, score 0.9663.
- Layout: `normal`; strategy: `hub_and_spoke`; profile: `horizontal`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `horizontal`; road shapes: `auto` (score `0.91`).
- Portrait checks: passed `True`; width `2.1`, height `1.8`, aspect `1.1667`, start-destination vertical separation `0.55`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 2 required taps, 0 alternate paths, 2 dead ends, 0 loops.
- Difficulty model: estimated `expert`, mechanical `0.9337`, visual `0.94`, campaign pacing `0.64`, preset fit `0.776`.
- Score breakdown: mechanic `1.0`, runtime `1.0`, readability `0.9175`, route interest `1.0`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.8964`, diversity `0.9663` (topology `1.0`, mechanic penalty `0.075`, topology penalty `0.0`).
- Route interest: score `1.0`; tags `fake_shortcut, split_rejoin, package_gate_tension, tempting_wrong_branch, multi_exit_hub, meaningful_turns`; fake shortcut `True`; branch/rejoin `True`; package tension `True`; loop/revisit `False`; turns `4`; repeated topology penalty `0.0`.
- Solution route: `start` -> `hub` -> `package_branch` -> `package` -> `rejoin` -> `switch_b` -> `destination`.
- Required taps: tap `hub` at `0.10s` -> `e_hub_package_branch` (0.4s window), tap `switch_b` at `5.63s` -> `e_switch_b_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.9130 vs 0.9045). Scores min/avg/max `0.8624`/`0.8933`/`0.913`.
- Accepted candidate audit: family `hub_choice`; variant `hub_choice_alternate`; tags `hub, multi_switch, rejoin, dead_end`; primary `hub`; topology `hub_spoke`; path `6`; orientation `horizontal`; Swift-required `False`; strategy `hub_and_spoke`; variant `normal`; orientation reason `mixed_horizontal`; route interest `1.0`; diversity `topology 1.0, mechanic penalty 0.075, topology penalty 0.0, score 0.9663`.
- Near miss `not_selected` seed `1631844815` score `0.9045` family `package_gate` variant `package_gate_long_gate` tags `package_gate, multi_switch` primary `package_gate` topology `package_gate` path `5` orientation `horizontal` Swift-required `False` strategy `split_lane` variant `normal` orientation reason `mixed_horizontal` route interest `0.737` diversity `topology 0.92, mechanic penalty 0.185, topology penalty 0.08, score 0.8728`.
- Near miss `route_interest_below_medium_gate` seed `1042844973` score `0.8624` family `multi_switch_order` variant `multi_switch_order_alternate` tags `multi_switch, switch_order` primary `multi_switch` topology `two_switch_order` path `4` orientation `horizontal` Swift-required `False` strategy `horizontal_route_progression` variant `normal` orientation reason `mixed_horizontal` route interest `0.405` diversity `topology 1.0, mechanic penalty 0.08, topology penalty 0.0, score 0.964`.
- Switch `hub` starts on `e_hub_dead_end_a` (north); tap 1 @ 0.10s -> `e_hub_package_branch` (east).
- Switch `switch_b` starts on `e_switch_b_dead_end_b` (south); tap 1 @ 5.63s -> `e_switch_b_destination` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 3-way switch 'hub' with 3 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'switch_b' with 2 option(s).
### `level_096`
- Recipe: `long_detour_gate` variant `long_detour_gate_primary`; abstract signature `6897b35c1955`.
- Mechanics: tags `long_route, detour, package_gate`; primary `long_route`; topology `detour_gate`; required path length `6`; layout orientation `horizontal` via `mixed_horizontal`; Swift-required `False`; unlock `detours unlocked`; depends on `short_detour_gate`.
- Diversity audit: topology 1.0, mechanic penalty 0.0667, topology penalty 0.0, score 0.97.
- Layout: `normal`; strategy: `split_lane`; profile: `horizontal`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `horizontal`; road shapes: `auto` (score `0.96`).
- Portrait checks: passed `True`; width `2.0`, height `0.9`, aspect `2.2222`, start-destination vertical separation `0.0`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 2 required taps, 0 alternate paths, 1 dead ends, 0 loops.
- Difficulty model: estimated `expert`, mechanical `0.8472`, visual `0.94`, campaign pacing `0.56`, preset fit `0.776`.
- Score breakdown: mechanic `0.96`, runtime `1.0`, readability `0.74`, route interest `1.0`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.8165`, diversity `0.97` (topology `1.0`, mechanic penalty `0.0667`, topology penalty `0.0`).
- Route interest: score `1.0`; tags `fake_shortcut, split_rejoin, correct_detour, package_gate_tension, tempting_wrong_branch, meaningful_turns`; fake shortcut `True`; branch/rejoin `True`; package tension `True`; loop/revisit `False`; turns `3`; repeated topology penalty `0.0`.
- Solution route: `start` -> `switch_gate` -> `detour_a` -> `package` -> `rejoin` -> `switch_exit` -> `destination`.
- Required taps: tap `switch_gate` at `0.10s` -> `e_switch_gate_detour_a` (0.25s window), tap `switch_exit` at `1.85s` -> `e_switch_exit_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.8817 vs 0.8736). Scores min/avg/max `0.8736`/`0.8777`/`0.8817`.
- Accepted candidate audit: family `long_detour_gate`; variant `long_detour_gate_primary`; tags `long_route, detour, package_gate`; primary `long_route`; topology `detour_gate`; path `6`; orientation `horizontal`; Swift-required `False`; strategy `split_lane`; variant `normal`; orientation reason `mixed_horizontal`; route interest `1.0`; diversity `topology 1.0, mechanic penalty 0.0667, topology penalty 0.0, score 0.97`.
- Near miss `not_selected` seed `2716366784` score `0.8736` family `return_loop_intro` variant `return_loop_intro_primary` tags `loop, repeated_tap, multi_switch, return_loop` primary `loop` topology `two_switch_order` path `4` orientation `horizontal` Swift-required `False` strategy `package_inside_loop` variant `normal` orientation reason `mixed_horizontal` route interest `0.58` diversity `topology 1.0, mechanic penalty 0.105, topology penalty 0.0, score 0.9527`.
- Switch `switch_gate` starts on `e_switch_gate_direct_bypass` (north); tap 1 @ 0.10s -> `e_switch_gate_detour_a` (east).
- Switch `switch_exit` starts on `e_switch_exit_dead_end_b` (north); tap 1 @ 1.85s -> `e_switch_exit_destination` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'switch_gate' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'switch_exit' with 2 option(s).
### `level_097`
- Recipe: `return_loop_intro` variant `return_loop_intro_primary`; abstract signature `95276aba2bfb`.
- Mechanics: tags `loop, repeated_tap, multi_switch, return_loop`; primary `loop`; topology `two_switch_order`; required path length `4`; layout orientation `horizontal` via `mixed_horizontal`; Swift-required `False`; unlock `return loops unlocked`; depends on `multi_switch_order`.
- Diversity audit: topology 1.0, mechanic penalty 0.08, topology penalty 0.0, score 0.964.
- Layout: `normal`; strategy: `package_inside_loop`; profile: `horizontal`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `horizontal`; road shapes: `auto` (score `0.97`).
- Portrait checks: passed `True`; width `2.0`, height `1.4`, aspect `1.4286`, start-destination vertical separation `-0.05`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 2 required taps, 0 alternate paths, 2 dead ends, 0 loops.
- Difficulty model: estimated `hard`, mechanical `0.7339`, visual `0.685`, campaign pacing `0.78`, preset fit `0.8845`.
- Score breakdown: mechanic `0.95`, runtime `1.0`, readability `0.9925`, route interest `0.58`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9966`, diversity `0.964` (topology `1.0`, mechanic penalty `0.08`, topology penalty `0.0`).
- Route interest: score `0.58`; tags `loop_or_revisit, meaningful_turns`; fake shortcut `False`; branch/rejoin `False`; package tension `False`; loop/revisit `True`; turns `3`; repeated topology penalty `0.0`.
- Solution route: `start` -> `switch_a` -> `package` -> `switch_b` -> `destination`.
- Required taps: tap `switch_a` at `0.82s` -> `e_switch_a_package` (0.45s window), tap `switch_b` at `2.70s` -> `e_switch_b_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.8779 vs 0.8755). Scores min/avg/max `0.8755`/`0.8767`/`0.8779`.
- Accepted candidate audit: family `return_loop_intro`; variant `return_loop_intro_primary`; tags `loop, repeated_tap, multi_switch, return_loop`; primary `loop`; topology `two_switch_order`; path `4`; orientation `horizontal`; Swift-required `False`; strategy `package_inside_loop`; variant `normal`; orientation reason `mixed_horizontal`; route interest `0.58`; diversity `topology 1.0, mechanic penalty 0.08, topology penalty 0.0, score 0.964`.
- Near miss `not_selected` seed `3506388832` score `0.8755` family `return_loop` variant `return_loop_upper` tags `loop, repeated_tap` primary `loop` topology `return_loop` path `6` orientation `horizontal` Swift-required `False` strategy `package_inside_loop` variant `normal` orientation reason `mixed_horizontal` route interest `0.822` diversity `topology 0.92, mechanic penalty 0.07, topology penalty 0.08, score 0.9245`.
- Switch `switch_a` starts on `e_switch_a_dead_end_a` (north); tap 1 @ 0.82s -> `e_switch_a_package` (east).
- Switch `switch_b` starts on `e_switch_b_dead_end_b` (north); tap 1 @ 2.70s -> `e_switch_b_destination` (south).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'switch_a' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'switch_b' with 2 option(s).
### `level_098`
- Recipe: `fake_shortcut` variant `fake_shortcut_primary`; abstract signature `29bedea142dc`.
- Mechanics: tags `fake_shortcut, detour, package_gate, dead_end`; primary `fake_shortcut`; topology `detour_gate`; required path length `6`; layout orientation `horizontal` via `probability`; Swift-required `False`; unlock `medium levels unlocked`; depends on `short_detour_gate`.
- Diversity audit: topology 0.92, mechanic penalty 0.0725, topology penalty 0.08, score 0.9234.
- Layout: `mirrored`; strategy: `split_lane`; profile: `vertical`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `horizontal`; road shapes: `auto` (score `0.96`).
- Portrait checks: passed `True`; width `2.0`, height `0.9`, aspect `2.2222`, start-destination vertical separation `0.0`.
- Vertical candidate rejected: `layout_node_too_close_to_edge`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 2 required taps, 0 alternate paths, 2 dead ends, 0 loops.
- Difficulty model: estimated `expert`, mechanical `0.7972`, visual `0.845`, campaign pacing `0.5`, preset fit `0.8425`.
- Score breakdown: mechanic `0.95`, runtime `1.0`, readability `0.99`, route interest `0.952`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9622`, diversity `0.9234` (topology `0.92`, mechanic penalty `0.0725`, topology penalty `0.08`).
- Route interest: score `0.952`; tags `fake_shortcut, correct_detour, package_gate_tension, meaningful_turns`; fake shortcut `True`; branch/rejoin `False`; package tension `True`; loop/revisit `False`; turns `3`; repeated topology penalty `0.08`.
- Solution route: `start` -> `choice` -> `detour_a` -> `package` -> `detour_b` -> `switch_b` -> `destination`.
- Required taps: tap `choice` at `0.10s` -> `e_choice_detour_a` (0.25s window), tap `switch_b` at `1.85s` -> `e_switch_b_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.8866 vs 0.8801). Scores min/avg/max `0.8126`/`0.8535`/`0.8866`.
- Accepted candidate audit: family `fake_shortcut`; variant `fake_shortcut_primary`; tags `fake_shortcut, detour, package_gate, dead_end`; primary `fake_shortcut`; topology `detour_gate`; path `6`; orientation `horizontal`; Swift-required `False`; strategy `split_lane`; variant `mirrored`; orientation reason `probability`; route interest `0.952`; diversity `topology 0.92, mechanic penalty 0.0725, topology penalty 0.08, score 0.9234`.
- Near miss `quality_similarity_above_threshold` seed `3691806` score `0.8801` family `package_gate_double_choice` variant `package_gate_double_choice_alternate` tags `package_gate, multi_switch, two_switch` primary `package_gate` topology `package_gate` path `4` orientation `vertical` Swift-required `False` strategy `vertical_split_lane` variant `mirrored` orientation reason `probability` route interest `0.64` diversity `topology 1.0, mechanic penalty 0.12, topology penalty 0.0, score 0.946`.
- Near miss `not_selected` seed `1473943189` score `0.8723` family `return_loop` variant `return_loop_upper` tags `loop, repeated_tap` primary `loop` topology `return_loop` path `6` orientation `horizontal` Swift-required `False` strategy `package_inside_loop` variant `normal` orientation reason `mixed_horizontal` route interest `0.87` diversity `topology 1.0, mechanic penalty 0.31, topology penalty 0.0, score 0.8605`.
- Near miss `route_interest_below_medium_gate` seed `298191596` score `0.816` family `multi_switch_order` variant `multi_switch_order_primary` tags `multi_switch, switch_order` primary `multi_switch` topology `two_switch_order` path `4` orientation `horizontal` Swift-required `False` strategy `horizontal_route_progression` variant `mirrored` orientation reason `mixed_horizontal` route interest `0.245` diversity `topology 0.7, mechanic penalty 0.115, topology penalty 0.3, score 0.7833`.
- Switch `choice` starts on `e_choice_shortcut_dead_end` (south); tap 1 @ 0.10s -> `e_choice_detour_a` (east).
- Switch `switch_b` starts on `e_switch_b_dead_end_b` (south); tap 1 @ 1.85s -> `e_switch_b_destination` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'choice' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'switch_b' with 2 option(s).
### `level_099`
- Recipe: `package_gate_double_choice` variant `package_gate_double_choice_primary`; abstract signature `f1f3a6cf8f7f`.
- Mechanics: tags `package_gate, multi_switch, two_switch`; primary `package_gate`; topology `package_gate`; required path length `4`; layout orientation `horizontal` via `mixed_horizontal`; Swift-required `False`; unlock `package gate learned`; depends on `package_gate_simple`.
- Diversity audit: topology 1.0, mechanic penalty 0.11, topology penalty 0.0, score 0.9505.
- Layout: `mirrored`; strategy: `split_lane`; profile: `horizontal`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `horizontal`; road shapes: `auto` (score `0.96`).
- Portrait checks: passed `True`; width `2.0`, height `0.9`, aspect `2.2222`, start-destination vertical separation `0.0`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 2 required taps, 0 alternate paths, 2 dead ends, 0 loops.
- Difficulty model: estimated `hard`, mechanical `0.7072`, visual `0.685`, campaign pacing `0.78`, preset fit `0.8845`.
- Score breakdown: mechanic `0.95`, runtime `1.0`, readability `0.99`, route interest `0.64`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9955`, diversity `0.9505` (topology `1.0`, mechanic penalty `0.11`, topology penalty `0.0`).
- Route interest: score `0.64`; tags `package_gate_tension, meaningful_turns`; fake shortcut `False`; branch/rejoin `False`; package tension `True`; loop/revisit `False`; turns `3`; repeated topology penalty `0.0`.
- Solution route: `start` -> `switch_a` -> `package` -> `switch_b` -> `destination`.
- Required taps: tap `switch_a` at `0.10s` -> `e_switch_a_package` (0.4s window), tap `switch_b` at `1.70s` -> `e_switch_b_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.8815 vs 0.8457). Scores min/avg/max `0.834`/`0.8509`/`0.8815`.
- Accepted candidate audit: family `package_gate_double_choice`; variant `package_gate_double_choice_primary`; tags `package_gate, multi_switch, two_switch`; primary `package_gate`; topology `package_gate`; path `4`; orientation `horizontal`; Swift-required `False`; strategy `split_lane`; variant `mirrored`; orientation reason `mixed_horizontal`; route interest `0.64`; diversity `topology 1.0, mechanic penalty 0.11, topology penalty 0.0, score 0.9505`.
- Near miss `route_interest_below_medium_gate` seed `1088213644` score `0.8457` family `multi_switch_order` variant `multi_switch_order_primary` tags `multi_switch, switch_order` primary `multi_switch` topology `two_switch_order` path `4` orientation `horizontal` Swift-required `False` strategy `horizontal_route_progression` variant `mirrored` orientation reason `mixed_horizontal` route interest `0.357` diversity `topology 0.92, mechanic penalty 0.07, topology penalty 0.08, score 0.9245`.
- Near miss `route_interest_below_medium_gate` seed `1085965553` score `0.8425` family `multi_switch_order` variant `multi_switch_order_primary` tags `multi_switch, switch_order` primary `multi_switch` topology `two_switch_order` path `4` orientation `horizontal` Swift-required `False` strategy `horizontal_route_progression` variant `normal` orientation reason `mixed_horizontal` route interest `0.357` diversity `topology 0.92, mechanic penalty 0.07, topology penalty 0.08, score 0.9245`.
- Near miss `not_selected` seed `2560713249` score `0.834` family `long_detour_gate` variant `long_detour_gate_primary` tags `long_route, detour, package_gate` primary `long_route` topology `detour_gate` path `6` orientation `horizontal` Swift-required `False` strategy `split_lane` variant `mirrored` orientation reason `mixed_horizontal` route interest `1.0` diversity `topology 0.62, mechanic penalty 0.15, topology penalty 0.38, score 0.7235`.
- Switch `switch_a` starts on `e_switch_a_dead_end_a` (south); tap 1 @ 0.10s -> `e_switch_a_package` (east).
- Switch `switch_b` starts on `e_switch_b_dead_end_b` (south); tap 1 @ 1.70s -> `e_switch_b_destination` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'switch_a' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'switch_b' with 2 option(s).
### `level_100`
- Recipe: `package_gate` variant `package_gate_crossing_avoidance`; abstract signature `57a53734d024`.
- Mechanics: tags `package_gate, multi_switch`; primary `package_gate`; topology `package_gate`; required path length `4`; layout orientation `horizontal` via `mixed_horizontal`; Swift-required `False`; unlock `none`; depends on `none`.
- Diversity audit: topology 0.7, mechanic penalty 0.385, topology penalty 0.3, score 0.6618.
- Layout: `normal`; strategy: `split_lane`; profile: `horizontal`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `horizontal`; road shapes: `auto` (score `0.96`).
- Portrait checks: passed `True`; width `2.0`, height `0.9`, aspect `2.2222`, start-destination vertical separation `0.0`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 2 required taps, 0 alternate paths, 2 dead ends, 0 loops.
- Difficulty model: estimated `hard`, mechanical `0.7072`, visual `0.685`, campaign pacing `0.65`, preset fit `0.8845`.
- Score breakdown: mechanic `0.95`, runtime `1.0`, readability `0.99`, route interest `0.66`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9955`, diversity `0.6618` (topology `0.7`, mechanic penalty `0.385`, topology penalty `0.3`).
- Route interest: score `0.66`; tags `fake_shortcut, package_gate_tension, meaningful_turns`; fake shortcut `True`; branch/rejoin `False`; package tension `True`; loop/revisit `False`; turns `3`; repeated topology penalty `0.3`.
- Solution route: `start` -> `short_entry_switch` -> `package` -> `short_finish_switch` -> `destination`.
- Required taps: tap `short_entry_switch` at `0.10s` -> `e_short_entry_switch_package` (0.4s window), tap `short_finish_switch` at `1.70s` -> `e_short_finish_switch_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.8818 vs 0.8661). Scores min/avg/max `0.8584`/`0.8671`/`0.8818`.
- Accepted candidate audit: family `package_gate`; variant `package_gate_crossing_avoidance`; tags `package_gate, multi_switch`; primary `package_gate`; topology `package_gate`; path `4`; orientation `horizontal`; Swift-required `False`; strategy `split_lane`; variant `normal`; orientation reason `mixed_horizontal`; route interest `0.66`; diversity `topology 0.7, mechanic penalty 0.385, topology penalty 0.3, score 0.6618`.
- Near miss `route_interest_below_medium_gate` seed `2554519713` score `0.8661` family `multi_switch_chain` variant `multi_switch_chain_stair_step` tags `multi_switch` primary `multi_switch` topology `two_switch_order` path `4` orientation `horizontal` Swift-required `False` strategy `horizontal_route_progression` variant `mirrored` orientation reason `mixed_horizontal` route interest `0.357` diversity `topology 0.92, mechanic penalty 0.23, topology penalty 0.08, score 0.8525`.
- Near miss `route_interest_below_medium_gate` seed `2552271622` score `0.8621` family `multi_switch_chain` variant `multi_switch_chain_stair_step` tags `multi_switch` primary `multi_switch` topology `two_switch_order` path `4` orientation `horizontal` Swift-required `False` strategy `horizontal_route_progression` variant `normal` orientation reason `mixed_horizontal` route interest `0.357` diversity `topology 0.92, mechanic penalty 0.23, topology penalty 0.08, score 0.8525`.
- Near miss `not_selected` seed `3438019607` score `0.8584` family `package_gate` variant `package_gate_crossing_avoidance` tags `package_gate, multi_switch` primary `package_gate` topology `package_gate` path `4` orientation `horizontal` Swift-required `False` strategy `split_lane` variant `mirrored` orientation reason `probability` route interest `0.66` diversity `topology 0.7, mechanic penalty 0.385, topology penalty 0.3, score 0.6618`.
- Switch `short_entry_switch` starts on `e_short_entry_switch_short_bypass` (north); tap 1 @ 0.10s -> `e_short_entry_switch_package` (east).
- Switch `short_finish_switch` starts on `e_short_finish_switch_short_dead_end` (north); tap 1 @ 1.70s -> `e_short_finish_switch_destination` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'short_entry_switch' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'short_finish_switch' with 2 option(s).

## Rejections

- Rejected candidates: `61`
- `candidate_too_similar_to_batch`: 40
- `important_node_readability_blocked_by_road`: 3
- `layout_node_out_of_bounds`: 4
- `quality_similarity_above_threshold`: 1
- `route_interest_below_medium_gate`: 9
- `solution_tap_not_before_switch_arrival`: 4

## Messages

- Rejected candidate level_093 seed=3168768331 template=multi_switch_chain reason=route_interest_below_medium_gate detail=route interest 0.405 < 0.420
- Rejected candidate level_094 seed=4253290300 template=multi_switch_order reason=route_interest_below_medium_gate detail=route interest 0.405 < 0.420
- Rejected candidate level_094 seed=252822925 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_091: same topology, solution, and layout (c115d191/547b0f2b)
- Rejected candidate level_095 seed=1042844973 template=multi_switch_order reason=route_interest_below_medium_gate detail=route interest 0.405 < 0.420
- Rejected candidate level_096 seed=2127366942 template=package_gate_double_choice reason=candidate_too_similar_to_batch detail=matches level_092: same topology, solution, and layout (501007b5/22e42c17)
- Rejected candidate level_096 seed=2421866863 template=split_path_rejoin reason=candidate_too_similar_to_batch detail=matches level_093: same topology, solution, and layout (404d3c3f/22e42c17)
- Rejected candidate level_098 seed=1443584 template=package_gate_double_choice reason=candidate_too_similar_to_batch detail=matches level_092: same topology, solution, and layout (501007b5/22e42c17)
- Rejected candidate level_098 seed=295943505 template=multi_switch_order reason=route_interest_below_medium_gate detail=route interest 0.245 < 0.420
- Rejected candidate level_098 seed=590443426 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_091: same topology, solution, and layout (c115d191/547b0f2b)
- Rejected candidate level_098 seed=884943347 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_095: same topology, solution, and layout (02fd7ebc/84ab4378)
- Rejected candidate level_098 seed=1179443268 template=split_path_rejoin reason=candidate_too_similar_to_batch detail=matches level_093: same topology, solution, and layout (404d3c3f/22e42c17)
- Rejected candidate level_098 seed=1443715 template=package_gate_double_choice reason=candidate_too_similar_to_batch detail=matches level_092: similarity 0.90 >= 0.88
- Rejected candidate level_098 seed=590443557 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_091: similarity 0.91 >= 0.88
- Rejected candidate level_098 seed=884943478 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_095: same topology, solution, and layout (02fd7ebc/84ab4378)
- Rejected candidate level_098 seed=1473943320 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_098: similarity 0.90 >= 0.88
- Rejected candidate level_098 seed=590460587 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_091: same topology, solution, and layout (c115d191/547b0f2b)
- Rejected candidate level_098 seed=590460718 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_091: similarity 0.91 >= 0.88
- Rejected candidate level_098 seed=3691675 template=package_gate_double_choice reason=candidate_too_similar_to_batch detail=matches level_092: similarity 0.91 >= 0.88
- Rejected candidate level_098 seed=298191596 template=multi_switch_order reason=route_interest_below_medium_gate detail=route interest 0.245 < 0.420
- Rejected candidate level_098 seed=592691517 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_091: similarity 0.90 >= 0.88
- Rejected candidate level_098 seed=887191438 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_095: similarity 0.90 >= 0.88
- Rejected candidate level_098 seed=1476191280 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_098: similarity 0.89 >= 0.88
- Rejected candidate level_098 seed=3691806 template=package_gate_double_choice reason=quality_similarity_above_threshold detail=similarity 0.87 > 0.87
- Rejected candidate level_099 seed=1085965553 template=multi_switch_order reason=route_interest_below_medium_gate detail=route interest 0.357 < 0.420
- Rejected candidate level_099 seed=1380465474 template=package_gate_double_choice reason=candidate_too_similar_to_batch detail=matches level_092: same topology, solution, and layout (501007b5/22e42c17)
- Rejected candidate level_099 seed=1674965395 template=split_path_rejoin reason=candidate_too_similar_to_batch detail=matches level_093: same topology, solution, and layout (404d3c3f/22e42c17)
- Rejected candidate level_099 seed=1969465316 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_094: same topology, solution, and layout (f152647c/50bb2282)
- Rejected candidate level_099 seed=2263965237 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_095: same topology, solution, and layout (02fd7ebc/84ab4378)
- Rejected candidate level_099 seed=2558465158 template=long_detour_gate reason=candidate_too_similar_to_batch detail=matches level_096: same topology, solution, and layout (eb2c3b9e/e45124c2)
- Rejected candidate level_099 seed=1380465605 template=package_gate_double_choice reason=candidate_too_similar_to_batch detail=matches level_092: similarity 0.90 >= 0.88
- Rejected candidate level_099 seed=1969465447 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_094: similarity 0.90 >= 0.88
- Rejected candidate level_099 seed=2263965368 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_095: same topology, solution, and layout (02fd7ebc/84ab4378)
- Rejected candidate level_099 seed=2558465289 template=long_detour_gate reason=candidate_too_similar_to_batch detail=matches level_096: same topology, solution, and layout (eb2c3b9e/e45124c2)
- Rejected candidate level_099 seed=1088213644 template=multi_switch_order reason=route_interest_below_medium_gate detail=route interest 0.357 < 0.420
- Rejected candidate level_099 seed=1971713407 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_094: similarity 0.90 >= 0.88
- Rejected candidate level_100 seed=2552271622 template=multi_switch_chain reason=route_interest_below_medium_gate detail=route interest 0.357 < 0.420
- Rejected candidate level_100 seed=2846771543 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_094: same topology, solution, and layout (f152647c/50bb2282)
- Rejected candidate level_100 seed=3141271464 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_091: same topology, solution, and layout (c115d191/547b0f2b)
- Rejected candidate level_100 seed=3730271306 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_095: same topology, solution, and layout (02fd7ebc/84ab4378)
- Rejected candidate level_100 seed=4024771227 template=split_path_rejoin reason=candidate_too_similar_to_batch detail=matches level_093: same topology, solution, and layout (404d3c3f/22e42c17)
- Rejected candidate level_100 seed=2846771674 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_094: similarity 0.90 >= 0.88
- Rejected candidate level_100 seed=3141271595 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_091: similarity 0.91 >= 0.88
- Rejected candidate level_100 seed=3435771516 template=package_gate reason=candidate_too_similar_to_batch detail=matches level_100: similarity 0.90 >= 0.88
- Rejected candidate level_100 seed=3730271437 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_095: same topology, solution, and layout (02fd7ebc/84ab4378)
- Rejected candidate level_100 seed=2554519713 template=multi_switch_chain reason=route_interest_below_medium_gate detail=route interest 0.357 < 0.420
- Rejected candidate level_100 seed=2849019634 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_094: similarity 0.89 >= 0.88
- Rejected candidate level_100 seed=3143519555 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_098: same topology, solution, and layout (c115d191/547b0f2b)
- Rejected candidate level_100 seed=3438019476 template=package_gate reason=candidate_too_similar_to_batch detail=matches level_100: similarity 0.91 >= 0.88
- Rejected candidate level_100 seed=3732519397 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_095: similarity 0.90 >= 0.88
- Rejected candidate level_100 seed=2849019765 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_094: similarity 0.89 >= 0.88
- Regenerated TinyRoutes.xcodeproj with xcodegen.

## Swift Test Summary

- Command: `not run`
- Result: `Swift tests were not run.`

## Next Steps

- Open generated levels in the Level Editor.
- Run Python validation and Swift solvability before committing production levels.
- `xcodegen generate` runs automatically for default production output; rerun it manually if resources were deleted outside the generator.
