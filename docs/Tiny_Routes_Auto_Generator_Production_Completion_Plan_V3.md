# Tiny Routes Auto Generator — Production Completion Plan

**Revision:** Updated after GitHub audit of the completed V2 master plan.
**Document purpose:** Complete the Tiny Routes automatic level generator after the archived [V2 generator and level designer implementation plan](archive/Tiny_Routes_Generator_and_Level_Designer_Implementation_Plan_V2.md) has been fully implemented.

**Final product requirement:** A user chooses a starting level number, count, campaign/difficulty profile, and optional seed; presses **Generate**; and receives a complete set of production-ready Tiny Routes levels, solutions, reports, and manifest updates without opening the Level Designer, repairing a graph, repositioning a node, authoring a solution, or manually selecting the “good” candidates.

**This is the final generator plan.** It includes the puzzle model, supporting runtime/schema work, topology generation, solving, difficulty analysis, layout, timing, batch diversity, transactional production output, tests, calibration, documentation, and release gates needed to finish the generator rather than merely improve it.

## Repository Audit Baseline

**Audited repository:** `deveydtj/Tiny-Routes`
**Audited branch/commit:** `main` at `54c6516f64781ac3a259a8715605d27673005035`
**Audit conclusion:** The first implementation plan has produced a strong V2 foundation and should be treated as completed implementation baseline work. The new plan must extend that foundation rather than recreate it.

### Completed V2 systems to reuse

- Live-lookahead switch eligibility and tap enforcement in Swift.
- Shared Python runtime models, simulator behavior, and Swift/Python parity fixtures.
- Schema 1 compatibility and explicit schema 2 live-routing rules.
- Package-state road availability: `always`, `beforePackage`, and `afterPackage`.
- Package-state switch normalization in Swift, Python, generator analysis, and editor playtesting.
- Measured `DecisionProfile` fields for dependencies, revisits, recovery, package phases, opened/closed roads, timing windows, and equivalent choices.
- Constructive graph layout, deterministic repair, road-shape validation, visual-clarity validation, candidate scoring, and campaign portfolio selection.
- Level Editor direct manipulation, undo/redo, live validation, playtesting, solution recording, generated-candidate inspection, and autosave recovery.
- Migration and verification of the existing 27-level production corpus.
- Root verification commands, fixed-seed regression infrastructure, production-content gates, release documentation, and architecture documentation.

### Audit caveat

The first plan document still contains stale unchecked global checklists and PR-breakdown rows even though the phase implementations are marked complete and the corresponding code exists. Phase 0 of this plan reconciles that documentation once, but does not repeat the completed engineering work.

### Confirmed remaining generator defects

- `MotifComposerService` still joins motifs serially through one entry and one primary exit.
- Advanced automatic motif selection still centers on `split_and_rejoin`, `package_branch`, and `straight_segment` filler.
- Several legacy recipe families remain mislabeled, duplicated, or behavior-isomorphic.
- Expanded recipe alternate variants still pass through a no-op `_swap_dead_end_order()` implementation.
- The abstract solver state is still limited to current node, switch indices, and a single `collected_package` Boolean.
- `TopologySolverService.search()` still returns one solved metadata result rather than a complete strategy proof set.
- Fixed-seed hard, expert, and mixed-campaign suites can exercise template generation instead of the actual production candidate pipeline.
- Production files are currently written before the optional Swift verification completes, so a Swift failure can leave changed output behind.

---

## 1. Executive Summary

The current generator has useful validation infrastructure, but its puzzle creation is still dominated by small fixed graphs, serial motif concatenation, recipe aliases, and local switch decisions. A map can look complicated while the player experience remains:

1. Watch the dot approach the next switch.
2. Tap the switch until its arrow points toward the obvious next road.
3. Repeat.

That is not the target game.

The production generator must instead create **multi-phase routing puzzles** in which the player:

- Understands the current objective.
- Compares meaningful route options.
- Commits to a route while the delivery dot is moving.
- Sees the puzzle state change after reaching a checkpoint.
- Re-evaluates the map for the next objective.
- Revisits switches or hubs whose correct direction has changed.
- Recovers from some mistakes instead of encountering only instant dead ends.
- Identifies the best successful route among believable alternatives.

The final architecture will generate a **puzzle blueprint first**, prove the blueprint is strategically valid, compose it from typed mechanics, solve the complete state space, construct a readable map, prove runtime timing, score it against calibrated difficulty targets, and select a diverse campaign portfolio. Production files will be written only after the entire requested batch passes Python and Swift validation.

---

## 2. Non-Negotiable Definition of Success

The generator is not complete until every item below is true.

### 2.1 One-command generation

- [ ] A single CLI command and a single GUI action can generate a complete production batch.
- [ ] The same seed and configuration produce byte-for-byte equivalent level logic, solution actions, selection results, and reports.
- [ ] The generator automatically retries failed candidates using new blueprints, compositions, layouts, and road geometry.
- [ ] The generator never requires a person to choose candidates or repair output.
- [ ] The generator either produces the full requested batch or writes no production changes.

### 2.2 No trivial generated levels

- [ ] Production generation never outputs a zero-tap or one-tap level.
- [ ] Production generation never outputs a level with fewer than two meaningful route decisions.
- [ ] Every generated level contains at least one adaptive decision that occurs after a checkpoint or route-state change.
- [ ] No production level can be solved by assigning one permanent outgoing road to every switch before movement begins.
- [ ] Medium, hard, and expert levels cannot be solved by a greedy “point each upcoming arrow toward the currently highlighted target” strategy.
- [ ] Equivalent choices, decorative branches, and branches with identical future consequences do not count as decisions.

### 2.3 Real route choice

- [ ] A decision counts only when at least two available choices differ in future state, objective progress, route cost, risk, recoverability, or later switch requirements.
- [ ] The correct choice on at least one switch depends on more than the immediately adjacent road.
- [ ] Harder levels require the player to reason across multiple upcoming intersections or objective phases.
- [ ] Wrong choices are understandable from the map and are not arbitrary hidden traps.
- [ ] At least some levels contain multiple successful routes with one unique optimal route, rather than forcing every level to have exactly one successful path.

### 2.4 Multi-stop play

- [ ] New production levels support ordered objectives such as Start → Pickup A → Checkpoint B → Pickup C → Destination.
- [ ] The number of objectives is selected from the difficulty target rather than hardcoded to one package and one destination.
- [ ] Reaching an objective can visibly unlock, lock, reveal, or alter routes for later phases.
- [ ] The next objective is always communicated clearly and never changes through untelegraphed randomness.

### 2.5 Runtime correctness and fairness

- [ ] The Python and Swift runtimes produce equivalent state transitions and traces.
- [ ] Every generated solution uses only legal taps during real eligibility windows.
- [ ] Required decision windows include a configurable safety margin.
- [ ] No generated level relies on frame-perfect input, hidden road state, or multiple rapid taps that exceed the intended accessibility target.
- [ ] A valid solution remains valid under bounded simulation jitter.

### 2.6 Production safety

- [ ] All output is created in a staging directory first.
- [ ] Python validation, solution replay, corpus checks, manifest validation, and required Swift parity all pass before promotion.
- [ ] Promotion is atomic.
- [ ] A failed run leaves the existing production corpus unchanged.
- [ ] Reports contain enough information to reproduce every candidate and failure.

---

## 3. Scope and Assumptions

### 3.1 Starting condition

This plan starts from the completed V2 level-system baseline on GitHub `main`. It does **not** reimplement live-lookahead control, shared runtime parity, package-state roads, the editor command architecture, constructive layout, production-corpus migration, or the existing release gates.

Phase 0 performs a clean baseline verification, reconciles stale first-plan documentation, and creates a protected V3 feature boundary. Failure of an existing gate blocks V3 work, but fixing that gate is treated as baseline repair rather than a new generator architecture task.

### 3.2 Included work

Although this is a generator-completion plan, it includes the minimum supporting changes required in:

- The existing `tiny_routes_core` shared Python package.
- The existing Swift `RouteEngine` and serialized level models.
- The existing Python parity simulator.
- Generator blueprint, motif, composition, solving, analysis, layout, timing, selection, and orchestration services.
- The Level Editor’s schema-3 debugging and visualization surfaces.
- CLI and GUI generation entry points.
- Tests, reports, CI, staging, rollback, calibration, and release gates.

The V3 implementation must extend current types and services through compatibility adapters. It must not introduce a second unrelated runtime, graph model, layout engine, or editor document model.

### 3.3 Existing production content

The current schema-2 production corpus remains supported and playable. V3 becomes the default for **new automatic generation** after release gates pass. Existing levels are replaced only through an explicit content decision; a mass rewrite of all working V2 levels is not required to finish the generator.

### 3.4 Human work during development versus normal generation

“Fun” cannot be established by a single formula. A one-time calibration phase uses representative blinded playtests to tune automated metrics. Periodic release QA may sample generated content, but normal generation must not require per-level review, candidate selection, editor repair, or manual promotion.

### 3.5 Out of scope

The final generator does not need:

- Runtime-random road changes that make a seed play differently each attempt.
- Machine-learning-generated graphs.
- Online services or internet access.
- Manual JSON editing.
- Manual promotion of individual candidates.
- A requirement that every wrong choice instantly fails.
- Reimplementation of completed V2 runtime, editor, parity, layout, or release infrastructure.

---

## 4. Current Implementation Gaps That This Plan Must Close

The following findings were confirmed against the audited GitHub revision and are mandatory plan inputs.

### 4.1 The current motif composer is serial

`MotifComposerService` connects the previous fragment to each motif’s entry and continues from that motif’s first exit. It does not perform general edge insertion, nested branch expansion, phase-aware rewiring, multi-port composition, or realization of a decision-dependency graph.

For medium and above, automatic selection is still dominated by:

- `split_and_rejoin`
- `package_branch`
- `straight_segment` filler

The registry contains useful stateful motifs, but the default composition algorithm does not combine them into deep, behaviorally varied puzzles.

### 4.2 Motif depth and effect diversity are insufficient

The default composer selects at most four motifs. Several fragments create one local decision and `straight_segment` creates none. Hard and expert puzzles therefore cannot reliably achieve deep cross-phase dependencies, multiple objective-state changes, or several meaningful route alternatives.

### 4.3 Legacy recipe names and variants still overstate variety

Confirmed examples include:

- `return_loop_intro` delegating to the ordinary medium two-switch chain.
- `ring_route_gate` using non-ring topology rules and a simple chain builder.
- `return_loop_with_gate` and `multi_switch_revisit` sharing the repeated-tap builder.
- `multi_four_way_route` reusing `four_way_package_gate`.
- `late_route_reversal` reusing `controlled_repeated_taps`.
- `branch_then_rejoin_with_wrong_order` declaring a rejoin concept without a true alternate branch that rejoins.
- `_swap_dead_end_order()` executing the same output operation in both branches.

These families may remain as fixtures only after they are correctly classified; they cannot be counted as production diversity.

### 4.4 Existing decision analysis is useful but package-specific

The current `DecisionProfile` already measures substantially more than the original implementation: dependencies, independent-decision ratio, revisits, state changes on revisit, recovery, failure outcomes, package-phase decisions, opened/closed roads, timing windows, and equivalent choices.

The remaining problem is that these measurements are derived from a one-package Boolean state model and bounded route enumeration. They must be generalized to arbitrary ordered objectives, typed route state, exact strategy classes, planning horizon, local obviousness, and long dependency chains. The V3 plan extends this model; it does not discard it.

### 4.5 Topology solving is not a complete proof system

The abstract search state currently contains:

- Current node.
- Active authored index for each switch.
- `collected_package` Boolean.
- Path and decision history.

`TopologySolverService.search()` wraps one `solve_metadata()` result. The final system needs a finite canonical state model, weighted optimal search, alternate-success enumeration, unique-optimal proof, static-policy analysis, recovery classification, declared proof budgets, and reproducible proof artifacts.

### 4.6 The current schema is limited to one package phase

Schema 2 can condition roads on package state, which is a valuable completed foundation, but it cannot represent Start → Pickup A → Checkpoint B → Pickup C → Destination or conditions tied to arbitrary objective completion. V3 must generalize the existing mechanism while preserving schema-2 decoding and behavior.

### 4.7 Current quality selection can still reward presentation over strategy

The V2 quality service combines measured logic with route interest, visual appeal, layout, difficulty fit, and diversity. V3 must move anti-triviality, strategy depth, static-policy rejection, planning horizon, and objective-state dependence into hard gates before weighted ranking. A visually attractive simple chain cannot compensate for weak puzzle logic.

### 4.8 Validation remains stronger than construction

The current pipeline often generates a recipe, lays it out, schedules it, and then rejects it. V3 must satisfy strategic and state constraints during blueprint planning and composition, using downstream rejection as a safety net rather than the primary design method.

### 4.9 Regression suites do not always test the real production path

The current fixed-seed service runs some hard, expert, and mixed-campaign suites through direct template generation, while conditional-road suites directly compose named motifs. These are useful fixture tests but do not prove that the same one-command production pipeline can construct a full high-quality campaign. V3 release suites must invoke the exact production orchestration path with no template bypass.

### 4.10 Production verification is not transactional

`BatchOrchestrationService` currently writes selected levels and solutions before running optional Swift tests. `_write_generated_files()` writes files one by one directly to their target directories. A later Swift failure can mark the run failed after output has already changed.

V3 must stage everything, run every mandatory Python and Swift gate against staging, and promote atomically only after all checks pass.

### 4.11 Full-run completion is not yet the product contract

The current generator can stop when a requested slot has no valid candidate. The final system must be designed around filling the entire requested portfolio under fixed quality thresholds through blueprint replanning, composition backtracking, adaptive search breadth, and global attempt allocation. It may never silently relax strategic, runtime, readability, or diversity invariants.

---

## 5. Locked Product and Technical Decisions

These decisions remove ambiguity from later tasks.

### 5.1 New generated production schema

New automatic production levels use **schema version 3**.

Schema 3 adds:

- Ordered route objectives.
- Objective reveal and completion state.
- Objective-state edge availability rules.
- Optional edge usage limits where explicitly enabled.
- The existing live-lookahead switch rules.

Schema versions 1 and 2 remain decodable. The existing schema-2 `availability` values are not discarded; they are compatibility shorthand adapted into the new condition model.

### 5.2 Ordered objectives generalize package state

The runtime exposes an ordered `objectives` array as the V3 source of truth. A generated objective includes:

- Stable ID.
- Node ID.
- Objective kind.
- Sequence index.
- Reveal policy.
- Optional display metadata.

The final objective is terminal. Legacy package and destination fields remain supported through adapters for schema 1 and 2.

V3 edge availability uses a small structured rule, not a scripting language. At minimum it supports:

- Required completed objective IDs.
- Forbidden completed objective IDs.
- Minimum and maximum active objective index.
- Optional usage limit.

Compatibility mapping:

- `always` → no objective restriction.
- `beforePackage` → package objective is forbidden from the completed set.
- `afterPackage` → package objective is required in the completed set.

This mapping must produce identical Swift and Python behavior for every existing schema-2 fixture and production level.

### 5.3 Deterministic state changes only

Generated levels may change routes after objectives are completed, but those changes are deterministic for the level seed and visible to the player.

The generator will not create untelegraphed random closures, random objective locations, or runtime randomness that invalidates planning.

### 5.4 Unique optimal, not necessarily unique successful

The solver classifies all successful strategy equivalence classes within declared bounds.

Production rules:

- A canonical optimal route must exist.
- The optimal route must be unique under the configured cost ordering unless a level explicitly targets equivalent optimal routes.
- Near-optimal and longer successful alternatives may exist.
- `parTaps` and time targets are derived from the optimal route plus calibrated allowances.

Default cost ordering:

1. Complete all objectives in order.
2. Avoid terminal failure.
3. Minimize accepted taps.
4. Minimize travel time.
5. Minimize total route distance.
6. Use deterministic tie breakers only after gameplay costs are equal.

### 5.5 Production generation has no one-tap mode

The automatic production generator never creates zero-tap or one-tap levels, including its easiest production difficulty.

Existing hand-authored tutorial content may remain simple. Any future tutorial generator must be invoked separately and cannot be selected by normal production campaign generation.

### 5.6 Recipes become fixtures and fallback references

Fixed recipe families remain useful for:

- Regression fixtures.
- Tutorial examples.
- Motif validation.
- Debugging.

They will not remain the primary production generation architecture after the new blueprint/composition pipeline passes release gates.

### 5.7 Quality thresholds never relax automatically

Adaptive retries may change:

- Seed.
- Puzzle blueprint.
- Motif selection.
- Composition order.
- Layout profile.
- Road-shape strategy.
- Candidate-pool size.
- Attempt allocation.

Adaptive retries may not lower:

- Minimum meaningful decisions.
- Minimum adaptive decisions.
- Static-policy rejection.
- Runtime safety margins.
- Solvability requirements.
- Readability requirements.
- Diversity limits.

### 5.8 Normal output requires no Level Editor pass

The editor remains a development and custom-authoring tool. “Open in editor and fix it” is not a valid production-generation step.

---

## 6. Player Experience Contract

### 6.1 Definitions

#### Meaningful decision

A switch encounter is a meaningful decision when at least two legal choices produce different future gameplay in one or more of these dimensions:

- Objective progress.
- Available roads after a state change.
- Required later switch state.
- Travel time or distance.
- Recoverability.
- Failure outcome.
- Number or timing of later decisions.

Choices that immediately rejoin with identical state and cost are equivalent and do not count.

#### Planning decision

A meaningful decision whose best choice depends on information at least two graph transitions away, on a later objective, or on a future state transition.

#### Adaptive decision

A meaningful decision that occurs after the level state has changed and whose correct choice differs from the route that would have been selected in an earlier phase.

Examples:

- A hub must send the dot toward Pickup A on the first visit and Destination C on the second visit.
- A shortcut becomes available only after Checkpoint B.
- An early road becomes unavailable after a package is collected, requiring a new return route.

#### Recoverable mistake

A non-optimal choice that does not immediately end the level and gives the player a later chance to return, reroute, or finish with a worse score.

#### Static routing policy

One permanent selected outgoing edge per switch for the entire attempt. If any static routing policy completes all objectives, the level is `static_policy_solvable`.

#### Greedy local policy

A policy that selects the branch appearing to move closest to the currently highlighted objective without reasoning about later phases or state changes.

### 6.2 Required production behavior

Every generated production level must satisfy all of the following:

- [ ] At least two meaningful decisions.
- [ ] At least one planning decision.
- [ ] At least one adaptive decision.
- [ ] At least one state change after movement begins.
- [ ] Not solvable by a static routing policy.
- [ ] No equivalent branch counted toward difficulty.
- [ ] No required decision depends on invisible information.
- [ ] The optimal route can be explained from visible roads, objective state, and introduced mechanics.

### 6.3 Difficulty target matrix

These are initial locked engineering targets. Human calibration may tune numeric boundaries, but it may not remove the anti-triviality requirements.

| Metric | Easy | Medium | Hard | Expert |
|---|---:|---:|---:|---:|
| Ordered objectives, excluding start | 2–3 | 3–4 | 3–5 | 4–6 |
| Meaningful decisions | 2–3 | 3–5 | 5–7 | 6–10 |
| Planning decisions | ≥1 | ≥2 | ≥3 | ≥4 |
| Adaptive decisions | ≥1 | ≥1 | ≥2 | ≥3 |
| Ordered dependency depth | ≥1 | ≥2 | ≥3 | ≥4 |
| Route-state changes | ≥1 | 1–2 | 2–3 | 3–5 |
| Required switch revisits | 0–1 | 1–2 | 1–3 | 2–4 |
| Recoverable mistake opportunities | ≥1 | ≥1 | ≥2 | ≥2 |
| Fatal wrong choices | 0–1 | ≤2 | ≤2 | ≤3 |
| Successful route classes | 1–2 | 1–3 | 1–4 | 1–5 |
| Unique optimal strategy | Required | Required | Required | Required |
| Static-policy solvable | No | No | No | No |
| Greedy-local policy success | Allowed only in intro subset | ≤35% of target corpus | ≤10% | 0% |
| Minimum safe decision window | 2.25 s | 1.80 s | 1.45 s | 1.20 s |
| Required rapid multi-tap windows | 0 | ≤1 | ≤1 | ≤2 |

### 6.4 Campaign pacing rules

- Easy introduces one stateful idea at a time.
- Medium combines two known ideas.
- Hard creates dependencies across multiple objective phases.
- Expert combines several mechanics but remains visually readable.
- Difficulty comes primarily from reasoning depth, not from shrinking tap windows.
- Adjacent campaign levels cannot repeat the same blueprint archetype, dependency signature, objective pattern, and layout silhouette.

---

## 7. Target Architecture

```text
Generation Request
        |
        v
Campaign Difficulty Plan
        |
        v
Puzzle Experience Target
        |
        v
Puzzle Blueprint Generator
  - objective sequence
  - state changes
  - dependency DAG
  - target strategy profile
        |
        v
Typed Motif Composer / Constraint Search
  - nested branch composition
  - hubs, loops, gates, rejoins
  - objective effects
        |
        v
Exact Structural State-Space Solver
  - optimal and alternate strategies
  - static policy test
  - greedy policy tests
  - failure and recovery analysis
        |
        v
Constructive Phase-Aware Layout
  - route lanes
  - state visibility
  - objective visibility
  - repair
        |
        v
Runtime Timing Search and Jitter Replay
        |
        v
Final Puzzle Analysis and Hard Quality Gates
        |
        v
Candidate Pool
        |
        v
Batch Portfolio Optimizer
        |
        v
Staging Write
        |
        v
Python + Swift + Corpus Verification
        |
        v
Atomic Production Promotion
```

### 7.1 Core data boundaries

The pipeline must use typed stage outputs. No stage should communicate core puzzle data through loosely structured dictionaries.

Required primary models:

- `PuzzleExperienceTarget`
- `PuzzleBlueprint`
- `ObjectiveSpec`
- `StateTransitionSpec`
- `TypedPuzzleMotif`
- `ComposedPuzzleGraph`
- `PuzzleState`
- `StrategySearchResult`
- `PuzzleAnalysis`
- `LayoutPlan`
- `RuntimeTimingPlan`
- `ProductionCandidate`
- `CampaignPortfolio`
- `ProductionRunManifest`

---

## 8. Implementation Rules for Entry-Level Tasks

Every task in this plan must follow these rules.

- One behavior change per pull request when practical.
- Add tests before or with implementation.
- Preserve deterministic seeds.
- Do not update golden seeds simply to hide a regression.
- Use explicit rejection codes.
- Keep Swift and Python field names and behavior documented together.
- Do not infer mechanics from recipe names.
- Do not count declared metadata as proof of gameplay behavior.
- Do not write production output during unit tests.
- Do not use the Level Editor as an automated repair dependency.
- A task is not complete when code compiles; its acceptance checks must pass.

---

# Phase 0 — Lock the Completed V2 Baseline

## Objective

Prove the current V2 repository is healthy, reconcile stale documentation, and create a protected V3 development boundary without redoing completed first-plan work.

## Task 0.1 — Pin and verify the audited baseline

**Files to update or add**

- `scripts/run_all_checks.py`
- `docs/generator_v3/v2_baseline_verification.md`
- `docs/generator_v3/v2_baseline_verification.json`

**Steps**

1. Record the baseline commit SHA and supported toolchain.
2. Run the existing root Python, fixed-seed, editor, production-corpus, and Swift gates using their documented commands.
3. Preserve command lines, output hashes, test totals, corpus totals, and failures.
4. Fail the baseline gate if the exact documented command cannot run from a clean checkout.
5. Do not create replacement test runners for functionality already covered by `run_all_checks.py`.

**Acceptance checks**

- [ ] The existing release-equivalent gate exits zero.
- [x] The baseline report records the exact commit and configuration.
- [x] Any baseline repair is committed separately from V3 behavior.

**2026-07-17 audit result:** The report was added at
`docs/generator_v3/v2_baseline_verification.md`. The release-equivalent gate
did not exit zero, so baseline repair remains a Phase 0 blocker. No baseline
behavior repair is included in AG-001 or AG-002.

## Task 0.2 — Reconcile the first-plan document

**File to update**

- `docs/archive/Tiny_Routes_Generator_and_Level_Designer_Implementation_Plan_V2.md`

**Steps**

1. Map every stale global acceptance row and PR-breakdown row to implemented files/tests.
2. Mark a row complete only when evidence exists.
3. Add a short completion record with the baseline commit and release-gate command.
4. Leave genuinely manual release-signoff rows as reusable unchecked templates.

This is documentation bookkeeping. It must not reopen completed architecture phases.

## Task 0.3 — Freeze a V2 generator behavior baseline

**Files to add**

- `Tools/LevelGenerator/tests/fixtures/v2_generator_baseline/`
- `Tools/LevelGenerator/docs/v2_generator_limitations.md`

Capture:

- Representative outputs from each production recipe family.
- Structural and behavioral signatures.
- Decision profiles.
- Rejection-code distributions.
- Full-pipeline success rates by difficulty.
- Known duplicate and mislabeled families.
- Known one-tap, static-policy, and simple-chain examples.

The baseline exists to prove V3 improvement and prevent accidental loss of working V2 compatibility. It is not a golden target for puzzle quality.

**2026-07-17 completion record:** Added the production-path capture service and
command, checked-in per-difficulty and per-family evidence under
`Tools/LevelGenerator/tests/fixtures/v2_generator_baseline/`, adversarial one-tap
and static-policy fixtures, and the V2 limitations guide.

## Task 0.4 — Add the V3 feature boundary

**Files to update**

- `GenerationConfig`
- CLI arguments
- GUI configuration
- Generator report schema

Add explicit modes:

- `v2_legacy` — compatibility and comparison only.
- `production_v3` — final blueprint/composition pipeline.

Rules:

- V3 code must not silently fall back to V2 recipes or templates.
- V2 and V3 reports identify their architecture version.
- Schema version and generator architecture version remain separate fields.
- V3 can run in dry-run/staging mode before it becomes the default.

**2026-07-17 completion record:** `GenerationConfig`, CLI, GUI, and reports now
carry `v2_legacy` or `production_v3`. The V3 selection stops at the explicit
unavailable boundary and never enters `BatchOrchestrationService`, so no V2
recipe/template fallback is possible.

## Task 0.5 — Add a real production-path baseline suite

The current fixed-seed fixture suite may use direct templates for hard, expert, and mixed campaigns. Add a separate baseline suite that invokes `LevelGenerationService.generate()` through `BatchOrchestrationService` with the same configuration path used by CLI and GUI.

Record, without relaxing gates:

- Requested versus accepted count.
- Attempts and generation errors.
- Strategic rejections.
- Layout/timing rejections.
- Total runtime.
- Whether the full batch completed.

It is acceptable for this V2 limitation suite to fail generation. Its purpose is to preserve evidence of the exact problem V3 must solve.

**2026-07-17 completion record:** The checked-in baseline invokes
`LevelGenerationService.generate()` through `BatchOrchestrationService` for all
five difficulty bands and records incomplete medium, hard, and expert runs as
evidence rather than bypassing them with templates.

## Phase 0 exit gate

- [ ] The completed V2 release gate passes from a clean checkout.
- [x] The first-plan document accurately reflects implementation status.
- [x] V2 behavior and limitations are frozen with reproducible evidence.
- [x] V3 work is isolated behind an explicit mode with no fallback.
- [x] A full-pipeline baseline exists that does not use template shortcuts.

---

# Phase 1 — Generalize Package State into Ordered Objective State

## Objective

Extend the completed schema-2 package-state implementation into the minimal schema-3 state model required for A → B → C → additional-point puzzles while preserving every existing level and parity fixture.

## Task 1.1 — Define shared ordered-objective models

**Files to add or update**

- `Tools/TinyRoutesCore/tiny_routes_core/models/route_objective.py`
- Existing shared `LevelDocument` model
- Swift domain equivalents

**Required objective fields**

- `id`
- `nodeID`
- `kind`
- `sequenceIndex`
- `revealPolicy`
- Optional display metadata
- Unknown-field preservation in Python tools

**Initial objective kinds**

- `pickup`
- `checkpoint`
- `delivery`
- `destination`

**Acceptance checks**

- [ ] Objective IDs are unique.
- [ ] Sequence indices are contiguous.
- [ ] Referenced nodes exist.
- [ ] Exactly one final terminal objective exists.
- [ ] Swift and Python round trips preserve known and unknown fields.

## Task 1.2 — Add schema-3 decoding and V1/V2 adapters

**Files to update**

- Existing Swift level document decoder/encoder
- Shared Python `LevelDocument`
- Editor repositories/models
- Generator output builder
- JSON schema documentation

**Rules**

1. Schema 1 and 2 decode exactly as before.
2. A legacy package and destination adapt to an internal two-objective sequence.
3. Schema-2 package-state edge availability adapts to objective-state rules.
4. Schema 3 writes `objectives` and structured edge conditions as source of truth.
5. Conflicting legacy and schema-3 fields fail validation.
6. Existing schema-2 files round-trip without forced rewriting unless migration is explicitly requested.

## Task 1.3 — Generalize road availability without replacing V2 behavior

**Files to add or update**

- Shared `EdgeAvailabilityRule` model
- Existing Swift and Python `RouteEdge`
- Runtime graph helpers
- Editor edge inspector

**Minimum structured fields**

- `requiredCompletedObjectiveIDs`
- `forbiddenCompletedObjectiveIDs`
- Optional `minimumObjectiveIndex`
- Optional `maximumObjectiveIndex`
- Optional `usageLimit`

Use a small typed model. Do not add arbitrary expressions or embedded scripts.

**Acceptance checks**

- [ ] Every `always`, `beforePackage`, and `afterPackage` fixture behaves identically after adaptation.
- [ ] An objective can unlock a shortcut.
- [ ] An objective can close an earlier route.
- [ ] A one-use edge is deterministic and traceable.
- [ ] Conditions never strand the dot on the edge it is already traversing.

## Task 1.4 — Extend Swift objective progression

Extend the existing `RouteEngine`; do not create a second gameplay engine.

**Steps**

1. Track active objective index and completed-objective state.
2. Complete only the active objective when its node is reached.
3. Define deterministic behavior for visiting a future objective early.
4. Advance, reveal, and complete objectives through normalized events.
5. Reevaluate edge availability and normalize switches at the same event boundary currently used for package collection.
6. Complete the level only after the terminal objective.
7. Restore all objective and usage state on restart.

## Task 1.5 — Extend Python parity behavior

Update the existing shared graph helpers, runtime state, simulator, traces, and solution replay to implement exactly the same objective event ordering and switch normalization as Swift.

Do not place objective progression only inside generator-specific code.

## Task 1.6 — Generalize state-aware switch selection

Reuse the current package-state filtering and authored-order normalization rules.

**Steps**

1. Filter outgoing edges by objective state and usage state.
2. Preserve the selected authored edge when it remains usable.
3. Otherwise select the first usable edge in authored order.
4. Emit a normalized switch-state-change trace event.
5. Reject taps that target unavailable edges.
6. Validate every relevant state boundary for unintended nonterminal dead ends.

## Task 1.7 — Add objective and state-change visuals

**Requirements**

- Current objective is visually dominant.
- Future revealed objectives are visually distinct.
- Locked roads remain visible as locked rather than disappearing.
- Unlocking, closing, and one-use consumption have short readable transitions.
- A state change becomes understandable before the next required decision window.
- Accessibility labels expose objective order and road state.

## Task 1.8 — Extend editor support and parity fixtures

**Editor features**

- Reorder objectives.
- Assign objective nodes and kinds.
- Configure structured edge rules.
- Show active/completed objectives during playtest.
- Show available, locked, closed, and consumed roads.
- Validate objective references, rule references, and state-specific dead ends.

**Required shared fixtures**

- Three ordered checkpoints.
- Schema-2 package gate adapted to V3 state.
- Shortcut unlock.
- Road closes after pickup.
- Hub revisit with changed exits.
- One-use recoverable detour.
- Out-of-order objective visit.
- Restart after partial objective completion.

**Trace fields**

- Time.
- Current node/edge.
- Active objective index.
- Completed objective IDs.
- Available and consumed edge IDs.
- Active switch edge IDs.
- Tap result.
- Outcome.

## Phase 1 exit gate

- [ ] Schema 3 round-trips in Swift, shared Python, generator, and editor.
- [ ] Every existing schema-1/2 parity fixture remains unchanged in outcome.
- [ ] A multi-stop fixture replays identically in Swift and Python.
- [ ] Objective-state road changes are deterministic, visible, and safe.
- [ ] Existing production levels remain valid without migration.

---

# Phase 2 — Define the Puzzle Blueprint and Complete State Model

## Objective

Generate an intended player experience before creating graph nodes and roads.

## Task 2.1 — Add `PuzzleExperienceTarget`

**File to add**

- `app/models/puzzle_experience_target.py`

**Fields**

- Difficulty.
- Objective count range.
- Meaningful decision range.
- Planning decision minimum.
- Adaptive decision minimum.
- Dependency-depth range.
- State-change range.
- Revisit range.
- Successful-route-class range.
- Recoverable mistake range.
- Fatal mistake cap.
- Decision-window targets.
- Allowed mechanic categories.
- Layout complexity target.
- Desired solve-time range.

## Task 2.2 — Add `PuzzleBlueprint`

**File to add**

- `app/models/puzzle_blueprint.py`

A blueprint describes intent without final node coordinates.

**Required content**

- Objective phases.
- Phase entry and exit roles.
- Decision IDs.
- Dependencies between decisions.
- Required revisits.
- State transitions.
- Allowed successful strategy count.
- Optimal-route requirements.
- Failure/recovery targets.
- Required and forbidden mechanic combinations.

## Task 2.3 — Add a decision-dependency DAG

**File to add**

- `app/models/decision_dependency_graph.py`

**Rules**

- A decision can depend on objective state.
- A decision can depend on an earlier switch choice.
- A revisit can require a different outgoing edge.
- Dependency cycles are allowed only when represented as explicit repeated phases, not as an invalid DAG cycle.

**Acceptance checks**

- [ ] The graph calculates dependency depth.
- [ ] It identifies independent decisions.
- [ ] It validates that every required dependency can be realized.

## Task 2.4 — Define the complete solver state

**File to add**

- `app/models/puzzle_state.py`

**State fields**

- Current node or edge position.
- Objective index.
- Completed objective IDs.
- Available edge state.
- One-use edge state.
- Active outgoing edge per switch.
- Visit count per relevant node.
- Accepted tap count.
- Elapsed time for runtime search.
- Terminal outcome.

Use compact immutable/hashable representations for search.

## Task 2.5 — Add a blueprint generator

**File to add**

- `app/services/puzzle_blueprint_service.py`

**Steps**

1. Resolve a difficulty target.
2. Select a challenge archetype.
3. Select objective count.
4. Build objective phases.
5. Build dependency structure.
6. Allocate recovery and failure outcomes.
7. Allocate state changes.
8. Validate the blueprint before topology work.

## Task 2.6 — Add initial challenge archetypes

**Required archetypes**

1. **Return to hub:** visit a central switch in multiple phases with a different correct exit.
2. **Unlock the shortcut:** take a longer route first; an objective opens a faster later route.
3. **Closed return:** the outbound route closes after pickup; choose a different return path.
4. **Ordered checkpoint chain:** several visible points must be visited in order.
5. **Split commitment:** an early choice determines which later rejoin is useful.
6. **Recoverable wrong loop:** a wrong branch returns to a previous decision at a cost.
7. **Destination decoy:** a tempting destination route fails before required objectives are complete.
8. **Multi-hub relay:** route through two hubs whose correct exits change by phase.
9. **Ring phase reversal:** use different portions of a ring before and after a state change.
10. **Competing successful routes:** multiple completions exist, but only one meets optimal taps/time.

## Phase 2 exit gate

- [ ] Blueprints are deterministic from seed.
- [ ] Every blueprint satisfies its target ranges before graph generation.
- [ ] Blueprint reports explain the intended player reasoning.
- [ ] No blueprint is merely a list of independent binary switches.

---

# Phase 3 — Upgrade Existing Motifs into Typed Stateful Motifs

## Objective

Build on the existing `PuzzleMotif`, `MotifRegistry`, and package-state seed motifs. Add typed ports, explicit preconditions/effects, and objective-state contracts so motifs can realize blueprint dependencies instead of being appended as serial fragments.

## Task 3.1 — Add typed ports to the existing motif model

**Files to add or update**

- Existing `app/models/puzzle_motif.py`
- `app/models/motif_port.py`
- Existing `app/motifs/base_motif.py`

**Port types**

- Main-route entry.
- Main-route exit.
- Branch insertion point.
- Rejoin input.
- Return-path input/output.
- Objective attachment.
- State-change attachment.
- Failure exit.
- Recovery exit.

Compatibility rules must be validated before graph mutation.

**2026-07-19 completion record:** Added the typed `MotifPort` model and all
required port roles, integrated typed main-route resolution and validation into
`PuzzleMotif` and `MotifComposerService`, and migrated `straight_segment` while
preserving legacy connector compatibility.

## Task 3.2 — Add explicit motif preconditions and effects

Each motif declares machine-readable:

- Allowed objective phase/index range.
- Required incoming objective state.
- Objective or edge-state changes created.
- Decisions created.
- Expected downstream dependency.
- Cycle, revisit, rejoin, failure, and recovery effects.
- Minimum layout footprint.
- Incompatible effects and composition limits.

Tags and prose remain documentation only.

**2026-07-19 completion record:** Added validated, machine-readable motif
precondition, edge-state-change, dependency, structural-effect, layout, and
composition-limit contracts. Migrated all four package-state motifs with typed
objective/state/return ports and contracts verified against their actual
conditional roads and legacy topology flags.

## Task 3.3 — Migrate the completed V2 motif catalog first

Convert and contract-test these existing assets before adding replacements:

- `straight_segment`
- `single_binary_choice`
- `dead_end_decoy`
- `recoverable_detour`
- `split_and_rejoin`
- `package_branch`
- `return_loop`
- `revisited_switch`
- `ring_route`
- `three_way_hub`
- `four_way_hub`
- `road_opens_after_package`
- `shortcut_closes_after_package`
- `return_route_changes_after_package`
- `package_state_revisited_switch`

The four package-state motifs become the first objective-state migration fixtures. Do not rewrite them from scratch unless their contract cannot be represented safely.

**2026-07-19 AG-033 completion record:** Converted `split_and_rejoin` into a typed,
explicitly structural motif with split/rejoin insertion ports and detected
topology evidence. It deliberately declares no gameplay decision effect because
its equal branches do not yet create distinct future consequences.

## Task 3.4 — Separate structural and gameplay effects

**Structural operations** shape the graph:

- Segment and bend.
- Split and rejoin.
- Hub and ring.
- Return corridor.
- Cross-phase connector.
- Lane/readability expansion.

**Gameplay effects** create reasoning:

- Objective gate.
- Unlock shortcut.
- Close-behind route.
- Required hub revisit.
- State-dependent branch.
- Destination decoy.
- Recoverable loop.
- Delayed consequence.
- Alternative successful detour.
- One-use connector.

A production motif may combine both, but the report and contract must distinguish them.

**2026-07-19 AG-034 completion record:** Motif contracts now classify structural and
gameplay effects separately. Added `objective_gate`, whose bypass and objective
branches visibly rejoin at a downstream gate; objective completion closes the
failure road and opens the successful road.

## Task 3.5 — Complete the minimum production motif catalog

After migrating the existing catalog, add behavior-distinct coverage for:

- [x] Binary split with later consequences.
- [x] Three-way hub with three distinct outcomes.
- [x] Four-way hub with four distinct outcomes.
- [x] Split/rejoin with unequal route costs.
- [x] Objective-gated branch.
- [x] Objective-unlocked shortcut.
- [x] Objective-closed return road.
- [x] Hub revisit with changed desired exit.
- [x] Switch revisit with changed desired state.
- [x] Recoverable loop.
- [x] Phase-dependent ring exits.
- [x] Destination-before-objectives decoy.
- [x] Nonfatal detour.
- [x] One-use connector.
- [x] Two-phase route reversal.
- [x] Three-phase relay.
- [x] Parallel successful routes with a unique optimum.
- [x] Branch with delayed downstream consequence.
- [x] Objective branch that changes later availability.
- [x] Readability spacer/lane expansion.

**2026-07-19 Task 3.5 completion record:** The evidence-backed production catalog
now contains 22 behavior-distinct typed motifs and covers all 20 required
capabilities. New stateful assets include real objective-opened and
objective-closed roads, a traversal-consumed one-use edge, changed hub and
switch revisits, phase-dependent ring exits, a three-objective relay, and
parallel successful routes with unequal cost.

A migrated V2 motif counts toward this catalog only after it passes the V3 typed contract and produces distinct behavior.

## Task 3.6 — Add motif contract and evidence tests

Every motif test proves:

- IDs and ports are valid.
- Declared topology matches detected topology.
- Preconditions are satisfiable.
- Declared state effects occur.
- Intended decisions are meaningful.
- Required dependencies are detected by exact analysis.
- Primary, alternate, failure, and recovery exits are explicit.
- Difficulty restrictions and composition limits are enforced.

Mechanic names and tags can never satisfy these checks.

**2026-07-19 Task 3.6 completion record:** Added exact graph-derived motif evidence
for topology, meaningful branch outcomes, objective-state transitions,
dependency kinds, typed exits, difficulty/precondition constraints, composition
limits, and ID-independent behavior signatures. Contract tests prove misleading
names, tags, prose, equal branches, and unsupported effect declarations cannot
satisfy production catalog checks.

## Phase 3 exit gate

- [x] Every existing seed motif is migrated, quarantined, or explicitly deprecated.
- [x] At least 20 behavior-distinct production motifs pass typed contracts.
- [x] Objective-state effects are represented directly.
- [x] Every production motif can participate in typed, nonserial composition.
- [x] No motif is accepted because of its name or metadata tags alone.

---

# Phase 4 — Audit and Quarantine Legacy Recipe Families

## Objective

Stop fixed recipes from overstating production capability. Preserve only useful fixtures; do not spend time repairing every obsolete family when quarantine is safer.

## Task 4.1 — Add automated topology and behavior contracts

For every named recipe, detect and compare its claimed behavior:

- Ring.
- Return loop/cycle.
- Rejoin.
- Revisit.
- Route reversal.
- Objective/package gate.
- High-arity switch.
- Recoverable route.
- Unique-success or unique-optimal requirement.

The audit emits a stable status and reason for every family and variant.

## Task 4.2 — Quarantine confirmed mismatches immediately

At minimum audit:

- `return_loop_intro`
- `ring_route_gate`
- `branch_then_rejoin_with_wrong_order`
- `return_loop_with_gate`
- `multi_switch_revisit`
- `multi_four_way_route`
- `late_route_reversal`
- Every primary/alternate pair affected by `_swap_dead_end_order()`

A mismatched family becomes `fixture_only` or `deprecated` before any optional repair. It cannot participate in production selection while the audit fails.

## Task 4.3 — Add graph and behavior isomorphism detection

**Files to add**

- `app/services/graph_isomorphism_service.py`
- `app/services/behavior_signature_service.py`

Canonical comparison must respect:

- Node roles.
- Objective phases.
- Switch degree and authored order.
- Edge availability/effects.
- Failure and recovery outcomes.
- Strategy equivalence classes.
- Optimal strategy and cost vector.

ID renaming, metadata changes, and layout mirroring do not create new behavior.

## Task 4.4 — Require real alternate variants

An alternate variant must differ in at least one:

- Graph topology.
- Objective-state transition.
- Decision dependency graph.
- Optimal strategy.
- Failure/recovery structure.

Fix `_swap_dead_end_order()` only if alternate edge order creates different runtime behavior and passes the behavior-signature test. Otherwise remove the alternate variant.

## Task 4.5 — Repair only valuable fixtures

Repair or rename a legacy recipe only when it is needed for:

- A tutorial fixture.
- A parity fixture.
- A motif contract fixture.
- A regression reproducer.

Do not make fixed recipes a prerequisite for V3 production generation.

## Task 4.6 — Add registry lifecycle status

Statuses:

- `production_v3`
- `fixture_only`
- `deprecated`

The V3 composer reads only typed motifs and blueprint archetypes. Fixed recipe families are never selected as a hidden production fallback.

## Phase 4 exit gate

- [ ] Every legacy recipe and variant has an audited status.
- [ ] No mislabeled or behavior-isomorphic recipe is production eligible.
- [ ] No-op alternate variants are removed or made behaviorally real.
- [ ] V3 generation has no dependency on fixed recipe families.

---

# Phase 5 — Build the Constraint-Based Puzzle Composer

## Objective

Convert a blueprint into many genuinely different graphs through typed, nested, state-aware composition.

## Task 5.1 — Add a composition search state

**File to add**

- `app/models/composition_state.py`

Track:

- Unfulfilled blueprint decisions.
- Open typed ports.
- Objective phase boundaries.
- Current graph.
- State effects already assigned.
- Current node/switch counts.
- Current cycle/rejoin counts.
- Estimated layout footprint.
- Partial strategic metrics.

## Task 5.2 — Implement nested motif insertion

**File to add**

- `app/services/puzzle_composer_service.py`

Support:

- Insert a motif into an existing edge.
- Expand a branch with additional decisions.
- Attach a rejoin to two branches.
- Connect a later phase back to an earlier hub.
- Place an objective inside a loop or branch.
- Add a state-dependent shortcut across phases.
- Replace a simple decision with a hub.

Do not limit composition to “append motif A, then motif B.”

## Task 5.3 — Use deterministic backtracking

When a chosen motif cannot satisfy remaining constraints:

1. Undo the placement.
2. Try another compatible motif.
3. Try another port.
4. Try another blueprint realization.
5. Stop only at a declared composition budget.

Record all rejection reasons and branch counts.

## Task 5.4 — Satisfy strategic constraints during composition

Prune partial graphs when they cannot still reach:

- Meaningful-decision minimum.
- Adaptive-decision minimum.
- Required dependency depth.
- Revisit count.
- Objective count.
- Recovery count.
- Switch-degree bounds.
- Layout footprint bounds.

**2026-07-19 AG-059 completion record:** Added blueprint-scoped partial
strategic feasibility assessment for meaningful and adaptive decisions,
dependency depth, revisits, objectives, recovery, switch count/degree, and
layout footprint. Deterministic backtracking now prunes impossible successors
before expansion and records every stable pruning reason in search evidence.

## Task 5.5 — Add composition transformations

After a valid graph is built, produce true variants through controlled transformations:

- Exchange which phase uses a hub exit.
- Move an objective to a different compatible branch.
- Reverse a ring’s phase order.
- Convert a fatal branch into a recoverable detour.
- Change which objective unlocks a shortcut.
- Swap branch costs while preserving the optimal proof target.
- Insert or remove a non-strategic readability segment.

Every transformation must re-run the solver.

**2026-07-19 AG-060 completion record:** Added typed, deterministic
transformations for phase-specific hub exits, objective branch placement, ring
phase order, fatal-to-recoverable branches, shortcut triggers, branch-cost
choice, and readability segment insertion/removal. A transformed state is
returned only after a fresh injected solver proof accepts it; rejected proofs
remain explicit results with no accepted graph.

## Task 5.6 — Add composition diversity constraints

Within one candidate pool:

- Cap repeated blueprint archetypes.
- Cap repeated motif multisets.
- Cap repeated dependency DAGs.
- Reject behavior-isomorphic graphs immediately.

## Task 5.7 — Remove production dependence on `MotifComposerService` serial selection

Migrate callers to `PuzzleComposerService`. Keep the old service only for fixture compatibility until deprecation.

## Phase 5 exit gate

- [ ] The same blueprint can produce multiple non-isomorphic valid graphs.
- [ ] The same difficulty can produce multiple blueprint archetypes.
- [ ] Hard and expert graphs are not serial chains with decorative branches.
- [ ] Partial composition pruning is deterministic and reported.

---

# Phase 6 — Implement Exact Structural Strategy Search

## Objective

Extend and ultimately supersede the current one-package `AbstractPuzzleSolverService` for V3 candidates. Keep the V2 solver unchanged for compatibility fixtures while the new proof engine is validated.

Prove what the player can do in the complete stateful puzzle, not merely whether one authored path exists.

## Task 6.1 — Add a canonical state transition engine

**File to add**

- `app/services/puzzle_state_transition_service.py`

This service applies one structural decision without runtime timestamps.

It must handle:

- Switch selection/rotation.
- Movement to the next decision or objective.
- Objective completion.
- Road availability changes.
- One-use roads.
- Switch persistence.
- Revisits.
- Completion and failure.

## Task 6.2 — Add a weighted optimal-strategy solver

**File to add**

- `app/services/strategy_search_service.py`

Use Dijkstra or A* over canonical states.

Return:

- Optimal cost.
- Canonical optimal strategy.
- All equal-cost optimal strategy classes up to proof completion.
- Near-optimal strategies within configured margins.
- Longer successful strategy classes.
- Failure outcomes.
- Explored-state count.
- Exhaustiveness status.

## Task 6.3 — Define strategy equivalence

Two action traces are equivalent when differences do not alter:

- Chosen outgoing roads at meaningful decisions.
- Objective sequence.
- State transitions.
- Success cost.

Differences in no-op taps, harmless timing jitter, or pass-through nodes must not inflate route counts.

## Task 6.4 — Prove unique optimal strategy

Reject when:

- No successful strategy exists.
- Search limits prevent proof.
- Multiple non-equivalent strategies have equal optimal gameplay cost and the blueprint did not permit that.
- The optimal strategy violates target decisions or state transitions.

## Task 6.5 — Add static-policy solver

**File to add**

- `app/services/static_policy_solver_service.py`

Enumerate or intelligently search permanent switch assignments.

A production candidate is rejected if any permanent assignment completes all objectives.

This is the primary automated gate against “tap every arrow once and then watch.”

## Task 6.6 — Add alternate route and recovery analysis

For every non-optimal meaningful choice, classify:

- Immediate dead end.
- Destination/objective order failure.
- Recoverable detour.
- Successful but slower route.
- Successful but higher-tap route.
- Loop until time expires.
- State trap.

## Task 6.7 — Replace shallow route enumeration

Migrate decision profiling away from `DecisionProfileService._enumerate_routes()` as the source of truth. The old profile may remain as a compatibility view built from exact `PuzzleAnalysis`.

## Task 6.8 — Add proof budgets and hard failure behavior

- Easy/medium state spaces must normally be exhaustively solved.
- Hard/expert may use larger bounded searches, but a production candidate cannot pass when optimal uniqueness or static-policy rejection remains unproven.
- Search-limit failures trigger a new candidate, not a relaxed proof requirement.

## Phase 6 exit gate

- [ ] Optimal strategy is proven for every accepted candidate.
- [ ] Static-policy-solvable candidates are rejected.
- [ ] Successful alternatives and recoverable mistakes are classified.
- [ ] Search-limit uncertainty cannot pass production gates.

---

# Phase 7 — Add Player-Policy Agents and Anti-Boring Analysis

## Objective

Measure whether a level requires reasoning beyond local arrow tapping.

## Task 7.1 — Add baseline player agents

**Files to add**

- `app/agents/random_agent.py`
- `app/agents/static_policy_agent.py`
- `app/agents/greedy_objective_agent.py`
- `app/agents/one_step_lookahead_agent.py`
- `app/agents/two_step_planning_agent.py`
- `app/agents/optimal_agent.py`

All agents consume the same visible state the player receives.

## Task 7.2 — Add policy evaluation service

**File to add**

- `app/services/policy_evaluation_service.py`

Measure:

- Success rate.
- Average taps.
- Average completion time.
- Failure types.
- Regret relative to optimum.
- Decisions where the agent diverges from the optimal strategy.

## Task 7.3 — Add planning-horizon classification

For every optimal decision, determine the minimum information horizon needed to prefer it:

- Immediate edge only.
- One transition.
- Two transitions.
- Objective-state knowledge.
- Cross-phase knowledge.

## Task 7.4 — Add local-obviousness analysis

Reject candidates when all optimal decisions are obvious from:

- Euclidean closeness to current objective.
- The only non-dead-end road.
- The only road not pointing backward.
- The first outgoing edge.
- A simple fixed direction rule.

## Task 7.5 — Add adaptive requirement analysis

Prove at least one decision:

- Occurs after an objective state change.
- Requires a different route than an earlier phase.
- Cannot be predetermined as a permanent switch assignment.

## Task 7.6 — Add agent-separation difficulty gates

Initial targets:

- Easy: optimal and one-step agents pass; greedy may pass only in designated introductions.
- Medium: optimal passes; greedy succeeds on no more than 35% of the calibrated corpus.
- Hard: one-step agent performs materially worse than two-step planner.
- Expert: optimal planning is required; greedy and one-step agents fail.

Use deterministic policy simulations, not random pass/fail in release tests.

## Phase 7 exit gate

- [ ] Every accepted candidate has a policy evaluation report.
- [ ] Production candidates are not solvable by static policy.
- [ ] Medium+ candidates show measurable separation from greedy local behavior.

---

# Phase 8 — Replace Quality Scoring with Hard Strategic Gates and Calibrated Ranking

## Objective

Separate non-negotiable gameplay validity from preference-based candidate ranking.

## Task 8.1 — Add `PuzzleAnalysis`

**File to add**

- `app/models/puzzle_analysis.py`

Include raw values for:

- Meaningful decisions.
- Planning decisions.
- Adaptive decisions.
- Dependency depth.
- Independent-decision ratio.
- Static-policy result.
- Agent results.
- Objective phases.
- State changes.
- Revisits.
- Successful strategy classes.
- Optimal uniqueness.
- Recovery/failure distribution.
- Equivalent/no-op choices.
- Route distance and timing costs.
- Visual complexity.

## Task 8.2 — Add hard rejection gates

**File to add**

- `app/services/production_puzzle_gate_service.py`

Mandatory rejection codes include:

- `production_one_tap_level`
- `insufficient_meaningful_decisions`
- `insufficient_planning_decisions`
- `insufficient_adaptive_decisions`
- `static_policy_solution_exists`
- `greedy_policy_too_successful`
- `equivalent_choice_present`
- `unique_optimal_not_proven`
- `objective_sequence_trivial`
- `state_change_without_player_consequence`
- `all_failures_are_instant_dead_ends`
- `unreadable_state_change`
- `runtime_solution_not_robust`

## Task 8.3 — Redesign candidate ranking

Only candidates that pass all hard gates receive a preference score.

Ranking dimensions:

- Strategic fit.
- Difficulty fit.
- Route-choice richness.
- Recovery quality.
- Visual readability.
- Runtime fairness.
- Novelty.
- Campaign pacing fit.

A high total score can never compensate for a failed hard gate.

## Task 8.4 — Derive par and time limits from solution distributions

- `parTaps` comes from the optimal accepted-tap cost.
- Time limit comes from optimal travel time plus difficulty-specific planning and input allowance.
- Optional star thresholds may use optimal and near-optimal distributions.
- Reject levels where the nominal time limit leaves no safe planning margin.

## Task 8.5 — Report human-readable reasoning

Reports should state, for example:

> “On phase 1, the player must route to Checkpoint B through the west hub. Completing B closes the outbound road and unlocks the south return. On the hub’s second visit, the correct exit changes from west to south. A permanent switch assignment cannot complete the level.”

This explanation must be derived from analysis, not authored metadata.

## Phase 8 exit gate

- [ ] No score can hide an anti-triviality failure.
- [ ] Par and time limits are derived from proven strategies.
- [ ] Reports explain why the level is a puzzle.

---

# Phase 9 — Build Runtime Timing for Thinking, Not Tap Spam

## Objective

Extend the existing `RuntimeSolutionSearchService`, live-lookahead eligibility logic, and timing metrics. Do not create a separate timing simulator.

Turn a valid strategic puzzle into a fair moving-dot experience.

## Task 9.1 — Make runtime timing search state-aware

Update runtime solution search to account for:

- Objective changes.
- Road availability changes.
- Revisited switches.
- Switch normalization.
- One-use roads.
- Multiple objective markers.

## Task 9.2 — Search timing choices, not only earliest legal taps

Generate candidate action schedules around:

- Early safe timing.
- Mid-window timing.
- Late safe timing.

Select a canonical schedule with robust margins rather than always using one fixed offset.

## Task 9.3 — Add jitter robustness simulation

Replay the solution under deterministic timing perturbations such as:

- ±50 ms.
- ±100 ms.
- Configured frame-step variations.
- Slight speed integration variation within runtime tolerance.

Reject a candidate whose solution fails within the required robustness envelope.

## Task 9.4 — Limit rapid cycling requirements

A multi-exit switch must not become difficult only because the player must tap rapidly several times.

Rules:

- Easy requires no rapid multi-tap window.
- Medium allows at most one deliberate multi-tap encounter.
- Hard/expert cap multi-tap encounters and preserve safety margin.
- Prefer outgoing-edge ordering that keeps commonly required selections within one tap.
- Count reasoning decisions separately from raw tap count.

## Task 9.5 — Add pre-decision readability time

Ensure the player can visually identify:

- Current objective.
- Active upcoming switch.
- Locked/unlocked roads.
- The consequence of the most recent objective.

before the next required input window opens.

## Task 9.6 — Add timing rejection codes

- `decision_window_below_target`
- `state_change_not_visible_before_decision`
- `required_tap_burst_exceeds_target`
- `solution_jitter_failure`
- `insufficient_inter_decision_thinking_time`

## Phase 9 exit gate

- [ ] Every accepted runtime solution survives jitter tests.
- [ ] Difficulty is driven by route reasoning more than input speed.
- [ ] State changes are visible before they affect a required decision.

---

# Phase 10 — Construct Phase-Aware Readable Layouts

## Objective

Extend the completed constructive `GraphLayoutPlannerService`, deterministic repair service, road-shape assignment, and visual-clarity validators with objective-phase overlays and stateful-hub constraints.

Make stateful route choices understandable on a portrait mobile screen without making the optimal path visually obvious.

## Task 10.1 — Add phase-aware layout metadata

**Files to update**

- Layout graph/model services

Track:

- Objective phase for each node/edge.
- Revisited hubs.
- Unlock/lock relationships.
- Primary and alternate strategy corridors.
- Failure and recovery corridors.

## Task 10.2 — Reserve visual space for stateful hubs

A hub visited in multiple phases must have:

- Clear outgoing separation.
- Space for locked-road indicators.
- A visible return approach.
- No overlapping objective marker.
- Camera framing that lets the player understand the second visit.

## Task 10.3 — Lay out objective progression clearly

- Current and future objectives must not overlap.
- Objective sequence should be readable from the preview without drawing a literal answer line.
- Multi-stop levels may use a larger portrait profile automatically.
- The full-level preview must show all revealed route options at readable scale.

## Task 10.4 — Make alternate routes believable

Reject layouts where:

- The optimal route is always the straightest obvious road.
- Wrong branches look like tiny decorative stubs.
- A recoverable route is visually indistinguishable from a dead end.
- Locked roads resemble broken geometry.
- Branch cost differences are impossible to perceive where perception is intended.

## Task 10.5 — Add state-overlay validation

Render or model both pre- and post-objective states and validate:

- Road lock icons.
- Objective markers.
- Active switch indicators.
- Route crossings.
- Camera bounds.
- Node clearance.

A layout passing only its initial state is insufficient.

## Task 10.6 — Add phase-aware repair operations

- Move a stateful hub.
- Widen a return lane.
- Relocate an objective marker.
- Move a lock indicator away from a crossing.
- Swap branch lanes.
- Expand vertical spacing between phases.
- Change bend order without changing logic.

## Task 10.7 — Add visual-state snapshots to debug output

For rejected or selected candidates, optionally output previews for:

- Initial state.
- Each objective completion state.
- Final route overlay.
- Optimal versus alternate route overlay.

## Phase 10 exit gate

- [ ] Every objective phase passes readability validation.
- [ ] Alternate choices look intentional.
- [ ] Stateful hubs remain readable on revisit.
- [ ] Layout repair never changes puzzle behavior.

---

# Phase 11 — Rebuild the Candidate Pipeline Around Blueprints

## Objective

Use the existing `LevelGenerationService` façade, `BatchOrchestrationService`, repositories, reports, and rejection-code infrastructure. Replace only the V3 candidate-construction path behind the architecture mode boundary.

Create a stage pipeline that constructs quality early and reports every rejection precisely.

## Task 11.1 — Add typed pipeline stage results

**Files to add**

- `app/models/blueprint_stage_result.py`
- `app/models/composition_stage_result.py`
- `app/models/strategy_stage_result.py`
- `app/models/layout_stage_result.py`
- `app/models/runtime_stage_result.py`
- `app/models/quality_stage_result.py`

## Task 11.2 — Implement the final candidate stage order

1. Resolve campaign target.
2. Generate puzzle blueprint.
3. Validate blueprint.
4. Compose graph.
5. Validate graph contracts.
6. Run exact structural strategy search.
7. Run static and heuristic policy agents.
8. Apply strategic hard gates.
9. Construct and repair layout.
10. Build final level document.
11. Run runtime timing search.
12. Run jitter and parity-ready replay.
13. Analyze final stateful puzzle.
14. Apply final hard gates.
15. Rank valid candidate.
16. Add it to the candidate pool.

## Task 11.3 — Add adaptive search breadth

When candidate yield is low, automatically increase:

- Number of blueprints.
- Composition alternatives per blueprint.
- Layout variants.
- Road-shape variants.
- Candidate pool size.
- Attempt budget for the affected difficulty/archetype.

Never reduce hard quality gates.

## Task 11.4 — Add rejection feedback to blueprint planning

If a batch repeatedly fails because of one cause:

- Avoid the failing motif combination.
- Request a larger layout profile.
- Select a different archetype.
- Reduce state-space size without reducing decision quality.
- Adjust outgoing-edge ordering for timing.

Record every automatic adjustment.

## Task 11.5 — Decompose `LevelGenerationService`

The façade should orchestrate focused services rather than contain stage logic.

Target services:

- `CampaignPlanService`
- `PuzzleBlueprintService`
- `PuzzleComposerService`
- `StrategySearchService`
- `PolicyEvaluationService`
- `ProductionPuzzleGateService`
- `PhaseAwareLayoutService`
- `RuntimeTimingService`
- `CandidatePoolService`
- `CampaignPortfolioService`
- `TransactionalPromotionService`

## Task 11.6 — Add stage budgets and metrics

Report:

- Blueprints attempted.
- Compositions attempted.
- Strategic passes.
- Layout passes.
- Runtime passes.
- Final candidates.
- Time by stage.
- Dominant rejection codes.
- Automatic search adjustments.

## Phase 11 exit gate

- [ ] Strategically weak graphs never consume layout/runtime work.
- [ ] Search breadth adapts without lowering quality.
- [ ] Every failure has a stage and stable code.

---

# Phase 12 — Select Diverse Full Campaigns, Not Independent Levels

## Objective

Upgrade the existing `CandidatePortfolioSelectionService` and candidate signatures rather than introducing a second selector. Selection must operate on complete V3 strategy/behavior evidence.

Ensure the complete generated run is varied, paced, and free from behavioral duplicates.

## Task 12.1 — Expand production candidate signatures

Include:

- Blueprint archetype.
- Objective count and kinds.
- Dependency DAG signature.
- Adaptive-decision pattern.
- State-transition pattern.
- Static-policy proof signature.
- Agent performance profile.
- Switch degree sequence.
- Revisit pattern.
- Success/failure distribution.
- Optimal strategy signature.
- Layout silhouette.
- Road-state visual signature.

## Task 12.2 — Build campaign-wide candidate pools

Generate several valid candidates for every requested level slot before final selection.

The pool may be generated in waves to control memory.

## Task 12.3 — Add a portfolio optimizer

Choose one candidate per slot while optimizing:

- Difficulty fit.
- Mechanic introduction order.
- Blueprint variety.
- Objective-count variety.
- Dependency-depth progression.
- Recovery/failure balance.
- Layout variety.
- Runtime pacing.
- Distance from existing production corpus.

## Task 12.4 — Add hard campaign diversity constraints

Example initial constraints:

- No identical blueprint archetype in adjacent levels.
- No identical behavior signature within the configured uniqueness window.
- No more than two consecutive levels with the same objective count.
- No more than two consecutive levels dominated by fatal dead ends.
- Every five-level medium+ window contains at least two different adaptive mechanic families.
- Expert campaign segments must include multiple dependency structures, not repeated hub revisits only.

## Task 12.5 — Add campaign backtracking

If the optimizer cannot fill every slot:

1. Identify the constrained slots.
2. Request targeted new candidates for those slots.
3. Re-run portfolio selection.
4. Repeat within a declared global budget.
5. Fail the run without writes if the complete portfolio remains impossible.

## Task 12.6 — Compare against production corpus

Reject candidates too similar to existing levels by behavior, not merely layout or names.

## Phase 12 exit gate

- [ ] A complete batch is selected as one portfolio.
- [ ] Behavioral duplicates are blocked.
- [ ] Campaign difficulty and mechanics progress intentionally.

---

# Phase 13 — Make Production Runs Transactional and Fully Automatic

## Objective

Guarantee that a generation run produces the full verified result or changes nothing. This phase specifically replaces the current order in which `_write_generated_files()` runs before optional Swift verification.

## Task 13.1 — Add a staging workspace

**Files to add**

- `app/services/production_staging_service.py`
- `app/models/production_run_manifest.py`

Staging includes:

- Levels.
- Solutions.
- Preview images.
- Reports.
- Proposed manifest.
- Validation logs.
- Seed/config snapshot.

## Task 13.2 — Write selected candidates only to staging

No selected level, sidecar, manifest entry, report, preview, or project-resource change may be written directly to production targets during generation. Existing repository writers may be reused only when pointed at the staging workspace.

## Task 13.3 — Validate the complete staged corpus

Run:

- JSON schema validation.
- Graph validation.
- Objective-state validation.
- Exact strategy replay.
- Runtime solution replay.
- Static-policy rejection.
- Quality gates.
- Duplicate checks.
- Manifest checks.
- Swift parity for every required level, executed against staged levels and sidecars.
- Xcode resource sync verification against the proposed staged corpus.
- Proof that the same staged files are the files selected for promotion.

## Task 13.4 — Add atomic promotion

**File to add**

- `app/services/transactional_promotion_service.py`

Steps:

1. Acquire a generation lock.
2. Verify production targets have not changed since preflight.
3. Back up files that will be overwritten.
4. Promote all staged files.
5. Update manifest/project resources.
6. Re-run a lightweight production-corpus validation.
7. Remove backup only after success.
8. Roll back on any failure.

## Task 13.5 — Add complete-run retry policy

A run may replan candidates automatically within configuration limits. It must not ask the user to intervene.

Final outcomes:

- `completed`
- `failed_no_changes`
- `rolled_back`

There is no “partial success” production state.

## Task 13.6 — Add the final production command

Target command:

```bash
python Tools/LevelGenerator/generate_production_campaign.py \
  --start 31 \
  --count 30 \
  --difficulty auto \
  --seed 12345 \
  --swift-tests
```

The command must:

- Use `production_v3`.
- Use all hard quality gates.
- Select a complete portfolio.
- Stage all files.
- Run verification.
- Promote atomically.
- Print one concise final summary.

## Task 13.7 — Add final GUI workflow

The GUI requires:

- Start level.
- Count.
- Difficulty/campaign profile.
- Seed or random seed.
- Output target.
- Generate button.
- Progress by pipeline stage.
- Final result and report link.

It must not require candidate review or editor cleanup.

## Phase 13 exit gate

- [ ] Failed runs leave production unchanged.
- [ ] Successful runs contain the full requested count.
- [ ] CLI and GUI invoke the same orchestration service.

---

# Phase 14 — Build Production Diagnostics Without Requiring Manual Selection

## Objective

Make failures actionable for developers while keeping normal generation automatic.

## Task 14.1 — Define stable rejection codes

Document each code with:

- Stage.
- Meaning.
- Likely cause.
- Automatic recovery action.
- Whether it indicates a code defect, tuning issue, or ordinary candidate rejection.

## Task 14.2 — Add reproducibility bundles

For a failed candidate or run, save:

- Request configuration.
- Root seed and derived seeds.
- Blueprint.
- Composed graph.
- Solver summary.
- Rejection details.
- Layout state if reached.
- Runtime trace if reached.

A developer should reproduce the failure with one command.

## Task 14.3 — Add aggregate health reports

Report by difficulty and archetype:

- Completion rate.
- Candidate yield.
- Dominant rejections.
- Static-policy rejection rate.
- Agent performance.
- Mean decision metrics.
- Layout repair rate.
- Runtime robustness rate.
- Portfolio diversity.

## Task 14.4 — Add automatic anomaly detection

Fail CI or stress runs when:

- One rejection code suddenly dominates.
- Candidate yield falls below baseline.
- Difficulty metrics drift.
- Duplicate rate rises.
- Static-policy-solvable output appears.
- Full-run completion rate drops.

## Phase 14 exit gate

- [ ] Every failure can be reproduced.
- [ ] Reports distinguish normal rejection churn from systemic regressions.
- [ ] No report workflow requires manual candidate approval.

---

# Phase 15 — Add Comprehensive Automated Tests

## Objective

Prevent regression to trivial, mislabeled, invalid, or unreliable generation.

## Task 15.1 — Unit-test all models and contracts

Test:

- Schema 3 objectives.
- Road conditions.
- Blueprint validation.
- Motif ports.
- State transitions.
- Strategy cost ordering.
- Strategy equivalence.
- Signatures.
- Transaction manifests.

## Task 15.2 — Add adversarial anti-triviality fixtures

Required negative fixtures:

- Zero-tap path.
- One-tap path.
- Two independent obvious switches.
- Permanent-switch solution.
- Equivalent branches.
- Decorative dead-end stubs.
- Fake rejoin.
- Fake ring.
- Revisit with unchanged correct state.
- State change that does not affect any decision.
- Greedy straight-to-objective route.
- Multiple equal optimal strategies when uniqueness is required.
- Hidden/unreadable unlock.
- Frame-tight solution.

Each must fail for the intended rejection code.

## Task 15.3 — Add positive strategic fixtures

Required positive fixtures:

- Simple hub revisit.
- Unlock shortcut.
- Closed return route.
- Three-objective relay.
- Recoverable wrong loop.
- Multiple successful routes with one optimum.
- State-dependent ring.
- Hard multi-hub dependency.

## Task 15.4 — Add property-based graph tests

Use deterministic property-based generation or fuzz seeds to verify:

- No dangling references.
- State transitions terminate or are bounded.
- Solver results replay.
- Accepted candidates meet hard gates.
- Serialization round trips.
- Layout repair preserves behavior.

## Task 15.5 — Add metamorphic tests

Examples:

- Renaming IDs does not change analysis.
- Mirroring coordinates does not change strategy analysis.
- Adding pass-through nodes does not create decisions.
- Reordering unrelated JSON fields does not change output.
- Changing a locked road to always available changes static-policy analysis as expected.

## Task 15.6 — Add production-path fixed-seed campaign suites

Suites:

- Fast pull-request V3 pipeline suite.
- Nightly 30-level V3 campaign suite.
- Release stress suite.

Mandatory path-fidelity rules:

- Every V3 campaign suite invokes the same `LevelGenerationService` → `BatchOrchestrationService` path used by CLI and GUI.
- V3 release evidence may not use `execution="template"`, direct template candidates, or direct named-motif composition.
- Direct recipe/template/motif suites remain unit or fixture tests and are reported separately.
- The suite records the generator architecture version and fails if a fallback path is used.

Every suite checks full requested count, determinism, anti-triviality, parity status, diversity, staging behavior, and no fallback.

## Task 15.7 — Add Swift integration tests

Test all stateful mechanics in `RouteEngine`, including:

- Multiple objectives.
- Road availability.
- Switch normalization.
- Revisit behavior.
- Restart.
- Timeouts.
- UI state exposure.
- Generated sidecar replay.

## Task 15.8 — Add transactional failure tests

Simulate:

- Python validation failure.
- Swift failure.
- Manifest collision.
- File write failure.
- Promotion interruption.
- Concurrent generation lock.

Verify production files remain unchanged or are restored.

## Phase 15 exit gate

- [ ] Every known boring pattern has a regression test.
- [ ] Every new mechanic has Swift/Python parity coverage.
- [ ] Transactional failures cannot corrupt production content.
- [ ] V3 campaign regression evidence exercises the exact production path with no template or motif shortcut.

---

# Phase 16 — Calibrate “Fun” and Difficulty Once, Then Automate It

## Objective

Use human playtests to calibrate metrics during development, not to manually approve every generated level.

## Task 16.1 — Build a blinded playtest corpus

Generate representative levels across:

- All difficulties.
- All blueprint archetypes.
- Different objective counts.
- Different recovery/failure patterns.
- Different layout profiles.

Include known weak negative fixtures without labeling them to testers.

## Task 16.2 — Define a short playtest rubric

Collect:

- Was the goal understandable?
- Did the player need to plan a route?
- Did the correct route change after an objective?
- Were wrong routes fair?
- Was recovery satisfying or tedious?
- Was the level boring, confusing, frustrating, or engaging?
- Perceived difficulty.
- Replay desire.

## Task 16.3 — Correlate human ratings with automated metrics

Analyze relationships between ratings and:

- Meaningful decisions.
- Planning horizon.
- Adaptive decisions.
- Agent separation.
- Recovery count.
- Failure distribution.
- Decision windows.
- Visual complexity.
- Objective count.

## Task 16.4 — Tune thresholds without weakening invariants

Permitted tuning:

- Difficulty ranges.
- Ranking weights.
- Recovery balance.
- Time allowances.
- Archetype frequency.

Not permitted:

- Reintroducing one-tap levels.
- Allowing static-policy solutions.
- Counting equivalent choices.
- Allowing unproven optimal strategy.

## Task 16.5 — Freeze a calibrated quality profile

Version the profile and include it in generation reports.

A future tuning change requires:

- Updated playtest evidence.
- Fixed-seed comparison.
- Explicit version change.

## Phase 16 exit gate

- [ ] Automated metrics separate weak fixtures from engaging fixtures.
- [ ] Difficulty labels broadly match human ratings.
- [ ] Normal generation no longer requires human candidate review.

---

# Phase 17 — Performance, Determinism, and Full-Run Reliability

## Objective

Make the final architecture practical for large automatic runs.

## Task 17.1 — Profile every pipeline stage

Measure:

- Blueprint generation.
- Composition search.
- Structural solver.
- Policy agents.
- Layout.
- Runtime timing.
- Swift validation.
- Portfolio optimization.

## Task 17.2 — Add safe memoization

Cache deterministic results for:

- Canonical graph signatures.
- State transitions.
- Static-policy checks.
- Equivalent strategy states.
- Layout-independent puzzle analysis.

Do not cache mutable documents or seed-dependent results under incomplete keys.

## Task 17.3 — Add parallel candidate generation

Generate independent candidate branches in parallel while preserving deterministic final ordering.

Rules:

- Derived seeds are allocated before workers start.
- Worker completion order cannot affect selection.
- Reports sort by deterministic candidate identity.

## Task 17.4 — Add global attempt budgeting

Allocate more attempts to constrained campaign slots while maintaining a global maximum.

Report:

- Attempts used per slot.
- Why allocation changed.
- Remaining budget.

## Task 17.5 — Set reference performance targets

On the project’s documented reference Mac:

- Fast smoke: 5 levels in under 60 seconds without Swift.
- Standard dry run: 30 levels in under 5 minutes without Swift.
- Production run: 30 levels plus batched Swift verification in under 15 minutes.

Treat these as engineering targets. Correctness and quality remain higher priority than speed.

## Task 17.6 — Prove full-run reliability

Release stress target:

- 100 deterministic 30-level campaign seeds.
- 3,000 requested levels produced.
- 100% complete batches within release budgets.
- Zero one-tap levels.
- Zero static-policy-solvable levels.
- Zero unproven optimal strategies.
- Zero parity failures.
- Zero transactional partial writes.

## Phase 17 exit gate

- [ ] Candidate parallelism remains deterministic.
- [ ] Release stress target passes.
- [ ] Full runs complete within documented budgets.

---

# Phase 18 — Make V3 the Default for New Generation

## Objective

Make V3 the normal automatic-generation path without forcing an unnecessary rewrite of the working schema-2 production corpus.

## Task 18.1 — Add mixed-schema production validation

Production validation distinguishes:

- Intentional schema-1 archival fixtures.
- Existing schema-2 production levels.
- New schema-3 generated levels.

New automatic production output must be schema 3. Existing schema-2 levels remain valid until deliberately replaced.

## Task 18.2 — Generate a complete staged V3 campaign

Use the final production command and exact production pipeline to generate a complete campaign in staging. Compare it with existing content for:

- Difficulty progression.
- Strategic depth.
- Objective clarity.
- Gameplay and behavior diversity.
- Runtime fairness.
- Layout readability.
- Performance and file size.

This campaign is release evidence; it does not automatically overwrite existing content.

## Task 18.3 — Replace existing levels only by explicit content decision

When replacement is desired:

- Preserve stable level IDs and progression references.
- Update sidecars and manifest transactionally.
- Record why the V3 level is better.
- Run complete replay, progression, and save-compatibility tests.

The generator is considered complete even if existing V2 levels are retained.

## Task 18.4 — Make `production_v3` the default

After all gates pass:

- CLI default automatic generation uses `production_v3`.
- GUI default uses `production_v3`.
- V2 comparison mode requires explicit selection and displays a non-production warning.
- New production content validation rejects V2 generator output.

## Task 18.5 — Remove production fallback

A V3 production run may not silently fall back to:

- Legacy templates.
- Fixed recipe families.
- Direct motif fixtures.
- Relaxed playtest portfolio mode.
- Lower quality thresholds.
- Manual editor promotion.

If V3 cannot complete the requested batch, it fails with no production changes.

## Task 18.6 — Deprecate obsolete production branches

After a stable V3 release window:

- Remove serial motif composition from production selection.
- Remove tag-only quality paths.
- Remove duplicate V3/V2 analysis implementations after compatibility adapters are stable.
- Remove obsolete architecture switches.
- Keep schema-1/2 readers and V2 fixture paths as required for compatibility.

## Phase 18 exit gate

- [ ] V3 is the default for all new automatic production generation.
- [ ] No weak fallback can ship content.
- [ ] Existing V2 production levels remain supported.
- [ ] Optional replacements preserve progression and pass transactional verification.

---

# Phase 19 — Final Documentation, Commands, and Release Gate

## Objective

Leave a maintainable system that does not require another completion plan.

## Task 19.1 — Write architecture documentation

**Files to add/update**

- `Tools/LevelGenerator/docs/production_v3_architecture.md`
- `Tools/LevelGenerator/docs/puzzle_blueprints.md`
- `Tools/LevelGenerator/docs/stateful_motifs.md`
- `Tools/LevelGenerator/docs/strategy_solver.md`
- `Tools/LevelGenerator/docs/quality_gates.md`
- `Tools/LevelGenerator/docs/transactional_generation.md`

## Task 19.2 — Write operator documentation

Clearly distinguish automatic generation from release QA: generation requires no candidate review or editor work; any human playtest sampling is a release-process signoff, not a prerequisite for a successful generation run.

Document:

- One-command generation.
- GUI generation.
- Seeds.
- Reports.
- Failure reproduction.
- Staging and rollback.
- Adding a motif.
- Adding a blueprint archetype.
- Updating quality profiles.

## Task 19.3 — Add a final release command

Target:

```bash
python scripts/run_all_checks.py --swift-tests \
  --production-content \
  --generator-v3-stress \
  --transaction-tests
```

The command returns zero only when all mandatory gates pass.

## Task 19.4 — Add release artifact summary

Output:

- Commit and configuration identity.
- Quality-profile version.
- Test totals.
- Stress totals.
- Campaign completion results.
- Parity results.
- Corpus metrics.
- Known non-blocking warnings.

## Phase 19 exit gate

- [ ] A new developer can run and understand production generation from documentation.
- [ ] One final command proves release readiness.
- [ ] There are no undocumented manual steps.

---

# 20. Entry-Level Pull Request Breakdown

The following sequence is intentionally small enough for junior contributors. Each PR must include tests and must not combine unrelated behavior changes.

## Foundation and schema

- [x] **AG-001:** Add audited V2 baseline verification report using the existing root gate.
- [x] **AG-002:** Reconcile stale first-plan global and PR checklists with implementation evidence.
- [x] **AG-003:** Add real production-path V2 limitation baseline plus one-tap/static-policy fixtures.
- [x] **AG-004:** Add explicit `v2_legacy` and `production_v3` architecture modes with no fallback.
- [x] **AG-005:** Add Python `RouteObjective` model and round-trip tests.
- [x] **AG-006:** Add Swift `RouteObjective` model and decoding tests.
- [x] **AG-007:** Add schema 3 objective validation.
- [x] **AG-008:** Add legacy package/destination objective adapter.
- [x] **AG-009:** Generalize Python package availability into objective-state rules with V2 adapters.
- [x] **AG-010:** Generalize Swift package availability into objective-state rules with V2 adapters.
- [x] **AG-011:** Add objective progression to Python simulator.
- [x] **AG-012:** Add objective progression to Swift runtime.
- [x] **AG-013:** Add objective-based road filtering to Python.
- [x] **AG-014:** Add objective-based road filtering to Swift.
- [x] **AG-015:** Add road-state and objective parity fixture.
- [x] **AG-016:** Add current-objective gameplay marker.
- [x] **AG-017:** Add locked-road rendering.
- [x] **AG-018:** Add editor objective list controls.
- [x] **AG-019:** Add editor road-condition controls.

## Blueprint models

- [x] **AG-020:** Add `PuzzleExperienceTarget`.
- [x] **AG-021:** Add `ObjectiveSpec` and `StateTransitionSpec`.
- [x] **AG-022:** Add decision dependency graph model.
- [x] **AG-023:** Add `PuzzleBlueprint` validation.
- [x] **AG-024:** Add difficulty target resolver.
- [x] **AG-025:** Add return-to-hub blueprint.
- [x] **AG-026:** Add unlock-shortcut blueprint.
- [x] **AG-027:** Add closed-return blueprint.
- [x] **AG-028:** Add ordered-checkpoint blueprint.
- [x] **AG-029:** Add recoverable-loop blueprint.
- [x] **AG-030:** Add competing-success-routes blueprint.

## Typed motifs

- [x] **AG-031:** Add typed ports to the existing `PuzzleMotif` model and migrate one V2 motif.
- [x] **AG-032:** Add explicit precondition/effect contracts and migrate package-state motifs.
- [x] **AG-033:** Convert structural split/rejoin motif.
- [x] **AG-034:** Add stateful objective-gate motif.
- [x] **AG-035:** Add unlock-shortcut motif.
- [x] **AG-036:** Add close-behind motif.
- [x] **AG-037:** Add hub-revisit motif.
- [x] **AG-038:** Add stateful ring motif.
- [x] **AG-039:** Add recoverable detour motif.
- [x] **AG-040:** Add delayed-consequence motif.
- [x] **AG-041:** Add unique-optimal alternate-route motif.
- [x] **AG-042:** Add motif contract test helper.

**2026-07-19 AG-041 completion record:** Upgraded `parallel_unique_optimum` to an
explicit typed contract with two successful rejoining lanes, a slower recovery
exit, and graph-derived proof that exactly one successful route has minimum cost.

**2026-07-19 AG-042 completion record:** Added a reusable motif-contract test
helper that checks model validity, detected topology and decisions, observed state
effects, dependency evidence, typed exits, satisfiable preconditions, incompatible
effects, and composition limits. The full seed catalog now runs through the helper.

**2026-07-19 AG-035 completion record:** Added an explicit typed
`objective_unlocked_shortcut` contract. Completing its objective opens a real
post-objective shortcut on the revisited entry switch, with objective-state
dependency, return-path ports, layout requirements, and composition limits.

**2026-07-19 AG-036 completion record:** Added an explicit typed
`objective_closed_return_road` contract. Completing its objective closes the
outbound road behind the player and opens the valid return exit, with exact
edge-state changes and focused contract tests.

**2026-07-19 AG-037 completion record:** Added an explicit typed
`objective_state_revisited_hub` contract. Its pre-objective hub choices close
after collection, the later exit opens, and typed rejoin, return, objective,
state-change, and recovery ports expose the full cross-phase structure.

**2026-07-19 AG-038 completion record:** Added an explicit typed
`phase_dependent_ring_exits` contract. Its ring entry and failure branch close
after collection while the post-objective exit opens, with detected ring,
revisit, objective-state, return-path, and failure behavior covered by focused
tests.

**2026-07-19 AG-039 completion record:** Added an explicit typed
`recoverable_detour` contract. Its direct and longer nonfatal branches have
unequal route costs, safely rejoin, and expose branch, rejoin, and recovery
ports with focused evidence tests.

**2026-07-19 AG-040 completion record:** Added an explicit typed
`binary_delayed_consequence` contract. Its early safe-or-commit decision leads
to a distinct downstream success/failure choice, with declared earlier-choice
dependency and explicit branch, rejoin, and failure ports.

## Legacy recipe correctness

- [x] **AG-043:** Add recipe topology contract test helper.
- [x] **AG-044:** Quarantine or repair `return_loop_intro` and repeated-builder aliases.
- [x] **AG-045:** Quarantine or repair `ring_route_gate`, `multi_four_way_route`, and `late_route_reversal`.
- [x] **AG-046:** Quarantine or implement a true rejoin in `branch_then_rejoin_with_wrong_order`.
- [x] **AG-047:** Add role-aware graph isomorphism service.
- [x] **AG-048:** Add behavior isomorphism service.
- [x] **AG-049:** Remove/fix `_swap_dead_end_order()` and reject behavior-isomorphic alternates.
- [x] **AG-050:** Add registry production/fixture/deprecated status.

**2026-07-19 AG-043 completion record:** Added a reusable recipe topology
contract helper and graph-derived audit evidence for claimed rings, cycles,
rejoins, revisits, reversals, objective gates, high-arity switches, recoverable
routes, and unique-success/unique-optimal requirements. Every family variant now
emits a deterministic pass/fail status with stable reason codes.

**2026-07-19 AG-044 completion record:** Quarantined the false
`return_loop_intro` contract plus the `return_loop_with_gate` and
`multi_switch_revisit` aliases of `controlled_repeated_taps`. They remain
available for audit and regression fixtures but are excluded from mixed and
explicit production recipe selection.

**2026-07-19 AG-045 completion record:** Quarantined `ring_route_gate` because
its generated graph has no ring or cycle, plus `multi_four_way_route` and
`late_route_reversal` because they are behavior-identical builder aliases of
`four_way_package_gate` and `controlled_repeated_taps`. All remain directly
available as deterministic audit fixtures but cannot be selected for production.

**2026-07-19 AG-046 completion record:** Quarantined
`branch_then_rejoin_with_wrong_order` because its sole viable branch is the
required route and its alternate terminates in a dead end instead of rejoining.
Topology-contract coverage preserves the fixture and proves the claimed rejoin
remains absent while production selection rejects the family.

**2026-07-19 AG-047 completion record:** Added exact rooted, edge-ordered graph
canonicalization that preserves node roles, ordered objective phases, switch
degree and authored order, availability, usage limits, and future dataclass edge
effects while ignoring identifier, family, variant, note, and layout metadata.
The service exposes stable signatures, exact comparisons, and canonical node
mappings with focused rename, role, phase, edge-order, and edge-state tests.

**2026-07-19 AG-048 completion record:** Added bounded canonical behavior-state
exploration over objective phase, persistent switch state, authored choices, and
edge usage. Its ID-independent signatures record strategy-equivalence classes,
failure and recovery outcomes, optimal cost vectors, and unique-optimal evidence.
Focused tests prove known legacy builder aliases collapse to the same behavior
while runtime-significant edge ordering remains distinct.

**2026-07-19 AG-049 completion record:** Removed the no-op
`_swap_dead_end_order()` path and the expanded-family alternate variants whose
only claimed distinction depended on it. Expanded fixed recipes now expose one
auditable primary variant; genuinely authored template variants remain intact,
and focused tests prevent the behavior-isomorphic alternates from returning.

**2026-07-19 AG-050 completion record:** Added explicit `production_v3`,
`fixture_only`, and `deprecated` lifecycle types plus deterministic family and
variant audit records. Every fixed recipe is classified, registry construction
fails for missing or unknown classifications, quarantined mismatches are
deprecated, sound legacy recipes are fixture-only, and the fixed-recipe registry
exposes no hidden `production_v3` fallback.

## Composition

- [x] **AG-051:** Add composition search state.
- [x] **AG-052:** Add typed port connection validator.
- [x] **AG-053:** Add edge insertion operation.
- [x] **AG-054:** Add branch expansion operation.
- [x] **AG-055:** Add rejoin operation.
- [x] **AG-056:** Add cross-phase return operation.
- [x] **AG-057:** Add objective attachment operation.
- [x] **AG-058:** Add deterministic composition backtracking.
- [x] **AG-059:** Add partial strategic pruning.
- [x] **AG-060:** Add composition transformation framework.
- [x] **AG-061:** Add composition duplicate rejection.

**2026-07-19 AG-051 completion record:** Added an immutable composition search
state that tracks unfulfilled blueprint decisions, qualified open ports,
objective-phase boundaries, the partial graph, assigned route-state effects,
motif placements, graph counts, layout footprint, and partial strategic metrics.
Stable validation codes, immutable successor creation, and deterministic state
signatures provide the foundation for backtracking and duplicate pruning.

**2026-07-19 AG-052 completion record:** Added an explicit typed-port
compatibility validator for main-route, branch-expansion, rejoin, return-path,
objective-attachment, and state-change-attachment connections. It enforces port
direction, open-port membership, forward/return phase semantics, terminal
failure exits, and same-phase attachments with stable rejection codes.

**2026-07-19 AG-053 completion record:** Added immutable motif insertion into a
selected existing edge. Motif node IDs and ports are instance-qualified, the
replaced edge's availability and one-use semantics are preserved, assigned
state effects are retargeted, and unconsumed nested ports remain open.

**2026-07-19 AG-054 completion record:** Added typed branch expansion that
consumes an open branch-insertion port, requires an existing route to create a
real alternate, validates port and phase compatibility before graph changes,
and exposes the attached motif's remaining ports for nested composition.

**2026-07-19 AG-055 completion record:** Added atomic typed rejoin attachment
for one or more branch exits. The operation consumes open ports only after all
connectors pass validation, rejects duplicate edges and decorative single-path
merges, and updates graph-derived rejoin counts deterministically.

**2026-07-19 AG-056 completion record:** Added typed cross-phase return
connection from a later objective phase to an earlier return input. The
operation requires a real directed cycle, consumes both ports atomically, and
records the new cycle and revisit evidence with stable rejection codes.

**2026-07-19 AG-057 completion record:** Added atomic objective attachment for
both objective-bearing motifs and separately composed objective branches. The
operation enforces typed ports and objective-phase alignment, consumes ports,
binds concrete entry/exit nodes to the ordered phase boundary, prevents duplicate
objective placement, and leaves rejected immutable states unchanged.

**2026-07-19 AG-058 completion record:** Added bounded deterministic depth-first
composition search over immutable states. Stable choice ordering retries motifs,
then ports, then blueprint realizations; visited-state signatures prevent repeat
work; and results record attempted branches, expanded and visited states, every
rejection reason, a reproducible trace, and hard budget exhaustion.

**2026-07-19 AG-059 completion record:** Added blueprint-scoped partial
strategic feasibility assessment for meaningful and adaptive decisions,
dependency depth, revisits, objectives, recovery, switch count/degree, and
layout footprint. Deterministic backtracking prunes impossible branches before
expansion and records stable reasons for every failed bound.

**2026-07-19 AG-060 completion record:** Added typed transformations for all
seven controlled variant categories in Task 5.5. Each valid changed candidate
must receive a fresh solver proof, and solver-rejected variants cannot surface
an accepted transformed state.

**2026-07-19 AG-061 completion record:** Added deterministic candidate-pool
gates for repeated blueprint archetypes, motif multisets, and dependency DAGs.
Completed compositions receive an ID-independent topology, objective-state,
authored-order, and route-effect signature; behavior-equivalent candidates are
rejected before they can consume diversity-cap capacity, with an adapter ready
for exact strategy signatures.

## Exact strategy analysis

- [x] **AG-062:** Add canonical `PuzzleState`.
- [x] **AG-063:** Add structural state transition service.
- [x] **AG-064:** Add weighted strategy search.
- [x] **AG-065:** Add strategy equivalence classifier.
- [x] **AG-066:** Add unique-optimal proof.
- [x] **AG-067:** Add alternate-success classification.
- [x] **AG-068:** Add failure/recovery classification.
- [x] **AG-069:** Add static-policy solver.
- [x] **AG-070:** Add search-limit hard rejection.
- [ ] **AG-071:** Adapt legacy decision profile from exact analysis.

**2026-07-19 AG-062 completion record:** Added a compact immutable and hashable
`PuzzleState` covering node-or-edge position, ordered objective progress,
available and consumed roads, persistent switch selections, visit counts,
accepted taps, elapsed runtime-search time, and terminal outcome. Set/map-like
fields normalize into stable tuples so logically equal states share one search
key regardless of construction order.

**2026-07-19 AG-063 completion record:** Added a schema-aware structural state
transition service that rotates persistent switches in authored order, collapses
pass-through travel to the next decision boundary, completes ordered objectives,
recomputes conditional-road availability, consumes one-use roads safely,
normalizes switches after state changes, records revisits, and terminates on
success, dead ends, early legacy destinations, or automatic cycles.

**2026-07-19 AG-064 completion record:** Added deterministic Dijkstra strategy
search over canonical puzzle states with the locked accepted-tap, travel-time,
and route-distance cost ordering. Typed proof results retain a canonical optimum,
all exact equal-cost action classes, configured near-optimal and longer successes,
failure traces, explored-state counts, and explicit non-exhaustive limit reasons.

**2026-07-20 AG-065 completion record:** Added typed gameplay-equivalence keys,
classes, and classification over exact structural traces. Meaningful outgoing-road
choices, ordered objectives, observable route-state changes, outcomes, and success
cost remain distinct while pass-through movement and trace noise collapse into one
deterministic canonical class. Exact search now deduplicates completed strategies
through this classifier without weakening its internal queue identity.

**2026-07-20 AG-066 completion record:** Added a hard unique-optimal proof service
that consumes exhaustive exact-search evidence and equivalence classes. It rejects
missing successes, bounded-search uncertainty, non-equivalent equal-cost optima,
and missing required decision, objective, opened-road, closed-road, or consumed-road
evidence using stable reason codes, while retaining typed canonical proof evidence.

**2026-07-20 AG-067 completion record:** Added typed alternate-success proof
evidence over exact gameplay-equivalence classes. Every non-canonical success is
deterministically classified as an equal-cost route, a slower same-tap route, or
a higher-tap route, with component cost deltas and search-exhaustiveness evidence.

**2026-07-20 AG-068 completion record:** Added per-choice failure and recovery
analysis keyed by decision ordinal, objective phase, node, and selected road. The
report distinguishes immediate dead ends, objective-order failures, recoverable
rejoins, slower and higher-tap successes, loops, and state traps while retaining
canonical and supporting exact traces for reproducible proof.

**2026-07-20 AG-069 completion record:** Added bounded exhaustive static-policy
search over permanent authored outgoing-edge assignments. The solver reuses the
canonical structural transition engine, detects fixed-policy loops, retains typed
successful witnesses and traces, and accepts a candidate only after proving that
no permanent assignment completes every ordered objective.

**2026-07-20 AG-070 completion record:** Added a hard search-limit gate across
exact strategy and static-policy proof results. State, action, and assignment
budget exhaustion now emits stable source-specific rejection reasons; uncertainty
cannot pass, while an already-found static-policy witness remains a conclusive
candidate rejection even if later assignment enumeration is bounded.

## Agents and quality

- [ ] **AG-072:** Add random agent.
- [ ] **AG-073:** Add greedy-objective agent.
- [ ] **AG-074:** Add one-step lookahead agent.
- [ ] **AG-075:** Add two-step planning agent.
- [ ] **AG-076:** Add optimal agent adapter.
- [ ] **AG-077:** Add policy evaluation report.
- [ ] **AG-078:** Add planning-horizon classifier.
- [ ] **AG-079:** Add local-obviousness rejection.
- [ ] **AG-080:** Add `PuzzleAnalysis` model.
- [ ] **AG-081:** Add production anti-triviality gates.
- [ ] **AG-082:** Add unique-optimal gate.
- [ ] **AG-083:** Derive par taps from optimal strategy.
- [ ] **AG-084:** Derive time limit from runtime distribution.

## Runtime timing and layout

- [ ] **AG-085:** Make runtime timing search objective-state aware.
- [ ] **AG-086:** Add timing jitter replay.
- [ ] **AG-087:** Add rapid multi-tap cap.
- [ ] **AG-088:** Add state-change visibility timing check.
- [ ] **AG-089:** Add phase metadata to layout graph.
- [ ] **AG-090:** Add stateful hub spacing rules.
- [ ] **AG-091:** Add objective marker clearance rules.
- [ ] **AG-092:** Add pre/post-state layout validation.
- [ ] **AG-093:** Add phase-aware layout repairs.
- [ ] **AG-094:** Add state snapshot previews.

## Pipeline and campaign

- [ ] **AG-095:** Add typed blueprint stage result.
- [ ] **AG-096:** Add typed strategy stage result.
- [ ] **AG-097:** Add typed final quality stage result.
- [ ] **AG-098:** Add V3 candidate pipeline coordinator.
- [ ] **AG-099:** Add adaptive search breadth.
- [ ] **AG-100:** Add rejection feedback planner.
- [ ] **AG-101:** Expand candidate signatures.
- [ ] **AG-102:** Add campaign candidate pools.
- [ ] **AG-103:** Add portfolio optimizer constraints.
- [ ] **AG-104:** Add targeted portfolio backtracking.
- [ ] **AG-105:** Add existing-corpus behavior comparison.

## Transactional production

- [ ] **AG-106:** Add staging workspace.
- [ ] **AG-107:** Add production run manifest.
- [ ] **AG-108:** Write selected candidates to staging only.
- [ ] **AG-109:** Add complete staged-corpus validation.
- [ ] **AG-110:** Add atomic promotion.
- [ ] **AG-111:** Add rollback tests.
- [ ] **AG-112:** Add generation lock.
- [ ] **AG-113:** Add final production CLI command.
- [ ] **AG-114:** Add final one-action GUI flow.

## Stress, calibration, and release

- [ ] **AG-115:** Add reproducibility bundle output.
- [ ] **AG-116:** Add generator health metrics.
- [ ] **AG-117:** Add anomaly thresholds.
- [ ] **AG-118:** Add anti-triviality adversarial suite.
- [ ] **AG-119:** Add positive stateful fixture suite.
- [ ] **AG-120:** Add property-based graph suite.
- [ ] **AG-121:** Add metamorphic suite.
- [ ] **AG-122:** Add five-level smoke through the exact V3 production orchestration path.
- [ ] **AG-123:** Add nightly 30-level V3 campaign with fallback-path detection.
- [ ] **AG-124:** Add 100-campaign release stress using staging and the exact production path.
- [ ] **AG-125:** Add blinded playtest export.
- [ ] **AG-126:** Add calibrated quality-profile versioning.
- [ ] **AG-127:** Add deterministic candidate parallelism.
- [ ] **AG-128:** Add global attempt budgeting.
- [ ] **AG-129:** Make V3 production default.
- [ ] **AG-130:** Remove weak production fallback.
- [ ] **AG-131:** Add final architecture/operator documentation.
- [ ] **AG-132:** Add final release wrapper.

---

# 21. Required Test Matrix

## 21.1 Schema and model tests

- Schema 1/2 backward compatibility.
- Schema 3 round trip.
- Objective ordering.
- Duplicate objective IDs.
- Missing objective node.
- Conflicting legacy fields.
- Road condition references.
- One-use road state.
- Unknown-field preservation.

## 21.2 Runtime tests

- Objective reveal and completion.
- Out-of-order arrival.
- Road unlock.
- Road closure.
- Switch normalization after closure.
- Revisited hub.
- Restart.
- Time expiration.
- Dead end.
- Completion after final objective.
- Live switch eligibility through state changes.

## 21.3 Blueprint tests

- Deterministic generation.
- Target range satisfaction.
- Dependency DAG validity.
- Archetype-specific invariants.
- No serial-independent-only blueprint.

## 21.4 Motif tests

- Typed port validation.
- Preconditions.
- Effects.
- Topology declarations.
- Decision consequence.
- Layout footprint.
- Compatibility.

## 21.5 Composer tests

- Nested insertion.
- Branch expansion.
- Rejoin.
- Return path.
- Objective placement.
- Backtracking.
- Partial pruning.
- Determinism.
- Non-isomorphic variants.

## 21.6 Solver tests

- Optimal strategy.
- Equal-cost strategy classes.
- Near-optimal route.
- Static policy.
- Recovery classification.
- Objective state.
- Conditional roads.
- Revisited switches.
- Search-limit rejection.

## 21.7 Anti-boring tests

- Zero tap rejected.
- One tap rejected.
- Independent switch chain rejected.
- Greedy route rejected at target difficulties.
- Equivalent branches rejected.
- Decorative branch rejected.
- No-consequence state change rejected.
- Static policy rejected.

## 21.8 Layout tests

- Objective clearance.
- Stateful hub clearance.
- Locked-road icon clearance.
- Every phase state.
- Camera preview.
- Repair behavior preservation.

## 21.9 Runtime timing tests

- Window discovery.
- Revisit timing.
- State-change timing.
- Jitter robustness.
- Multi-tap cap.
- Thinking-time minimum.

## 21.10 Campaign tests

- Complete count.
- Difficulty progression.
- Archetype diversity.
- Behavior uniqueness.
- Existing-corpus uniqueness.
- Deterministic portfolio selection.

## 21.11 Transaction tests

- Stage-only writes.
- Successful promotion.
- Validation failure.
- Swift failure.
- Collision.
- Rollback.
- Concurrent lock.

---

# 22. Final Verification Commands

The repository must end with documented commands equivalent to the following.

```bash
# All Python suites
python scripts/run_python_tests.py

# Swift unit and integration tests
xcodebuild test \
  -project TinyRoutes.xcodeproj \
  -scheme TinyRoutes \
  -destination 'platform=iOS Simulator,name=iPhone 16 Pro,OS=18.5'

# Fast V3 smoke
python Tools/LevelGenerator/generate_production_campaign.py \
  --start 9001 \
  --count 5 \
  --difficulty auto \
  --seed 10101 \
  --dry-run

# Deterministic 30-level campaign regression
python Tools/LevelGenerator/stress_test_generation.py \
  --mode production_v3 \
  --campaign-count 1 \
  --levels-per-campaign 30 \
  --seed 20202

# Release stress: 100 complete campaigns
python Tools/LevelGenerator/stress_test_generation.py \
  --mode production_v3 \
  --campaign-count 100 \
  --levels-per-campaign 30 \
  --seed-range 1-100 \
  --require-complete-batches \
  --fail-on-one-tap \
  --fail-on-static-policy \
  --fail-on-parity-error

# Production corpus validation
python Tools/LevelGenerator/validate_generated_levels.py \
  --all-production \
  --require-schema-v3-for-new-content \
  --require-puzzle-analysis \
  --swift-tests

# Transaction failure suite
python -m pytest Tools/LevelGenerator/tests/test_transactional_generation.py

# Final release wrapper
python scripts/run_all_checks.py --swift-tests \
  --production-content \
  --generator-v3-stress \
  --transaction-tests
```

---

# 23. Final Production Acceptance Scenarios

## Scenario A — Automatic five-level generation

- [ ] User selects five levels and a seed.
- [ ] The generator creates a complete portfolio.
- [ ] No level has fewer than two meaningful decisions.
- [ ] Every level has an adaptive state change.
- [ ] All files are staged and verified.
- [ ] Production promotion succeeds without editor use.

## Scenario B — A → B → C → D routing

- [ ] A level begins at Start A.
- [ ] The active objective is Pickup B.
- [ ] Completing B changes road availability.
- [ ] The active objective becomes Checkpoint C.
- [ ] The player revisits a hub and must choose a different exit.
- [ ] Completing C reveals Destination D.
- [ ] The level completes only at D.
- [ ] Swift and Python traces match.

## Scenario C — Not solvable by tapping every switch once

- [ ] Static-policy search finds no successful permanent assignment.
- [ ] The optimal route revisits at least one decision context after state change.
- [ ] A switch or hub requires a different correct route in a later phase.
- [ ] The generated explanation identifies that dependency.

## Scenario D — Multiple successful routes with one best route

- [ ] At least two successful strategy classes exist.
- [ ] Exactly one has optimal cost.
- [ ] `parTaps` matches the optimal strategy.
- [ ] The alternate route is understandable and recoverable.
- [ ] The level is not rejected merely because another completion exists.

## Scenario E — Full 30-level campaign

- [ ] All 30 requested slots are filled.
- [ ] Difficulty progresses.
- [ ] Objective counts and archetypes vary.
- [ ] No prohibited behavior duplicate appears.
- [ ] Every solution passes jitter replay.
- [ ] Required Swift parity passes.
- [ ] Promotion is atomic.

## Scenario F — Failure with no corruption

- [ ] Force a Swift parity failure after staging.
- [ ] The command returns failure.
- [ ] No production level, solution, manifest, or project file changes.
- [ ] The report includes a reproducibility bundle.

---

# 24. Final Definition of Done

The Tiny Routes automatic level generator is fully complete only when all of the following are true:

- [ ] The existing master generator/editor plan passes every executable exit gate.
- [ ] Schema version 3 supports ordered multi-stop objectives and deterministic route-state changes.
- [ ] Swift and Python simulate those mechanics identically.
- [ ] The generator creates a puzzle blueprint before topology.
- [ ] Typed stateful motifs realize blueprint dependencies through nested composition.
- [ ] Fixed recipe names and variants accurately describe their behavior.
- [ ] Behavior-isomorphic recipes and candidates are detected.
- [ ] The exact structural solver proves the optimal strategy.
- [ ] Multiple successful routes are allowed when one unique optimal route exists.
- [ ] Static-policy-solvable levels are always rejected.
- [ ] Zero-tap and one-tap generated production levels are always rejected.
- [ ] Every generated level has at least two meaningful decisions.
- [ ] Every generated level has at least one planning decision.
- [ ] Every generated level has at least one adaptive decision after a state change.
- [ ] Medium+ levels require reasoning beyond greedy local arrow selection.
- [ ] Runtime schedules use legal, robust decision windows.
- [ ] Layout validation covers every objective state, not just the initial map.
- [ ] Candidate selection considers the complete campaign portfolio.
- [ ] A full requested run completes automatically or writes nothing.
- [ ] Output is staged, verified in Python and Swift, and promoted atomically.
- [ ] The normal workflow never requires the Level Editor or manual candidate review.
- [ ] The 100-campaign release stress suite produces 3,000 valid requested levels with no partial batches.
- [ ] Calibrated human playtest evidence supports the automated difficulty and engagement thresholds.
- [ ] `production_v3` is the default production generator.
- [ ] Weak legacy/template fallback cannot silently ship content.
- [ ] Architecture, operator, tuning, failure-code, and release documentation is complete.

When this definition of done passes, Tiny Routes will no longer be generating maps that merely look complex. It will be generating complete moving-route puzzles in which the player must plan, commit, react to deterministic state changes, revisit decisions, compare viable routes, and find the best path through multiple objectives—without manual level construction or cleanup after generation.
