# Recipe Diversity and Layout Rescue Plan

## Purpose

Fix the current generator ceiling where mixed auto generation runs out of meaningful variety, hard/expert generation starves or fails too often, and accepted levels still feel similar after the recipe-first, layout, road-shape, validation, and scoring work.

This is a planning document only. Do not implement generator code in this task. Do not modify production level JSON or solution sidecars while executing this plan.

## Non-Negotiable Rules

Do:

- Keep validation strict.
- Preserve visual clarity gates and switch-arrow clarity rules.
- Preserve Python runtime simulation and Swift parity rules.
- Preserve solution sidecar generation and review rules.
- Use dry runs or scratch folders for stress tests.
- Keep generation deterministic by seed.
- Make hard and expert levels harder through mechanic interaction, not just extra switches.

Do not:

- Do not weaken difficulty validation to make longer levels pass.
- Do not accept visually confusing crossings because topology is interesting.
- Do not add recipe families that only rename an existing topology.
- Do not write production `TinyRoutes/Resources/Levels` JSON during this rescue.
- Do not commit generated levels without matching `TinyRoutesTests/Resources/LevelSolutions` sidecars.
- Do not rely on Python-only validation for production hard/expert output when Swift validation is required.

## Current Diversity Bottlenecks

### Current Recipe And Template Families

The recipe-first registry currently combines legacy-compatible template recipe families from `template_recipe_family.py` with expanded recipe families from `expanded_recipe_family.py`.

| Family | Difficulties | Source | Topology status |
|---|---|---|---|
| `straight_delivery` | tutorial | template recipe | Distinct no-switch line, but tiny space. |
| `single_switch` | tutorial, easy | template recipe | Distinct one-switch branch family; variants are mostly layout/branch placement. |
| `package_gate` | easy, medium | template recipe | Distinct two-switch package gate; variants are mostly layout placement. |
| `return_loop` | medium | template recipe | Distinct revisit loop with repeated tap. |
| `multi_switch_chain` | medium, hard | template recipe | Linear chain family; variants mostly change count and layout. |
| `ring_route` | hard | template recipe | Distinct ring topology, Swift-required in production. |
| `four_way_intersection` | expert | template recipe | Distinct central four-way revisit pattern, but no mechanic tags from template variant specs. |
| `straight_delivery_intro` | tutorial | expanded recipe | Same basic no-switch topology as `straight_delivery`. |
| `single_switch_intro` | tutorial | expanded recipe | Same one-switch topology as basic `single_switch`. |
| `single_switch_wrong_dead_end` | tutorial | expanded recipe | Same one-switch topology with renamed dead end. |
| `package_before_destination_intro` | tutorial | expanded recipe | Distinct longer no-switch intro line. |
| `single_switch_package_choice` | easy | expanded recipe | Same one-switch package choice shape. |
| `two_switch_order_intro` | easy | expanded recipe | Distinct compact two-switch ordered route. |
| `short_detour_gate` | easy | expanded recipe | Slightly distinct one-switch detour, but still simple branch. |
| `safe_dead_end_choice` | easy | expanded recipe | Slightly distinct one-switch readable wrong branch. |
| `package_gate_simple` | easy | expanded recipe | One-switch package gate intro. |
| `multi_switch_order` | medium | expanded recipe | Same two-switch ordered route shape as `two_switch_order_intro`. |
| `package_gate_double_choice` | medium | expanded recipe | Same two-switch route shape as `two_switch_order_intro` with package-gate tags. |
| `return_loop_intro` | medium | expanded recipe | Metadata says return loop, but current builder reuses `_medium_two_switch`; topologically not a loop. |
| `split_path_rejoin` | medium | expanded recipe | Distinct split/rejoin route, but currently one narrow shape. |
| `fake_shortcut` | medium | expanded recipe | Metadata says fake shortcut, but current builder reuses `_medium_two_switch`; topologically not distinct enough. |
| `hub_choice` | medium | expanded recipe | Metadata says hub, but current builder reuses `_medium_two_switch`; no true three-way hub topology. |
| `return_loop_with_gate` | hard | expanded recipe | Metadata says loop gate, but current builder reuses `_hard_three_switch_chain`; topologically a chain. |
| `ring_route_gate` | hard | expanded recipe | Metadata says ring route, but current builder reuses `_hard_three_switch_chain`; not a ring. |
| `multi_switch_revisit` | hard | expanded recipe | Metadata says revisit, but current builder reuses `_hard_three_switch_chain`; no actual revisit. |
| `package_inside_loop` | hard | expanded recipe | More distinct loop-shaped route with package inside, but still acyclic route graph in current builder. |
| `two_phase_route` | hard | expanded recipe | Metadata says two phase, but current builder reuses `_hard_three_switch_chain`. |
| `branch_then_rejoin_with_wrong_order` | hard | expanded recipe | Distinct branch/rejoin route, but one shape. |
| `four_way_intro` | expert | expanded recipe | Central four-way revisit pattern, Swift-required. |
| `four_way_package_gate` | expert | expanded recipe | Metadata says package gate, but current builder reuses central four-way intro topology. |
| `four_way_ring` | expert | expanded recipe | Metadata says ring, but current builder reuses central four-way intro topology. |
| `multi_four_way_route` | expert | expanded recipe | Metadata says multi four-way, but current builder reuses central four-way intro topology. |
| `controlled_repeated_taps` | expert | expanded recipe | Metadata says repeated taps, but current builder reuses `_medium_two_switch`; likely underfits expert. |
| `late_route_reversal` | expert | expanded recipe | Metadata says reversal, but current builder reuses `_hard_three_switch_chain`; no actual reversal. |

### Why Mixed Still Repeats

- Many expanded family names are mechanic labels over the same underlying graph builders.
- Topology uniqueness currently relies heavily on hashes of concrete node IDs, edge IDs, solution taps, and layout, so renamed families can look more unique than they feel.
- Layout variation includes `normal`, `mirrored`, `wide`, `tall`, `offset`, `jittered`, and recipe-planner `rotated`, but these are transforms of the same skeletons.
- Template families lack mechanic tags in many cases, which makes nearby-level mechanic pacing weak.
- Mixed weighting can rotate among family names while still choosing the same topology class: two-switch order, three-switch chain, central four-way, or simple branch.
- Candidate similarity scoring includes layout similarity, but it does not yet score mechanic-tag repetition or topology class repetition as a separate concern.

### Why Expert Generation Is Too Narrow Or Unreliable

- Expert is concentrated around central four-way patterns, plus a hard-style chain and a medium-style two-switch route promoted to expert by metadata.
- Several expert expanded families are Swift-required or should be treated as Swift-risky because four-way behavior depends on runtime parity.
- Four-way families reuse a central switch with package, return node, and destination, so duplicate rejection and visual clarity rejection quickly consume attempts.
- `controlled_repeated_taps` currently has expert tags but a two-switch topology, so it risks failing difficulty fit or feeling like a medium level.
- `late_route_reversal` currently has expert tags but a three-switch chain topology, so it does not yet provide a true reversal/revisit skill test.
- Expert levels should not rely mostly on one central four-way pattern because that creates repetition and makes failures cluster around the same layout and switch clarity risks.

### Why 30 Auto Levels May Not Reach Expert

`DifficultyCurveService.difficulty_for_level` currently maps:

- Levels 1-3: `tutorial`
- Levels 4-10: `easy`
- Levels 11-25: `medium`
- Levels 26-40: `hard`
- Levels 41 and later: `expert`

A command starting at level 1 with `--count 30 --difficulty auto` only produces levels 1 through 30. That reaches hard at levels 26 through 30, but it does not reach expert because expert starts at level 41. To include expert from level 1, the count must be at least 41. To test 10 expert levels through auto from level 1, use `--count 50`.

## Recipe Diversity Rescue

### Priority Strategy

1. Upgrade existing misleading expanded families so the topology matches the mechanic name.
2. Add new topology classes before tuning weights.
3. Add beginner/easy variants only where they introduce a skill safely, not as filler.
4. Add medium/hard families that create branches, rejoins, loops, package placement decisions, and staged routes.
5. Add expert families that combine mechanics in readable ways rather than adding more switch count.

### Coverage Plan

| Difficulty | Coverage goal |
|---|---|
| beginner/tutorial | No-switch order, one switch, readable wrong branch, package/destination separation. |
| easy | Simple detour, package branch choice, safe dead end, two-switch order intro. |
| medium | Split/rejoin, fake shortcut, hub choice, package gate, short loop intro. |
| hard | Long detour gate, package inside loop, branch/rejoin wrong order, multi-switch revisit, two-phase route. |
| expert | Four-way package gate, four-way ring, repeated taps with actual revisits, staged route reversal, multi-hub decisions. |

### Proposed Families

| Family | Priority | Intended mechanic | Difficulty bands | Required player skill | Node target | Switch target | Tap target | Repeated taps | Four-way | Package/destination pattern | Diversity value | Minimum tests |
|---|---:|---|---|---|---:|---:|---:|---|---|---|---|---|
| `split_path_rejoin` | 1 | Choose a branch that later rejoins the main path. | medium, hard | Track continuity across a split and rejoin. | 8-11 | 2-3 | 2-3 | No | No | Package after rejoin for medium; package before final rejoin for hard. | Adds non-linear route reading without requiring loops. | Recipe solves; required path includes split and rejoin; wrong branch exists; layout uses separated lanes; visual clarity passes; simulation passes. |
| `fake_shortcut` | 1 | Reject a visually tempting short route that cannot complete delivery. | easy, medium, hard | Prefer goal order over apparent shortest path. | 6-10 | 1-3 | 1-3 | No | No | Package is on longer route; shortcut either misses package or dead-ends before destination. | Creates a different decision type from switch chains. | Abstract solver sees false route; shortcut is visually clear but invalid; package-before-destination enforced; route interest passes. |
| `hub_choice` | 1 | Use a true three-way hub to choose among package, dead end, and onward route. | medium, hard | Count taps on a three-exit choice and read hub exits. | 7-11 | 1-3 | 2-4 | Optional hard only | No | Package is one hub exit; destination requires a later gate or revisit. | Introduces hub topology without jumping to four-way. | Outgoing count is 3; switch visual buckets distinct; mechanic tag `hub`; layout strategy `hub_and_spoke`; no adjacent hub clones. |
| `long_detour_gate` | 1 | Take a longer gated detour because the direct route is wrong. | easy, medium, hard | Recognize a correct longer route and maintain route plan. | 6-12 | 1-3 | 1-4 | No | No | Package sits on detour; destination reached after rejoin. | Makes longer levels arise from route necessity, not coordinate stretching. | Required path length meets band; direct path is false; route has at least two turns; timing slack remains fair. |
| `package_inside_loop` | 2 | Collect package inside a loop before exiting. | hard, expert | Track objective state while moving around a loop. | 9-13 | 3-4 | 3-5 | Optional expert | Optional expert variant | Package lies inside or on the inner loop; destination outside the loop. | Makes package placement part of topology. | Loop metadata present; package is not on outer straight line; no confusing crossings; Swift-required if four-way variant added. |
| `two_phase_route` | 2 | Solve a package phase, then a separate exit phase. | medium, hard, expert | Chunk route into before-package and after-package decisions. | 8-13 | 2-4 | 2-5 | Optional expert | Optional expert | Phase 1 reaches package; phase 2 opens exit/destination. | Creates staged puzzle structure instead of one long chain. | Report shows phase tags; solution has separated tap clusters with fair spacing; phase transition readable in layout. |
| `branch_then_rejoin_wrong_order` | 2 | Branch rejoins before a later switch, but applying later logic early is wrong. | hard, expert | Reason about order after a branch rejoins. | 9-13 | 3-4 | 3-5 | No hard, optional expert | No | Package after first rejoin; destination after later gate. | Tests order and path memory, not just count. | Wrong-order branch exists; solver false-route count increases; rejoin visually clear; no duplicate chain topology. |
| `multi_switch_revisit` | 2 | Revisit an earlier switch after route state changes. | hard, expert | Remember a switch state across a loop or return path. | 9-13 | 2-4 | 3-5 | Yes | Optional expert | Package before or during revisit; destination unlocked after revisit. | Adds memory and route-state interaction. | Required path repeats at least one switch node; repeated taps allowed only in supported bands; tap windows pass phone timing. |
| `four_way_package_gate` | 3 | Use a four-way decision to collect package and a separate gate to exit. | expert | Count four-way taps while also tracking package gate state. | 8-12 | 2-3 | 3-5 | Optional | Yes | Four-way reaches package; non-central gate controls destination. | Breaks expert out of the single central four-way-only pattern. | At least one four-way plus one separate switch; Swift validation required; visual buckets distinct; no central-only topology reuse. |
| `four_way_ring` | 3 | Navigate a ring that includes a four-way entry or exit. | expert | Combine ring reading with four-way direction counting. | 9-13 | 2-4 | 3-6 | Optional | Yes | Package on ring segment; destination outside ring. | Gives expert a spatial topology class, not just tap count. | Ring loop metadata; four-way not always central; Swift validation required; road-shape crossing audit passes. |
| `controlled_repeated_taps` | 3 | Repeat taps on one switch at clearly separated visits. | medium intro, hard, expert | Understand that the same switch can be correct twice for different route goals. | 7-12 | 1-3 | 2-5 | Yes | Optional expert | Package collected between first and second visit; destination after second visit. | Turns repeated taps into a visible route-state mechanic. | Required path repeats tapped node; repeated taps rejected for easy; minimum tap spacing above preset; report highlights repeated tap tag. |

Additional low-risk beginner/easy support can come from upgrading existing `single_switch_intro`, `single_switch_wrong_dead_end`, `package_before_destination_intro`, `short_detour_gate`, `safe_dead_end_choice`, and `package_gate_simple` with mechanic tags, topology classes, and path-length metadata. These should stay intentionally small.

## Longer Level Support

Longer levels should come from gameplay structure, not from stretching coordinates.

Use:

- Required path length with meaningful intermediate decisions.
- Detours that are correct because they collect package, avoid a false route, or open an exit.
- Loops where the revisit changes the needed switch state.
- Split/rejoin paths that require branch continuity.
- Staged routes with a package phase and destination phase.
- Revisit mechanics with clear repeated taps and fair timing.

Do not use:

- Straight lines with extra filler nodes.
- Chains of identical switches with identical wrong dead ends.
- Longer roads that only increase travel time.
- Dense crossings to create fake complexity.

### Target Required Path Length

Count path length as required route edges, not coordinate distance.

| Difficulty | Target path length | Notes |
|---|---:|---|
| tutorial | 2-4 | Mostly no switch or one switch. |
| easy | 4-6 | One detour or two-switch intro is enough. |
| medium | 6-9 | Split/rejoin, fake shortcut, or simple hub. |
| hard | 8-12 | Detour plus gate, loop, two phase, or revisit. |
| expert | 9-14 | Mechanic interaction with four-way, revisit, ring, or staged route. |

### Long-Level Rejection Rules

Reject or heavily penalize long candidates when:

- More than 60 percent of required route edges are monotonic in the same direction with no branch, loop, or objective change.
- A route adds more than two filler route nodes without adding a decision, package interaction, rejoin, loop, or revisit.
- Consecutive switches have the same local pattern three times in a row.
- The false-route count is zero for medium or higher and the level is only long because of route distance.
- Layout readability falls below current thresholds.
- Required path crossings or long parallel road segments make the route hard to parse.
- Average tap spacing or minimum reaction window drops below the difficulty preset.

### Timing Requirements

- Keep `RouteTimingService` and `SolutionBuilderService` as the timing source.
- Require every generated sidecar tap to have reaction windows at or above the preset minimum: 0.40 seconds for tutorial through hard and 0.45 seconds for expert unless presets intentionally change in a later PR.
- Report simulated elapsed time, time limit, slack ratio, minimum reaction window, and average tap spacing for long levels.
- Reject long levels that pass only because of excessive time limit padding while still requiring rushed taps.
- Keep phone fairness as a hard gate: longer travel can create more thinking time, but taps must still be visually telegraphed.

## Better Vertical-Space Usage

### Current State

`GraphLayoutPlannerService` already has a `vertical_route_progression` strategy and `_route_progression_positions(..., vertical=True)`. It is underused because `_strategy_for_recipe` never selects `vertical_route_progression`; most families fall back to `horizontal_route_progression`, `split_lane`, `ring_loop`, `package_inside_loop`, `hub_and_spoke`, or `four_way_intersection`.

`LayoutVariantService` has a `tall` transform, but that is not the same as a vertical topology. Template families also mostly start from horizontal fixed positions. Current vertical support exists as a capability, but not as a selected design mode.

### Planned Controls

Add configuration and report fields:

- `layout_orientation_preference`: `horizontal`, `vertical`, `mixed`, `auto`
- `vertical_route_probability`
- `prefer_vertical_for_long_routes`
- `snake_layout`
- `s_curve_layout`
- `vertical_split_lane`
- `vertical_loop`

Behavior:

- `horizontal`: use existing horizontal route progression unless recipe-specific strategies override it.
- `vertical`: prefer vertical progression or vertical-specific strategies when validation passes.
- `mixed`: include horizontal and vertical candidates in the layout pool.
- `auto`: choose based on recipe tags, path length, branch shape, and recent accepted layouts.
- `vertical_route_probability`: apply only when preference is `mixed` or `auto`.
- `prefer_vertical_for_long_routes`: raises vertical probability for medium/hard/expert levels above target path length midpoint.
- `snake_layout`: uses alternating horizontal lanes while progressing vertically.
- `s_curve_layout`: uses route bends and staged lanes without adding visual crossings.
- `vertical_split_lane`: creates upper/lower or left/right branch lanes in vertical progression.
- `vertical_loop`: places loop/revisit families around vertical space rather than squeezing them into horizontal rings.

### Vertical Acceptance Criteria

- Important nodes remain readable and separated: `start`, package, destination, required switches, and revisited hubs.
- Switches are not too close to edges; keep current edge margin checks or stricter.
- Package and destination are visually distinct and not adjacent unless the mechanic explicitly requires a close finish.
- Road crossings are absent or clearly non-confusing after road-shape planning.
- Tap targets remain comfortable on phone layouts.
- Revisited switches remain recognizable on both visits.
- Vertical layouts fit within existing board coordinates without scrolling, camera, or zoom changes.

Scrolling, camera movement, or zoom should be future optional work only. They are not part of this rescue.

## Topology Diversity Scoring

### Mechanic Tags

Add explicit tags to every recipe and template recipe variant, including legacy-compatible template families.

Required tag vocabulary:

- `single_switch`
- `multi_switch`
- `package_gate`
- `loop`
- `ring`
- `rejoin`
- `fake_shortcut`
- `hub`
- `four_way`
- `repeated_tap`
- `long_route`
- `vertical_layout`
- `snake_layout`

Also consider:

- `detour`
- `dead_end`
- `two_phase`
- `wrong_order`
- `route_reversal`
- `package_inside_loop`
- `split_path`
- `safe_choice`

### Topology Class

Add a topology class separate from family name and layout:

- `straight_line`
- `single_branch`
- `two_switch_order`
- `package_gate`
- `split_rejoin`
- `hub_spoke`
- `detour_gate`
- `return_loop`
- `ring`
- `two_phase`
- `revisit`
- `four_way_gate`
- `four_way_ring`
- `route_reversal`

Candidate signatures should include topology class and mechanic tags in reportable metadata, but duplicate detection should not rely only on family names. Similarity should compare structure, repeated nodes, branch/rejoin points, outgoing degree distribution, loop/revisit count, package position class, and tap-node repetition.

### Selection Rules

- Penalize accepted candidates that share major mechanic tags with the immediately previous level.
- Penalize candidates that repeat the same topology class within a 3-level window.
- For hard/expert, require at least one of the last 5 accepted levels to differ in primary topology class.
- Do not reject solely because one tag repeats if the combined tag set and topology class differ meaningfully.
- Use hard rejection only for exact topology class plus same primary tags plus high structural similarity.

### Report Fields

Generation reports should show:

- `recipeFamily`
- `recipeVariant`
- `mechanicTags`
- `primaryMechanicTag`
- `topologyClass`
- `layoutOrientation`
- `layoutStrategy`
- `requiredPathLength`
- `routeDistance`
- `minimumReactionWindowSeconds`
- `averageTapSpacingSeconds`
- `topologyDiversityScore`
- `nearbyMechanicTagPenalty`
- `nearbyTopologyClassPenalty`
- `diversityScore`

Markdown reports should include these in accepted-level details and candidate-selection summaries. JSON reports should include the full values for audits.

## Expert Generation Rescue

Expert generation needs several reliable topology classes. It should not rely mostly on one central four-way pattern because that makes every expert candidate fight the same visual, duplicate, and Swift-risk profile.

### Expert-Specific Families

Recommended expert weights after the families are real and tested:

| Family | Weight | Role |
|---|---:|---|
| `four_way_package_gate` | 3 | Four-way plus separate package/exit gate. |
| `four_way_ring` | 3 | Spatial ring with four-way interaction. |
| `controlled_repeated_taps` | 3 | Revisit/repeated tap without requiring four-way every time. |
| `multi_switch_revisit` | 2 | Expert memory path with repeated or staged switch use. |
| `two_phase_route` | 2 | Before-package and after-package route phases. |
| `branch_then_rejoin_wrong_order` | 2 | Order reasoning after rejoin. |
| `package_inside_loop` | 2 | Objective inside loop. |
| `late_route_reversal` | 2 | Actual reversal/revisit topology after upgrade. |
| `hub_choice` expert variant | 1 | Multi-exit hub as non-four-way expert spice. |
| `four_way_intersection` legacy/template | 1 | Keep as fallback, not the center of expert generation. |

Tune these only after dry-run reports show real starvation patterns.

### Expert Safeguards

- Require expert difficulty because of mechanic interaction: four-way plus gate, loop plus package state, repeated tap plus revisit, or branch/rejoin plus wrong order.
- Do not accept expert candidates that are only medium/hard topologies with expert tags.
- Require accepted expert levels to include at least one advanced tag: `four_way`, `repeated_tap`, `ring`, `route_reversal`, `two_phase`, `revisit`, or `package_inside_loop`.
- Keep Swift-required handling explicit for four-way and ring-risk families.
- Track expert family acceptance rates and rejection reasons separately.

### Direct Generation Tests

Add tests that prove expert dry runs can produce accepted levels:

- `test_expert_mixed_dry_run_accepts_10_levels`
- `test_expert_family_weights_include_non_central_four_way_topologies`
- `test_expert_rejects_metadata_only_medium_topology`
- `test_expert_reports_topology_class_and_tags`
- `test_expert_four_way_families_require_swift_validation_for_production`

These tests should use dry-run or temporary output directories only.

## Mixed Auto Generation Target

New success target:

- Mixed auto dry-run can generate at least 50 levels from a clean scratch output without excessive duplicate rejection.
- Expert dry-run can generate at least 10 accepted levels.
- Hard dry-run can generate at least 20 accepted levels.
- Accepted levels show meaningful recipe-family and mechanic-tag diversity.

Suggested dry-run commands:

```bash
python3 Tools/LevelGenerator/generate_levels.py \
  --start 1 \
  --count 50 \
  --difficulty auto \
  --template mixed \
  --generation-mode recipe-first \
  --seed 9001 \
  --dry-run \
  --no-compare-existing \
  --report /tmp/tiny-routes-auto50.md \
  --json-report /tmp/tiny-routes-auto50.json
```

```bash
python3 Tools/LevelGenerator/generate_levels.py \
  --start 41 \
  --count 10 \
  --difficulty expert \
  --template mixed \
  --generation-mode recipe-first \
  --seed 9101 \
  --dry-run \
  --no-compare-existing \
  --report /tmp/tiny-routes-expert10.md \
  --json-report /tmp/tiny-routes-expert10.json
```

```bash
python3 Tools/LevelGenerator/generate_levels.py \
  --start 26 \
  --count 20 \
  --difficulty hard \
  --template mixed \
  --generation-mode recipe-first \
  --seed 9201 \
  --dry-run \
  --no-compare-existing \
  --report /tmp/tiny-routes-hard20.md \
  --json-report /tmp/tiny-routes-hard20.json
```

Expected report fields to inspect:

- `acceptedLevels[].recipeFamily`
- `acceptedLevels[].recipeVariant`
- `acceptedLevels[].mechanicTags`
- `acceptedLevels[].topologyClass`
- `acceptedLevels[].layoutOrientation`
- `acceptedLevels[].selectedLayoutVariant`
- `acceptedLevels[].layoutMetadata.strategy`
- `acceptedLevels[].quality.details.difficultyMetrics.solutionPathLength`
- `acceptedLevels[].quality.mobileTapComfort`
- `candidateSelection[].acceptedCandidate.mechanicTags`
- `candidateSelection[].acceptedCandidate.topologyClass`
- `rejectionReasonCounts`
- `topologyDiversityScore`

## Implementation Order

### Phase 1 - Add Mechanic Tags To Existing Recipes

Files likely touched:

- `Tools/LevelGenerator/app/recipes/template_recipe_family.py`
- `Tools/LevelGenerator/app/templates/*_template.py`
- `Tools/LevelGenerator/app/models/recipe_variant_spec.py` if primary tags are added
- `Tools/LevelGenerator/tests/test_recipe_family_registry.py`
- Report tests that assert mechanic tags

Tests required:

- Existing template recipe families expose non-empty tags.
- Expanded recipe families keep existing tags.
- Reports show tags for legacy-compatible template recipes.

Acceptance criteria:

- Every family has tags.
- Existing validations and simulation still pass.
- No production JSON changes.

Do:

- Add tags conservatively.
- Preserve existing family and variant names.

Do not:

- Do not tune weights in this phase.
- Do not add new generator behavior beyond metadata.

### Phase 2 - Add Topology Diversity Report And Audit

Files likely touched:

- `Tools/LevelGenerator/app/models/candidate_signature.py`
- `Tools/LevelGenerator/app/services/candidate_signature_service.py`
- `Tools/LevelGenerator/app/repositories/generation_report_repository.py`
- `Tools/LevelGenerator/tests/test_candidate_signature_service.py`
- `Tools/LevelGenerator/tests/test_generation_report_repository.py`

Tests required:

- Topology class is stable for known fixtures.
- Report includes family, tags, topology class, orientation placeholder, path length, and diversity audit fields.
- Same topology with different layout is visible as same topology class.

Acceptance criteria:

- Reports can explain repetition without changing selection behavior yet.

Do:

- Keep this phase observational.

Do not:

- Do not reject candidates based on the new score yet.

### Phase 3 - Add Layout Orientation Controls And Vertical/Snake Strategies

Files likely touched:

- `Tools/LevelGenerator/app/generation_config.py`
- `Tools/LevelGenerator/app/cli.py`
- `Tools/LevelGenerator/app/gui/gui_state.py`
- `Tools/LevelGenerator/app/gui/gui_widgets.py`
- `Tools/LevelGenerator/app/services/level_generation_service.py`
- `Tools/LevelGenerator/app/services/graph_layout_service.py`
- `Tools/LevelGenerator/app/services/recipe_to_level_builder_service.py`
- `Tools/LevelGenerator/tests/test_graph_layout_service.py`
- CLI and GUI tests

Tests required:

- `vertical_route_progression` can be selected intentionally.
- `mixed` or `auto` orientation includes vertical candidates.
- Long routes can prefer vertical when configured.
- Snake and S-curve strategies keep nodes inside bounds and readable.

Acceptance criteria:

- Vertical layouts appear in dry-run reports.
- Existing horizontal output remains available and valid.

Do:

- Keep all layouts inside current board bounds.
- Use current visual clarity validation.

Do not:

- Do not add scrolling, camera, or zoom.
- Do not bypass layout validation.

### Phase 4 - Add 3-4 Medium/Hard Recipe Families

Recommended first families:

- `fake_shortcut`
- `hub_choice`
- `long_detour_gate`
- upgraded `split_path_rejoin`

Files likely touched:

- `Tools/LevelGenerator/app/recipes/expanded_recipe_family.py`
- `Tools/LevelGenerator/app/recipes/recipe_family_registry.py`
- `Tools/LevelGenerator/app/services/graph_layout_service.py`
- `Tools/LevelGenerator/tests/test_recipe_family_registry.py`
- `Tools/LevelGenerator/tests/test_generator_batch_checks.py`

Tests required:

- Each family solves abstractly.
- Each family builds levels that pass validation.
- Required path and false-route metadata match intended mechanic.
- Medium/hard dry-run accepts a meaningful mix.

Acceptance criteria:

- Medium/hard no longer depend mostly on two-switch order and three-switch chain.

Do:

- Make topology match the family name.

Do not:

- Do not add family names that reuse `_medium_two_switch` or `_hard_three_switch_chain` without meaningful structural changes.

### Phase 5 - Add 2-3 Expert Recipe Families

Recommended first families:

- upgraded `controlled_repeated_taps`
- upgraded `four_way_package_gate`
- upgraded `four_way_ring`

Files likely touched:

- `Tools/LevelGenerator/app/recipes/expanded_recipe_family.py`
- `Tools/LevelGenerator/app/services/abstract_puzzle_solver_service.py` only if solver limits need legitimate expert support
- `Tools/LevelGenerator/app/services/graph_layout_service.py`
- expert recipe tests and Swift-policy tests

Tests required:

- Expert dry-run accepts 10 levels.
- Four-way families have Swift-required production policy.
- Repeated-tap expert has actual repeated tap topology.

Acceptance criteria:

- Expert accepted set includes at least three topology classes.

Do:

- Keep four-way switch exits visually distinct.

Do not:

- Do not make expert a central four-way clone set.

### Phase 6 - Add Topology Diversity Scoring

Files likely touched:

- `Tools/LevelGenerator/app/services/generation_quality_service.py`
- `Tools/LevelGenerator/app/services/candidate_uniqueness_service.py`
- `Tools/LevelGenerator/app/services/campaign_pacing_service.py`
- `Tools/LevelGenerator/app/services/level_generation_service.py`
- quality and generation tests

Tests required:

- Adjacent repeated topology class is penalized.
- Nearby repeated mechanic tags are penalized.
- Distinct topology can beat same-family layout variation.
- Strict validation still rejects bad candidates before scoring.

Acceptance criteria:

- Candidate selection prefers topology diversity when validation and quality are otherwise close.

Do:

- Keep scoring explainable in reports.

Do not:

- Do not let diversity compensate for bad readability, switch clarity, or runtime solvability.

### Phase 7 - Add Mixed-Auto And Expert Dry-Run Stress Tests

Files likely touched:

- `Tools/LevelGenerator/tests/test_generator_batch_checks.py`
- `Tools/LevelGenerator/tests/test_generation_service.py`
- Optional helper fixtures under `Tools/LevelGenerator/tests`

Tests required:

- Auto 50 dry-run succeeds in temporary paths.
- Expert 10 dry-run succeeds.
- Hard 20 dry-run succeeds.
- Reports show tag and topology distribution.

Acceptance criteria:

- Stress tests prove accepted-level diversity and no excessive duplicate rejection.

Do:

- Keep stress tests deterministic and reasonably bounded.

Do not:

- Do not write production resources from tests.

### Phase 8 - Tune Weights After Real Starvation Data

Files likely touched:

- `Tools/LevelGenerator/app/recipes/recipe_family_registry.py`
- `Tools/LevelGenerator/app/services/difficulty_curve_service.py`
- tests for deterministic family selection or distribution

Tests required:

- Weight changes preserve expected early campaign pacing.
- Auto 50, hard 20, and expert 10 still pass.

Acceptance criteria:

- Weights reflect observed acceptance rates, not assumptions.

Do:

- Use report rejection data to tune.

Do not:

- Do not tune weights before topology exists and stress reports expose real failure modes.

## Suggested Codex Prompts For First Two PRs

### PR 1 Prompt

```text
Implement Phase 1 from Tools/LevelGenerator/docs/recipe_diversity_and_layout_rescue_plan.md.

Add mechanic tags and primary topology metadata to all existing recipe/template families without changing graph generation behavior, validation strictness, production level JSON, or solution-sidecar rules. Update focused tests and reports so every accepted recipe-first candidate shows tags. Do not tune weights or add new families yet.
```

### PR 2 Prompt

```text
Implement Phase 2 from Tools/LevelGenerator/docs/recipe_diversity_and_layout_rescue_plan.md.

Add topology-class and diversity audit fields to candidate signatures and generation reports, but keep candidate selection behavior unchanged. The audit should show family, tags, topology class, layout orientation if known, required path length, and diversity placeholders. Add tests proving that same topology with different layout is still auditable as the same topology class. Do not reject candidates using the new score yet.
```

## Old Document Cleanup Plan

Docs inspected in `Tools/LevelGenerator/docs`:

| File | Classification | Reason | Action |
|---|---|---|---|
| `Tools/LevelGenerator/docs/production_generation_checklist.md` | keep | Active production workflow doc. It protects dry-run, scratch, Swift, simulator, and sidecar rules. | Keep unchanged, optionally link from this plan. |
| `Tools/LevelGenerator/docs/next_generation_completion_status.md` | keep | Active completion/status history for the recipe-first, solver, layout, road-shape, clarity, runtime, and difficulty work. | Keep. |
| `Tools/LevelGenerator/docs/next_generation_master_plan.md` | keep | Broad architecture and workflow plan. Some parts are completed, but it still records important design principles. | Keep, optionally add a top link to this rescue plan later. |
| `Tools/LevelGenerator/docs/current_state.md` | replace with link to new plan | Stale: it omits current expanded recipe families and understates current layout/recipe-first behavior. | Replace later with a short current-state index linking to this plan and the production checklist. Review before deleting. |
| `Tools/LevelGenerator/docs/completion_status.md` | merge into new plan or replace with link | Historical completed-plan status overlaps with `next_generation_completion_status.md` and newer docs. | Review before deleting after any unique history is migrated or intentionally archived. |

Safe deletion recommendation for this planning task: none.

Review-before-deleting candidates:

- `Tools/LevelGenerator/docs/current_state.md`: delete only after replacing it with a current index or moving any still-useful CLI/path notes to README.
- `Tools/LevelGenerator/docs/completion_status.md`: delete only after confirming the old completion history is not needed, or after replacing it with a link to `next_generation_completion_status.md`.

Do not delete architecture docs, README files, production workflow docs, or active completion/status files during this task.

## Definition Of Done

- [ ] Every existing family has mechanic tags and a topology class.
- [ ] Reports show family, tags, topology class, layout orientation, path length, and diversity audit fields.
- [ ] Vertical, snake, S-curve, vertical split-lane, and vertical loop strategies are available without scrolling or zoom changes.
- [ ] Medium/hard include real split/rejoin, fake shortcut, hub choice, and long detour topologies.
- [ ] Expert includes at least three reliable topology classes and does not depend mostly on central four-way clones.
- [ ] Longer levels come from required path structure, detours, loops, revisits, and staged routes.
- [ ] Long levels are rejected when boring, too straight, too repetitive, visually confusing, or unfair on phones.
- [ ] Topology diversity scoring avoids adjacent or nearby repeats without weakening validation.
- [ ] Mixed auto dry-run generates at least 50 accepted levels from clean scratch conditions.
- [ ] Expert dry-run generates at least 10 accepted levels.
- [ ] Hard dry-run generates at least 20 accepted levels.
- [ ] Accepted levels show meaningful recipe-family and mechanic-tag diversity.
- [ ] Python tests pass.
- [ ] Swift-required production policies remain intact.
- [ ] Production JSON and solution sidecars remain untouched unless a later production-generation task explicitly requests them.
