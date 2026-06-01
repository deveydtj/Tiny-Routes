# Tiny Routes Auto-Generated Level Generator — Master Improvement Plan

## Goal

Make the Tiny Routes auto-generated level system production-grade: reliable enough to create large batches of readable, solvable, fun, mobile-friendly levels while still giving the designer final review control.

The final system should not just create valid JSON. It should create levels that feel intentionally designed.

## Current Assessment

The current generator is a strong foundation. It already includes:

- `Tools/LevelGenerator/app/services/level_generation_service.py`
- difficulty presets and campaign curve support
- templates for straight delivery, single switch, package gate, return loop, multi-switch chain, ring route, and four-way intersections
- candidate signatures and duplicate detection
- existing-level comparison
- validation services
- Python solution simulation
- quality scoring
- GUI support
- map seed import support
- preview/report generation
- Xcode resource sync and delete tooling
- generated solution sidecars

However, the current setup still behaves mostly like a template generator. The next step is to turn it into a real level design pipeline:

```text
mechanic recipe -> abstract solver -> layout planner -> road shape planner -> visual validator -> runtime-parity simulator -> quality scorer -> human review -> production write
```

## Phase 0 Baseline Snapshot

Current templates:

- `straight_delivery`
- `single_switch`
- `package_gate`
- `return_loop`
- `multi_switch_chain`
- `ring_route`
- `four_way_intersection`
- `mixed`, which filters and weights the concrete templates by difficulty

Current validators:

- Swift-side production level decoding and graph construction through `LevelRepository` and `RouteEngine`.
- Swift level validation support in `TinyRoutesTests/Support/LevelValidator.swift`.
- Python generated-level validation in `GeneratedLevelValidationService`, including structural checks and solution simulation.
- `LevelValidationRunnerService` for invoking Swift validation from generator workflows when available.
- Candidate uniqueness checks against the current batch and existing production levels.

Current simulation behavior:

- The Python simulator replays timed tap actions, switch rotations, package collection, destination arrival, max-step guards, and time-limit success/failure.
- The Swift runtime remains the source of truth for in-app movement through `RouteEngine`, `RuntimeRouteGraph`, and `RoadPath`.
- `SolutionBuilderService` derives solution timing from route events for generated sidecars.

Current report/preview behavior:

- Markdown and JSON generation reports include accepted candidates, rejected candidates, seeds, template/variant notes, candidate signatures, quality details, and simulation details.
- Preview SVGs are generated under `docs/generated_levels/previews`.
- `production_manifest_service.py` maintains generated-level manifest data.
- The Tkinter generator GUI uses the same generation services and can show candidate lists and visual previews before writing approved levels.

Known limitations:

- The generator still primarily emits template-shaped levels rather than solved mechanic recipes.
- Fixed or lightly varied layouts can still produce visually similar levels.
- Switch visual clarity is not yet enforced by a Python-side validation gate.
- Runtime-parity switch arrow tests now exist, and a level-028-style fixture is preserved under `TinyRoutesTests/Fixtures/SwitchArrowBug`, but generator rejection of confusing switch exits remains future Phase 1 work.

## Core Principle

Generated levels must pass three gates:

1. **Data correctness** — JSON is valid, resources sync, solution sidecar exists.
2. **Gameplay correctness** — the level is solvable in the actual runtime behavior, with fair timing.
3. **Design quality** — the level is readable, unique, mechanically interesting, and difficulty-appropriate.

Do not accept a level just because it passes JSON validation.

---

# Phase 0 — Baseline, Safety, and Bug Reproduction

## Purpose

Lock down the current behavior before changing the generator so bugs do not move around or become harder to diagnose.

## Tasks

- [ ] Create a new plan/status file:
  - [ ] `Tools/LevelGenerator/docs/next_generation_master_plan.md`
  - [ ] `Tools/LevelGenerator/docs/next_generation_completion_status.md`
- [ ] Add a short current-state summary to the new plan:
  - [ ] current templates
  - [ ] current validators
  - [ ] current simulation behavior
  - [ ] current report/preview behavior
  - [ ] known limitations
- [ ] Save a reproduction case for the switch arrow bug:
  - [ ] find or recreate the failing generated level, especially the “level 28” style case
  - [ ] save the level JSON under a test fixture folder
  - [ ] save the matching solution JSON
  - [ ] document what the arrow displays
  - [ ] document what direction the car actually travels
- [ ] Add regression tests before fixing the bug:
  - [ ] test that the active switch arrow uses the first road-path tangent, not direct target-node vector
  - [ ] test that diagonal target positions do not produce misleading diagonal/down arrows when the road initially leaves horizontally
  - [ ] test both `horizontalFirst` and `verticalFirst` road shapes
- [ ] Run the existing local generator checks before any refactor:
  - [ ] `python Tools/LevelGenerator/run_all_generator_checks.py`
  - [ ] `python -m pytest Tools/LevelGenerator/tests`
  - [ ] Swift tests if Xcode is available

## Do

- Do create regression fixtures before making changes.
- Do keep existing generated production levels safe.
- Do use scratch folders or dry runs while testing.
- Do preserve deterministic seeds.

## Don’t

- Do not overwrite production levels while developing generator changes.
- Do not fix the arrow visually without also validating the generator output.
- Do not remove existing templates during the first pass.
- Do not rely on manual playtesting as the only proof that the bug is fixed.

## Acceptance Criteria

- [ ] A reproducible bug fixture exists.
- [ ] The current test suite still passes before changes.
- [ ] The issue is documented clearly enough for another engineer to understand.

---

# Phase 1 — Runtime-Parity Switch Direction and Arrow Correctness

## Purpose

Fix the mismatch where a switch arrow visually points one direction but tapping sends the car along a different-feeling road direction.

## Problem

The current Swift arrow direction resolver in `TinyRoutes/UI/GameplayScreen.swift` prefers the vector from the switch node to the target node. For L-shaped roads, that can disagree with the actual first movement direction of the road path.

The generator can accidentally create levels where the direct vector looks diagonal or downward even though the road initially exits horizontally or vertically.

## Tasks

- [ ] Update `SwitchArrowDirectionResolver`:
  - [ ] use `edge.roadPath.tangent(atProgress: 0)` as the primary source of direction
  - [ ] only fall back to target-node vector when the road path has no valid tangent
  - [ ] normalize near-zero vectors safely
  - [ ] add helper method for testability, such as `directionAngleForRoadPathStart(...)`
- [ ] Add Swift unit tests:
  - [ ] straight horizontal road points right/left
  - [ ] straight vertical road points up/down
  - [ ] `horizontalFirst` L-road points horizontally from the switch
  - [ ] `verticalFirst` L-road points vertically from the switch
  - [ ] active outgoing edge changes arrow direction after rotation
- [ ] Add Python-side generator validation:
  - [ ] create `SwitchVisualClarityService`
  - [ ] calculate the starting tangent for every outgoing edge from a switch
  - [ ] reject switches where two outgoing options start in the same visual direction bucket
  - [ ] reject switches where the visual direction is ambiguous
  - [ ] reject switches where a required solution tap cycles to a visually confusing edge
- [ ] Add generator tests:
  - [ ] fixture with two outgoing roads that both initially leave right should fail
  - [ ] fixture with up/right/down/left distinct exits should pass
  - [ ] fixture with L-shaped outgoing roads should use first road segment, not target vector
- [ ] Add report details:
  - [ ] include switch visual direction buckets in JSON report
  - [ ] include warning/rejection reason counts for visual switch failures

## Do

- Do make the arrow represent where the car will initially move.
- Do keep the runtime and generator using the same direction concept.
- Do reject generated levels that are technically solvable but visually unfair.
- Do keep four-way intersection support explicit and tested.

## Don’t

- Do not use direct target-node angle as the primary arrow direction.
- Do not allow two switch choices to visually leave in the same direction unless the UI can clearly distinguish them.
- Do not hide this problem by changing only asset rotation.
- Do not make the generator accept unclear switches just because simulation passes.

## Acceptance Criteria

- [ ] The level 28-style arrow mismatch is fixed.
- [ ] L-shaped roads display arrows based on the road’s actual starting direction.
- [ ] Generated levels with ambiguous switch exits are rejected before writing.
- [ ] Swift and Python tests cover the bug.

---

# Phase 2 — Move From Template-First to Recipe-First Generation

## Purpose

Make the generator create puzzle mechanics first, then lay them out visually. This gives better variety than hardcoded full-level templates.

## Current State

There is already graph recipe code:

- `GraphRecipeService`
- `RecipeToLevelBuilderService`
- `GraphRecipe` models

But the main generation path still primarily chooses templates and has templates generate full levels directly.

## Target State

Templates become recipe producers, not final level builders.

```text
DifficultyPreset
  -> MechanicRecipeGenerator
  -> AbstractPuzzleGraph
  -> Solver
  -> LayoutPlanner
  -> RoadShapePlanner
  -> GeneratedLevel
```

## Tasks

- [ ] Introduce a new recipe-generation interface:
  - [ ] `MechanicRecipeGenerator`
  - [ ] `RecipeFamily`
  - [ ] `RecipeVariantSpec`
- [ ] Convert current templates into recipe families:
  - [ ] straight delivery recipe
  - [ ] single switch recipe
  - [ ] package gate recipe
  - [ ] return loop recipe
  - [ ] multi-switch chain recipe
  - [ ] ring route recipe
  - [ ] four-way intersection recipe
- [ ] Keep old templates temporarily:
  - [ ] mark them as legacy-compatible
  - [ ] allow old templates to remain available behind a config flag
  - [ ] do not delete until recipe-first output reaches parity
- [ ] Update `LevelGenerationService`:
  - [ ] choose recipe family instead of full-level template when recipe mode is enabled
  - [ ] generate multiple abstract recipe candidates
  - [ ] solve abstract recipes before layout
  - [ ] pass only valid solved recipes into layout generation
- [ ] Add config fields:
  - [ ] `generation_mode`: `legacy_template`, `recipe_first`, `hybrid`
  - [ ] `recipe_pool_size`
  - [ ] `layouts_per_recipe`
  - [ ] `road_shapes_per_layout`
- [ ] Add CLI options:
  - [ ] `--generation-mode recipe-first`
  - [ ] `--recipe-pool-size`
  - [ ] `--layouts-per-recipe`
  - [ ] `--road-shapes-per-layout`
- [ ] Add GUI controls for the new options.
- [ ] Update reports:
  - [ ] show recipe family
  - [ ] show recipe variant
  - [ ] show abstract graph signature
  - [ ] show selected layout variant
  - [ ] show selected road-shape strategy

## Do

- Do keep compatibility with current level JSON.
- Do build recipes around gameplay intent.
- Do allow multiple layouts from the same recipe.
- Do score mechanics separately from visual layout.

## Don’t

- Do not let the recipe layer know about final pixel/UI rendering.
- Do not encode final node coordinates inside recipe families unless absolutely required for a handcrafted pattern.
- Do not delete old templates until recipe-first generation can reproduce all current level categories.
- Do not treat “more switches” as the only way to increase difficulty.

## Acceptance Criteria

- [ ] Generator can create levels through the recipe-first path.
- [ ] Current template families have equivalent recipe families.
- [ ] Reports clearly show the recipe source of each level.
- [ ] Legacy generation still works during transition.

---

# Phase 3 — Abstract Puzzle Solver

## Purpose

Before worrying about visual layout, prove that the generated puzzle graph has a valid solution and meaningful choices.

## Tasks

- [x] Create `AbstractPuzzleSolverService`:
  - [x] input: recipe graph, start, package, destination, switch behavior
  - [x] output: solved path, required switch taps, alternate paths, dead ends, failure paths
- [x] Model switch state explicitly:
  - [x] default active outgoing edge
  - [x] tap order rotation
  - [x] two-way, three-way, and four-way switch behavior
  - [x] repeated taps allowed or disallowed by difficulty
- [x] Search possible tap sequences:
  - [x] breadth-first search for lower difficulties
  - [x] bounded search for hard/expert levels
  - [x] max tap count guard
  - [x] max state count guard
- [x] Identify solution quality:
  - [x] minimum required taps
  - [x] optional taps
  - [x] false routes
  - [x] route loops
  - [x] repeated switch usage
  - [x] whether package is collected before destination
- [x] Reject bad abstract puzzles:
  - [x] no solution
  - [x] solution skips package
  - [x] destination reachable before package when that would confuse scoring
  - [x] every choice is obvious/no-op
  - [x] too many equivalent solutions
  - [x] requires too many taps for difficulty
  - [x] requires repeated taps before player has learned that mechanic
- [x] Store solved recipe metadata:
  - [x] `solutionTapNodeIDs`
  - [x] `solutionSwitchStates`
  - [x] `requiredPath`
  - [x] `alternatePathCount`
  - [x] `deadEndCount`
  - [x] `loopCount`
- [x] Add tests:
  - [x] no-switch tutorial route
  - [x] single switch with one wrong branch
  - [x] package gate
  - [x] return loop
  - [x] ring route
  - [x] four-way intersection
  - [x] unsolvable graph
  - [x] destination-before-package graph

## Do

- Do solve the abstract graph before assigning coordinates.
- Do keep solver deterministic.
- Do set hard limits to prevent hangs.
- Do make failure reasons reportable.

## Don’t

- Do not rely only on timed simulation to discover basic graph unsolvability.
- Do not allow infinite loop exploration.
- Do not accept a recipe that technically solves but has no meaningful player decision.
- Do not generate hard/expert puzzles by simply adding random dead ends.

## Acceptance Criteria

- [x] Every recipe-first candidate is abstractly solved before layout.
- [x] Solver failures produce clear rejection codes.
- [x] Solver tests cover all supported mechanic families.

---

# Phase 4 — Layout Planner

## Purpose

Place nodes in readable, mobile-friendly positions after the abstract puzzle is known to work.

## Target Behavior

The layout planner should generate several candidate layouts per solved recipe and reject unclear ones.

## Tasks

- [x] Create or expand `GraphLayoutPlannerService`:
  - [x] input: solved abstract recipe
  - [x] output: node coordinates with layout metadata
- [x] Support layout strategies:
  - [x] horizontal route progression
  - [x] vertical route progression
  - [x] hub-and-spoke
  - [x] ring/loop layout
  - [x] package-inside-loop layout
  - [x] split-lane layout
  - [x] four-way intersection layout
- [x] Add spacing constraints:
  - [x] minimum distance between all nodes
  - [x] larger minimum distance between important nodes
  - [x] minimum distance from board edge
  - [x] minimum distance between switch nodes
  - [x] avoid placing package/destination too close together
- [x] Add composition rules:
  - [x] start should be visually obvious
  - [x] package should be visually reachable and not hidden in clutter
  - [x] destination should feel like the goal
  - [x] dead ends should look intentional
  - [x] switches should have enough empty space around them for tap targets and arrows
- [x] Add layout variation:
  - [x] mirror horizontally
  - [x] mirror vertically
  - [x] rotate when safe
  - [x] widen/narrow route
  - [x] shift route center
  - [x] apply controlled jitter
- [x] Add rejection reasons:
  - [x] `layout_node_cluster`
  - [x] `layout_important_nodes_too_close`
  - [x] `layout_switch_too_close_to_edge`
  - [x] `layout_package_destination_confusing`
  - [x] `layout_dead_end_not_readable`
- [x] Add tests:
  - [x] each layout strategy stays inside preset coordinate bounds
  - [x] important nodes meet spacing requirements
  - [x] layout variation changes layout hash
  - [x] invalid clustered layouts are rejected

## Do

- Do use the difficulty preset’s coordinate bounds.
- Do generate multiple layout options per recipe.
- Do keep coordinates deterministic for a seed.
- Do design for phone screen readability.

## Don’t

- Do not let random jitter break readability.
- Do not place key nodes near the extreme edge unless intentionally supported by UI layout.
- Do not allow package/destination overlap or visual ambiguity.
- Do not consider a layout final before road-shape validation.

## Acceptance Criteria

- [x] Layout planner generates multiple valid layouts for each recipe family.
- [x] Layout rejection reasons are visible in reports.
- [x] No generated candidate can pass with clustered important nodes.

---

# Phase 5 — Road Shape Planner

## Purpose

Choose `horizontalFirst` or `verticalFirst` deliberately so roads are readable and switch arrows are honest.

## Current Risk

`RoadShapeService.pick_for_positions(...)` currently chooses road shape mainly by comparing horizontal and vertical deltas. That is simple and deterministic, but not always best for puzzle readability.

## Tasks

- [x] Expand `RoadShapeService` into a planner:
  - [x] input: node positions, abstract solved path, outgoing switch choices
  - [x] output: road shape for each edge plus scoring metadata
- [x] Generate road-shape alternatives:
  - [x] all-straight where possible
  - [x] horizontal-first preference
  - [x] vertical-first preference
  - [x] switch-clarity optimized
  - [x] crossing-minimized
  - [x] main-route-smoothed
- [x] Add switch-exit clarity rules:
  - [x] outgoing choices from a switch should have different starting tangents
  - [x] required route and wrong route should not initially overlap
  - [x] four-way switches should ideally use four cardinal directions
  - [x] avoid diagonal-feeling arrows caused by endpoint vector mismatch
- [x] Add road crossing rules:
  - [x] count crossings
  - [x] distinguish harmless decorative crossings from confusing crossings
  - [x] reject crossings near switches, package, or destination
  - [x] penalize crossings on the required path
- [x] Add road overlap rules:
  - [x] reject overlapping first segments from the same switch
  - [x] reject long parallel road segments that visually merge
  - [x] reject path segments too close to important nodes
- [x] Add tests:
  - [x] road shape can be chosen to separate two switch exits
  - [x] horizontal-first and vertical-first create different tangents for L-roads
  - [x] crossing-heavy candidate scores lower
  - [x] overlapping first segments fail validation

## Do

- Do choose road shape based on gameplay readability.
- Do make switch exits the top priority.
- Do prefer clear cardinal directions over mathematically shortest paths.
- Do score multiple road-shape options per layout.

## Don’t

- Do not choose road shape only by largest coordinate delta.
- Do not allow two options from a switch to visually stack on top of each other.
- Do not rely on the player guessing what an L-road will do.
- Do not accept visually confusing roads because the solver succeeds.

## Acceptance Criteria

- [x] Road-shape selection reduces visual ambiguity.
- [x] Switch arrows and road exits match.
- [x] Road-shape scores are included in quality reports.

---

# Phase 6 — Visual Clarity Validator

## Purpose

Reject levels that are technically valid but visually bad.

## Tasks

- [x] Create `VisualClarityValidationService` or expand current validation:
  - [x] route crossing analysis
  - [x] route overlap analysis
  - [x] node spacing analysis
  - [x] switch exit direction analysis
  - [x] tap target spacing analysis
  - [x] important-node readability analysis
- [x] Add switch-specific checks:
  - [x] duplicate outgoing start direction
  - [x] ambiguous active edge arrow
  - [x] active edge visually hidden under another road
  - [x] switch too close to another switch
  - [x] four-way switch missing clear cardinal options
- [x] Add route-specific checks:
  - [x] required path crosses itself too much
  - [x] wrong route crosses required route near a switch
  - [x] dead end looks like the main route
  - [x] return loop visually unclear
  - [x] package is off the visual flow without being intentional
- [x] Add mobile UI checks:
  - [x] switch tap target has enough screen separation
  - [x] arrow icon will not collide with node label or package icon
  - [x] important nodes remain readable at current board zoom
  - [x] level still reads well on small devices
- [x] Add severity levels:
  - [x] `error`: structured hard-failure issue severity
  - [x] `warning`: structured soft issue severity
  - [x] `info`: structured report-only issue severity
- [x] Add tests:
  - [x] visual clarity errors reject generation
  - [x] warnings lower quality score
  - [x] report includes exact node/edge IDs

Implementation note: `VisualClarityValidationService` defines the Phase 6 rule set and emits structured `error`, `warning`, and `info` issues with related node/edge IDs. Visual errors are wired into generator rejection, warnings lower readability quality, and JSON reports include exact node/edge IDs.

## Do

- Do reject visually unfair levels.
- Do make every visual rejection explain exactly what is wrong.
- Do make validators independent and testable.
- Do keep warnings separate from hard failures.

## Don’t

- Do not bury visual issues inside generic validation failures.
- Do not make the designer manually discover every bad layout.
- Do not use one global crossing threshold for every difficulty without context.
- Do not allow readability to get worse just because the level is harder.

## Acceptance Criteria

- [x] Visual clarity validation catches ambiguous switches and messy roads.
- [x] Reports clearly identify failed nodes/edges.
- [x] The generator rejects ugly/confusing levels before human review.

---

# Phase 7 — Runtime-Parity Simulation

## Purpose

Make Python validation behave as close as possible to the Swift runtime, then use Swift tests as the final authority before production.

## Current Risk

Python simulation currently approximates route movement using Manhattan distance and switch state. The Swift runtime uses `RoadPath` geometry, trimmed roads, transitions, and actual movement behavior.

## Tasks

- [x] Audit Swift runtime behavior:
  - [x] `RouteEngine.swift`
  - [x] `RuntimeRouteGraph.swift`
  - [x] `NodeSwitchController.swift`
  - [x] `RoadPath` in `RouteEdge.swift`
  - [x] gameplay screen arrow rendering
- [x] Update Python simulator:
  - [x] compute road path length using the same segment rules as Swift
  - [x] support horizontal-first and vertical-first turn lengths
  - [x] account for connector/transition behavior if it affects timing
  - [x] model tap ignored/current-edge behavior exactly
  - [x] model switch rotation order exactly
- [x] Add parity fixtures:
  - [x] straight road
  - [x] horizontal-first L-road
  - [x] vertical-first L-road
  - [x] return loop
  - [x] ring route
  - [x] four-way switch
- [x] Add Swift validation harness improvements:
  - [x] allow testing a specific generated level ID
  - [x] allow testing scratch-level directories
  - [x] return structured failure details
  - [x] expose simulation trace where practical
- [x] Add production rule:
  - [x] hard and expert generated levels require Swift validation before commit
  - [x] ring and four-way levels require Swift validation before production
  - [x] Python-only validation is allowed for quick dry runs but not final production batches

## Do

- Do make Python fast and conservative.
- Do use Swift tests as production authority.
- Do add max-step and max-time guards to all simulation paths.
- Do compare Python timing against Swift timing where possible.

## Don’t

- Do not let Python simulation accept levels Swift would fail.
- Do not make generated hard/expert levels production-ready without Swift confidence.
- Do not remove simulation guards.
- Do not allow infinite loops in either Python or Swift tests.

## Acceptance Criteria

- [x] Python simulator uses road-path-aware timing.
- [x] Swift-specific production checks are required for risky mechanics.
- [x] Simulation failures include useful traces.

---

# Phase 8 — Difficulty Model and Campaign Progression

## Purpose

Make levels feel like a smooth campaign instead of random valid puzzles.

## Tasks

- [x] Expand difficulty metrics:
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
- [x] Define difficulty bands:
  - [x] tutorial
  - [x] easy
  - [x] medium
  - [x] hard
  - [x] expert
- [x] Add feature unlock gates:
  - [x] no switches before tutorial introduces movement
  - [x] single switch before multi-switch
  - [x] package gate before return loop
  - [x] return loop before ring route
  - [x] two-way switches before four-way intersections
  - [x] four-way intersections only after clear tutorial/supporting levels
- [x] Add campaign curve rules:
  - [x] avoid sudden tap-count spikes
  - [x] avoid back-to-back levels with same recipe family
  - [x] alternate dense levels with simpler breather levels
  - [x] introduce new mechanics with low visual complexity
  - [x] repeat mechanic with variation before increasing complexity
- [x] Add batch-level scoring:
  - [x] compare level to previous campaign levels
  - [x] reject adjacent levels with too-similar signatures
  - [x] reject difficulty cliffs
  - [x] penalize repeated recipe family streaks
- [x] Add tests:
  - [x] auto curve outputs expected difficulty bands
  - [x] hard levels have meaningful complexity
  - [x] tutorial levels stay simple
  - [x] adjacent duplicate mechanics are penalized

## Do

- Do treat difficulty as more than switch count.
- Do consider visual difficulty separately from mechanical difficulty.
- Do enforce mechanic introduction order.
- Do build campaign pacing into batch generation.

## Don’t

- Do not make early levels visually busy.
- Do not unlock four-way intersections too early.
- Do not put repeated-tap mechanics before the player understands switch rotation.
- Do not generate long chains as the default hard-level solution.

## Acceptance Criteria

- [x] Difficulty scoring explains why a level belongs in its band.
- [x] Auto generation produces smoother campaign batches.
- [x] Reports show mechanical and visual difficulty separately.

---

# Phase 9 — Recipe Library Expansion

## Purpose

Add enough mechanic variety that large batches do not feel samey.

## Recipe Families to Add

### Beginner/Tutorial

- [x] `straight_delivery_intro`
- [x] `single_switch_intro`
- [x] `single_switch_wrong_dead_end`
- [x] `package_before_destination_intro`

### Easy

- [x] `single_switch_package_choice`
- [x] `two_switch_order_intro`
- [x] `short_detour_gate`
- [x] `safe_dead_end_choice`
- [x] `package_gate_simple`

### Medium

- [x] `multi_switch_order`
- [x] `package_gate_double_choice`
- [x] `return_loop_intro`
- [x] `split_path_rejoin`
- [x] `fake_shortcut`
- [x] `hub_choice`

### Hard

- [x] `return_loop_with_gate`
- [x] `ring_route_gate`
- [x] `multi_switch_revisit`
- [x] `package_inside_loop`
- [x] `two_phase_route`
- [x] `branch_then_rejoin_with_wrong_order`

### Expert

- [x] `four_way_intro`
- [x] `four_way_package_gate`
- [x] `four_way_ring`
- [x] `multi_four_way_route`
- [x] `controlled_repeated_taps`
- [x] `late_route_reversal`

## Tasks

- [x] For each recipe family, define:
  - [x] intended mechanic
  - [x] supported difficulties
  - [x] required player skill
  - [x] allowed switch counts
  - [x] allowed tap counts
  - [x] allowed repeated taps
  - [x] visual layout requirements
  - [x] reason it is fun or useful
- [x] Add recipe-family tests:
  - [x] generated recipe validates
  - [x] abstract solver finds solution
  - [x] layout planner can place it
  - [x] final validator accepts at least one deterministic seed
- [x] Add recipe weights:
  - [x] by difficulty
  - [x] by level number
  - [x] by recently used mechanic families
  - [x] by whether a mechanic is newly introduced
- [x] Update reports:
  - [x] recipe family
  - [x] mechanic tags
  - [x] unlock requirement
  - [x] prior mechanic dependency

## Do

- Do define the intended player lesson for each recipe.
- Do make each recipe family produce several distinct solved graphs.
- Do use tags like `package_gate`, `return_loop`, `four_way`, `repeated_tap`.
- Do give the generator enough variety before increasing batch size.

## Don’t

- Do not create new recipes that are only longer versions of old recipes.
- Do not add four-way/expert recipes without strong validation.
- Do not hide confusing mechanics behind random generation.
- Do not let recipe count grow without tests.

## Acceptance Criteria

- [x] Each difficulty band has multiple reliable recipe families.
- [x] Hard generation no longer depends heavily on `multi_switch_chain`.
- [x] Expert generation has clear four-way progression.

---

# Phase 10 — Candidate Search, Scoring, and Selection

## Purpose

Choose the best candidate from many possibilities, not the first valid candidate.

## Recommended Defaults

```text
candidate_pool_size: 25 for normal generation
candidate_pool_size: 50 for hard/expert generation
recipe_pool_size: 10-20
layouts_per_recipe: 3-5
road_shapes_per_layout: 2-4
max_attempts_per_level: 300 for production batches
```

## Tasks

- [x] Update default candidate pool behavior:
  - [x] keep `candidate_pool_size=1` only for fast tests
  - [x] use larger default for GUI production mode
  - [x] warn if production generation uses pool size 1
- [x] Expand quality score categories:
  - [x] abstract mechanic quality
  - [x] runtime solvability
  - [x] visual readability
  - [x] switch clarity
  - [x] difficulty fit
  - [x] uniqueness
  - [x] campaign pacing
  - [x] mobile tap comfort
  - [x] visual appeal
- [x] Add hard rejection thresholds:
  - [x] minimum total quality
  - [x] minimum switch clarity score
  - [x] minimum runtime confidence
  - [x] maximum similarity score
- [x] Add soft penalties:
  - [x] too many crossings
  - [x] too many nearby nodes
  - [x] repeated recipe family
  - [x] awkward tap timing
  - [x] route too straight for difficulty
  - [x] route too complex for difficulty
- [x] Update reports:
  - [x] show top rejected near-miss candidates
  - [x] show score breakdown for accepted candidate
  - [x] show why the accepted candidate beat other candidates
  - [x] show minimum/average/max candidate scores per generated level
- [x] Add tests:
  - [x] higher clarity beats lower clarity
  - [x] unique candidate beats near duplicate
  - [x] difficulty-fit candidate beats wrong-band candidate
  - [x] pool selection is deterministic for same seed

## Do

- Do generate more candidates than you need.
- Do make scoring explainable.
- Do keep hard failure validation separate from quality scoring.
- Do keep deterministic ordering and tie-breaking.

## Don’t

- Do not accept the first valid candidate in production mode.
- Do not let high route interest compensate for bad switch clarity.
- Do not hide candidate selection decisions from the report.
- Do not make scoring so complex it becomes impossible to debug.

## Acceptance Criteria

- [x] Production generation uses meaningful candidate pools.
- [x] Reports explain candidate selection.
- [x] Low-quality but technically valid candidates are not accepted.

---

# Phase 11 — Generated Solution Sidecars and Human-Friendly Timing

## Purpose

Ensure every generated solution is correct, readable, and fair for players.

## Tasks

- [x] Improve solution-building metadata:
  - [x] record why each tap is needed
  - [x] record expected edge after tap
  - [x] record player reaction window
  - [x] record switch state before and after tap
- [x] Add solution timing rules:
  - [x] minimum spacing by difficulty
  - [x] minimum reaction time before switch arrival
  - [x] no tap required immediately after level start unless tutorialized
  - [x] no rapid repeated taps except expert levels
  - [x] required taps should align with visible switch approach
- [x] Add solution sidecar comments/metadata where schema allows:
  - [x] recipe family
  - [x] solution route
  - [x] required tap order
  - [x] generated seed
  - [x] validation version
- [x] Add validation:
  - [x] reject placeholder solutions
  - [x] reject missing sidecars
  - [x] reject sidecars that do not match level ID
  - [x] reject actions targeting non-switchable nodes
  - [x] reject taps too close together
  - [x] reject solutions that fail Python or Swift simulation
- [x] Add tests:
  - [x] generated solution matches level ID
  - [x] solution actions are ordered
  - [x] solution timing is difficulty-appropriate
  - [x] no placeholder sidecar can pass production validation

## Do

- Do make solution files useful for testing and review.
- Do use timing that feels fair on phones.
- Do expose solution reasoning in reports.
- Do ensure level and sidecar are always written together.

## Don’t

- Do not commit generated levels without sidecars.
- Do not allow solution sidecars to be placeholders.
- Do not allow impossible or barely possible tap timing.
- Do not make the player tap faster than the UI clearly communicates.

## Acceptance Criteria

- [x] Every generated production level has a valid matching solution sidecar.
- [x] Solution timing is reviewed automatically for fairness.
- [x] Reports show the intended tap sequence and route.

---

# Phase 12 — Optional Map-Inspired Generation Hardening

## Purpose

Use map data as inspiration without making production generation dependent on public APIs or messy real-world road geometry.

## Tasks

- [ ] Keep map import optional:
  - [ ] no network dependency for normal generation
  - [ ] no map dependency for tests unless explicitly marked optional
- [ ] Add map seed validation:
  - [ ] seed graph has enough nodes
  - [ ] seed graph has enough turns/intersections
  - [ ] seed graph can be normalized into bounds
  - [ ] attribution is preserved
- [ ] Add map-to-recipe adapter improvements:
  - [ ] choose interesting intersections as switch candidates
  - [ ] choose recognizable path structures as recipe hints
  - [ ] simplify noisy graph data before puzzle generation
  - [ ] keep map geometry as inspiration, not as final layout authority
- [ ] Add production warnings:
  - [ ] report map source
  - [ ] report attribution
  - [ ] warn if attribution missing
  - [ ] warn if map-inspired geometry was heavily modified
- [ ] Add tests:
  - [ ] map seed can influence node layout
  - [ ] bad map seed fails clearly
  - [ ] no map mode works without optional dependencies

## Do

- Do treat map data as inspiration.
- Do preserve attribution if map-inspired levels ship.
- Do cache imported map seeds.
- Do keep production generation deterministic after seed import.

## Don’t

- Do not call external APIs during normal generation.
- Do not ship map-derived content without license/attribution review.
- Do not let real road geometry override puzzle readability.
- Do not make map import necessary for the generator to work.

## Acceptance Criteria

- [ ] Map-inspired generation is optional, deterministic, and documented.
- [ ] Bad map seeds fail safely.
- [ ] Production reports preserve source information.

---

# Phase 13 — GUI Workflow for Designer Review

## Purpose

Make the GUI the safe production workflow for reviewing, rejecting, regenerating, and writing generated levels.

## Tasks

- [ ] Improve candidate preview:
  - [ ] show level graph
  - [ ] show start/package/destination
  - [ ] show active switch arrows
  - [ ] show all switch outgoing choices
  - [ ] show intended solution route
  - [ ] show tap order badges
  - [ ] show warnings directly on preview
- [ ] Add candidate comparison:
  - [ ] compare multiple candidates for the same level number
  - [ ] show score breakdown side-by-side
  - [ ] show duplicate/similarity warnings
- [ ] Add review statuses:
  - [ ] pending
  - [ ] approved
  - [ ] rejected
  - [ ] needs manual edit
  - [ ] requires Swift validation
- [ ] Add reject reasons:
  - [ ] visually confusing
  - [ ] too easy
  - [ ] too hard
  - [ ] too similar
  - [ ] bad switch arrow
  - [ ] bad route shape
  - [ ] other/manual note
- [ ] Add actions:
  - [ ] regenerate selected level number
  - [ ] regenerate with different recipe family
  - [ ] regenerate layout only
  - [ ] regenerate road shapes only
  - [ ] open in Level Editor
  - [ ] write approved levels only
  - [ ] export review report
- [ ] Add production safety:
  - [ ] dry-run required before production write
  - [ ] warning before overwriting production levels
  - [ ] require matching solution sidecars
  - [ ] show Xcode sync status
  - [ ] show Swift validation status
- [ ] Add tests:
  - [ ] GUI state transitions
  - [ ] approved candidates are preserved
  - [ ] rejected candidates are not written
  - [ ] write action writes approved levels and sidecars together

## Do

- Do make the GUI a review tool, not just a launch button.
- Do show exactly why a candidate was accepted or rejected.
- Do allow human taste to override generated candidates safely.
- Do support scratch output before production output.

## Don’t

- Do not write unreviewed production batches from the GUI by accident.
- Do not hide validation warnings off-screen.
- Do not make users inspect JSON manually for every issue.
- Do not let GUI state diverge from CLI behavior.

## Acceptance Criteria

- [ ] A designer can review and approve generated levels from the GUI.
- [ ] The GUI prevents accidental bad production writes.
- [ ] Preview clearly shows switch arrows and solution route.

---

# Phase 14 — Reports, Manifests, and Audit Trail

## Purpose

Make every generated batch traceable, reviewable, and reproducible.

## Tasks

- [ ] Expand markdown report:
  - [ ] command arguments
  - [ ] seed
  - [ ] generation mode
  - [ ] recipe family
  - [ ] layout strategy
  - [ ] road-shape strategy
  - [ ] difficulty score
  - [ ] visual score
  - [ ] switch clarity score
  - [ ] runtime simulation result
  - [ ] Swift validation result
  - [ ] rejection summary
  - [ ] preview images
- [ ] Expand JSON report:
  - [ ] full score object
  - [ ] solver metadata
  - [ ] visual validation metadata
  - [ ] switch direction metadata
  - [ ] timing metadata
  - [ ] candidate pool statistics
  - [ ] rejected near-miss candidates
- [ ] Add manifest improvements:
  - [ ] level ID
  - [ ] level name
  - [ ] recipe family
  - [ ] mechanic tags
  - [ ] difficulty metrics
  - [ ] quality metrics
  - [ ] signature hashes
  - [ ] generated seed
  - [ ] validation version
  - [ ] generated/hand-authored flag
- [ ] Add reproducibility workflow:
  - [ ] command to regenerate a specific level candidate by seed
  - [ ] command to regenerate a whole reviewed batch
  - [ ] command to compare current generated level to report metadata
- [ ] Add tests:
  - [ ] report contains required sections
  - [ ] JSON schema stays stable
  - [ ] manifest rebuild detects missing sidecars
  - [ ] manifest rebuild detects stale/generated mismatches

## Do

- Do make generated batches reproducible.
- Do include enough metadata to debug bad levels later.
- Do use reports as production review artifacts.
- Do keep markdown human-readable and JSON machine-readable.

## Don’t

- Do not bury critical failures only in console output.
- Do not make reports depend on image previews existing.
- Do not commit incidental report churn unless it is part of the reviewed batch.
- Do not hide rejected candidate information that explains generator behavior.

## Acceptance Criteria

- [ ] Every production batch has enough report data to reproduce and audit it.
- [ ] Manifest can detect missing or stale generated resources.
- [ ] Reports clearly show why each accepted level was selected.

---

# Phase 15 — Test Suite and CI Hardening

## Purpose

Make generator changes safe and keep CI from hanging or accepting broken levels.

## Test Categories

### Unit Tests

- [ ] recipe generation
- [ ] abstract solver
- [ ] layout planner
- [ ] road-shape planner
- [ ] visual clarity validation
- [ ] switch direction/tangent logic
- [ ] quality scoring
- [ ] difficulty scoring
- [ ] report payloads

### Integration Tests

- [ ] generate tutorial batch
- [ ] generate easy batch
- [ ] generate medium batch
- [ ] generate hard batch
- [ ] generate expert/four-way batch
- [ ] generate mixed auto campaign segment
- [ ] validate sidecars
- [ ] validate reports
- [ ] validate manifest

### Regression Tests

- [ ] level 28-style switch arrow mismatch
- [ ] generated hard batch starvation
- [ ] duplicate-looking generated levels
- [ ] stale Xcode resource references after deletion
- [ ] simulator hang guard
- [ ] missing solution sidecar

### Fuzz/Soak Tests

- [ ] run 100 deterministic seeds for each difficulty
- [ ] run 1,000 candidate generation attempts in scratch mode
- [ ] assert no hangs
- [ ] assert rejection reasons remain explainable
- [ ] assert accepted quality scores stay above threshold

### Swift Runtime Tests

- [ ] targeted generated-level solvability test
- [ ] road-path timing parity test
- [ ] switch rotation parity test
- [ ] four-way switch runtime test
- [ ] resource loading test

## Tasks

- [ ] Update `run_all_generator_checks.py`:
  - [ ] fast mode
  - [ ] full mode
  - [ ] soak mode
  - [ ] optional Swift mode
- [ ] Add CI-friendly timeouts:
  - [ ] unit tests
  - [ ] batch generation tests
  - [ ] simulation tests
  - [ ] Swift tests
- [ ] Add failure artifacts:
  - [ ] rejected candidate JSON
  - [ ] debug report
  - [ ] preview image
  - [ ] simulation trace
- [ ] Add performance baselines:
  - [ ] average generation time per level
  - [ ] max generation time per level
  - [ ] candidate attempts per accepted level
  - [ ] rejection reason distribution

## Do

- Do add or update tests with every service change.
- Do keep fast tests fast.
- Do isolate soak tests from normal unit tests.
- Do preserve failure artifacts for debugging.

## Don’t

- Do not let tests write production resources.
- Do not rely on one seed only.
- Do not allow simulation loops without guards.
- Do not make optional Swift/Xcode availability break Python-only CI.

## Acceptance Criteria

- [ ] Fast checks catch normal regressions quickly.
- [ ] Full checks validate batch behavior.
- [ ] Soak checks catch rare generator failures.
- [ ] CI cannot hang indefinitely in solvability tests.

---

# Phase 16 — Performance and Scalability

## Purpose

Support larger generation batches without slowdowns, hangs, or poor candidate variety.

## Tasks

- [ ] Add timing instrumentation:
  - [ ] recipe generation time
  - [ ] abstract solving time
  - [ ] layout planning time
  - [ ] road-shape planning time
  - [ ] validation time
  - [ ] simulation time
  - [ ] report generation time
- [ ] Add performance report section:
  - [ ] average attempts per accepted level
  - [ ] max attempts for any accepted level
  - [ ] common rejection reasons
  - [ ] slowest accepted candidates
- [ ] Optimize obvious hot spots:
  - [ ] cache existing-level signatures
  - [ ] cache layout readability calculations
  - [ ] avoid recomputing path geometry repeatedly
  - [ ] short-circuit invalid candidates early
- [ ] Add generation budgets:
  - [ ] max candidate attempts per level
  - [ ] max abstract solver states
  - [ ] max layout attempts per recipe
  - [ ] max validation time per candidate
- [ ] Add graceful failure behavior:
  - [ ] clear message when generation cannot find enough variety
  - [ ] report which recipe families were exhausted
  - [ ] suggest increasing pool size or enabling more recipes

## Do

- Do reject bad candidates early.
- Do cache expensive stable calculations.
- Do report slow phases.
- Do keep generation deterministic even with optimization.

## Don’t

- Do not optimize before adding measurements.
- Do not hide generation starvation behind generic failure messages.
- Do not let large batches silently reduce quality thresholds.
- Do not make performance improvements change generated output unexpectedly unless documented.

## Acceptance Criteria

- [ ] Large batches complete predictably.
- [ ] Slow generation phases are visible.
- [ ] Candidate starvation produces actionable messages.

---

# Phase 17 — Production Workflow and Release Rules

## Purpose

Define exactly when generated levels are allowed into the game.

## Production Generation Workflow

- [ ] Run deterministic dry run.
- [ ] Review markdown and JSON reports.
- [ ] Generate into scratch folders.
- [ ] Open candidates in GUI preview.
- [ ] Approve/reject candidates.
- [ ] Open questionable candidates in Level Editor.
- [ ] Run Python validation.
- [ ] Run Swift validation for hard/expert/ring/four-way levels.
- [ ] Playtest approved production candidates in simulator.
- [ ] Write approved levels and sidecars together.
- [ ] Rebuild manifest.
- [ ] Sync Xcode resources.
- [ ] Commit level JSON, solution JSON, and intentional metadata/report changes.

## Production Acceptance Checklist Per Level

- [ ] Level JSON exists.
- [ ] Matching solution JSON exists.
- [ ] Level ID and solution ID match.
- [ ] Package must be collected before destination.
- [ ] Required route is solvable.
- [ ] Switch arrows match actual outgoing road direction.
- [ ] No visually ambiguous switches.
- [ ] Tap timing is fair.
- [ ] Important nodes are readable.
- [ ] Road crossings are acceptable.
- [ ] Difficulty fits campaign placement.
- [ ] Level is not too similar to nearby levels.
- [ ] Swift validation passed if required.
- [ ] Manual review approved.

## Do

- Do commit levels and sidecars together.
- Do keep generated batches reproducible.
- Do reject levels that feel unfair even if they pass validation.
- Do document seed/template/recipe info in PR notes.

## Don’t

- Do not ship unreviewed generated batches.
- Do not accept generated levels that only pass Python simulation when Swift validation is required.
- Do not use `--overwrite` casually.
- Do not ignore stale resource warnings.

## Acceptance Criteria

- [ ] Every production generated level has a clear audit trail.
- [ ] No generated level enters production without sidecar and review.
- [ ] Hard/expert risky mechanics receive Swift/runtime validation.

---

# Phase 18 — Documentation and Engineer Workflow

## Purpose

Make the system maintainable for future work and safe for coding agents or entry-level engineers.

## Tasks

- [ ] Update `Tools/LevelGenerator/README.md`:
  - [ ] recipe-first overview
  - [ ] dry-run workflow
  - [ ] scratch workflow
  - [ ] GUI review workflow
  - [ ] production workflow
  - [ ] troubleshooting
- [ ] Add architecture docs:
  - [ ] `docs/architecture/recipe_generation.md`
  - [ ] `docs/architecture/abstract_solver.md`
  - [ ] `docs/architecture/layout_planner.md`
  - [ ] `docs/architecture/road_shape_planner.md`
  - [ ] `docs/architecture/visual_validation.md`
  - [ ] `docs/architecture/runtime_parity.md`
- [ ] Add agent task docs:
  - [ ] one task per PR
  - [ ] tests required with every behavior change
  - [ ] no production writes during tests
  - [ ] use scratch directories
  - [ ] update completion status after each task
- [ ] Add troubleshooting docs:
  - [ ] duplicate-looking levels
  - [ ] impossible levels
  - [ ] switch arrow mismatch
  - [ ] stale Xcode references
  - [ ] missing sidecars
  - [ ] map seed import problems
  - [ ] Swift test failures

## Do

- Do keep docs close to the tool.
- Do explain the why, not just the command syntax.
- Do keep a completion checklist current.
- Do write docs that a new engineer can follow.

## Don’t

- Do not rely on memory or chat history for generator rules.
- Do not let architecture drift away from implementation.
- Do not leave finished tasks unchecked.
- Do not make docs only useful to the original author.

## Acceptance Criteria

- [ ] A new engineer can safely run, test, review, and modify the generator.
- [ ] Architecture docs match the actual implementation.
- [ ] Completion status reflects current progress.

---

# Suggested Task Execution Order

Use this order for implementation. Each numbered item should be small enough for one focused PR or coding-agent task.

## Critical Bug-Fix Track

1. [ ] Add level 28-style switch arrow regression fixture.
2. [ ] Add Swift tests for arrow direction using road path tangent.
3. [ ] Change `SwitchArrowDirectionResolver` to use starting road-path tangent first.
4. [ ] Add Python switch visual direction helper.
5. [ ] Add generator validation for ambiguous switch exits.
6. [ ] Add report details for switch direction failures.
7. [ ] Run Python tests and targeted Swift tests.

## Generator Architecture Track

8. [ ] Add recipe-first config mode.
9. [ ] Add new recipe generator interface.
10. [ ] Wrap current templates as recipe families.
11. [ ] Add abstract solver service.
12. [ ] Add recipe-to-layout planner interface.
13. [ ] Add road-shape planner interface.
14. [ ] Integrate recipe-first path into `LevelGenerationService` behind a flag.
15. [ ] Add recipe-first reports.

## Quality Track

16. [ ] Expand difficulty metrics.
17. [ ] Add visual clarity validator.
18. [ ] Add switch clarity score.
19. [ ] Add candidate pool production defaults.
20. [ ] Add batch-level campaign pacing score.
21. [ ] Add top-candidate comparison in reports.

## Content Track

22. [ ] Add easy recipe families.
23. [ ] Add medium recipe families.
24. [ ] Add hard recipe families.
25. [ ] Add expert/four-way recipe families.
26. [ ] Add mechanic unlock gates.
27. [ ] Add recipe-family weighting by level number.

## Tooling Track

28. [ ] Improve GUI preview with switch arrows and solution route.
29. [ ] Add GUI review statuses and reject reasons.
30. [ ] Add regenerate-layout-only and regenerate-road-shapes-only actions.
31. [ ] Improve markdown/JSON reports.
32. [ ] Improve manifest metadata.
33. [ ] Add reproducibility commands.

## Test/CI Track

34. [ ] Add full recipe-first unit tests.
35. [ ] Add integration generation tests per difficulty.
36. [ ] Add fuzz/soak generation checks.
37. [ ] Add optional Swift runtime parity checks.
38. [ ] Add performance instrumentation.
39. [ ] Update `run_all_generator_checks.py` modes.

## Documentation Track

40. [ ] Update README.
41. [ ] Add architecture docs.
42. [ ] Add troubleshooting docs.
43. [ ] Add production review guide.
44. [ ] Update completion status.

---

# Global Do and Don’t Rules

## Do

- Do keep generation deterministic by seed.
- Do generate in dry-run or scratch mode first.
- Do validate with both data checks and gameplay checks.
- Do preserve solution sidecars.
- Do prefer recipe-first generation for long-term quality.
- Do score multiple candidates before accepting one.
- Do make every rejection reason specific.
- Do keep Swift/runtime behavior as the production truth.
- Do add tests with every behavior change.
- Do manually review generated production levels.

## Don’t

- Do not ship levels just because JSON is valid.
- Do not use direct target-node vector for switch arrow direction when road path tangent is available.
- Do not let templates be the only source of variety long term.
- Do not rely on external map APIs for normal generation.
- Do not accept visually confusing switch exits.
- Do not make hard levels by only adding more switches.
- Do not commit generated levels without matching solution files.
- Do not write production files from tests.
- Do not let CI or simulation loops hang.
- Do not delete legacy behavior before the new pipeline is proven.

---

# Final Definition of Done

The auto-generated level system is “best it can be” when all of this is true:

- [ ] The level 28-style switch arrow mismatch cannot recur.
- [ ] Switch arrows are based on actual road-path exit direction.
- [ ] Generated levels with ambiguous switch exits are rejected.
- [ ] The generator supports recipe-first generation.
- [ ] Abstract puzzles are solved before layout.
- [ ] Layouts are generated and scored separately from mechanics.
- [ ] Road shapes are chosen for readability, not just coordinate delta.
- [ ] Visual clarity is a first-class validator.
- [ ] Python simulation closely matches Swift runtime behavior.
- [ ] Hard/expert/ring/four-way levels require Swift validation for production.
- [ ] Candidate pool selection chooses the best candidate, not the first valid candidate.
- [ ] Campaign batches avoid repeated/samey levels.
- [ ] Reports explain why candidates were accepted or rejected.
- [ ] GUI review allows approval/rejection before production write.
- [ ] Every production generated level has a matching solution sidecar.
- [ ] CI/test checks prevent hangs, stale resources, missing sidecars, and broken generated content.
- [ ] Documentation is complete enough for another engineer or coding agent to continue safely.
