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

Run both Python suites from the repository root. Each suite is launched in its
own working directory, and both run even when the first one fails:

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
  --destination 'platform=iOS Simulator,name=iPhone 16 Pro'
```

Use `--python /path/to/python` with any script when dependencies are installed
in a different interpreter. The two Python suites can also be collected in one
process without package-name collisions:

```bash
python -m pytest Tools/LevelGenerator/tests Tools/LevelEditor/tests
```

## Design Goals

- Simple one-thumb gameplay
- Fast bite-sized puzzle levels
- Daily route challenges with streak rewards
- Unlockable cosmetics (route themes, delivery dots, trails)
- Clean minimalist visual style
- Hybrid monetization: rewarded ads, optional IAP, no-ads purchase
