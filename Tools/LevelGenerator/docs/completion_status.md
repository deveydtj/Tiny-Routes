# Level Generator Plan Completion Status

This file records what was completed in the first implementation pass for the Tiny Routes auto-generated level creation tool plan.

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

- [x] Smoke dry-run passed without writing production level or solution files:

```bash
python3.11 Tools/LevelGenerator/generate_levels.py --start 99 --count 2 --difficulty easy --template mixed --seed 123 --dry-run --report /tmp/tiny-routes-smoke.md --json-report /tmp/tiny-routes-smoke.json
```

## Remaining Original Plan

### Phase 3 - Existing Production Level Similarity Checks

- [ ] Add `ExistingLevelRepository`.
- [ ] Load all existing `level_###.json` files.
- [ ] Load matching `level_###.solution.json` files when available.
- [ ] Return warnings for missing or malformed existing files.
- [ ] Add `compare_against_existing` to generation config.
- [ ] Add CLI flags `--compare-existing` and `--no-compare-existing`.
- [ ] Add GUI checkbox for avoiding similarity with existing levels.
- [ ] Load existing signatures at generation start.
- [ ] Reject candidates similar to existing production levels with `candidate_too_similar_to_existing`.
- [ ] Include matching existing level IDs in rejection messages and reports.
- [ ] Add repository, CLI, GUI state, and generation integration tests.

### Phase 4 - Layout Variation and Readability

- [ ] Expand `GraphLayoutService` with scale, translate, rotate, normalize, jitter, edge spacing, and crossing helpers.
- [ ] Add edge crossing detection.
- [ ] Add route readability helpers.
- [ ] Add shared `LayoutVariantService`.
- [ ] Support normal, mirrored, wide, tall, offset, and jittered layout variants.
- [ ] Update templates to use `LayoutVariantService` instead of local variant/mirror logic.
- [ ] Add small package, destination, dead-end, and route-bend placement variations.
- [ ] Add layout and template tests for valid positions and varied layout hashes.

### Phase 5 - Template Variety Expansion

- [ ] Add `TemplateVariantSpec`.
- [ ] Add tests for `TemplateVariantSpec`.
- [ ] Add easy variants:
  - [ ] `single_switch_upper_package`
  - [ ] `single_switch_lower_package`
  - [ ] `single_switch_short_dead_end`
  - [ ] `package_gate_left_entry`
  - [ ] `package_gate_right_entry`
  - [ ] `package_gate_crossing_avoidance`
- [ ] Add medium variants:
  - [ ] `multi_switch_chain_zigzag`
  - [ ] `multi_switch_chain_stair_step`
  - [ ] `multi_switch_chain_split_dead_ends`
  - [ ] `return_loop_upper`
  - [ ] `return_loop_lower`
  - [ ] `package_gate_double_choice`
- [ ] Add hard variants:
  - [ ] `ring_route_clockwise`
  - [ ] `ring_route_counterclockwise`
  - [ ] `ring_route_package_inside`
  - [ ] `ring_route_package_outside`
  - [ ] `multi_switch_chain_four_switch`
  - [ ] `multi_switch_chain_double_gate`
- [ ] Mark variants needing Swift validation.
- [ ] Add easy, medium, and hard uniqueness/validation tests.

Notes: Some easy and medium template variety was added during the duplicate-detection pass, but this phase is not complete because `TemplateVariantSpec`, the full named variant set, hard ring expansion, and full variant tests are still outstanding.

### Phase 6 - Graph Recipe Generation

- [ ] Add graph recipe models.
- [ ] Validate required path starts at `start` and ends at `destination`.
- [ ] Validate required path visits package before destination.
- [ ] Add `GraphRecipeService`.
- [ ] Generate abstract graphs before assigning positions.
- [ ] Add difficulty-based required path lengths, dead ends, return loops, repeated taps, and ring loops.
- [ ] Add recipe-to-level builder service.
- [ ] Build `LevelDocument` from recipes and positions.
- [ ] Add tests for recipe models, recipe generation, and recipe-to-level building.

### Phase 7 - Python Solution Simulation

- [ ] Add `SimulationStep` and `SimulationResult` models.
- [ ] Add `PythonSolutionSimulatorService`.
- [ ] Simulate switch behavior and timed tap actions.
- [ ] Confirm package is reached before destination.
- [ ] Confirm destination is reached within the time limit.
- [ ] Add max-step and max-time guards.
- [ ] Return clear failure reasons.
- [ ] Integrate Python simulation into generated-level validation.
- [ ] Add error code `solution_simulation_failed`.
- [ ] Derive solution timing from route events in `SolutionBuilderService`.
- [ ] Add simulator, validation, and solution-builder tests.

### Phase 8 - Quality Scoring and Best-Candidate Selection

- [ ] Add `GenerationQualityScore`.
- [ ] Add `GenerationQualityService`.
- [ ] Score readability, uniqueness, difficulty fit, and route interest.
- [ ] Penalize crossings, close nodes, duplicates, bad difficulty fit, and uninteresting routes.
- [ ] Add `candidate_pool_size` to config.
- [ ] Generate a pool of valid candidates per level.
- [ ] Accept the highest-scoring candidate instead of the first valid candidate.
- [ ] Add quality details to reports.
- [ ] Add quality and best-candidate selection tests.

### Phase 9 - Difficulty Curve and Campaign Batch Generation

- [ ] Add generation batch plan models.
- [ ] Add `DifficultyCurveService`.
- [ ] Implement default campaign curve:
  - [ ] Levels 1-3 tutorial.
  - [ ] Levels 4-10 easy.
  - [ ] Levels 11-25 medium.
  - [ ] Levels 26+ hard.
- [ ] Add template weights per level number.
- [ ] Add CLI difficulty choice `auto`.
- [ ] Add GUI difficulty option `auto`.
- [ ] Build a `GenerationBatchPlan` for auto mode.
- [ ] Report actual difficulty per accepted level.
- [ ] Add model, service, CLI, GUI, and generation tests.

### Phase 10 - Map-Inspired Generation Completion

- [ ] Add map import CLI command or `import_map_seed.py`.
- [ ] Support place import.
- [ ] Support bounding-box import.
- [ ] Require explicit output path.
- [ ] Write raw simplified seed graph and attribution to cache.
- [ ] Keep import separate from production generation.
- [ ] Upgrade `MapGraphSimplifier`.
- [ ] Prefer intersections and meaningful turns.
- [ ] Remove duplicate edges and isolated nodes.
- [ ] Normalize coordinates to generator bounds.
- [ ] Preserve road-shape metadata.
- [ ] Add deterministic node selection with seed.
- [ ] Make `MapSeedToTemplateAdapter` influence layout geometry.
- [ ] Select start, package, destination, switches, and dead ends from map structure.
- [ ] Preserve attribution in generation notes and reports.
- [ ] Add optional `map_seed_path` mode to config, CLI, GUI, and generation service.
- [ ] Add map import, simplifier, adapter, config, and generation tests.

### Phase 11 - GUI Completion

- [ ] Add generation preview list/table.
- [ ] Show level ID, difficulty, template, variant, seed, graph counts, quality, and similarity warning.
- [ ] Show rejection count summary and report path.
- [ ] Add visual preview canvas.
- [ ] Render nodes, edges, important node labels, tap sequence, time limit, and par taps.
- [ ] Add dry-run generate, regenerate selected, reject selected, approve selected, and write approved levels actions.
- [ ] Keep approved candidates in memory until written.
- [ ] Ensure write uses already-approved candidates.
- [ ] Run long generation on a worker thread.
- [ ] Keep Tkinter updates on the main thread.
- [ ] Add progress/status and cancel support.
- [ ] Add Level Editor integration button.
- [ ] Add GUI controller/state tests where practical.

### Phase 12 - Resource Sync, Deletion, and Xcode Safety

- [ ] Add `LevelResourceSyncService`.
- [ ] Check written level and solution references in `TinyRoutes.xcodeproj/project.pbxproj`.
- [ ] Detect stale level and solution references.
- [ ] Return structured warnings/errors.
- [ ] Add delete-levels command.
- [ ] Support explicit level IDs and numeric ranges.
- [ ] Delete level JSON and matching solution JSON.
- [ ] Run XcodeGen by default after deletion.
- [ ] Support `--dry-run` and `--no-xcodegen`.
- [ ] Add GUI delete/range cleanup helper.
- [ ] Optionally review and simplify app-side level loading fallback.
- [ ] Add resource sync, delete CLI, GUI cleanup, and Swift repository tests if behavior changes.

### Phase 13 - Reports, Preview Images, and Review Artifacts

- [ ] Expand markdown and JSON reports with template variant, layout variant, quality, similarity, simulation, Swift, resource sync, map attribution, and preview paths.
- [ ] Generate preview image files.
- [ ] Draw route graph, important nodes, and tap order.
- [ ] Write previews to the report directory and link from markdown.
- [ ] Add production manifest.
- [ ] Rebuild manifest from current production levels.
- [ ] Include level ID, name, difficulty estimate, graph counts, tap count, and signature hashes.
- [ ] Use manifest for existing-level similarity when fresh.
- [ ] Add report, preview image, and manifest tests.

### Phase 14 - Validation Hardening

- [ ] Add graph reachability checks.
- [ ] Ensure package is reachable from start under some switch sequence.
- [ ] Ensure destination is reachable after package under some switch sequence.
- [ ] Reject disconnected or meaningless routes/traps.
- [ ] Add visual readability checks.
- [ ] Reject too many crossings, overlapping road segments, node clusters, and too-close important nodes.
- [ ] Add difficulty drift checks.
- [ ] Add route length ranges, minimum decision counts, and repeated tap limits per difficulty.
- [ ] Keep range exceptions out of production generation.
- [ ] Add validation fixtures and difficulty service tests.

### Phase 15 - Test Suite and CI Readiness

- [ ] Add unit tests for every new remaining service.
- [ ] Add batch integration tests.
- [ ] Generate dry-run tutorial, easy, medium, and hard batches.
- [ ] Verify every accepted candidate passes validation.
- [ ] Verify batch uniqueness threshold is met.
- [ ] Verify reports are written.
- [ ] Add performance tests or guardrails.
- [ ] Ensure simulation guards prevent hangs.
- [ ] Add local validation script `run_all_generator_checks.py`.
- [ ] Run Python tests, smoke generation, and production-level validation from one command.
- [ ] Keep Swift tests optional behind `--swift-tests`.

### Phase 16 - Documentation and Developer Workflow

- [ ] Rewrite LevelGenerator README around workflows.
- [ ] Document what the tool does and what files it writes.
- [ ] Document dry-run, scratch, production, GUI, delete/cleanup, map-inspired, and validation workflows.
- [ ] Add troubleshooting for stale levels, Swift tests, and duplicate-looking levels.
- [ ] Add generated-level review guide.
- [ ] Explain good levels, confusing levels, route readability, difficulty, solution sidecars, and manual playtesting.
- [ ] Add agent task instructions.
- [ ] Tell agents to complete one task at a time.
- [ ] Tell agents to add/update tests with every service change.
- [ ] Tell agents not to write production levels during tests.
- [ ] Tell agents to prefer scratch directories for generated output.
- [ ] Tell agents to update this status document after finishing tasks.
