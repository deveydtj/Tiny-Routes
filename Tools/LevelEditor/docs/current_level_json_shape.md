# Current Level JSON Shape

This document describes the version 2 level format and the legacy production files in `TinyRoutes/Resources/Levels/`. New files should use version 2; version 1 remains readable during migration.

---

## Top-Level Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `schemaVersion` | integer | version 2: yes; legacy: no | Schema revision. Omitted files are treated as version 1. New files use `2`. |
| `rules` | object | version 2: yes; legacy: no | Switch interaction rules (see below). Omitted rules use the legacy defaults. |
| `id` | string | yes | Unique level identifier, e.g. `"level_001"` |
| `name` | string | yes | Human-readable level title, e.g. `"First Pickup"` |
| `graph` | object | yes | Contains the `nodes` and `edges` arrays (see below) |
| `startNodeID` | string | yes | `id` of the node where the dot begins |
| `packageNodeID` | string | yes | `id` of the node that holds the package |
| `destinationNodeID` | string | yes | `id` of the node the dot must reach after picking up the package |
| `timeLimitSeconds` | integer | yes | Maximum seconds the player has to complete the level |
| `parTaps` | integer | yes | The par (expected) number of switch taps to solve the level optimally |
| `tutorialMessage` | string | no | Short gameplay instruction displayed above the board. Use only while introducing a mechanic. |
| `solution` | object | no | Embedded solution hint present in some levels (see below) |

## Version 2 `rules` Object

| Field | Type | Required | Description |
|---|---|---|---|
| `switchInteractionMode` | string | yes | `"liveLookahead"` for newly generated production levels. `"legacyGlobal"` is reserved for unmigrated content. |
| `switchLookaheadSeconds` | number | yes | Positive, finite travel-time window in which the first upcoming switch can be tapped. |
| `switchTapCooldownSeconds` | number | yes | Finite, nonnegative delay between accepted taps. |

When `schemaVersion` or `rules` is missing, the runtime uses `legacyGlobal`, a 1.35-second look-ahead value, and a 0.12-second cooldown. The numeric values complete the effective rules object, but legacy-global interaction does not use look-ahead eligibility. Invalid explicit values are validation errors.

To migrate an old file, add `"schemaVersion": 2` and an explicit `rules` object, replay its solution under live look-ahead behavior, and adjust tap timestamps or redesign the route if necessary. Keep the old file in legacy mode until that replay passes.

---

## `graph` Object

| Field | Type | Required | Description |
|---|---|---|---|
| `nodes` | array of node objects | yes | All route nodes in the level |
| `edges` | array of edge objects | yes | All directed edges connecting nodes |

---

## Node Object (`graph.nodes[*]`)

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique node identifier within the level, e.g. `"start"`, `"package"`, `"switch_a"` |
| `x` | float | yes | Horizontal position in the level's graph coordinate space |
| `y` | float | yes | Vertical position in the level's graph coordinate space |
| `outgoingEdgeIDs` | array of strings | yes | IDs of edges that leave this node. Empty array `[]` for terminal nodes (destination, dead ends). |

### Node Role Notes

Nodes are identified by their `id` string and by their role in the top-level fields. There is no explicit `type` field on nodes in the JSON. The role of each node is inferred:

| Role | How it is identified |
|---|---|
| Start | `id` matches top-level `startNodeID` |
| Package | `id` matches top-level `packageNodeID` |
| Destination | `id` matches top-level `destinationNodeID` |
| Switch | Has 2 or more `outgoingEdgeIDs` and is not the package or destination node |
| Dead end | Has 0 `outgoingEdgeIDs` and is not the destination node |
| Route (plain) | Has exactly 1 `outgoingEdgeIDs` and no special role |

---

## Edge Object (`graph.edges[*]`)

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique edge identifier within the level, e.g. `"e_start_package"` |
| `fromNodeID` | string | yes | `id` of the node this edge originates from |
| `toNodeID` | string | yes | `id` of the node this edge leads to |
| `roadShape` | string | no | Optional road rendering hint. Allowed values: `"horizontalFirst"`, `"verticalFirst"`. When omitted, the Swift engine defaults to `horizontalFirst`. |
| `availability` | string | no | Package-state condition for using the road: `"always"`, `"beforePackage"`, or `"afterPackage"`. Omitted values decode as `"always"`. Unknown values are invalid. |

Road availability is evaluated whenever the runtime chooses or rotates an outgoing road. A `beforePackage` road is usable only until the package is collected; an `afterPackage` road is usable only after collection. Every authored nonterminal node must retain at least one usable outgoing road in both package states so a condition cannot create an accidental dead end.

---

## `solution` Object (optional, top-level)

Present in some level files as an embedded hint. Not decoded by the main Swift `LevelData` struct.

| Field | Type | Required | Description |
|---|---|---|---|
| `tapNodeIDs` | array of strings | yes (when present) | Ordered list of node IDs to tap to complete the level |

Example:

```json
"solution": {
  "tapNodeIDs": ["choice"]
}
```

Canonical production solutions use sidecar files; embedded solutions are retained only for backward compatibility.

---

## Solution Sidecar Files (`level_###.solution.json`)

Solution sidecar files live in `TinyRoutesTests/Resources/LevelSolutions/` and are used by the test infrastructure. They are separate from the level JSON files.

| Field | Type | Required | Description |
|---|---|---|---|
| `levelID` | string | yes | Must match the level `id`, e.g. `"level_001"` |
| `description` | string | yes | Human-readable description of the solution |
| `expectedOutcome` | string | yes | Expected result. Currently always `"completed"` |
| `maxTaps` | integer | yes | Maximum number of taps the solution uses |
| `requiresWithinTimeLimit` | boolean | yes | Whether the solution must finish within `timeLimitSeconds` |
| `actions` | array of action objects | yes | Ordered list of timed tap actions. Empty array for no-tap levels. |

### Action Object (`actions[*]`)

| Field | Type | Required | Description |
|---|---|---|---|
| `timeSeconds` | float | yes | Time in seconds at which this tap occurs |
| `tapNodeID` | string | yes | `id` of the node to tap at this time |

---

## Fields Present in Swift Models but Not in Level JSON

The following fields exist in the Swift runtime models but are computed at runtime and are not stored in the level JSON files:

- `RoadShape` default: When `roadShape` is omitted from an edge, the Swift `RoadPath.make(from:to:shape:)` defaults to `.horizontalFirst`. This default is not written back into the JSON.
- `RoadAvailability` default: When `availability` is omitted from an edge, Swift and Python both treat it as `always`.
- `RouteNode.validateOutgoingEdges(against:)`: A validation helper on `RouteNode` that confirms `outgoingEdgeIDs` is consistent with the graph edges list. This is test/debug-time only and not stored in JSON.

---

## Fields Present in Level JSON but Not in Swift `LevelData`

- `solution.tapNodeIDs`: Present in `level_002.json` as a convenience hint. The Swift `LevelData` struct does not have a `solution` property and does not decode this field. The canonical solution format is the `level_###.solution.json` sidecar file.

---

## Example: `level_001.json`

This is a complete legacy example. It intentionally omits `schemaVersion` and `rules`.

```json
{
  "id": "level_001",
  "name": "First Pickup",
  "graph": {
    "nodes": [
      { "id": "start", "x": 0.0, "y": 0.0, "outgoingEdgeIDs": ["e_start_package"] },
      { "id": "package", "x": 1.5, "y": 0.0, "outgoingEdgeIDs": ["e_package_destination"] },
      { "id": "destination", "x": 3.0, "y": 0.0, "outgoingEdgeIDs": [] }
    ],
    "edges": [
      { "id": "e_start_package", "fromNodeID": "start", "toNodeID": "package" },
      { "id": "e_package_destination", "fromNodeID": "package", "toNodeID": "destination" }
    ]
  },
  "startNodeID": "start",
  "packageNodeID": "package",
  "destinationNodeID": "destination",
  "timeLimitSeconds": 30,
  "parTaps": 0
}
```

## Complete Version 2 Example

```json
{
  "schemaVersion": 2,
  "rules": {
    "switchInteractionMode": "liveLookahead",
    "switchLookaheadSeconds": 1.35,
    "switchTapCooldownSeconds": 0.12
  },
  "id": "level_101",
  "name": "Live First Choice",
  "graph": {
    "nodes": [
      { "id": "start", "x": 0.0, "y": 0.0, "outgoingEdgeIDs": ["e_start_switch"] },
      { "id": "switch", "x": 1.0, "y": 0.0, "outgoingEdgeIDs": ["e_switch_dead", "e_switch_package"] },
      { "id": "dead", "x": 2.0, "y": -1.0, "outgoingEdgeIDs": [] },
      { "id": "package", "x": 2.0, "y": 1.0, "outgoingEdgeIDs": ["e_package_destination"] },
      { "id": "destination", "x": 3.0, "y": 1.0, "outgoingEdgeIDs": [] }
    ],
    "edges": [
      { "id": "e_start_switch", "fromNodeID": "start", "toNodeID": "switch" },
      { "id": "e_switch_dead", "fromNodeID": "switch", "toNodeID": "dead" },
      { "id": "e_switch_package", "fromNodeID": "switch", "toNodeID": "package", "roadShape": "verticalFirst" },
      { "id": "e_package_destination", "fromNodeID": "package", "toNodeID": "destination" }
    ]
  },
  "startNodeID": "start",
  "packageNodeID": "package",
  "destinationNodeID": "destination",
  "timeLimitSeconds": 30,
  "parTaps": 1
}
```

## Example: `level_002.json` (with optional `roadShape` and `solution`)

```json
{
  "id": "level_002",
  "name": "First Choice",
  "graph": {
    "nodes": [
      { "id": "start", "x": 0.0, "y": 0.0, "outgoingEdgeIDs": ["e_start_approach"] },
      { "id": "approach", "x": 1.0, "y": 0.0, "outgoingEdgeIDs": ["e_approach_choice"] },
      { "id": "choice", "x": 2.0, "y": 0.0, "outgoingEdgeIDs": ["e_choice_bypass", "e_choice_package"] },
      { "id": "package", "x": 3.0, "y": 0.9, "outgoingEdgeIDs": ["e_package_destination"] },
      { "id": "bypass", "x": 3.0, "y": -0.9, "outgoingEdgeIDs": [] },
      { "id": "destination", "x": 3.0, "y": 1.8, "outgoingEdgeIDs": [] }
    ],
    "edges": [
      { "id": "e_start_approach", "fromNodeID": "start", "toNodeID": "approach" },
      { "id": "e_approach_choice", "fromNodeID": "approach", "toNodeID": "choice" },
      { "id": "e_choice_bypass", "fromNodeID": "choice", "toNodeID": "bypass", "roadShape": "horizontalFirst" },
      { "id": "e_choice_package", "fromNodeID": "choice", "toNodeID": "package", "roadShape": "horizontalFirst" },
      { "id": "e_package_destination", "fromNodeID": "package", "toNodeID": "destination" }
    ]
  },
  "startNodeID": "start",
  "packageNodeID": "package",
  "destinationNodeID": "destination",
  "timeLimitSeconds": 36,
  "parTaps": 1,
  "solution": {
    "tapNodeIDs": ["choice"]
  }
}
```
