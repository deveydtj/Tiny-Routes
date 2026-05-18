# Tiny Routes Level Solution Intent DSL Plan

## Purpose

Document the next-generation solution-script format before implementing it.

The current timed-action scripts are good enough to prove solvability, but they are still lower level than the puzzle intent engineers actually reason about. This plan defines a future intent-based DSL that can compile down to the existing timed-action format so the repository can keep the current test harness stable while making future scripts easier to author and review.

---

## Why Timed Scripts Are Phase 1 Only

Timed scripts were the right first step because they let the test suite prove real levels are completable through the real `RouteEngine` with very little new infrastructure.

They are still phase 1 only for four reasons:

1. They encode exact seconds instead of player intent.
2. They are brittle if dot speed, frame step, or level geometry changes.
3. They are harder to review because the winning idea is hidden inside raw timings.
4. They encourage hand-tuned values when the real requirement is usually "rotate this switch before the dot arrives."

Phase 1 therefore stays as:

- authored timed actions in JSON
- validated by existing solvability tests
- used as the compilation target for any future higher-level DSL

Phase 2 should add intent steps without replacing the current harness. The intent DSL should compile into the same `actions: [LevelSolutionAction]` shape so existing simulation and playability checks continue to work.

---

## Design Goals

The intent DSL should:

- describe **what** the player is trying to do, not exact timestamps
- stay readable in source control
- compile deterministically into timed actions
- reuse the current `LevelSimulationHarness` and `LevelHumanPlayabilityRules`
- support multi-tap switch rotations without repeating nearly identical steps

The intent DSL should not:

- change production level JSON
- require solver/search behavior
- bypass the real `RouteEngine`

---

## Proposed Script Shape

Timed scripts remain valid. A future intent-based script can add a `steps` array:

```json
{
  "levelID": "level_010",
  "description": "Route through the package path, then prepare the final branch to destination.",
  "expectedOutcome": "completed",
  "maxTaps": 3,
  "requiresWithinTimeLimit": true,
  "steps": [
    {
      "type": "beforeDotReachesNode",
      "targetNodeID": "a_switch",
      "tapNodeID": "a_switch",
      "rotateCount": 1
    },
    {
      "type": "beforeDotReachesNode",
      "targetNodeID": "c_switch",
      "tapNodeID": "c_switch",
      "rotateCount": 2
    }
  ]
}
```

`steps` should be mutually exclusive with authored `actions` in the same file. The compiler is responsible for producing the timed `actions` array used by the current harness.

---

## Step Types

### `beforeDotReachesNode`

Use this as the default step.

Meaning:

- watch the simulated run until the delivery dot is committed to approaching `targetNodeID`
- rotate `tapNodeID` before the dot reaches `targetNodeID`
- apply the tap `rotateCount` times using safe minimum spacing

Recommended fields:

```json
{
  "type": "beforeDotReachesNode",
  "targetNodeID": "switch_a",
  "tapNodeID": "switch_a",
  "rotateCount": 1
}
```

Rules:

- `targetNodeID` is the node whose arrival creates the gameplay deadline
- `tapNodeID` is the switch to rotate
- the compiled tap time must leave enough margin to satisfy human-playability rules
- if multiple safe times are possible, prefer the latest safe time so the step stays robust to earlier graph changes

This step should cover most current levels because designers usually think in terms of "set the switch before the dot gets here."

### `afterDotLeavesNode`

Use this only when a switch must not be changed until the dot has already departed from a specific node.

Meaning:

- watch the simulated run until the dot leaves `targetNodeID`
- once departure is confirmed, rotate `tapNodeID`
- apply the tap `rotateCount` times using safe minimum spacing

Recommended fields:

```json
{
  "type": "afterDotLeavesNode",
  "targetNodeID": "switch_a",
  "tapNodeID": "switch_b",
  "rotateCount": 1
}
```

Guidance:

- prefer `beforeDotReachesNode` unless this later trigger is actually needed
- compile this step to the first safe instant after the departure event, plus any spacing required for repeated rotations
- use it for cases where rotating too early would change the route the dot is currently taking away from `targetNodeID`

---

## `rotateCount` Behavior

`rotateCount` means "perform this many successful switch rotations on `tapNodeID` when the step triggers."

Rules:

1. Omitted `rotateCount` defaults to `1`.
2. `rotateCount` must be positive.
3. A value greater than `1` compiles into repeated taps on the same node.
4. Repeated taps must be separated by at least `LevelHumanPlayabilityRules.minimumTapSpacingSeconds`.
5. The compiler should fail clearly if the requested rotation count cannot fit inside the safe timing window.

Example expansion:

```json
{
  "type": "beforeDotReachesNode",
  "targetNodeID": "switch_b",
  "tapNodeID": "switch_b",
  "rotateCount": 2
}
```

Compiles to the same effect as two timed taps on `switch_b`, spaced far enough apart to satisfy playability rules.

---

## How Intent Steps Convert to Timed Actions

The intent DSL should compile into today's timed `actions` format instead of introducing a second execution path.

Recommended compilation flow:

1. Load the level and the intent script.
2. Build a `RouteEngine` with the same parameters used by solvability tests.
3. Simulate forward in time while tracking dot movement, current node transitions, and pending intent steps.
4. When the next step's trigger condition becomes true, compute the latest safe tap time for that step.
5. Expand `rotateCount` into one or more timed taps separated by the minimum spacing.
6. Append those taps to a generated `actions` array.
7. Continue simulation using the updated switch state so later steps are resolved against the real route that earlier steps produced.
8. Run the generated timed actions through the existing `LevelSimulationHarness`.

Important compiler rules:

- Compilation must use the real engine state, not only static graph distance.
- Generated times should be deterministic for the same level and script.
- Compiler errors must mention `levelID`, step index, and the trigger that could not be satisfied.
- Generated actions must still pass the current human-playability rules.

This keeps one authoritative execution path:

`intent steps -> compiled timed actions -> LevelSimulationHarness -> LevelSolvabilityResult`

---

## Examples

### One-Switch Level

```json
{
  "levelID": "level_002",
  "description": "Flip the only switch before the dot arrives.",
  "expectedOutcome": "completed",
  "maxTaps": 1,
  "requiresWithinTimeLimit": true,
  "steps": [
    {
      "type": "beforeDotReachesNode",
      "targetNodeID": "choice",
      "tapNodeID": "choice"
    }
  ]
}
```

Reading this script should immediately tell a reviewer the puzzle idea: there is one important switch and it must be rotated before arrival.

### Multi-Switch Level

```json
{
  "levelID": "level_010",
  "description": "Route toward the package branch, then open the final destination branch.",
  "expectedOutcome": "completed",
  "maxTaps": 3,
  "requiresWithinTimeLimit": true,
  "steps": [
    {
      "type": "beforeDotReachesNode",
      "targetNodeID": "a_switch",
      "tapNodeID": "a_switch",
      "rotateCount": 1
    },
    {
      "type": "afterDotLeavesNode",
      "targetNodeID": "a_switch",
      "tapNodeID": "c_switch",
      "rotateCount": 2
    }
  ]
}
```

This example shows why both triggers can be useful:

- the first switch must be ready before arrival
- the second switch should wait until the dot has already committed to leaving the first area

---

## Rollout Recommendation

Implement the DSL only after the current timed-script infrastructure is stable and trusted.

Suggested rollout:

1. keep all existing timed scripts working
2. add a compiler that turns `steps` into timed `actions`
3. test compiler output against a few known-good levels
4. migrate scripts gradually only when the intent version is clearly more readable

Until that compiler exists, timed scripts remain the source of truth for solvability tests.
