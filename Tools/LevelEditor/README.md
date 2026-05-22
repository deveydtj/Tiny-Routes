# Tiny Routes Level Editor

This is an internal GUI tool for creating and editing Tiny Routes level files.

## Documentation

- [Current Level JSON Shape](docs/current_level_json_shape.md) — Describes the exact fields used by the real `level_###.json` files. Read this before implementing Python data models.
- [Solution JSON Shape](docs/solution_json_shape.md) — Documents the sidecar solution scripts used by the Swift test harness and Level Editor.

## Validation

The Level Editor has two validation paths:

- **Validate** is fast and Python-only. It checks the level JSON structure, graph references, route-order reachability, solution metadata, solution action timing, and whether every solution `tapNodeID` exists in the level graph.
- **Run Tests** runs the Swift solvability test harness through `xcodebuild`. This is the source of truth for gameplay completion because it uses the real Tiny Routes runtime and test infrastructure.

Python validation does not duplicate the Swift gameplay engine. It catches data integrity problems early, then Swift tests verify that the scripted solution truly completes the level.

Common solution validation failures:

- `solution_level_id_mismatch`: the sidecar `levelID` does not match the open level. Update the solution file or reopen the matching level.
- `max_taps_less_than_action_count` / `max_taps_greater_than_action_count`: `maxTaps` should equal the number of scripted tap actions.
- `solution_action_unknown_tap_node`: an action references a node ID that is not present in the graph.
- `tap_node_is_not_switchable`: an action taps a node with fewer than two outgoing edges, so the tap likely cannot change route selection.
- `solution_actions_not_sorted`: action times must be sorted by `timeSeconds`.
- `solution_marked_placeholder`: the editor created a blank placeholder because no sidecar solution was found.
