# Production V3 Architecture

Production V3 is the only automatic-generation path eligible to write new
Tiny Routes production levels. It is a blueprint-first, proof-driven pipeline;
`v2_legacy` remains available only for compatibility fixtures and comparison.

## Candidate pipeline

Every candidate passes through the same ordered stages:

1. `blueprint` selects strategic intent and validates objective, decision, and
   state-transition targets.
2. `composition` realizes that intent with typed motif ports and deterministic
   backtracking.
3. `strategy` searches the canonical puzzle state, proves the optimum, rejects
   static policies, and classifies alternatives and recovery.
4. `layout` assigns and repairs phase-aware geometry without changing behavior.
5. `runtime` schedules legal taps, checks accessibility limits, and replays
   timing jitter.
6. `quality` applies protected anti-triviality gates before ranking the valid
   candidate.

`V3CandidatePipelineCoordinator` owns this order and stops at the first failed
stage. Stage results retain candidate ID, level ID, seed, difficulty, stable
code, and evidence. A passing result contains all six stages. The production
policy rejects a result that used a template, fixed recipe, direct fixture,
legacy architecture, relaxed thresholds, or manual approval.

## Campaign and transaction boundary

`ProductionCampaignService` resolves the requested campaign curve, constructs
candidate pools under one global attempt budget, selects a complete portfolio,
and verifies the policy evidence for every selected candidate. Candidate IDs and
derived seeds are allocated before bounded parallel execution; results are
merged in identity order so worker timing cannot affect output.

The complete portfolio is written to an isolated staging workspace. Python
replay, manifest/corpus validation, and Swift parity run against staged bytes.
Only a validated workspace can reach atomic promotion. Failure at any earlier
stage leaves production unchanged. See
[Transactional Generation](transactional_generation.md).

## Main entry points

- CLI: `Tools/LevelGenerator/generate_production_campaign.py`
- GUI: **Generate Production Campaign** in `launch_gui.py`
- Candidate boundary: `app/services/v3_candidate_pipeline_coordinator.py`
- Campaign boundary: `app/services/production_campaign_service.py`
- Final release gate: `scripts/run_all_checks.py`

Both UI entry points use the same campaign service. Normal generation has no
candidate-review pause and never requires the Level Editor.

## Compatibility boundary

Schema 1 and 2 levels remain decodable and replayable. Schema 3 is required for
new automatic production content and represents ordered objectives plus
objective-state road conditions. Compatibility adapters translate legacy
package/destination and `beforePackage`/`afterPackage` behavior; they do not make
V2 generation production eligible.

## Related references

- [Puzzle Blueprints](puzzle_blueprints.md)
- [Stateful Motifs](stateful_motifs.md)
- [Strategy Solver](strategy_solver.md)
- [Quality Gates](quality_gates.md)
- [Production Operator Runbook](production_generation_checklist.md)
