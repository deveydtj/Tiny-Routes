# Current Level JSON Shape

This document describes the exact fields used by the real `level_###.json` files in `TinyRoutes/Resources/Levels/` as of the time it was written. Use this as the reference when implementing Python data models.

---

## Top-Level Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique level identifier, e.g. `"level_001"` |
| `name` | string | yes | Human-readable level title, e.g. `"First Pickup"` |
| `graph` | object | yes | Contains the `nodes` and `edges` arrays (see below) |
| `startNodeID` | string | yes | `id` of the node where the dot begins |
| `packageNodeID` | string | yes | `id` of the node that holds the package |
| `destinationNodeID` | string | yes | `id` of the node the dot must reach after picking up the package |
| `timeLimitSeconds` | integer | yes | Maximum seconds the player has to complete the level |
| `parTaps` | integer | yes | The par (expected) number of switch taps to solve the level optimally |
| `solution` | object | no | Embedded solution hint present in some levels (see below) |

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

---

## `solution` Object (optional, top-level)

Present in some level files as an embedded hint. Not decoded by the main Swift `LevelData` struct.

| Field | Type | Required | Description |
|---|---|---|---|
| `tapNodeIDs` | array of strings | yes (when present) | Ordered list of node IDs to tap to complete the level |

Example from `level_002.json`:

```json
"solution": {
  "tapNodeIDs": ["choice"]
}
```

This field is only present in `level_002.json` among the current ten levels.

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
- `RouteNode.validateOutgoingEdges(against:)`: A validation helper on `RouteNode` that confirms `outgoingEdgeIDs` is consistent with the graph edges list. This is test/debug-time only and not stored in JSON.

---

## Fields Present in Level JSON but Not in Swift `LevelData`

- `solution.tapNodeIDs`: Present in `level_002.json` as a convenience hint. The Swift `LevelData` struct does not have a `solution` property and does not decode this field. The canonical solution format is the `level_###.solution.json` sidecar file.

---

## Example: `level_001.json`

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
