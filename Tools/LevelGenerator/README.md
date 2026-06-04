# Tiny Routes Level Generator

Procedural generation tool for creating Tiny Routes production level JSON and matching solution sidecar files. The generator writes the same shapes used by the Swift runtime and the Python Level Editor, then validates candidates before saving them.

## Install

The generator runtime uses only the Python standard library:

```bash
python Tools/LevelGenerator/generate_levels.py --help
```

On macOS setups without a `python` shim, use `python3` for the same commands.

Tests use `pytest`, matching the existing tool tests:

```bash
python -m pytest Tools/LevelGenerator/tests
```

Map-inspired generation is optional and intentionally separate. Normal generation does not require network access. See `app/map_import/README.md`.

## Quick Start

Dry-run one tutorial level:

```bash
python Tools/LevelGenerator/generate_levels.py --start 12 --count 1 --difficulty tutorial --template straight_delivery --seed 1 --dry-run
```

## Smoke Test

Start with this deterministic dry run when setting up or changing the generator:

```bash
python Tools/LevelGenerator/generate_levels.py --start 99 --count 2 --difficulty easy --template mixed --seed 123 --dry-run
```

Expected behavior:

- The command exits successfully.
- It prints accepted candidates.
- It writes reports if report paths are configured.
- It does not write level or solution files in dry-run mode.

Write one tutorial level and matching solution:

```bash
python Tools/LevelGenerator/generate_levels.py --start 12 --count 1 --difficulty tutorial --template straight_delivery --seed 1
```

Generate multiple levels:

```bash
python Tools/LevelGenerator/generate_levels.py --start 12 --count 5 --difficulty easy --template mixed --seed 1234
```

Generate along the default campaign curve:

```bash
python Tools/LevelGenerator/generate_levels.py --start 1 --count 30 --difficulty auto --template mixed --seed 1234 --dry-run
```

Validate generated files:

```bash
python Tools/LevelGenerator/validate_generated_levels.py --levels level_012 level_013
```

Delete generated levels and matching solution sidecars:

```bash
python Tools/LevelGenerator/delete_levels.py 31-35 --dry-run
```

Rebuild the production manifest:

```bash
python Tools/LevelGenerator/rebuild_manifest.py
```

Run the local generator check suite:

```bash
python Tools/LevelGenerator/run_all_generator_checks.py
```

## Simple GUI

Run:

```bash
python Tools/LevelGenerator/launch_gui.py
```

The GUI is a thin wrapper around the same generation and validation services used by the CLI. Use dry-run first, then write to a temporary output folder before writing production levels. The GUI writes the same markdown and JSON reports as the CLI.

Use a Python 3.10+ interpreter with Tkinter enabled.

## Options

`--overwrite` allows replacing existing level and solution files. Without it, the generator refuses to overwrite anything.

`--dry-run` generates and validates candidates without writing level or solution files. Reports are still written when report paths are configured.

`--seed` makes generation reproducible. Candidate seeds are recorded in the markdown and JSON reports.

`--swift-tests` runs the real Swift solvability tests after files are written. `--no-swift-tests` skips them.

`--compare-existing` rejects candidates that are too similar to existing level files in the configured output folders. This is enabled by default; use `--no-compare-existing` for scratch experiments.

`--generation-mode` controls the generation architecture. `recipe-first` is the default and preferred path; `legacy-template` and `hybrid` remain available for comparison and fallback runs.

Recipe-first generation solves multiple abstract recipes before layout, then tries layout and road-shape variants. The default breadth is 4 recipes, 3 layouts per recipe, 3 road-shape strategies per layout, and 8 valid candidates scored before accepting the best one.

`--layout-orientation` defaults to `portrait_vertical`. This profile asks recipe-first layouts to compose routes for mobile portrait play: the generated map should be taller than wide, the start should sit in the lower portion of the layout, and the destination should sit in the upper portion. Horizontal branches, detours, and side movement are still allowed when the overall composition passes the portrait safety checks.

Generation reports include the selected layout profile plus lightweight portrait metrics: width, height, aspect ratio, start-to-destination vertical separation, and whether portrait checks passed. Larger scrolling maps, camera follow, zoom, and gameplay rendering changes are intentionally out of scope for this generator phase.

`--candidate-pool-size` scores multiple valid candidates for each level and accepts the highest-scoring one. Reports include quality and simulation details.

`--difficulty auto` uses the default campaign curve: levels 1-3 tutorial, 4-10 easy, 11-25 medium, 26-40 hard, and 41+ expert.

`--map-seed-path` applies a saved map seed JSON to generated node positions. Map import is separate from production generation:

```bash
python Tools/LevelGenerator/import_map_seed.py --place "Imperial, Missouri, USA" --output /tmp/imperial-seed.json --cache-dir /tmp/tiny-routes-map-cache
```

## Difficulty and Templates

Supported difficulty presets:

- `tutorial`
- `easy`
- `medium`
- `hard`
- `expert`
- `auto`

Supported templates:

- `straight_delivery`
- `single_switch`
- `package_gate`
- `return_loop`
- `multi_switch_chain`
- `ring_route`
- `four_way_intersection`
- `mixed`

`mixed` filters templates by difficulty and prefers safer templates for beginner presets.

## Xcode Troubleshooting

The repository uses `project.yml` as the XcodeGen source of truth and the checked-in `.xcodeproj` has explicit JSON resource references. When generation writes to the default production folders, the generator runs XcodeGen automatically before optional Swift tests:

```bash
python Tools/LevelGenerator/generate_levels.py --start 31 --count 5 --difficulty hard --template mixed --swift-tests
```

Use `--no-xcodegen` only when writing to a scratch folder or when you intentionally want to defer project regeneration. To sync manually:

```bash
xcodegen generate
```

If Xcode reports missing level JSON inputs after deleting or regenerating only part of a batch, run `xcodegen generate` so stale file references are removed from `TinyRoutes.xcodeproj`.

If `xcodebuild` is missing, install Xcode or run generation with `--no-swift-tests`, then validate on a Mac with Xcode before committing generated production levels.

## Generated-Level Review Checklist

- Dry-run generation works.
- Write generation works.
- Reports open correctly.
- Open generated level in the Level Editor.
- Confirm nodes are visually readable.
- Confirm route lines do not overlap badly.
- Confirm package and destination are obvious.
- Confirm dead ends look intentional.
- Run Python validation.
- Run Swift solvability tests when available.
- Play the level manually in simulator before committing.
- Commit level JSON and solution JSON together.

## Developer Workflow

- Work one task at a time and keep generated production files out of tests.
- Use scratch directories or `--dry-run` for experiments.
- Add or update tests with every service change.
- Keep `completion_status.md` current when finishing generator work.
- Run `python Tools/LevelGenerator/run_all_generator_checks.py` before relying on a production batch.

Good generated levels have readable routes, clear start/package/destination placement, intentional dead ends, difficulty-appropriate decision counts, and a non-placeholder solution sidecar. Confusing levels usually have crossing-heavy routes, clustered important nodes, or tap timing that only works by accident; reject those during review even when validation passes.
