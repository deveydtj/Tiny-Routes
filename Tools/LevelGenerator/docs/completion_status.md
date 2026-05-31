# Level Generator Plan Completion Status

This file records completion of the Tiny Routes auto-generated level creation tool plan.

## Completed

### Phase 1 - Baseline Safety and Current-State Cleanup

- [x] Created `Tools/LevelGenerator/docs/current_state.md`.
- [x] Documented current CLI commands.
- [x] Documented the current GUI entry point.
- [x] Listed current templates:
  - [x] `straight_delivery`
  - [x] `single_switch`
  - [x] `package_gate`
  - [x] `return_loop`
  - [x] `multi_switch_chain`
  - [x] `ring_route`
- [x] Documented supported difficulty presets for each template.
- [x] Documented whether current layouts are fixed, mirrored, variant-based, or procedurally placed.
- [x] Documented the remaining known issue around fixed-template variety and manual review.
- [x] Documented output paths:
  - [x] `TinyRoutes/Resources/Levels`
  - [x] `TinyRoutesTests/Resources/LevelSolutions`
- [x] Documented that generated levels must be committed with matching solution sidecars.
- [x] Created `Tools/LevelGenerator/docs/production_generation_checklist.md`.
- [x] Added dry-run checklist steps.
- [x] Added scratch-folder generation checklist steps.
- [x] Added production-folder generation checklist steps.
- [x] Added Level Editor visual review checklist steps.
- [x] Added Swift test checklist steps.
- [x] Added simulator playtest checklist steps.
- [x] Added Xcode resource cleanup checklist steps.
- [x] Added commit checklist steps.
- [x] Updated `Tools/LevelGenerator/README.md` with a Smoke Test section.
- [x] Included the requested smoke-test command.
- [x] Documented expected smoke-test behavior.

### Phase 2 - Candidate Signature and Duplicate Detection

- [x] Created `Tools/LevelGenerator/app/models/candidate_signature.py`.
- [x] Added immutable `CandidateSignature` dataclass.
- [x] Added docstring explaining duplicate/similarity usage.
- [x] Created `Tools/LevelGenerator/app/services/candidate_signature_service.py`.
- [x] Added stable signature generation for graph topology, normalized layout, and solution tap order.
- [x] Built `topology_hash` from sorted normalized edges.
- [x] Built `layout_hash` from rounded normalized node coordinates.
- [x] Built `solution_hash` from ordered tap node IDs.
- [x] Counted dead ends excluding the destination.
- [x] Used full SHA-256 hashes internally.
- [x] Created `Tools/LevelGenerator/app/services/candidate_uniqueness_service.py`.
- [x] Added exact and near-duplicate checks.
- [x] Added similarity scoring with enough detail for reports/messages.
- [x] Added default duplicate threshold.
- [x] Integrated accepted-candidate signature tracking into `LevelGenerationService`.
- [x] Added rejection code `candidate_too_similar_to_batch`.
- [x] Added similarity details to rejection messages.
- [x] Added accepted signature payloads to JSON reports.
- [x] Added short signature hashes to markdown reports.
- [x] Added tests:
  - [x] `test_candidate_signature_service.py`
  - [x] `test_candidate_uniqueness_service.py`
- [x] Updated generation and report tests for duplicate rejection and signature output.

### Template Variety Added During Integration

- [x] Added variants to `single_switch`.
- [x] Added variants to `package_gate`.
- [x] Added variants to `return_loop`.
- [x] Added route-shape variants to `multi_switch_chain`.
- [x] Added generation notes with selected template variant.
- [x] Added regression coverage that medium mixed generation accepts 10 unique signatures for a fixed seed.

## Verified

- [x] Full LevelGenerator Python test suite passed:

```bash
/tmp/tiny-routes-pytest/bin/python -m pytest Tools/LevelGenerator/tests
```

Result: `82 passed`.

- [x] Full LevelGenerator Python test suite passed after completing the remaining plan:

```bash
/tmp/tiny-routes-pytest/bin/python -m pytest Tools/LevelGenerator/tests
```

Result: `121 passed`.

- [x] Smoke dry-run passed without writing production level or solution files:

```bash
python3.11 Tools/LevelGenerator/generate_levels.py --start 99 --count 2 --difficulty easy --template mixed --seed 123 --dry-run --report /tmp/tiny-routes-smoke.md --json-report /tmp/tiny-routes-smoke.json
```

- [x] Smoke dry-run passed after completing the remaining plan:

```bash
/tmp/tiny-routes-pytest/bin/python Tools/LevelGenerator/generate_levels.py --start 99 --count 2 --difficulty easy --template mixed --seed 123 --dry-run --report /tmp/tiny-routes-smoke.md --json-report /tmp/tiny-routes-smoke.json
```

- [x] Consolidated local generator checks passed:

```bash
/tmp/tiny-routes-pytest/bin/python Tools/LevelGenerator/run_all_generator_checks.py --python /tmp/tiny-routes-pytest/bin/python
```

## Completed Original Plan

### Phase 3 - Existing Production Level Similarity Checks

- [x] Add `ExistingLevelRepository`.
- [x] Load all existing `level_###.json` files.
- [x] Load matching `level_###.solution.json` files when available.
- [x] Return warnings for missing or malformed existing files.
- [x] Add `compare_against_existing` to generation config.
- [x] Add CLI flags `--compare-existing` and `--no-compare-existing`.
- [x] Add GUI checkbox for avoiding similarity with existing levels.
- [x] Load existing signatures at generation start.
- [x] Reject candidates similar to existing production levels with `candidate_too_similar_to_existing`.
- [x] Include matching existing level IDs in rejection messages and reports.
- [x] Add repository, CLI, GUI state, and generation integration tests.

### Phase 4 - Layout Variation and Readability

- [x] Expand `GraphLayoutService` with scale, translate, rotate, normalize, jitter, edge spacing, and crossing helpers.
- [x] Add edge crossing detection.
- [x] Add route readability helpers.
- [x] Add shared `LayoutVariantService`.
- [x] Support normal, mirrored, wide, tall, offset, and jittered layout variants.
- [x] Update templates to use `LayoutVariantService` instead of local variant/mirror logic.
- [x] Add small package, destination, dead-end, and route-bend placement variations.
- [x] Add layout and template tests for valid positions and varied layout hashes.

### Phase 5 - Template Variety Expansion

- [x] Add `TemplateVariantSpec`.
- [x] Add tests for `TemplateVariantSpec`.
- [x] Add easy variants:
  - [x] `single_switch_upper_package`
  - [x] `single_switch_lower_package`
  - [x] `single_switch_short_dead_end`
  - [x] `package_gate_left_entry`
  - [x] `package_gate_right_entry`
  - [x] `package_gate_crossing_avoidance`
- [x] Add medium variants:
  - [x] `multi_switch_chain_zigzag`
  - [x] `multi_switch_chain_stair_step`
  - [x] `multi_switch_chain_split_dead_ends`
  - [x] `return_loop_upper`
  - [x] `return_loop_lower`
  - [x] `package_gate_double_choice`
- [x] Add hard variants:
  - [x] `ring_route_clockwise`
  - [x] `ring_route_counterclockwise`
  - [x] `ring_route_package_inside`
  - [x] `ring_route_package_outside`
  - [x] `multi_switch_chain_four_switch`
  - [x] `multi_switch_chain_double_gate`
- [x] Mark variants needing Swift validation.
- [x] Add easy, medium, and hard uniqueness/validation tests.

Notes: The second implementation pass completed `TemplateVariantSpec`, the full named variant set, hard ring expansion, layout variants, Python simulation, quality scoring, auto difficulty planning, map seed integration, GUI workflow support, resource deletion/sync helpers, previews, and manifest generation.

### Phase 6 - Graph Recipe Generation

- [x] Add graph recipe models.
- [x] Validate required path starts at `start` and ends at `destination`.
- [x] Validate required path visits package before destination.
- [x] Add `GraphRecipeService`.
- [x] Generate abstract graphs before assigning positions.
- [x] Add difficulty-based required path lengths, dead ends, return loops, repeated taps, and ring loops.
- [x] Add recipe-to-level builder service.
- [x] Build `LevelDocument` from recipes and positions.
- [x] Add tests for recipe models, recipe generation, and recipe-to-level building.

### Phase 7 - Python Solution Simulation

- [x] Add `SimulationStep` and `SimulationResult` models.
- [x] Add `PythonSolutionSimulatorService`.
- [x] Simulate switch behavior and timed tap actions.
- [x] Confirm package is reached before destination.
- [x] Confirm destination is reached within the time limit.
- [x] Add max-step and max-time guards.
- [x] Return clear failure reasons.
- [x] Integrate Python simulation into generated-level validation.
- [x] Add error code `solution_simulation_failed`.
- [x] Derive solution timing from route events in `SolutionBuilderService`.
- [x] Add simulator, validation, and solution-builder tests.

### Phase 8 - Quality Scoring and Best-Candidate Selection

- [x] Add `GenerationQualityScore`.
- [x] Add `GenerationQualityService`.
- [x] Score readability, uniqueness, difficulty fit, and route interest.
- [x] Penalize crossings, close nodes, duplicates, bad difficulty fit, and uninteresting routes.
- [x] Add `candidate_pool_size` to config.
- [x] Generate a pool of valid candidates per level.
- [x] Accept the highest-scoring candidate instead of the first valid candidate.
- [x] Add quality details to reports.
- [x] Add quality and best-candidate selection tests.

### Phase 9 - Difficulty Curve and Campaign Batch Generation

- [x] Add generation batch plan models.
- [x] Add `DifficultyCurveService`.
- [x] Implement default campaign curve:
  - [x] Levels 1-3 tutorial.
  - [x] Levels 4-10 easy.
  - [x] Levels 11-25 medium.
  - [x] Levels 26-40 hard.
  - [x] Levels 41+ expert.
- [x] Add template weights per level number.
- [x] Add CLI difficulty choice `auto`.
- [x] Add GUI difficulty option `auto`.
- [x] Build a `GenerationBatchPlan` for auto mode.
- [x] Report actual difficulty per accepted level.
- [x] Add model, service, CLI, GUI, and generation tests.

### Phase 10 - Map-Inspired Generation Completion

- [x] Add map import CLI command or `import_map_seed.py`.
- [x] Support place import.
- [x] Support bounding-box import.
- [x] Require explicit output path.
- [x] Write raw simplified seed graph and attribution to cache.
- [x] Keep import separate from production generation.
- [x] Upgrade `MapGraphSimplifier`.
- [x] Prefer intersections and meaningful turns.
- [x] Remove duplicate edges and isolated nodes.
- [x] Normalize coordinates to generator bounds.
- [x] Preserve road-shape metadata.
- [x] Add deterministic node selection with seed.
- [x] Make `MapSeedToTemplateAdapter` influence layout geometry.
- [x] Select start, package, destination, switches, and dead ends from map structure.
- [x] Preserve attribution in generation notes and reports.
- [x] Add optional `map_seed_path` mode to config, CLI, GUI, and generation service.
- [x] Add map import, simplifier, adapter, config, and generation tests.

### Phase 11 - GUI Completion

- [x] Add generation preview list/table.
- [x] Show level ID, difficulty, template, variant, seed, graph counts, quality, and similarity warning.
- [x] Show rejection count summary and report path.
- [x] Add visual preview canvas.
- [x] Render nodes, edges, important node labels, tap sequence, time limit, and par taps.
- [x] Add dry-run generate, regenerate selected, reject selected, approve selected, and write approved levels actions.
- [x] Keep approved candidates in memory until written.
- [x] Ensure write uses already-approved candidates.
- [x] Run long generation on a worker thread.
- [x] Keep Tkinter updates on the main thread.
- [x] Add progress/status and cancel support.
- [x] Add Level Editor integration button.
- [x] Add GUI controller/state tests where practical.

### Phase 12 - Resource Sync, Deletion, and Xcode Safety

- [x] Add `LevelResourceSyncService`.
- [x] Check written level and solution references in `TinyRoutes.xcodeproj/project.pbxproj`.
- [x] Detect stale level and solution references.
- [x] Return structured warnings/errors.
- [x] Add delete-levels command.
- [x] Support explicit level IDs and numeric ranges.
- [x] Delete level JSON and matching solution JSON.
- [x] Run XcodeGen by default after deletion.
- [x] Support `--dry-run` and `--no-xcodegen`.
- [x] Add GUI delete/range cleanup helper.
- [x] Optionally review and simplify app-side level loading fallback.
- [x] Add resource sync, delete CLI, GUI cleanup, and Swift repository tests if behavior changes.

### Phase 13 - Reports, Preview Images, and Review Artifacts

- [x] Expand markdown and JSON reports with template variant, layout variant, quality, similarity, simulation, Swift, resource sync, map attribution, and preview paths.
- [x] Generate preview image files.
- [x] Draw route graph, important nodes, and tap order.
- [x] Write previews to the report directory and link from markdown.
- [x] Add production manifest.
- [x] Rebuild manifest from current production levels.
- [x] Include level ID, name, difficulty estimate, graph counts, tap count, and signature hashes.
- [x] Use manifest for existing-level similarity when fresh.
- [x] Add report, preview image, and manifest tests.

### Phase 14 - Validation Hardening

- [x] Add graph reachability checks.
- [x] Ensure package is reachable from start under some switch sequence.
- [x] Ensure destination is reachable after package under some switch sequence.
- [x] Reject disconnected or meaningless routes/traps.
- [x] Add visual readability checks.
- [x] Reject too many crossings, overlapping road segments, node clusters, and too-close important nodes.
- [x] Add difficulty drift checks.
- [x] Add route length ranges, minimum decision counts, and repeated tap limits per difficulty.
- [x] Keep range exceptions out of production generation.
- [x] Add validation fixtures and difficulty service tests.

### Phase 15 - Test Suite and CI Readiness

- [x] Add unit tests for every new remaining service.
- [x] Add batch integration tests.
- [x] Generate dry-run tutorial, easy, medium, and hard batches.
- [x] Verify every accepted candidate passes validation.
- [x] Verify batch uniqueness threshold is met.
- [x] Verify reports are written.
- [x] Add performance tests or guardrails.
- [x] Ensure simulation guards prevent hangs.
- [x] Add local validation script `run_all_generator_checks.py`.
- [x] Run Python tests, smoke generation, and production-level validation from one command.
- [x] Keep Swift tests optional behind `--swift-tests`.

### Phase 16 - Documentation and Developer Workflow

- [x] Rewrite LevelGenerator README around workflows.
- [x] Document what the tool does and what files it writes.
- [x] Document dry-run, scratch, production, GUI, delete/cleanup, map-inspired, and validation workflows.
- [x] Add troubleshooting for stale levels, Swift tests, and duplicate-looking levels.
- [x] Add generated-level review guide.
- [x] Explain good levels, confusing levels, route readability, difficulty, solution sidecars, and manual playtesting.
- [x] Add agent task instructions.
- [x] Tell agents to complete one task at a time.
- [x] Tell agents to add/update tests with every service change.
- [x] Tell agents not to write production levels during tests.
- [x] Tell agents to prefer scratch directories for generated output.
- [x] Tell agents to update this status document after finishing tasks.
