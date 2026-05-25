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

Write one tutorial level and matching solution:

```bash
python Tools/LevelGenerator/generate_levels.py --start 12 --count 1 --difficulty tutorial --template straight_delivery --seed 1
```

Generate multiple levels:

```bash
python Tools/LevelGenerator/generate_levels.py --start 12 --count 5 --difficulty easy --template mixed --seed 1234
```

Validate generated files:

```bash
python Tools/LevelGenerator/validate_generated_levels.py --levels level_012 level_013
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

## Difficulty and Templates

Supported difficulty presets:

- `tutorial`
- `easy`
- `medium`
- `hard`

Supported templates:

- `straight_delivery`
- `single_switch`
- `package_gate`
- `return_loop`
- `multi_switch_chain`
- `ring_route`
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
