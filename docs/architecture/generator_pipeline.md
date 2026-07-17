# Generator Pipeline Architecture

## Entry points

`Tools/LevelGenerator/app/cli.py` and the Tk GUI create a `GenerationConfig`
and call `LevelGenerationService.generate`. The service is the dependency
container and public façade. `BatchOrchestrationService` owns the batch loop,
pooling, selection, persistence, reporting, and optional Swift gate.

All random choices derive from `RandomSource` children rooted at
`GenerationConfig.base_seed`. A stage must request a named child seed rather
than use process-global randomness. This is what makes accepted files, reports,
and fixed-seed regression hashes reproducible.

## Pipeline

The effective pipeline is:

1. **Plan and preflight.** `DifficultyCurveService` assigns level IDs,
   difficulties, and pacing weights. Configuration, template/family support,
   Swift-validation policy, and output collisions are checked before work.
2. **Seed topology.** A recipe family composes motifs into a `GraphRecipe`.
   Recipe metadata is descriptive; graph validation and measured results are
   authoritative. There is no legacy-template or hybrid execution branch.
3. **Solve topology.** `TopologySolverService` proves a package-before-destination
   route and records required path/decisions. `DecisionProfileService` measures
   dependencies, revisits, package phases, alternate outcomes, and independent
   decisions. Strategically weak recipes can be rejected before layout.
4. **Plan and repair layout.** `GraphLayoutPlannerService` assigns layers,
   orientation, size profile, and coordinates. `LayoutRepairService` attempts
   deterministic local repairs for spacing and crossings.
5. **Assign road geometry.** `RoadShapeService` assigns horizontal-first or
   vertical-first roads, ports, and readability metadata. Geometry uses the
   final coordinates, not topology-only proxies.
6. **Build runtime documents.** `RecipeToLevelBuilderService` creates the shared
   `LevelDocument`, live-lookahead rules, and candidate metadata.
7. **Schedule a real solution.** `RuntimeSolutionSearchService` converts topology
   decisions into taps inside measured eligibility windows. The sidecar is
   built only from an accepted Python runtime replay.
8. **Validate.** `GeneratedLevelValidationService` combines editor structure and
   sidecar validation with difficulty, timing, unique-solution, package,
   layout, road geometry, visual clarity, and Python simulation checks.
9. **Gate and score.** `RuntimeParityValidator` determines whether Swift replay
   is mandatory. `GenerationQualityService` scores measured logic, route
   interest, layout, difficulty fit, and diversity. Hard thresholds reject weak
   candidates.
10. **Pool and select.** Each requested level collects multiple valid candidates.
    `CandidatePortfolioSelectionService` chooses one per slot while balancing
    quality, decision/visual diversity, production distance, mechanic
    progression, and adjacent variety with deterministic tie-breakers.
11. **Persist and verify.** Repositories write level JSON, solution sidecars, and
    human/JSON reports. Production output synchronizes app resources and the
    manifest. Requested Swift tests replay the written files before the batch
    is considered successful.

## Stage data and ownership

- Shared serialized data comes from `tiny_routes_core.models` and preserves
  unknown extension fields on round trip.
- `GraphRecipe` and `RecipeTopologyRules` are generator-only topology inputs.
- `GeneratedLevel` is the candidate aggregate. It carries the level, solution,
  seed, source metadata, solver/runtime evidence, layout reports, quality score,
  and parity decision.
- `StageResult` and `CandidateStageResult` are report boundaries. New stage
  output should use named fields rather than unstructured dictionaries.
- `GenerationResult` is the batch aggregate and owns accepted candidates,
  rejection counts, selection summaries, written paths, Swift results, and
  report paths.

## Rejection flow

Candidate construction exceptions become `candidate_generation_error` unless
the exception supplies a stable `code`. Validation errors are ordered and
recorded by `CandidateRejectionService`; custom runtime, quality, and similarity
rejections use the same service. Optional debug output contains the rejected
level, sidecar, and messages, and must never be copied into app resources.

Warnings stay on the candidate report. Any `GeneratorValidationMessage` with
severity `error`, any mandatory parity failure, or any hard quality/selection
gate prevents production acceptance. Code meanings and fixes are cataloged in
[`docs/reference/level_validation_and_rejection_codes.md`](../reference/level_validation_and_rejection_codes.md).

## Determinism and reports

Stable output depends on all of the following:

- named child seeds for candidate, recipe, layout, map, and road choices;
- stable authored edge order and stable sorting before comparisons;
- deterministic candidate and portfolio tie-breakers ending in seed/hash data;
- no wall-clock input in generation or simulation; and
- explicit baseline updates for intentional fixed-seed changes.

The JSON report is the machine-readable audit trail. The Markdown report is a
review surface derived from it; do not add acceptance logic only to report
formatting.

## Extension points

- Add a mechanic as a motif/recipe plus measured topology and decision evidence.
- Add a layout strategy through the planner and repair/validation boundaries.
- Add a validation rule as a stable code with tests and a reference-table row.
- Add quality signals only when derived from graph, simulation, or layout
  measurements; tags alone cannot raise quality.
- Require Swift validation when a mechanic adds cycles, revisits, high-arity
  switches, phase changes, or other behavior not safely represented by simple
  structural checks.

Run `python scripts/run_all_checks.py` for the local Python, fixed-seed, smoke,
and production gates; add `--swift-tests` for the release-equivalent runtime
gate.
