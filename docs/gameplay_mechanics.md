# Gameplay Mechanics

## Level Schema and Switch Interaction Mode

Schema version 2 levels contain an explicit `rules` object. New generated production content uses `liveLookahead`: only the first upcoming switch on the selected route can rotate, and only when its travel time is within `switchLookaheadSeconds`. Accepted taps observe `switchTapCooldownSeconds`. The normative eligibility and timing details are in [the switch interaction contract](gameplay/switch_interaction_contract.md).

```json
{
  "schemaVersion": 2,
  "rules": {
    "switchInteractionMode": "liveLookahead",
    "switchLookaheadSeconds": 1.35,
    "switchTapCooldownSeconds": 0.12
  }
}
```

Archived files may omit both fields. They retain decode-and-replay compatibility with `legacyGlobal` behavior and effective numeric defaults of 1.35 and 0.12 seconds. The mode cannot be selected for new editor or production content. Migration is deliberate: add the version 2 fields and replay the canonical solution with eligibility enforced. See the [complete level JSON reference](../Tools/LevelEditor/docs/current_level_json_shape.md) for a full valid example.

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

Usable outgoing edges are the valid edges whose package-state `availability` condition currently passes. Roads may be `always`, `beforePackage`, or `afterPackage`; omitted availability is `always`. Switch classification, rotation, look-ahead traversal, and departure use only usable edges. When package collection makes the active road unavailable, the first usable road in `outgoingEdgeIDs` order becomes active before departure. Authored nonterminal nodes must have a usable road both before and after package collection.

The tap cycle order is the order of `outgoingEdgeIDs`. At level start, the active outgoing edge is the first valid outgoing edge. Each successful tap rotates the active edge to the next valid edge, wrapping back to the first edge after the last one. Switch state persists unless the player taps the switch again. In `liveLookahead`, such taps are accepted only during the eligibility window; `legacyGlobal` retains the former global interaction solely when an archived level is decoded and replayed.

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

## Camera, Bounds, and Larger Maps

Gameplay rendering now treats level extents as the source of truth for camera behavior. Extents are calculated from all runtime nodes plus sampled road paths, then expanded by a small camera-safe margin so markers, roads, and the delivery dot stay readable near edges.

Small levels still use the original fit-to-board layout when their full extents can fit at a readable scale. Larger levels keep a stable readable scale instead of shrinking the whole puzzle to one screen. The camera follows the active delivery dot with a short eased transition and clamps the content offset so the viewport does not expose large empty areas outside the level bounds.

For larger portrait maps, gameplay shows a brief full-level preview before the dot advances. The preview uses a fit-to-level camera so the player can read the overall route, then transitions into the normal follow camera. Existing small levels skip this preview and start as before.

Known limitations:

- Camera follow is automatic; there is no manual pan or planning mode.
- The camera does not zoom dynamically during gameplay.
- The preview is intentionally brief and does not add fog of war or hidden areas.
- Bounds are derived from graph geometry and road samples, not from authored metadata in level JSON.
