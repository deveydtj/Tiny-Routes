# Level Runtime Architecture

## Purpose and source of truth

`RouteEngine` is the production gameplay source of truth. It owns movement,
switch rotation, package collection, the countdown, and terminal outcomes. UI
code may present engine state, but must not reproduce route or eligibility
logic.

The normative interaction rules live in
[`docs/gameplay/switch_interaction_contract.md`](../gameplay/switch_interaction_contract.md).
This document explains how the Swift implementation is divided and how data
flows through it.

## Serialized domain model

`TinyRoutes/Domain` contains the Codable level representation:

- `LevelData` stores identity, graph, special-node IDs, time/par values, schema
  version, and optional `LevelRules`.
- `RouteGraph`, `RouteNode`, and `RouteEdge` describe authored topology.
- `RoadShape` controls the standardized rendered path. `RoadAvailability`
  (`always`, `beforePackage`, or `afterPackage`) controls package-state use.
- `LevelData.effectiveRules` maps missing rules to archival `legacyGlobal`
  decode-and-replay compatibility; production schema-version-2 levels
  explicitly use `liveLookahead`.

Decoding is deliberately separate from gameplay validation. Repositories can
decode legacy JSON, while editor, generator, and test gates reject malformed or
unmigrated production content.

## Runtime graph construction

`RouteEngine.buildGraph(from:)` is the load boundary:

1. Clear all state from the previous run.
2. Verify start, package, and destination nodes exist.
3. Verify every edge endpoint exists.
4. Convert authored nodes and edges into `RuntimeRouteGraph` values and concrete
   `RoadPath` geometry.
5. Reject switches with more than four valid outgoing roads.
6. Reject a node whose authored roads all become unavailable in either package
   phase.
7. Normalize each node's active road to its first usable authored road.
8. Create the `DeliveryDot`, timer, package state, and initial eligibility state.

Authored `outgoingEdgeIDs` order is significant: it is both the initial-choice
order and the rotation order. Do not sort it in a repository, editor, or
runtime adapter.

## Update and outcome flow

`GameplayScreen` starts movement, supplies frame-independent elapsed time to
`RouteEngine.updateDot(deltaTime:)`, and pauses updates while its pause UI is
active. The engine consumes elapsed time chronologically and may cross several
roads in one update.

At each arrival the engine:

1. snaps or transitions the dot to the node;
2. collects the package when the package node is reached;
3. normalizes active roads after the package changes availability;
4. resolves destination completion or destination-before-package failure; and
5. commits to the selected usable outgoing road, or fails at a dead end.

The countdown is consumed only by gameplay updates. Reaching zero produces
`timeExpired`. Completion and all failures are terminal. Traversal uses an
internal step guard so malformed cycles cannot hang a frame.

## Switch interaction

`SwitchEligibilityService` performs a read-only walk along the dot's selected
route. It includes the remaining current road or transition, follows pass-through
nodes, and stops at the first switch, terminal node, repeated traversal state,
or safety limit. Its `SwitchEligibilitySnapshot` publishes the upcoming node,
travel time, eligible node, and diagnostic reason.

`RouteEngine.rotateSwitchNode(nodeID:)` returns `SwitchTapResult`, never a bare
success flag. In live-lookahead mode it rejects terminal, committed,
non-switchable, noneligible, and cooldown taps; an accepted tap rotates exactly
once, increments `tapCount`, records cooldown time, and immediately changes the
published active edge. `GameplayScreen` rejects paused input before calling the
engine and feeds the snapshot into `SwitchNodeView`.

Legacy mode keeps unrestricted switch selection for archived JSON, but still
rejects terminal and committed taps. This path is frozen compatibility for
decoding, replay, and migration, not an authoring option; production content
must not depend on it.

## Package-state roads

Road availability is evaluated every time outgoing roads are queried. A stored
active road that becomes unavailable is normalized to the first usable road.
Both load-time validation and runtime graph construction require every authored
nonterminal node to retain a usable road before and after package collection.

## UI boundary

The gameplay UI consumes these engine-owned values:

- runtime graph and dot position for drawing;
- `eligibleSwitchNodeID` and `upcomingSwitchTravelTime` for affordances;
- `SwitchTapResult` for accepted/rejected feedback;
- package state, tap count, remaining time, and `LevelOutcome` for HUD and flow.

UI animation may interpolate visuals, but cannot choose roads, advance the
countdown, or determine whether a tap is legal.

## Verification and safe changes

Runtime behavior is covered by `RouteEngineTests`,
`SwitchEligibilityServiceTests`, `LevelSimulationHarnessTests`, production
solution replay, and shared parity fixtures. When changing rules, movement,
road geometry, package availability, or event ordering:

1. update the normative contract;
2. update Swift and Python in the same change;
3. add or update a shared fixture;
4. run Python parity tests and the Swift test scheme; and
5. replay the production corpus before release.
