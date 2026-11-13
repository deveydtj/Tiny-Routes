# Tiny Routes

**One-tap delivery puzzles**

Tiny Routes is a minimalist one-thumb route puzzle game for iPhone. Players guide a tiny delivery dot through compact route-map puzzles by tapping intersections, rotating direction arrows, collecting packages, and reaching the destination before time runs out.

> **Current direction:** the game is now the "set the switches, then press Go" multi-van puzzle. Home → Play → Levels opens its 19 levels (`TinyRoutes/Resources/PrototypeLevels`); the original 27 single-dot levels have been removed. See the [multi-van prototype plan](docs/prototype/multi_van_prototype_plan.md). Sections below that describe the single-dot game, its generator and editor are historical until that code is retired.

## Concept

Each level is a small abstract city-map puzzle. The player taps a dotted road to choose the delivery dot's starting direction, then the dot moves automatically along connected route lines. The player taps intersections to rotate arrows, switches, or gates so the dot reaches the correct destination.

- The player does not directly move the dot
- The player controls the route

## Core Gameplay

1. Tap a dotted starting road to begin driving; the timer waits for this choice
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

Run all fixed-seed release regressions, including the mixed 30-level campaign
and the revisit, high-arity-switch, and conditional-road batches:

```bash
python Tools/LevelGenerator/run_fixed_seed_regressions.py
```

Intentional generator changes must update the committed hashes explicitly and
review the JSON report before committing the new baselines:

```bash
python Tools/LevelGenerator/run_fixed_seed_regressions.py \
  --update-baselines --json-output /tmp/tiny-routes-fixed-seeds.json
```

Run all Python checks together, optionally including Swift tests:

```bash
python scripts/run_all_checks.py
python scripts/run_all_checks.py --swift-tests \
  --destination 'platform=iOS Simulator,name=iPhone 16 Pro,OS=18.5'
```

Run the final production V3 release gate, retaining its JSON and Markdown
artifact summary under `artifacts/production-v3-release`:

```bash
python scripts/run_all_checks.py --swift-tests \
  --production-content \
  --generator-v3-stress \
  --transaction-tests
```

This release form includes the 100-campaign/3,000-level exact-path stress gate
and returns zero only when every mandatory gate passes.

The combined command also verifies the production corpus and manifest. Retain
the fixed-seed and corpus reports for release review with:

```bash
python scripts/run_all_checks.py --swift-tests \
  --reports-dir artifacts/level-system-release
```

Run the same full Xcode test scheme used by macOS CI:

```bash
python3 scripts/run_swift_tests.py
```

CI runs on pushes to `main`, pull requests, and manual dispatches. Python CI
also enforces fixed-seed hashes and every non-Swift production-content gate.
It uses Python 3.11 with the headless `QT_QPA_PLATFORM=minimal`; Swift CI uses the
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

## TestFlight upload

Double-click `Build TestFlight.command` in Finder, or run
`./Build\ TestFlight.command` from the repository root. It uses the Apple account
in Xcode Settings → Accounts to archive `MultiVanInternal`, verify its packaged
resources, and upload for **internal TestFlight testing only**. Xcode manages the
upload build number. Logs and archives stay in the ignored `.local/testflight/`
directory. After Apple processes the build, check App Store Connect → Tiny Routes
→ TestFlight. Testers play through Home → Play, as in the App Store build.

For external testing, double-click `Build External TestFlight.command`. It builds
the current working tree with the production `TinyRoutes` / `Release` scheme,
checks the packaged resources, uploads a new build, waits for processing, and
submits it to the existing **Family and friends** external group. It enables
tester notifications after Apple's beta approval. It does not create groups or
add testers. Test information and beta review contact details must already be
complete in App Store Connect.

This script uses the installed `fastlane`. Before running, set `FASTLANE_USER`
to your Apple ID and complete the first sign-in/2FA in a terminal, or set
`APP_STORE_CONNECT_API_KEY_PATH` to a fastlane API-key JSON file stored outside
the repository. External submission requires App Manager or Admin access.
Xcode's saved account handles signing, but cannot authenticate fastlane.
An existing fastlane session or API key can run without a browser login; a
locked signing keychain can still require unlocking the Mac.

Archives, IPAs and build logs stay in `.local/testflight/external-*/`. To retry
distribution after a processing, metadata or authentication failure without
uploading again, run `./Build\ External\ TestFlight.command ipa:/absolute/path/to/TinyRoutes.ipa`.
The IPA's exact version and build number are used, so a retry cannot select a
different upload. Keep API keys and passwords out of git.
Run the offline submission checks with `ruby scripts/check_external_testflight.rb`.

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
