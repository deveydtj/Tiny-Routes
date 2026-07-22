# Puzzle Blueprints

A `PuzzleBlueprint` describes the intended player reasoning before any concrete
node IDs, coordinates, or road shapes exist. This keeps construction focused on
strategic requirements instead of generating arbitrary graphs and hoping later
validators accept them.

## Model

A blueprint contains:

- a `PuzzleExperienceTarget` resolved from difficulty and the active calibrated
  quality profile;
- ordered `ObjectiveSpec` values, including exactly one final terminal
  objective;
- a `DecisionDependencyGraph` describing meaningful decisions and dependency
  depth;
- `StateTransitionSpec` values that reveal objectives and open, close, or
  consume edge roles;
- required planning, adaptive, and revisit decisions;
- successful-strategy, recovery, and fatal-mistake targets;
- required and forbidden mechanic combinations.

Validation uses stable issue codes. Objective indices must be contiguous,
references must resolve, dependency requirements must be realizable, and the
blueprint must satisfy its target ranges before composition starts.

## Production archetypes

The registry currently provides `return_to_hub`, `unlock_shortcut`,
`closed_return`, `ordered_checkpoint`, `recoverable_loop`, and
`competing_success_routes`. A seed deterministically chooses and parameterizes
an eligible archetype. Reports preserve the archetype, target, decision graph,
objective plan, intended player explanation, and rejection evidence.

## Adding an archetype

1. Add a deterministic builder to `PuzzleBlueprintService` that consumes only
   the supplied seed/random source and experience target.
2. Express required consequences in the decision graph and state transitions;
   do not encode a concrete recipe or layout.
3. Register the archetype and add its calibrated frequency in a new quality
   profile version.
4. Add validation tests for target ranges, dependency depth, determinism, and
   the archetype-specific invariant.
5. Add at least one positive exact-strategy fixture and run the fixed-seed,
   five-level production smoke, and release checks.

An archetype is not production-ready if it can collapse to independent binary
switches, depends on a named legacy recipe, or cannot be realized by multiple
role-preserving graph forms.
