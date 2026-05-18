# Tiny Routes Level Editor

An internal desktop GUI tool for creating, editing, and validating Tiny Routes level files.

## Purpose

This tool lets engineers and level designers build and edit `level_###.json` files visually instead of hand-editing JSON. It connects to the level validation and solvability infrastructure so you can create a level, validate it, prove it is beatable, and commit with confidence.

## Requirements

- Python 3.10 or later
- PySide6 (Qt for Python)
- pytest (for running editor tests)

## Setup

```bash
cd Tools/LevelEditor
pip install -r requirements.txt
```

## Running the Editor

From the repo root:

```bash
python Tools/LevelEditor/run_level_editor.py
```

Or from inside the `Tools/LevelEditor/` folder:

```bash
python run_level_editor.py
```

## Running the Editor Tests

From inside `Tools/LevelEditor/`:

```bash
pytest tests/
```

Or from the repo root:

```bash
pytest Tools/LevelEditor/tests/
```

## Documentation

- [Current Level JSON Shape](docs/current_level_json_shape.md) — the real fields used by production level files

## Architecture Overview

The editor is organised into four layers:

| Layer | Folder | Responsibility |
|---|---|---|
| Models | `app/models/` | Plain data structures — no Qt, no file I/O |
| Repositories | `app/repositories/` | File I/O only — load and save JSON |
| Services | `app/services/` | Business logic — validation, layout, test commands |
| UI | `app/ui/` | Qt widgets and canvas items |

Entry point: `app/main.py` → `app/main_window.py`

## Phased Plan

See [docs/plans/gui_level_editor_plan.md](../../docs/plans/gui_level_editor_plan.md) for the full phased implementation plan and engineering tasks.

## Notes

This tool is separate from the iOS game target. It does not modify game source files. The real source of truth remains the level JSON files and the `RouteEngine` tests.
