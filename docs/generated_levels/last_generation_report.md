# Tiny Routes Generation Report

- Generated: `2026-06-07T13:11:12.045965+00:00`
- Repo root: `/Users/jake/Developer/Tiny-Routes`
- Difficulty: `hard`
- Template mode: `mixed`
- Generation profile: `production`
- Generation mode: `recipe_first`
- Base seed: `None`
- Dry run: `False`
- Dry-run pass rate: `0.0009`
- Compare existing levels: `True`
- Candidate pool size: `3`
- Candidate generation count: `7860`
- Candidate validation count: `7607`
- Rejection phases: `{'generationErrors': 0, 'validationFailures': 5265, 'selectionFilters': 2324}`
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

- Difficulty: `{'hard': 7}`
- Recipe: `{'branch_then_rejoin_with_wrong_order': 1, 'fake_shortcut': 1, 'hub_choice': 1, 'long_detour_gate': 1, 'ring_route': 1, 'split_path_rejoin': 1, 'two_phase_route': 1}`
- Topology: `{'detour_gate': 2, 'hub_spoke': 1, 'ring': 1, 'split_rejoin': 2, 'two_phase': 1}`
- Family streaks: `{'longest': {'value': 'long_detour_gate', 'length': 1}, 'repeatedStreaks': []}`
- Topology streaks: `{'longest': {'value': 'split_rejoin', 'length': 2}, 'repeatedStreaks': [{'value': 'split_rejoin', 'length': 2}]}`
- Map size: `{'large_portrait': 2, 'standard_portrait': 5}`
- Route interest score: `{'excellent': 6, 'strong': 1}`
- Route interest by difficulty: `{'hard': {'minimum': 0.815, 'average': 0.9736, 'maximum': 1.0, 'count': 7, 'distribution': {'excellent': 6, 'strong': 1}}}`
- Candidate generation by difficulty: `{'hard': 7860}`
- Candidate validation by difficulty: `{'hard': 7607}`
- Accepted vs rejected by difficulty: `{'hard': {'accepted': 7, 'rejected': 7589}}`
- Similarity rejections by difficulty: `{'hard': 2230}`
- Starvation causes: `{'totalRejections': 7589, 'phaseCounts': {'generationErrors': 0, 'validationFailures': 5265, 'selectionFilters': 2324}, 'topCategories': [{'category': 'layoutValidity', 'count': 2425, 'share': 0.3195}, {'category': 'batchSimilarity', 'count': 2230, 'share': 0.2938}, {'category': 'readabilityBlockedRoads', 'count': 319, 'share': 0.042}, {'category': 'routeInterestGate', 'count': 94, 'share': 0.0124}, {'category': 'tapTiming', 'count': 22, 'share': 0.0029}], 'topReasons': [{'reason': 'candidate_too_similar_to_batch', 'count': 2230, 'share': 0.2938}, {'reason': 'non_adjacent_roads_too_close', 'count': 1901, 'share': 0.2505}, {'reason': 'portrait_layout_too_wide', 'count': 895, 'share': 0.1179}, {'reason': 'same_switch_first_segments_overlap', 'count': 767, 'share': 0.1011}, {'reason': 'implicit_intersection_without_graph_node', 'count': 763, 'share': 0.1005}]}`

## Accepted Levels

| Level | Source | Mechanics | Topology | Path | Orientation | Diversity | Seed | Difficulty | Nodes | Edges | Switches | Par Taps | Time Limit | Quality | Preview | Signatures | Status |
|---|---|---|---|---:|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|---|
| `level_021` | `long_detour_gate / long_detour_gate_primary` | `long_route: long_route, detour, package_gate` | `detour_gate` | 8 | `vertical` | `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0` | 3673204628 | hard | 12 | 12 | 3 | 3 | 30 | 0.9577 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_021.svg) | `T:363dcbeb L:0ad618f3 S:8962f818` | passed |
| `level_022` | `two_phase_route / two_phase_route_primary` | `two_phase: two_phase, package_gate, split_path, rejoin, multi_switch` | `two_phase` | 8 | `vertical` | `topology 1.0, mechanic penalty 0.024, topology penalty 0.0, score 0.9892` | 1346241903 | hard | 12 | 12 | 3 | 3 | 30 | 0.9393 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_022.svg) | `T:a7a27ce9 L:72fddbf1 S:12c1018d` | passed |
| `level_023` | `hub_choice / hub_choice_primary` | `hub: hub, multi_switch, rejoin, dead_end` | `hub_spoke` | 8 | `vertical` | `topology 1.0, mechanic penalty 0.06, topology penalty 0.0, score 0.973` | 2725263793 | hard | 12 | 12 | 3 | 3 | 30 | 0.9316 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_023.svg) | `T:f4e1bc6c L:1a9b28f2 S:b7150b30` | passed |
| `level_024` | `ring_route / ring_route_package_inside` | `ring: ring, package_gate` | `ring` | 5 | `vertical` | `topology 1.0, mechanic penalty 0.08, topology penalty 0.0, score 0.964` | 3220785920 | hard | 9 | 11 | 3 | 3 | 30 | 0.9185 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_024.svg) | `T:a9d95cd3 L:1062f4c1 S:6047f946` | passed |
| `level_025` | `fake_shortcut / fake_shortcut_alternate` | `fake_shortcut: fake_shortcut, detour, package_gate, dead_end` | `detour_gate` | 8 | `vertical` | `topology 1.0, mechanic penalty 0.095, topology penalty 0.0, score 0.9573` | 3716325208 | hard | 12 | 11 | 3 | 3 | 30 | 0.9457 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_025.svg) | `T:7c294735 L:63c3ea84 S:a6ef2f9f` | passed |
| `level_026` | `branch_then_rejoin_with_wrong_order / branch_then_rejoin_with_wrong_order_alternate` | `split_path: split_path, rejoin, wrong_order, branch` | `split_rejoin` | 7 | `vertical` | `topology 1.0, mechanic penalty 0.0425, topology penalty 0.0, score 0.9809` | 1683862404 | hard | 11 | 10 | 3 | 3 | 30 | 0.9073 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_026.svg) | `T:e240dafe L:6008d97e S:56d7db03` | passed |
| `level_027` | `split_path_rejoin / split_path_rejoin_primary` | `split_path: split_path, rejoin, multi_switch, package_gate` | `split_rejoin` | 7 | `vertical` | `topology 0.7, mechanic penalty 0.305, topology penalty 0.3, score 0.6977` | 1137362672 | hard | 11 | 11 | 3 | 3 | 30 | 0.8742 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_027.svg) | `T:7162a7ad L:baf4d140 S:56d7db03` | passed |

## Level Details

### `level_021`
- Recipe: `long_detour_gate` variant `long_detour_gate_primary`; abstract signature `af9ddf5e33ac`.
- Mechanics: tags `long_route, detour, package_gate`; primary `long_route`; topology `detour_gate`; required path length `8`; layout orientation `vertical` via `portrait_profile_default`; Swift-required `False`; unlock `detours unlocked`; depends on `short_detour_gate`.
- Diversity audit: topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0.
- Layout: `normal`; strategy: `vertical_split_lane`; profile: `portrait_vertical`; map size: `large_portrait` from `difficulty_curve` via `difficulty_curve_route_interest_candidate`; orientation: `vertical`; road shapes: `auto` (score `0.86`).
- Portrait checks: passed `True`; width `1.5`, height `3.1`, aspect `0.4839`, start-destination vertical separation `3.1`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 3 required taps, 0 alternate paths, 2 dead ends, 0 loops.
- Difficulty model: estimated `expert`, mechanical `1.0`, visual `1.0`, campaign pacing `1.0`, preset fit `0.882`.
- Score breakdown: mechanic `1.0`, runtime `1.0`, readability `0.965`, route interest `1.0`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.8967`, diversity `1.0` (topology `1.0`, mechanic penalty `0.0`, topology penalty `0.0`).
- Route interest: score `1.0`; tags `fake_shortcut, split_rejoin, correct_detour, package_gate_tension, tempting_wrong_branch, meaningful_turns`; fake shortcut `True`; branch/rejoin `True`; package tension `True`; loop/revisit `False`; turns `6`; repeated topology penalty `0.0`.
- Solution route: `start` -> `switch_gate` -> `detour_a` -> `switch_package` -> `package` -> `rejoin` -> `switch_exit` -> `exit_gate_lane` -> `destination`.
- Required taps: tap `switch_gate` at `0.15s` -> `e_switch_gate_detour_a` (0.45s window), tap `switch_package` at `1.20s` -> `e_switch_package_package` (0.45s window), tap `switch_exit` at `3.38s` -> `e_switch_exit_exit_gate_lane` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.9577 vs 0.9514). Scores min/avg/max `0.9222`/`0.9438`/`0.9577`.
- Accepted candidate audit: family `long_detour_gate`; variant `long_detour_gate_primary`; tags `long_route, detour, package_gate`; primary `long_route`; topology `detour_gate`; path `8`; orientation `vertical`; Swift-required `False`; strategy `vertical_split_lane`; variant `normal`; orientation reason `portrait_profile_default`; route interest `1.0`; diversity `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0`.
- Near miss `not_selected` seed `556219855` score `0.9514` family `two_phase_route` variant `two_phase_route_primary` tags `two_phase, package_gate, split_path, rejoin, multi_switch` primary `two_phase` topology `two_phase` path `8` orientation `vertical` Swift-required `False` strategy `vertical_split_lane` variant `normal` orientation reason `portrait_profile_default` route interest `1.0` diversity `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0`.
- Near miss `not_selected` seed `3967687388` score `0.9222` family `branch_then_rejoin_with_wrong_order` variant `branch_then_rejoin_with_wrong_order_primary` tags `split_path, rejoin, wrong_order, branch` primary `split_path` topology `split_rejoin` path `7` orientation `vertical` Swift-required `False` strategy `vertical_split_lane` variant `normal` orientation reason `portrait_profile_default` route interest `0.815` diversity `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0`.
- Switch `switch_gate` starts on `e_switch_gate_direct_bypass` (west); tap 1 @ 0.15s -> `e_switch_gate_detour_a` (east).
- Switch `switch_package` starts on `e_switch_package_dead_end_b` (east); tap 1 @ 1.20s -> `e_switch_package_package` (south).
- Switch `switch_exit` starts on `e_switch_exit_dead_end_c` (west); tap 1 @ 3.38s -> `e_switch_exit_exit_gate_lane` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'switch_gate' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'switch_package' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 3 taps 2-way switch 'switch_exit' with 2 option(s).
### `level_022`
- Recipe: `two_phase_route` variant `two_phase_route_primary`; abstract signature `dcf45b884645`.
- Mechanics: tags `two_phase, package_gate, split_path, rejoin, multi_switch`; primary `two_phase`; topology `two_phase`; required path length `8`; layout orientation `vertical` via `portrait_profile_default`; Swift-required `False`; unlock `hard levels unlocked`; depends on `package_gate_double_choice`.
- Diversity audit: topology 1.0, mechanic penalty 0.024, topology penalty 0.0, score 0.9892.
- Layout: `normal`; strategy: `vertical_split_lane`; profile: `portrait_vertical`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `vertical`; road shapes: `auto` (score `0.85`).
- Portrait checks: passed `True`; width `1.75`, height `2.0`, aspect `0.875`, start-destination vertical separation `2.0`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 3 required taps, 0 alternate paths, 2 dead ends, 0 loops.
- Difficulty model: estimated `expert`, mechanical `1.0`, visual `1.0`, campaign pacing `0.92`, preset fit `0.792`.
- Score breakdown: mechanic `1.0`, runtime `1.0`, readability `0.9625`, route interest `1.0`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.8956`, diversity `0.9892` (topology `1.0`, mechanic penalty `0.024`, topology penalty `0.0`).
- Route interest: score `1.0`; tags `fake_shortcut, split_rejoin, package_gate_tension, tempting_wrong_branch, two_phase, meaningful_turns`; fake shortcut `True`; branch/rejoin `True`; package tension `True`; loop/revisit `False`; turns `6`; repeated topology penalty `0.0`.
- Solution route: `start` -> `phase_one_switch` -> `package_lane` -> `package` -> `phase_bridge` -> `exit_choice` -> `exit_lane` -> `switch_final` -> `destination`.
- Required taps: tap `phase_one_switch` at `0.10s` -> `e_phase_one_switch_package_lane` (0.35s window), tap `exit_choice` at `2.15s` -> `e_exit_choice_exit_lane` (0.45s window), tap `switch_final` at `3.21s` -> `e_switch_final_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.9393 vs 0.9190). Scores min/avg/max `0.9173`/`0.9252`/`0.9393`.
- Accepted candidate audit: family `two_phase_route`; variant `two_phase_route_primary`; tags `two_phase, package_gate, split_path, rejoin, multi_switch`; primary `two_phase`; topology `two_phase`; path `8`; orientation `vertical`; Swift-required `False`; strategy `vertical_split_lane`; variant `normal`; orientation reason `portrait_profile_default`; route interest `1.0`; diversity `topology 1.0, mechanic penalty 0.024, topology penalty 0.0, score 0.9892`.
- Near miss `not_selected` seed `1640741824` score `0.919` family `ring_route` variant `ring_route_counterclockwise` tags `ring, package_gate` primary `ring` topology `ring` path `5` orientation `vertical` Swift-required `True` strategy `vertical_ring_loop` variant `normal` orientation reason `portrait_profile_default` route interest `1.0` diversity `topology 1.0, mechanic penalty 0.06, topology penalty 0.0, score 0.973`.
- Near miss `not_selected` seed `462742140` score `0.9173` family `branch_then_rejoin_with_wrong_order` variant `branch_then_rejoin_with_wrong_order_alternate` tags `split_path, rejoin, wrong_order, branch` primary `split_path` topology `split_rejoin` path `7` orientation `vertical` Swift-required `False` strategy `vertical_split_lane` variant `normal` orientation reason `portrait_profile_default` route interest `0.815` diversity `topology 1.0, mechanic penalty 0.0, topology penalty 0.0, score 1.0`.
- Switch `phase_one_switch` starts on `e_phase_one_switch_early_exit` (west); tap 1 @ 0.10s -> `e_phase_one_switch_package_lane` (east).
- Switch `exit_choice` starts on `e_exit_choice_dead_end_b` (south); tap 1 @ 2.15s -> `e_exit_choice_exit_lane` (east).
- Switch `switch_final` starts on `e_switch_final_dead_end_c` (west); tap 1 @ 3.21s -> `e_switch_final_destination` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'phase_one_switch' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'exit_choice' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 3 taps 2-way switch 'switch_final' with 2 option(s).
### `level_023`
- Recipe: `hub_choice` variant `hub_choice_primary`; abstract signature `a18c9a9a1c0f`.
- Mechanics: tags `hub, multi_switch, rejoin, dead_end`; primary `hub`; topology `hub_spoke`; required path length `8`; layout orientation `vertical` via `portrait_profile_default`; Swift-required `False`; unlock `three-way switches unlocked`; depends on `multi_switch_order`.
- Diversity audit: topology 1.0, mechanic penalty 0.06, topology penalty 0.0, score 0.973.
- Layout: `normal`; strategy: `vertical_hub_choice`; profile: `portrait_vertical`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `vertical`; road shapes: `auto` (score `0.87`).
- Portrait checks: passed `True`; width `1.7`, height `1.95`, aspect `0.8718`, start-destination vertical separation `1.95`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `0.92`, 1 issue(s).
- Abstract solution: 3 required taps, 0 alternate paths, 3 dead ends, 0 loops.
- Difficulty model: estimated `expert`, mechanical `1.0`, visual `1.0`, campaign pacing `0.84`, preset fit `0.792`.
- Score breakdown: mechanic `1.0`, runtime `1.0`, readability `0.9509`, route interest `1.0`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.8544`, diversity `0.973` (topology `1.0`, mechanic penalty `0.06`, topology penalty `0.0`).
- Route interest: score `1.0`; tags `fake_shortcut, split_rejoin, package_gate_tension, tempting_wrong_branch, multi_exit_hub, meaningful_turns`; fake shortcut `True`; branch/rejoin `True`; package tension `True`; loop/revisit `False`; turns `6`; repeated topology penalty `0.0`.
- Solution route: `start` -> `hub` -> `package_branch` -> `package` -> `rejoin` -> `switch_b` -> `route_mid` -> `switch_c` -> `destination`.
- Required taps: tap `hub` at `0.10s` -> `e_hub_package_branch` (0.35s window), tap `switch_b` at `3.06s` -> `e_switch_b_route_mid` (0.45s window), tap `switch_c` at `3.66s` -> `e_switch_c_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.9316 vs 0.9178). Scores min/avg/max `0.905`/`0.9181`/`0.9316`.
- Accepted candidate audit: family `hub_choice`; variant `hub_choice_primary`; tags `hub, multi_switch, rejoin, dead_end`; primary `hub`; topology `hub_spoke`; path `8`; orientation `vertical`; Swift-required `False`; strategy `vertical_hub_choice`; variant `normal`; orientation reason `portrait_profile_default`; route interest `1.0`; diversity `topology 1.0, mechanic penalty 0.06, topology penalty 0.0, score 0.973`.
- Near miss `not_selected` seed `2430763872` score `0.9178` family `ring_route` variant `ring_route_package_inside` tags `ring, package_gate` primary `ring` topology `ring` path `5` orientation `vertical` Swift-required `True` strategy `vertical_ring_loop` variant `normal` orientation reason `portrait_profile_default` route interest `1.0` diversity `topology 1.0, mechanic penalty 0.105, topology penalty 0.0, score 0.9527`.
- Near miss `not_selected` seed `1252764188` score `0.905` family `split_path_rejoin` variant `split_path_rejoin_primary` tags `split_path, rejoin, multi_switch, package_gate` primary `split_path` topology `split_rejoin` path `7` orientation `vertical` Swift-required `False` strategy `vertical_split_lane` variant `normal` orientation reason `portrait_profile_default` route interest `1.0` diversity `topology 1.0, mechanic penalty 0.1425, topology penalty 0.0, score 0.9359`.
- Switch `hub` starts on `e_hub_dead_end_a` (west); tap 1 @ 0.10s -> `e_hub_package_branch` (east).
- Switch `switch_b` starts on `e_switch_b_dead_end_b` (west); tap 1 @ 3.06s -> `e_switch_b_route_mid` (east).
- Switch `switch_c` starts on `e_switch_c_dead_end_c` (north); tap 1 @ 3.66s -> `e_switch_c_destination` (south).
- Warning: tap_node_switch_context: Solution action 1 taps 3-way switch 'hub' with 3 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'switch_b' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 3 taps 2-way switch 'switch_c' with 2 option(s).
- Warning: nodes_too_close: Nodes 'switch_c' and 'dead_end_c' are only 0.25 board units apart.
- Visual clarity warning: `nodes_too_close` node `switch_c` edge `None`.
### `level_024`
- Recipe: `ring_route` variant `ring_route_package_inside`; abstract signature `42f4e4eedf8e`.
- Mechanics: tags `ring, package_gate`; primary `ring`; topology `ring`; required path length `5`; layout orientation `vertical` via `portrait_profile_default`; Swift-required `True`; unlock `none`; depends on `none`.
- Diversity audit: topology 1.0, mechanic penalty 0.08, topology penalty 0.0, score 0.964.
- Layout: `normal`; strategy: `vertical_ring_loop`; profile: `portrait_vertical`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `vertical`; road shapes: `auto` (score `0.9`).
- Portrait checks: passed `True`; width `1.6`, height `1.8`, aspect `0.8889`, start-destination vertical separation `1.8`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 3 required taps, 7 alternate paths, 2 dead ends, 602 loops.
- Difficulty model: estimated `expert`, mechanical `1.0`, visual `1.0`, campaign pacing `0.84`, preset fit `0.652`.
- Score breakdown: mechanic `1.0`, runtime `1.0`, readability `0.975`, route interest `1.0`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9012`, diversity `0.964` (topology `1.0`, mechanic penalty `0.08`, topology penalty `0.0`).
- Route interest: score `1.0`; tags `fake_shortcut, split_rejoin, package_gate_tension, tempting_wrong_branch, loop_or_revisit, multi_exit_hub, meaningful_turns`; fake shortcut `True`; branch/rejoin `True`; package tension `True`; loop/revisit `True`; turns `4`; repeated topology penalty `0.0`.
- Solution route: `start` -> `hub` -> `package` -> `ring_b` -> `gate` -> `destination`.
- Required taps: tap `hub` at `0.50s` -> `e_hub_package` (0.45s window), tap `ring_b` at `2.19s` -> `e_ring_b_gate` (0.45s window), tap `gate` at `2.69s` -> `e_gate_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.9185 vs 0.9044). Scores min/avg/max `0.899`/`0.9073`/`0.9185`.
- Accepted candidate audit: family `ring_route`; variant `ring_route_package_inside`; tags `ring, package_gate`; primary `ring`; topology `ring`; path `5`; orientation `vertical`; Swift-required `True`; strategy `vertical_ring_loop`; variant `normal`; orientation reason `portrait_profile_default`; route interest `1.0`; diversity `topology 1.0, mechanic penalty 0.08, topology penalty 0.0, score 0.964`.
- Near miss `not_selected` seed `2337286157` score `0.9044` family `split_path_rejoin` variant `split_path_rejoin_primary` tags `split_path, rejoin, multi_switch, package_gate` primary `split_path` topology `split_rejoin` path `7` orientation `vertical` Swift-required `False` strategy `vertical_split_lane` variant `normal` orientation reason `portrait_profile_default` route interest `1.0` diversity `topology 1.0, mechanic penalty 0.1675, topology penalty 0.0, score 0.9246`.
- Near miss `not_selected` seed `1884264140` score `0.899` family `branch_then_rejoin_with_wrong_order` variant `branch_then_rejoin_with_wrong_order_alternate` tags `split_path, rejoin, wrong_order, branch` primary `split_path` topology `split_rejoin` path `7` orientation `vertical` Swift-required `False` strategy `vertical_split_lane` variant `normal` orientation reason `portrait_profile_default` route interest `0.815` diversity `topology 1.0, mechanic penalty 0.075, topology penalty 0.0, score 0.9663`.
- Switch `hub` starts on `e_hub_ring_a` (west); tap 1 @ 0.50s -> `e_hub_package` (east).
- Switch `ring_b` starts on `e_ring_b_ring_a` (north); tap 1 @ 2.19s -> `e_ring_b_gate` (west).
- Switch `gate` starts on `e_gate_dead_end_b` (west); tap 1 @ 2.69s -> `e_gate_destination` (south).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'hub' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 3-way switch 'ring_b' with 3 option(s).
- Warning: tap_node_switch_context: Solution action 3 taps 3-way switch 'gate' with 3 option(s).
### `level_025`
- Recipe: `fake_shortcut` variant `fake_shortcut_alternate`; abstract signature `bacbcf8e2415`.
- Mechanics: tags `fake_shortcut, detour, package_gate, dead_end`; primary `fake_shortcut`; topology `detour_gate`; required path length `8`; layout orientation `vertical` via `portrait_profile_default`; Swift-required `False`; unlock `medium levels unlocked`; depends on `short_detour_gate`.
- Diversity audit: topology 1.0, mechanic penalty 0.095, topology penalty 0.0, score 0.9573.
- Layout: `normal`; strategy: `vertical_split_lane`; profile: `portrait_vertical`; map size: `large_portrait` from `difficulty_curve` via `difficulty_curve_route_interest_candidate`; orientation: `vertical`; road shapes: `auto` (score `0.87`).
- Portrait checks: passed `True`; width `1.15`, height `2.85`, aspect `0.4035`, start-destination vertical separation `2.85`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `1.0`, 0 issue(s).
- Abstract solution: 3 required taps, 0 alternate paths, 3 dead ends, 0 loops.
- Difficulty model: estimated `expert`, mechanical `1.0`, visual `1.0`, campaign pacing `0.84`, preset fit `0.882`.
- Score breakdown: mechanic `1.0`, runtime `1.0`, readability `0.9675`, route interest `1.0`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.8979`, diversity `0.9573` (topology `1.0`, mechanic penalty `0.095`, topology penalty `0.0`).
- Route interest: score `1.0`; tags `fake_shortcut, correct_detour, package_gate_tension, meaningful_turns`; fake shortcut `True`; branch/rejoin `False`; package tension `True`; loop/revisit `False`; turns `6`; repeated topology penalty `0.0`.
- Solution route: `start` -> `choice` -> `detour_a` -> `switch_b` -> `package` -> `detour_b` -> `rejoin` -> `switch_c` -> `destination`.
- Required taps: tap `choice` at `0.10s` -> `e_choice_detour_a` (0.42s window), tap `switch_b` at `1.00s` -> `e_switch_b_package` (0.45s window), tap `switch_c` at `3.08s` -> `e_switch_c_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.9457 vs 0.9056). Scores min/avg/max `0.8361`/`0.8832`/`0.9457`.
- Accepted candidate audit: family `fake_shortcut`; variant `fake_shortcut_alternate`; tags `fake_shortcut, detour, package_gate, dead_end`; primary `fake_shortcut`; topology `detour_gate`; path `8`; orientation `vertical`; Swift-required `False`; strategy `vertical_split_lane`; variant `normal`; orientation reason `portrait_profile_default`; route interest `1.0`; diversity `topology 1.0, mechanic penalty 0.095, topology penalty 0.0, score 0.9573`.
- Near miss `not_selected` seed `4010807968` score `0.9056` family `branch_then_rejoin_with_wrong_order` variant `branch_then_rejoin_with_wrong_order_primary` tags `split_path, rejoin, wrong_order, branch` primary `split_path` topology `split_rejoin` path `7` orientation `vertical` Swift-required `False` strategy `vertical_split_lane` variant `normal` orientation reason `portrait_profile_default` route interest `0.815` diversity `topology 1.0, mechanic penalty 0.0575, topology penalty 0.0, score 0.9741`.
- Near miss `not_selected` seed `3109112275` score `0.8923` family `split_path_rejoin` variant `split_path_rejoin_alternate` tags `split_path, rejoin, multi_switch, package_gate` primary `split_path` topology `split_rejoin` path `7` orientation `vertical` Swift-required `False` strategy `vertical_split_lane` variant `normal` orientation reason `portrait_profile_default` route interest `1.0` diversity `topology 1.0, mechanic penalty 0.1575, topology penalty 0.0, score 0.9291`.
- Near miss `boring_topology_for_difficulty` seed `3417206343` score `0.8361` family `multi_switch_chain` variant `multi_switch_chain_stair_step` tags `multi_switch` primary `multi_switch` topology `two_switch_order` path `5` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `wide` orientation reason `portrait_profile_default` route interest `0.305` diversity `topology 1.0, mechanic penalty 0.16, topology penalty 0.0, score 0.928`.
- Switch `choice` starts on `e_choice_shortcut_dead_end` (south); tap 1 @ 0.10s -> `e_choice_detour_a` (west).
- Switch `switch_b` starts on `e_switch_b_dead_end_b` (east); tap 1 @ 1.00s -> `e_switch_b_package` (west).
- Switch `switch_c` starts on `e_switch_c_dead_end_c` (west); tap 1 @ 3.08s -> `e_switch_c_destination` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'choice' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'switch_b' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 3 taps 2-way switch 'switch_c' with 2 option(s).
### `level_026`
- Recipe: `branch_then_rejoin_with_wrong_order` variant `branch_then_rejoin_with_wrong_order_alternate`; abstract signature `05617f98da35`.
- Mechanics: tags `split_path, rejoin, wrong_order, branch`; primary `split_path`; topology `split_rejoin`; required path length `7`; layout orientation `vertical` via `portrait_profile_default`; Swift-required `False`; unlock `hard levels unlocked`; depends on `split_path_rejoin`.
- Diversity audit: topology 1.0, mechanic penalty 0.0425, topology penalty 0.0, score 0.9809.
- Layout: `normal`; strategy: `vertical_split_lane`; profile: `portrait_vertical`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `vertical`; road shapes: `auto` (score `0.93`).
- Portrait checks: passed `True`; width `1.4`, height `1.85`, aspect `0.7568`, start-destination vertical separation `1.85`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `0.84`, 2 issue(s).
- Abstract solution: 3 required taps, 0 alternate paths, 3 dead ends, 0 loops.
- Difficulty model: estimated `expert`, mechanical `1.0`, visual `1.0`, campaign pacing `0.84`, preset fit `0.792`.
- Score breakdown: mechanic `1.0`, runtime `1.0`, readability `0.9326`, route interest `0.815`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.8102`, diversity `0.9809` (topology `1.0`, mechanic penalty `0.0425`, topology penalty `0.0`).
- Route interest: score `0.815`; tags `split_rejoin, meaningful_turns`; fake shortcut `False`; branch/rejoin `True`; package tension `False`; loop/revisit `False`; turns `5`; repeated topology penalty `0.0`.
- Solution route: `start` -> `switch_a` -> `branch_a` -> `rejoin` -> `switch_b` -> `package` -> `switch_c` -> `destination`.
- Required taps: tap `switch_a` at `0.10s` -> `e_switch_a_branch_a` (0.31s window), tap `switch_b` at `1.07s` -> `e_switch_b_package` (0.45s window), tap `switch_c` at `1.86s` -> `e_switch_c_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.9073 vs 0.8962). Scores min/avg/max `0.8407`/`0.8696`/`0.9073`.
- Accepted candidate audit: family `branch_then_rejoin_with_wrong_order`; variant `branch_then_rejoin_with_wrong_order_alternate`; tags `split_path, rejoin, wrong_order, branch`; primary `split_path`; topology `split_rejoin`; path `7`; orientation `vertical`; Swift-required `False`; strategy `vertical_split_lane`; variant `normal`; orientation reason `portrait_profile_default`; route interest `0.815`; diversity `topology 1.0, mechanic penalty 0.0425, topology penalty 0.0, score 0.9809`.
- Near miss `not_selected` seed `3160710350` score `0.8962` family `split_path_rejoin` variant `split_path_rejoin_alternate` tags `split_path, rejoin, multi_switch, package_gate` primary `split_path` topology `split_rejoin` path `7` orientation `vertical` Swift-required `False` strategy `vertical_split_lane` variant `normal` orientation reason `portrait_profile_default` route interest `1.0` diversity `topology 1.0, mechanic penalty 0.1475, topology penalty 0.0, score 0.9336`.
- Near miss `boring_topology_for_difficulty` seed `2860492759` score `0.8747` family `multi_switch_chain` variant `multi_switch_chain_stair_step` tags `multi_switch` primary `multi_switch` topology `two_switch_order` path `6` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `normal` orientation reason `portrait_profile_default` route interest `0.435` diversity `topology 1.0, mechanic penalty 0.12, topology penalty 0.0, score 0.946`.
- Near miss `boring_topology_for_difficulty` seed `2860492760` score `0.8747` family `multi_switch_chain` variant `multi_switch_chain_stair_step` tags `multi_switch` primary `multi_switch` topology `two_switch_order` path `6` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `normal` orientation reason `portrait_profile_default` route interest `0.435` diversity `topology 1.0, mechanic penalty 0.12, topology penalty 0.0, score 0.946`.
- Switch `switch_a` starts on `e_switch_a_dead_end_a` (south); tap 1 @ 0.10s -> `e_switch_a_branch_a` (west).
- Switch `switch_b` starts on `e_switch_b_dead_end_b` (east); tap 1 @ 1.07s -> `e_switch_b_package` (west).
- Switch `switch_c` starts on `e_switch_c_dead_end_c` (west); tap 1 @ 1.86s -> `e_switch_c_destination` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'switch_a' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'switch_b' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 3 taps 2-way switch 'switch_c' with 2 option(s).
- Warning: nodes_too_close: Nodes 'branch_a' and 'rejoin' are only 0.25 board units apart.
- Warning: important_nodes_tight_on_small_device: Switch 'switch_b' is tight against important node 'package' at small-device scale.
- Visual clarity warning: `nodes_too_close` node `branch_a` edge `None`.
- Visual clarity warning: `important_nodes_tight_on_small_device` node `switch_b` edge `None`.
### `level_027`
- Recipe: `split_path_rejoin` variant `split_path_rejoin_primary`; abstract signature `55487039791b`.
- Mechanics: tags `split_path, rejoin, multi_switch, package_gate`; primary `split_path`; topology `split_rejoin`; required path length `7`; layout orientation `vertical` via `portrait_profile_default`; Swift-required `False`; unlock `medium levels unlocked`; depends on `two_switch_order_intro`.
- Diversity audit: topology 0.7, mechanic penalty 0.305, topology penalty 0.3, score 0.6977.
- Layout: `normal`; strategy: `vertical_split_lane`; profile: `portrait_vertical`; map size: `standard_portrait` from `difficulty_curve` via `difficulty_curve_standard_candidate`; orientation: `vertical`; road shapes: `auto` (score `0.92`).
- Portrait checks: passed `True`; width `1.8`, height `2.05`, aspect `0.878`, start-destination vertical separation `2.05`.
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `0.84`, 2 issue(s).
- Abstract solution: 3 required taps, 0 alternate paths, 2 dead ends, 0 loops.
- Difficulty model: estimated `expert`, mechanical `1.0`, visual `1.0`, campaign pacing `0.71`, preset fit `0.792`.
- Score breakdown: mechanic `1.0`, runtime `1.0`, readability `0.931`, route interest `1.0`, switch clarity `0.84`, mobile comfort `1.0`, visual appeal `0.8095`, diversity `0.6977` (topology `0.7`, mechanic penalty `0.305`, topology penalty `0.3`).
- Route interest: score `1.0`; tags `fake_shortcut, split_rejoin, package_gate_tension, tempting_wrong_branch, meaningful_turns`; fake shortcut `True`; branch/rejoin `True`; package tension `True`; loop/revisit `False`; turns `5`; repeated topology penalty `0.3`.
- Solution route: `start` -> `switch_a` -> `upper_branch` -> `switch_b` -> `package` -> `rejoin` -> `switch_c` -> `destination`.
- Required taps: tap `switch_a` at `0.10s` -> `e_switch_a_upper_branch` (0.4s window), tap `switch_b` at `0.88s` -> `e_switch_b_package` (0.45s window), tap `switch_c` at `2.46s` -> `e_switch_c_destination` (0.45s window).
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.8742 vs 0.8755). Scores min/avg/max `0.8415`/`0.8655`/`0.8755`.
- Accepted candidate audit: family `split_path_rejoin`; variant `split_path_rejoin_primary`; tags `split_path, rejoin, multi_switch, package_gate`; primary `split_path`; topology `split_rejoin`; path `7`; orientation `vertical`; Swift-required `False`; strategy `vertical_split_lane`; variant `normal`; orientation reason `portrait_profile_default`; route interest `1.0`; diversity `topology 0.7, mechanic penalty 0.305, topology penalty 0.3, score 0.6977`.
- Near miss `boring_topology_for_difficulty` seed `231406449` score `0.8755` family `multi_switch_chain` variant `multi_switch_chain_zigzag` tags `multi_switch` primary `multi_switch` topology `two_switch_order` path `6` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `normal` orientation reason `portrait_profile_default` route interest `0.435` diversity `topology 1.0, mechanic penalty 0.09, topology penalty 0.0, score 0.9595`.
- Near miss `boring_topology_for_difficulty` seed `231406450` score `0.8755` family `multi_switch_chain` variant `multi_switch_chain_zigzag` tags `multi_switch` primary `multi_switch` topology `two_switch_order` path `6` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `normal` orientation reason `portrait_profile_default` route interest `0.435` diversity `topology 1.0, mechanic penalty 0.09, topology penalty 0.0, score 0.9595`.
- Near miss `boring_topology_for_difficulty` seed `4283471899` score `0.8755` family `multi_switch_chain` variant `multi_switch_chain_double_gate` tags `multi_switch` primary `multi_switch` topology `two_switch_order` path `6` orientation `vertical` Swift-required `False` strategy `vertical_route_progression` variant `normal` orientation reason `portrait_profile_default` route interest `0.435` diversity `topology 1.0, mechanic penalty 0.09, topology penalty 0.0, score 0.9595`.
- Switch `switch_a` starts on `e_switch_a_lower_shortcut` (west); tap 1 @ 0.10s -> `e_switch_a_upper_branch` (south).
- Switch `switch_b` starts on `e_switch_b_dead_end_b` (east); tap 1 @ 0.88s -> `e_switch_b_package` (south).
- Switch `switch_c` starts on `e_switch_c_dead_end_c` (west); tap 1 @ 2.46s -> `e_switch_c_destination` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'switch_a' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'switch_b' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 3 taps 2-way switch 'switch_c' with 2 option(s).
- Warning: important_nodes_tight_on_small_device: Switch 'switch_b' is tight against important node 'package' at small-device scale.
- Warning: arrow_icon_may_collide_with_node_label_or_package: Arrow for edge 'e_switch_b_package' may collide with node 'package' artwork or label.
- Visual clarity warning: `important_nodes_tight_on_small_device` node `switch_b` edge `None`.
- Visual clarity warning: `arrow_icon_may_collide_with_node_label_or_package` node `switch_b` edge `e_switch_b_package`.

## Rejections

- Rejected candidates: `7589`
- `boring_topology_for_difficulty`: 94
- `candidate_too_similar_to_batch`: 2230
- `implicit_intersection_without_graph_node`: 763
- `important_node_readability_blocked_by_road`: 319
- `non_adjacent_roads_too_close`: 1901
- `portrait_layout_too_wide`: 895
- `portrait_start_destination_not_vertically_separated`: 598
- `same_switch_first_segments_overlap`: 767
- `solution_tap_not_before_switch_arrival`: 14
- `switch_tap_targets_too_close`: 8

## Messages

- Loaded 20 existing level signatures for similarity checks.
- Rejected candidate level_024 seed=3809802923 template=long_detour_gate reason=candidate_too_similar_to_batch detail=matches level_021: same topology, solution, and layout (363dcbeb/8962f818)
- Rejected candidate level_024 seed=3223034011 template=ring_route reason=candidate_too_similar_to_batch detail=matches level_024: similarity 0.91 >= 0.88
- Rejected candidate level_024 seed=3812051014 template=long_detour_gate reason=candidate_too_similar_to_batch detail=matches level_021: similarity 0.91 >= 0.88
- Rejected candidate level_024 seed=3814299105 template=long_detour_gate reason=candidate_too_similar_to_batch detail=matches level_021: same template/topology and layout similarity 0.99
- Rejected candidate level_024 seed=2337286158 template=split_path_rejoin reason=candidate_too_similar_to_batch detail=matches level_024: same topology, solution, and layout (7162a7ad/56d7db03)
- Rejected candidate level_024 seed=3220785921 template=ring_route reason=candidate_too_similar_to_batch detail=matches level_024: same topology, solution, and layout (a9d95cd3/6047f946)
- Rejected candidate level_024 seed=3809802924 template=long_detour_gate reason=candidate_too_similar_to_batch detail=matches level_021: same topology, solution, and layout (363dcbeb/8962f818)
- Rejected candidate level_024 seed=3223034012 template=ring_route reason=candidate_too_similar_to_batch detail=matches level_024: similarity 0.91 >= 0.88
- Rejected candidate level_024 seed=3814299106 template=long_detour_gate reason=candidate_too_similar_to_batch detail=matches level_021: same template/topology and layout similarity 0.99
- Rejected candidate level_024 seed=1295264298 template=ring_route reason=candidate_too_similar_to_batch detail=matches level_024: same topology, solution, and layout (a9d95cd3/6047f946)
- Rejected candidate level_025 seed=599340435 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_023: same topology, solution, and layout (f4e1bc6c/b7150b30)
- Rejected candidate level_025 seed=599357596 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_023: same template/topology and layout similarity 1.00
- Rejected candidate level_025 seed=4013056059 template=branch_then_rejoin_with_wrong_order reason=candidate_too_similar_to_batch detail=matches level_025: similarity 0.93 >= 0.88
- Rejected candidate level_025 seed=3718573299 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_025: similarity 0.93 >= 0.88
- Rejected candidate level_025 seed=601605687 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_023: similarity 0.90 >= 0.88
- Rejected candidate level_025 seed=4015304150 template=branch_then_rejoin_with_wrong_order reason=candidate_too_similar_to_batch detail=matches level_025: same template/topology and layout similarity 0.99
- Rejected candidate level_025 seed=603853778 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_023: same template/topology and layout similarity 0.99
- Rejected candidate level_025 seed=4010807969 template=branch_then_rejoin_with_wrong_order reason=candidate_too_similar_to_batch detail=matches level_025: same topology, solution, and layout (e240dafe/56d7db03)
- Rejected candidate level_025 seed=599340436 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_023: same topology, solution, and layout (f4e1bc6c/b7150b30)
- Rejected candidate level_025 seed=3716325209 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_025: same topology, solution, and layout (7c294735/a6ef2f9f)
- Rejected candidate level_025 seed=599357597 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_023: same template/topology and layout similarity 1.00
- Rejected candidate level_025 seed=601588527 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_023: similarity 0.90 >= 0.88
- Rejected candidate level_025 seed=3718573300 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_025: similarity 0.93 >= 0.88
- Rejected candidate level_025 seed=4015304151 template=branch_then_rejoin_with_wrong_order reason=candidate_too_similar_to_batch detail=matches level_025: same template/topology and layout similarity 0.99
- Rejected candidate level_025 seed=603853779 template=hub_choice reason=candidate_too_similar_to_batch detail=matches level_023: same template/topology and layout similarity 0.99
- Rejected candidate level_025 seed=2379786267 template=branch_then_rejoin_with_wrong_order reason=candidate_too_similar_to_batch detail=matches level_025: same topology, solution, and layout (e240dafe/56d7db03)
- Rejected candidate level_025 seed=3263286030 template=two_phase_route reason=candidate_too_similar_to_batch detail=matches level_022: same topology, solution, and layout (a7a27ce9/12c1018d)
- Rejected candidate level_025 seed=2968803270 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_025: same topology, solution, and layout (7c294735/a6ef2f9f)
- Rejected candidate level_025 seed=3263303191 template=two_phase_route reason=candidate_too_similar_to_batch detail=matches level_022: same template/topology and layout similarity 0.99
- Rejected candidate level_025 seed=2382034358 template=branch_then_rejoin_with_wrong_order reason=candidate_too_similar_to_batch detail=matches level_025: similarity 0.93 >= 0.88
- Rejected candidate level_025 seed=2971051361 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_025: similarity 0.93 >= 0.88
- Rejected candidate level_025 seed=2384282449 template=branch_then_rejoin_with_wrong_order reason=candidate_too_similar_to_batch detail=matches level_025: same template/topology and layout similarity 0.99
- Rejected candidate level_025 seed=3267799373 template=two_phase_route reason=candidate_too_similar_to_batch detail=matches level_022: same template/topology and layout similarity 0.99
- Rejected candidate level_025 seed=2379786268 template=branch_then_rejoin_with_wrong_order reason=candidate_too_similar_to_batch detail=matches level_025: same topology, solution, and layout (e240dafe/56d7db03)
- Rejected candidate level_025 seed=3263286031 template=two_phase_route reason=candidate_too_similar_to_batch detail=matches level_022: same topology, solution, and layout (a7a27ce9/12c1018d)
- Rejected candidate level_025 seed=2968803271 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_025: same topology, solution, and layout (7c294735/a6ef2f9f)
- Rejected candidate level_025 seed=3263303192 template=two_phase_route reason=candidate_too_similar_to_batch detail=matches level_022: same template/topology and layout similarity 0.99
- Rejected candidate level_025 seed=2971051362 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_025: similarity 0.93 >= 0.88
- Rejected candidate level_025 seed=3265551283 template=two_phase_route reason=candidate_too_similar_to_batch detail=matches level_022: similarity 0.92 >= 0.88
- Rejected candidate level_025 seed=2384282450 template=branch_then_rejoin_with_wrong_order reason=candidate_too_similar_to_batch detail=matches level_025: same template/topology and layout similarity 0.99
- Rejected candidate level_025 seed=3267799374 template=two_phase_route reason=candidate_too_similar_to_batch detail=matches level_022: same template/topology and layout similarity 0.99
- Rejected candidate level_025 seed=159764724 template=branch_then_rejoin_with_wrong_order reason=candidate_too_similar_to_batch detail=matches level_025: same topology, solution, and layout (e240dafe/56d7db03)
- Rejected candidate level_025 seed=748764566 template=two_phase_route reason=candidate_too_similar_to_batch detail=matches level_022: same topology, solution, and layout (a7a27ce9/12c1018d)
- Rejected candidate level_025 seed=748781727 template=two_phase_route reason=candidate_too_similar_to_batch detail=matches level_022: same template/topology and layout similarity 0.99
- Rejected candidate level_025 seed=1632281490 template=fake_shortcut reason=candidate_too_similar_to_batch detail=matches level_025: same topology, solution, and layout (7c294735/a6ef2f9f)
- Rejected candidate level_025 seed=751012657 template=two_phase_route reason=candidate_too_similar_to_batch detail=matches level_022: similarity 0.92 >= 0.88
- Rejected candidate level_025 seed=164260906 template=branch_then_rejoin_with_wrong_order reason=candidate_too_similar_to_batch detail=matches level_025: same template/topology and layout similarity 0.99
- Rejected candidate level_025 seed=753277909 template=two_phase_route reason=candidate_too_similar_to_batch detail=matches level_022: same template/topology and layout similarity 0.99
- Rejected candidate level_025 seed=159764725 template=branch_then_rejoin_with_wrong_order reason=candidate_too_similar_to_batch detail=matches level_025: same topology, solution, and layout (e240dafe/56d7db03)
- Rejected candidate level_025 seed=748764567 template=two_phase_route reason=candidate_too_similar_to_batch detail=matches level_022: same topology, solution, and layout (a7a27ce9/12c1018d)
- Additional candidate rejection messages suppressed after 50; see rejectionReasonCounts and candidateSelection in the report.
- Could not generate valid level_028 after 40 attempts.

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
