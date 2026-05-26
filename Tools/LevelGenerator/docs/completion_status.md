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

## Not Completed Yet

- [ ] Existing production level similarity checks.
- [ ] Shared layout variant service.
- [ ] Graph recipe generation.
- [ ] Python route simulation.
- [ ] Quality scoring and best-candidate selection.
- [ ] Automatic campaign difficulty curve.
- [ ] Map-inspired generation completion.
- [ ] GUI preview, approval, regeneration, and background execution workflow.
- [ ] Resource sync and delete-level tooling.
- [ ] Preview image generation and production manifest.
- [ ] Validation hardening beyond the current checks.
- [ ] Full workflow README rewrite and review guide.
