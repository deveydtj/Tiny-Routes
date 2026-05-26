# Gameplay Mechanics

## Switch Nodes

Tiny Routes uses the existing level JSON graph shape for switch behavior. No JSON schema migration is required for 4-way switch intersections.

A node's switch behavior is inferred from its valid outgoing directed edges:

- `0` valid outgoing edges: terminal or dead-end node.
- `1` valid outgoing edge: pass-through node.
- `2` valid outgoing edges: 2-way switch.
- `3` valid outgoing edges: 3-way switch.
- `4` valid outgoing edges: 4-way intersection switch.
- `5+` valid outgoing edges: invalid and unsupported.

Valid outgoing edges are the edge IDs listed in `RouteNode.outgoingEdgeIDs` that also exist in the graph and start at that node. Missing edge IDs or edge IDs that belong to another source node do not count as valid switch choices.

The tap cycle order is the order of `outgoingEdgeIDs`. At level start, the active outgoing edge is the first valid outgoing edge. Each successful tap rotates the active edge to the next valid edge, wrapping back to the first edge after the last one. Switch state persists for the rest of the level unless the player taps the switch again.

Roads are directed. Adding an outgoing edge from `central_switch` to `package` does not create a return route from `package` to `central_switch`; that return path must be represented by its own directed edge.

A 4-way switch intersection is represented with four outgoing directed edges on the same node:

```json
{
  "id": "central_switch",
  "x": 0.0,
  "y": 0.0,
  "outgoingEdgeIDs": [
    "e_central_dead_end",
    "e_central_package",
    "e_central_destination",
    "e_central_side_branch"
  ]
}
```

The package must still be collected before the destination is reached. A valid 4-way level usually routes the dot from the package branch back to the central switch before sending it to the destination branch.

In the Level Editor, outgoing edge order is displayed in tap-cycle order. The default active edge is the first valid listed edge. The editor's cardinal sort helper uses clockwise order starting at Up: Up, Right, Down, Left, with diagonal directions placed between those cardinal directions.
