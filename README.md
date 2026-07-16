# Tiny Routes

**One-tap delivery puzzles**

Tiny Routes is a minimalist one-thumb route puzzle game for iPhone. Players guide a tiny delivery dot through compact route-map puzzles by tapping intersections, rotating direction arrows, collecting packages, and reaching the destination before time runs out.

## Concept

Each level is a small abstract city-map puzzle. A glowing delivery dot automatically moves along connected route lines. The player taps intersections to rotate arrows, switches, or gates so the dot reaches the correct destination.

- The player does not directly move the dot
- The player controls the route

## Core Gameplay

1. A delivery dot starts moving automatically
2. The player taps switch nodes to rotate or change their direction
3. The dot follows the direction of the active node
4. Collect the package, then reach the destination
5. Performance is rated on time, taps, hints, and mistakes

## Target Platform

iPhone (iOS)

## Developer setup

Python 3.11 or newer is recommended. Create one virtual environment at the
repository root and install both tools' dependencies plus pytest:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r Tools/LevelGenerator/requirements.txt
python -m pip install -r Tools/LevelEditor/requirements.txt pytest
```

The Level Editor uses PySide6. On macOS, Swift checks additionally require a
full Xcode installation with an iOS Simulator matching the selected
destination.

## Developer commands

Run all Python suites from the repository root. The shared core, generator, and
editor suites are each launched in their
own working directory, and all run even when an earlier suite fails:

```bash
python scripts/run_python_tests.py
```

Run the deterministic, non-writing generator smoke check:

```bash
python scripts/run_generator_smoke.py
```

Run all Python checks together, optionally including Swift tests:

```bash
python scripts/run_all_checks.py
python scripts/run_all_checks.py --swift-tests \
  --destination 'platform=iOS Simulator,name=iPhone 16 Pro,OS=18.5'
```

Run the same full Xcode test scheme used by macOS CI:

```bash
python3 scripts/run_swift_tests.py
```

CI runs on pushes to `main`, pull requests, and manual dispatches. Python CI
uses Python 3.11 with the headless `QT_QPA_PLATFORM=minimal`; Swift CI uses the
`macos-15` runner with Xcode 16.4 and an iPhone 16 Pro running iOS 18.5. Keep
the destination in `scripts/run_swift_tests.py` synchronized with
`.github/workflows/swift-ci.yml` when updating the supported toolchain.

Use `--python /path/to/python` with any script when dependencies are installed
in a different interpreter. The Python suites can also be collected in one
process without package-name collisions:

```bash
python -m pytest Tools/TinyRoutesCore/tests Tools/LevelGenerator/tests Tools/LevelEditor/tests
```

The generator and editor share the standard-library-only `tiny-routes-core`
package. Install it once in editable mode for local development so imports work
from either tool and from any working directory:

```bash
python -m pip install -e Tools/TinyRoutesCore
```

## Git publishing

Direct commits and pushes use standard `git` commands and do not require the
GitHub CLI (`gh`). Use `gh` only for GitHub-specific operations such as creating
or managing pull requests from the command line.

## Design Goals

- Simple one-thumb gameplay
- Fast bite-sized puzzle levels
- Daily route challenges with streak rewards
- Unlockable cosmetics (route themes, delivery dots, trails)
- Clean minimalist visual style
- Hybrid monetization: rewarded ads, optional IAP, no-ads purchase
