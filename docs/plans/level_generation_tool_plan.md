# Tiny Routes Level Generation Tool Plan

Implementation order:

1. Scaffold `Tools/LevelGenerator`.
2. Reuse Level Editor models and validation through a narrow import shim.
3. Generate procedural graphs with matching solution sidecars.
4. Reject malformed candidates before writing files.
5. Write markdown/JSON reports for every run.
6. Optionally run Swift `LevelSolvabilityTests`.
7. Keep optional map import separate from normal generation.

The generator produces the current production level JSON shape documented in:

- `Tools/LevelEditor/docs/current_level_json_shape.md`
- `Tools/LevelEditor/docs/solution_json_shape.md`

The Swift runtime remains the final truth for solvability:

- `TinyRoutes/Gameplay/RouteEngine.swift`
- `TinyRoutesTests/LevelSolvabilityTests.swift`
- `TinyRoutesTests/Support/LevelSimulationHarness.swift`
- `TinyRoutesTests/Support/LevelHumanPlayabilityRules.swift`

Acceptance target:

```bash
python Tools/LevelGenerator/generate_levels.py --start 12 --count 1 --difficulty tutorial --template straight_delivery --seed 1 --swift-tests
```

Expected output:

```text
TinyRoutes/Resources/Levels/level_012.json
TinyRoutesTests/Resources/LevelSolutions/level_012.solution.json
docs/generated_levels/last_generation_report.md
docs/generated_levels/last_generation_report.json
```

Generated production solutions must never be marked `isPlaceholder`. Every generated level and solution pair must pass Python structural validation before writing. Ring-route levels require Swift validation before they should be treated as production-ready.
