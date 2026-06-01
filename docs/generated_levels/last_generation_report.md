# Tiny Routes Generation Report

- Generated: `2026-06-01T03:23:05.977575+00:00`
- Repo root: `/Users/jake/Developer/Tiny-Routes`
- Difficulty: `medium`
- Template mode: `return_loop`
- Generation mode: `recipe_first`
- Base seed: `123`
- Dry run: `True`
- Compare existing levels: `True`
- Candidate pool size: `25`
- Recipe pool size: `4`
- Layouts per recipe: `3`
- Road shapes per layout: `3`
- Xcode project sync: `True`
- Swift tests: `Swift tests were not run.`

## Accepted Levels

| Level | Source | Seed | Difficulty | Nodes | Edges | Switches | Par Taps | Time Limit | Quality | Preview | Signatures | Status |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|---|
| `level_016` | `return_loop / return_loop_upper` | 3209180135 | medium | 7 | 7 | 2 | 3 | 30 | 0.8824 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_016.svg) | `T:b0ddc5b0 L:bfac11b3 S:c09ff266` | passed |
| `level_017` | `return_loop / return_loop_classic` | 639403786 | medium | 7 | 7 | 2 | 3 | 30 | 0.8805 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_017.svg) | `T:18a00047 L:be5d90ce S:c6e81a71` | passed |
| `level_018` | `return_loop / return_loop_classic` | 1623720224 | medium | 7 | 7 | 2 | 3 | 30 | 0.8725 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_018.svg) | `T:18a00047 L:f9902909 S:c6e81a71` | passed |
| `level_019` | `return_loop / return_loop_lower` | 4089836770 | medium | 7 | 7 | 2 | 3 | 30 | 0.8705 | [SVG](/Users/jake/Developer/Tiny-Routes/docs/generated_levels/previews/level_019.svg) | `T:f152647c L:998cd5e3 S:50bb2282` | passed |

## Level Details

### `level_016`
- Recipe: `return_loop` variant `return_loop_upper`; abstract signature `2bb3eb201ab5`.
- Layout: `normal`; strategy: `package_inside_loop`; road shapes: `auto` (score `0.92`).
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `0.92`, 1 issue(s).
- Abstract solution: 3 required taps, 1 alternate paths, 1 dead ends, 9 loops.
- Difficulty model: estimated `expert`, mechanical `1.0`, visual `0.78`, campaign pacing `0.78`.
- Score breakdown: mechanic `1.0`, runtime `1.0`, readability `0.74`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.8365`.
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.8824 vs 0.8805). Scores min/avg/max `0.8705`/`0.8765`/`0.8824`.
- Near miss `not_selected` seed `3209145944` score `0.8805`.
- Near miss `not_selected` seed `3209163105` score `0.8725`.
- Near miss `not_selected` seed `2468271434` score `0.8705`.
- Switch `upper_alpha_switch` starts on `e_upper_alpha_switch_destination` (south); tap 1 @ 1.46s -> `e_upper_alpha_switch_package` (west), tap 2 @ 4.56s -> `e_upper_alpha_switch_destination` (south).
- Switch `upper_beta_switch` starts on `e_upper_beta_switch_upper_dead_end` (south); tap 1 @ 3.32s -> `e_upper_beta_switch_upper_return` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'upper_alpha_switch' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'upper_beta_switch' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 3 taps 2-way switch 'upper_alpha_switch' with 2 option(s).
- Warning: return_loop_visually_unclear: Return loop revisits switch 'upper_alpha_switch', which can obscure the intended route flow.
- Visual clarity warning: `return_loop_visually_unclear` node `upper_alpha_switch` edge `None`.
### `level_017`
- Recipe: `return_loop` variant `return_loop_classic`; abstract signature `b0a174910854`.
- Layout: `mirrored`; strategy: `package_inside_loop`; road shapes: `auto` (score `0.92`).
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `0.92`, 1 issue(s).
- Abstract solution: 3 required taps, 1 alternate paths, 1 dead ends, 9 loops.
- Difficulty model: estimated `expert`, mechanical `1.0`, visual `0.72`, campaign pacing `0.78`.
- Score breakdown: mechanic `1.0`, runtime `1.0`, readability `0.959`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9456`.
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.8805 vs 0.8731). Scores min/avg/max `0.8705`/`0.8747`/`0.8805`.
- Near miss `not_selected` seed `639403788` score `0.8731`.
- Near miss `not_selected` seed `639386494` score `0.8705`.
- Switch `alpha_switch` starts on `e_alpha_switch_destination` (south); tap 1 @ 1.46s -> `e_alpha_switch_package` (east), tap 2 @ 4.56s -> `e_alpha_switch_destination` (south).
- Switch `beta_switch` starts on `e_beta_switch_dead_end_a` (east); tap 1 @ 3.32s -> `e_beta_switch_return_a` (west).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'alpha_switch' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'beta_switch' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 3 taps 2-way switch 'alpha_switch' with 2 option(s).
- Warning: return_loop_visually_unclear: Return loop revisits switch 'alpha_switch', which can obscure the intended route flow.
- Visual clarity warning: `return_loop_visually_unclear` node `alpha_switch` edge `None`.
### `level_018`
- Recipe: `return_loop` variant `return_loop_classic`; abstract signature `b0a174910854`.
- Layout: `mirrored`; strategy: `package_inside_loop`; road shapes: `switch_clarity_optimized` (score `0.92`).
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `0.92`, 1 issue(s).
- Abstract solution: 3 required taps, 1 alternate paths, 1 dead ends, 9 loops.
- Difficulty model: estimated `expert`, mechanical `1.0`, visual `0.72`, campaign pacing `0.78`.
- Score breakdown: mechanic `1.0`, runtime `1.0`, readability `0.959`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.9456`.
- Candidate selection: Accepted candidate had the highest deterministic quality score (0.8725 vs 0.8705). Scores min/avg/max `0.8705`/`0.8715`/`0.8725`.
- Near miss `not_selected` seed `2364611632` score `0.8705`.
- Switch `alpha_switch` starts on `e_alpha_switch_destination` (north); tap 1 @ 1.46s -> `e_alpha_switch_package` (west), tap 2 @ 4.56s -> `e_alpha_switch_destination` (north).
- Switch `beta_switch` starts on `e_beta_switch_dead_end_a` (west); tap 1 @ 3.32s -> `e_beta_switch_return_a` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'alpha_switch' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'beta_switch' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 3 taps 2-way switch 'alpha_switch' with 2 option(s).
- Warning: return_loop_visually_unclear: Return loop revisits switch 'alpha_switch', which can obscure the intended route flow.
- Visual clarity warning: `return_loop_visually_unclear` node `alpha_switch` edge `None`.
### `level_019`
- Recipe: `return_loop` variant `return_loop_lower`; abstract signature `c849c4630a7f`.
- Layout: `normal`; strategy: `package_inside_loop`; road shapes: `auto` (score `0.92`).
- Road-shape checks: 0 crossings, 0 required-path crossings, 0 long parallel segments.
- Visual clarity: score `0.92`, 1 issue(s).
- Abstract solution: 3 required taps, 1 alternate paths, 1 dead ends, 9 loops.
- Difficulty model: estimated `expert`, mechanical `1.0`, visual `0.78`, campaign pacing `0.78`.
- Score breakdown: mechanic `1.0`, runtime `1.0`, readability `0.74`, switch clarity `1.0`, mobile comfort `1.0`, visual appeal `0.8365`.
- Candidate selection: Only one scored candidate passed validation and quality thresholds. Scores min/avg/max `0.8705`/`0.8705`/`0.8705`.
- Switch `lower_alpha_switch` starts on `e_lower_alpha_switch_destination` (south); tap 1 @ 1.46s -> `e_lower_alpha_switch_package` (west), tap 2 @ 4.56s -> `e_lower_alpha_switch_destination` (south).
- Switch `lower_beta_switch` starts on `e_lower_beta_switch_lower_dead_end` (south); tap 1 @ 3.32s -> `e_lower_beta_switch_lower_return` (east).
- Warning: tap_node_switch_context: Solution action 1 taps 2-way switch 'lower_alpha_switch' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 2 taps 2-way switch 'lower_beta_switch' with 2 option(s).
- Warning: tap_node_switch_context: Solution action 3 taps 2-way switch 'lower_alpha_switch' with 2 option(s).
- Warning: return_loop_visually_unclear: Return loop revisits switch 'lower_alpha_switch', which can obscure the intended route flow.
- Visual clarity warning: `return_loop_visually_unclear` node `lower_alpha_switch` edge `None`.

## Rejections

- Rejected candidates: `53990`
- `candidate_too_similar_to_batch`: 53984
- `candidate_too_similar_to_existing`: 6

## Messages

- Loaded 20 existing level signatures for similarity checks.
- Rejected candidate level_016 seed=3209145813 template=return_loop reason=candidate_too_similar_to_existing detail=matches level_014: same topology, solution, and layout (18a00047/c6e81a71)
- Rejected candidate level_016 seed=3209145814 template=return_loop reason=candidate_too_similar_to_existing detail=matches level_014: same topology, solution, and layout (18a00047/c6e81a71)
- Rejected candidate level_016 seed=3209145815 template=return_loop reason=candidate_too_similar_to_existing detail=matches level_014: same topology, solution, and layout (18a00047/c6e81a71)
- Rejected candidate level_016 seed=3209145945 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same topology, solution, and layout (18a00047/c6e81a71)
- Rejected candidate level_016 seed=3209145946 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same topology, solution, and layout (18a00047/c6e81a71)
- Rejected candidate level_016 seed=3209146075 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=3209146076 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=3209146077 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=3209162974 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=3209162975 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=3209162976 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=3209163106 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same topology, solution, and layout (18a00047/c6e81a71)
- Rejected candidate level_016 seed=3209163107 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same topology, solution, and layout (18a00047/c6e81a71)
- Rejected candidate level_016 seed=3209163236 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=3209163237 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=3209163238 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=3209180136 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same topology, solution, and layout (b0ddc5b0/c09ff266)
- Rejected candidate level_016 seed=3209180137 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same topology, solution, and layout (b0ddc5b0/c09ff266)
- Rejected candidate level_016 seed=3209180266 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.89 >= 0.88
- Rejected candidate level_016 seed=3209180267 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.89 >= 0.88
- Rejected candidate level_016 seed=3209180268 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=3209180397 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same template/topology and layout similarity 0.99
- Rejected candidate level_016 seed=3209180398 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same template/topology and layout similarity 0.99
- Rejected candidate level_016 seed=3209180399 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same template/topology and layout similarity 0.99
- Rejected candidate level_016 seed=3209197296 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=3209197297 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=3209197298 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=3209197427 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same topology, solution, and layout (18a00047/c6e81a71)
- Rejected candidate level_016 seed=3209197428 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same topology, solution, and layout (18a00047/c6e81a71)
- Rejected candidate level_016 seed=3209197429 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same topology, solution, and layout (18a00047/c6e81a71)
- Rejected candidate level_016 seed=3209197558 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=3209197559 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=3209197560 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=2468237112 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same topology, solution, and layout (b0ddc5b0/c09ff266)
- Rejected candidate level_016 seed=2468237113 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same topology, solution, and layout (b0ddc5b0/c09ff266)
- Rejected candidate level_016 seed=2468237114 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same topology, solution, and layout (b0ddc5b0/c09ff266)
- Rejected candidate level_016 seed=2468237243 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.89 >= 0.88
- Rejected candidate level_016 seed=2468237244 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.89 >= 0.88
- Rejected candidate level_016 seed=2468237245 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.89 >= 0.88
- Rejected candidate level_016 seed=2468237374 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same template/topology and layout similarity 0.99
- Rejected candidate level_016 seed=2468237375 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same template/topology and layout similarity 0.99
- Rejected candidate level_016 seed=2468237376 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same template/topology and layout similarity 0.99
- Rejected candidate level_016 seed=2468254273 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=2468254274 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=2468254275 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=2468254404 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same topology, solution, and layout (18a00047/c6e81a71)
- Rejected candidate level_016 seed=2468254405 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same topology, solution, and layout (18a00047/c6e81a71)
- Rejected candidate level_016 seed=2468254406 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: same topology, solution, and layout (18a00047/c6e81a71)
- Rejected candidate level_016 seed=2468254535 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Rejected candidate level_016 seed=2468254536 template=return_loop reason=candidate_too_similar_to_batch detail=matches level_016: similarity 0.90 >= 0.88
- Additional candidate rejection messages suppressed after 50; see rejectionReasonCounts and candidateSelection in the report.
- Could not generate valid level_020 after 300 attempts.

## Recommendations

- Most common rejection: `candidate_too_similar_to_batch`.
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
