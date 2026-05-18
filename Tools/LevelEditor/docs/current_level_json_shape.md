# Current Level JSON Shape

This document describes the exact fields used by the production level JSON files found in `TinyRoutes/Resources/Levels/`.

It was produced by inspecting `level_001.json`, `level_002.json`, `level_003.json`, `level_004.json`, `level_005.json`, and `level_010.json`, and by cross-referencing the Swift domain models in `TinyRoutes/Domain/`.

Use this document to implement the Python editor models in Task 005.

---

## Top-Level Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | Yes | Matches the file name, e.g. `"level_001"` |
| `name` | string | Yes | Human-readable level name, e.g. `"First Pickup"` |
| `graph` | object | Yes | Contains `nodes` and `edges` arrays |
| `startNodeID` | string | Yes | ID of the start node in the graph |
| `packageNodeID` | string | Yes | ID of the package pickup node |
| `destinationNodeID` | string | Yes | ID of the delivery destination node |
| `timeLimitSeconds` | integer | Yes | Time limit in seconds (must be > 0) |
| `parTaps` | integer | Yes | Target number of switch taps for par score (0 = no taps needed) |
| `solution` | object | No | Inline solution hint; only present in some levels (see below) |

### Example (level_001.json — minimal level, no switches)

```json
{
  "id": "level_001",
  "name": "First Pickup",
  "graph": { ... },
  "startNodeID": "start",
  "packageNodeID": "package",
  "destinationNodeID": "destination",
  "timeLimitSeconds": 30,
  "parTaps": 0
}
```

### Example (level_002.json — includes inline solution)

```json
{
  "id": "level_002",
  "name": "First Choice",
  ...
  "parTaps": 1,
  "solution": {
    "tapNodeIDs": ["choice"]
  }
}
```

---

## `graph` Object

The `graph` object contains two arrays:

| Field | Type | Required | Notes |
|---|---|---|---|
| `nodes` | array of node objects | Yes | All nodes in the level graph |
| `edges` | array of edge objects | Yes | All directed edges in the level graph |

---

## Node Object

Each entry in `graph.nodes` has the following fields:

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | Yes | Unique within the level. Convention: descriptive names like `"start"`, `"package"`, `"choice"`, `"dead_end"`, `"a_switch"` |
| `x` | number (float) | Yes | Horizontal position in level space. Range is approximately 0.0–6.0 across observed levels |
| `y` | number (float) | Yes | Vertical position in level space. Positive = down on screen. Negative = up |
| `outgoingEdgeIDs` | array of string | Yes | IDs of edges that depart from this node. Empty array `[]` for terminal nodes (destination, dead end) |

There is **no explicit `type` field** in the JSON for nodes. The node's role (start, package, destination, switch, dead end, route) is inferred by the editor and tests from:
- Matching `startNodeID`, `packageNodeID`, `destinationNodeID` at the top level
- The number of outgoing edges (0 = terminal; 1 = through-node or start; 2+ = switch)
- Node ID naming conventions (e.g. `"dead_end"`, `"switch"`, `"loop"`)

### Example nodes

```json
{ "id": "start",       "x": 0.0, "y": 0.0, "outgoingEdgeIDs": ["e_start_approach"] }
{ "id": "choice",      "x": 2.0, "y": 0.0, "outgoingEdgeIDs": ["e_choice_bypass", "e_choice_package"] }
{ "id": "destination", "x": 3.0, "y": 1.8, "outgoingEdgeIDs": [] }
{ "id": "dead_end",    "x": 5.0, "y": 1.2, "outgoingEdgeIDs": [] }
```

---

## Edge Object

Each entry in `graph.edges` has the following fields:

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | Yes | Unique within the level. Convention: `"e_<fromNode>_<toNode>"` |
| `fromNodeID` | string | Yes | ID of the source node |
| `toNodeID` | string | Yes | ID of the target node |
| `roadShape` | string | No | Optional rendering hint. Values: `"horizontalFirst"` or `"verticalFirst"`. Absent means straight line or default shape |

Every edge listed in `graph.edges` must also appear in the `outgoingEdgeIDs` of the corresponding `fromNode`.

### Example edges

```json
{ "id": "e_start_approach",  "fromNodeID": "start",  "toNodeID": "approach" }
{ "id": "e_choice_bypass",   "fromNodeID": "choice", "toNodeID": "bypass",  "roadShape": "horizontalFirst" }
{ "id": "e_choice_package",  "fromNodeID": "choice", "toNodeID": "package", "roadShape": "horizontalFirst" }
```

---

## `solution` Object (Optional, Inline)

Some levels include an inline `solution` object at the top level. This is present in levels that were authored with a known tap sequence.

| Field | Type | Notes |
|---|---|---|
| `tapNodeIDs` | array of string | Ordered list of switch node IDs the player must tap to solve the level |

```json
"solution": {
  "tapNodeIDs": ["choice"]
}
```

Not all levels have this field. It is absent from levels with `parTaps: 0` (levels that require no switch taps).

---

## Node Role Inference Rules (Editor Logic)

Because the JSON has no explicit type field, the Python editor infers node roles as follows:

| Role | Inference rule |
|---|---|
| **Start** | `node.id == level.startNodeID` |
| **Package** | `node.id == level.packageNodeID` |
| **Destination** | `node.id == level.destinationNodeID` |
| **Dead end** | Terminal node (`outgoingEdgeIDs == []`) that is not the destination |
| **Switch** | Has two or more outgoing edges (branching node) |
| **Route node** | Has exactly one outgoing edge, and is not start/package/destination |

---

## Swift Model Reference

These are the Swift structs that define the authoritative data shape:

```swift
// TinyRoutes/Domain/LevelData.swift
struct LevelData: Identifiable, Codable {
    let id: String
    var name: String
    var graph: RouteGraph
    var startNodeID: String
    var packageNodeID: String
    var destinationNodeID: String
    var timeLimitSeconds: Int
    var parTaps: Int
}

// TinyRoutes/Domain/RouteGraph.swift
struct RouteGraph: Codable {
    var nodes: [RouteNode]
    var edges: [RouteEdge]
}

// TinyRoutes/Domain/RouteNode.swift
struct RouteNode: Identifiable, Codable {
    let id: String
    var x: Double
    var y: Double
    var outgoingEdgeIDs: [String]
}

// TinyRoutes/Domain/RouteEdge.swift
struct RouteEdge: Identifiable, Codable {
    let id: String
    let fromNodeID: String
    let toNodeID: String
    var roadShape: RoadShape?   // optional: "horizontalFirst" | "verticalFirst"
}
```

The Python editor models in Task 005 must match these field names exactly so that level files load and save without data loss.

---

## Fields Present in Swift but Absent from JSON

| Swift field | Notes |
|---|---|
| `RouteEdge.roadShape` | Exists in Swift as `RoadShape?`. Present in JSON only when the edge uses a non-default path shape. If absent from JSON, Swift decodes it as `nil` and uses the default straight rendering. |

The `solution` object is not part of the official `LevelData` Swift struct. It appears to be a separate optional field that some levels carry in their JSON. The canonical solution files used by tests live in `TinyRoutesTests/Resources/LevelSolutions/` as `.solution.json` sidecar files.

---

## Observations Across Levels 001–010

| Level | Switches | Dead ends | Inline solution |
|---|---|---|---|
| 001 | 0 | 0 | No |
| 002 | 1 (`choice`) | 1 (`bypass`) | Yes — `["choice"]` |
| 003 | 2 (`pickup_switch`, `gate`) | 0 | No |
| 004 | 2 (`west_switch`, `east_switch`) | 0 | No |
| 005 | 2 (`approach`, `finish_switch`) | 0 | No |
| 006–009 | (similar variety) | (varies) | No |
| 010 | 3 (`a_switch`, `b_switch`, `c_switch`) | 1 (`dead_end`) | No |

The editor should handle 0–5 switches and 0–3 dead ends without issue.
