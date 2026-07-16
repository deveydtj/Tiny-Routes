# Runtime Parity Architecture

## Contract

Swift `RouteEngine` is the production source of truth. Python
`tiny_routes_core.simulation.RuntimeSimulator` is a deterministic parity
implementation used by the generator and editor. Both are governed by
[`docs/gameplay/switch_interaction_contract.md`](../gameplay/switch_interaction_contract.md),
including floating-point tolerance, route order, package-state availability,
eligibility, cooldown, commitment, event ordering, and safety limits.

Parity means that the same level, initial state, actions, speed, and elapsed-time
steps produce the same accepted/rejected taps, active road states, package/order
events, terminal outcome, and relevant elapsed time. Similar-looking UI output
is not sufficient.

## Shared serialized inputs

`SharedFixtures/RuntimeParity/manifest.json` is the fixture index. Every entry
points to:

- `level.json`: the language-neutral level and rules;
- `events.json`: ordered absolute-time tap actions and a description; and
- `expected.json`: outcome, failure reason, tap count, package/destination state,
  optional final active roads, and optional safety limit.

Both test targets discover this directory from the repository root. Do not copy
fixtures into language-specific test resources or maintain a second manifest.

## Python side

`tiny_routes_core.models` decodes the fixture without Qt or generator imports.
`RuntimeState.initialize` constructs package-aware runtime graph state.
`switch_eligibility` and `RuntimeSimulator` apply the contract with a `1e-9`
numeric tolerance and produce typed tap records plus chronological events.

`Tools/TinyRoutesCore/tests/test_switch_eligibility_and_simulator.py` executes
the manifest cases against their expected files. The generator's
`run_runtime_parity_fixtures.py` can export normalized traces. Normalization
rounds report timestamps only after simulation and retains outcome, package
order, taps, final switch states, elapsed time, and events.

## Swift side

`RouteEngine`, `SwitchEligibilityService`, and `LevelSimulationHarness` decode
the same level/sidecar shape and exercise production movement. The Swift suites
cover boundary eligibility, tap rejection/rotation, package gates, outcome
ordering, and production solution replay. `RuntimeParityFixtureTests` also
validates shared-fixture discovery and directly replays package-state fixtures.

Generator-triggered Swift validation uses `SwiftTestService`. For an accepted
batch it passes selected level IDs and external level/solution directories via:

- `TINY_ROUTES_VALIDATION_LEVEL_IDS`
- `TINY_ROUTES_LEVELS_DIR`
- `TINY_ROUTES_SOLUTIONS_DIR`

`LevelSolvabilityTests.testRequestedGeneratedLevelsCompleteFromEnvironmentDirectories`
then decodes and replays the files that would be published, rather than a stale
bundled copy.

## Generator parity gate

`SwiftValidationGate` examines concrete graph behavior and mechanic metadata.
Cycles, rings, revisits, rejoins, repeated taps, four-way switches, multiphase
routes, and explicitly marked recipes require Swift validation. A dry run may
report a required gate as skipped; production generation may not accept it
without a passing Swift summary.

`RuntimeParityValidator` stores the decision, reason, command, environment,
status, failure details, and stable failure reason on the candidate. Parsed
failure reasons distinguish switch-tap, package-order, solution-sidecar, and
generic Swift parity failures. These codes are production blockers.

## Event-order invariants

Keep these invariants synchronized:

1. taps at a timestamp are applied before advancing beyond that timestamp;
2. accepted taps alone rotate, increment tap count, and start cooldown;
3. commitment closes the window before movement continues on the chosen road;
4. package collection precedes availability normalization and destination
   resolution at the same arrival;
5. pause freezes gameplay time and cooldown;
6. completion/failure rejects later input; and
7. safety limits terminate traversal deterministically instead of hanging.

Never use UI frame timestamps or wall-clock time in a parity fixture.

## Adding or changing a fixture

1. Add one directory containing the three required JSON files.
2. Add it once to `manifest.json`.
3. Use explicit rules, action times away from scheduler jitter, and an explicit
   safety limit when testing cycles.
4. Run the core fixture test and normalized Python trace exporter.
5. Add or update the Swift assertion that exercises the production behavior.
6. Run `python scripts/run_all_checks.py --swift-tests`.

If a change is intentional, update the contract and both implementations in the
same commit. Never update only `expected.json` to make a disagreement disappear.

