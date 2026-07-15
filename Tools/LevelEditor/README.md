# Tiny Routes Level Editor

This is an internal GUI tool for creating and editing Tiny Routes level files.

## Documentation

- [Current Level JSON Shape](docs/current_level_json_shape.md) — Describes the exact fields used by the real `level_###.json` files. Read this before implementing Python data models.
- [Solution JSON Shape](docs/solution_json_shape.md) — Documents the sidecar solution scripts used by the Swift test harness and Level Editor.
- [Manual Usability Test](docs/manual_usability_test.md) — A no-coaching, end-to-end novice workflow for authoring, playtesting, saving, reopening, and Swift-verifying a live-routing level.

## Validation

The Level Editor has two validation paths:

- **Validate** is fast and Python-only. It checks the level JSON structure, graph references, route-order reachability, solution metadata, solution action timing, and whether every solution `tapNodeID` exists in the level graph.
- **Run Tests** runs the Swift solvability test harness through `xcodebuild`. This is the source of truth for gameplay completion because it uses the real Tiny Routes runtime and test infrastructure.

The dockable **Puzzle Analysis** panel updates after document edits and reports
measured decision count, route dependencies, failure outcomes, activation
windows, decision spacing, estimated difficulty, and the legacy front-load
diagnostic. Double-click a recommendation to select its affected node. **Run
All Checks** performs structural validation, verified-solution search, saved
solution replay, front-load diagnosis, decision-quality analysis, and the Swift
parity test gate in one action.

Generated candidates can be opened directly from the generator's **Open in
Level Editor** action. The generator writes an ignored editor-draft bundle so
the level, solution sidecar, and quality report open together. Imported score
factors appear at the top of Puzzle Analysis. Use **File > Save Draft** while
iterating, then **Tools > Promote Draft to Production Level**; production level
and solution overwrites still require confirmation.

In Select mode, Shift-click adds or removes items from the selection and a
background drag creates a marquee selection. The Edit menu aligns and
distributes selected nodes. Arrow keys nudge selected nodes by 0.05 level units;
Shift+Arrow uses a 0.25-unit nudge. Each arrangement is one undoable edit.

Use **View > Fit View**, **Zoom to Selection**, or **Reset Zoom** to frame the
canvas. Pan at any time with the middle mouse button, or hold Space and drag
with the left mouse button. Property-only edits preserve the current zoom and
canvas center.

While a document is dirty, the editor periodically writes an atomic recovery
bundle to the operating system's application-data directory; it never writes
over the source level automatically. After an unclean shutdown, the next editor
launch offers to recover or discard that bundle. Saving, discarding the dirty
document, or closing cleanly removes the recovery data.

Python validation does not duplicate the Swift gameplay engine. It catches data integrity problems early, then Swift tests verify that the scripted solution truly completes the level.

Common solution validation failures:

- `solution_level_id_mismatch`: the sidecar `levelID` does not match the open level. Update the solution file or reopen the matching level.
- `max_taps_less_than_action_count` / `max_taps_greater_than_action_count`: `maxTaps` should equal the number of scripted tap actions.
- `solution_action_unknown_tap_node`: an action references a node ID that is not present in the graph.
- `tap_node_is_not_switchable`: an action taps a node with fewer than two outgoing edges, so the tap likely cannot change route selection.
- `solution_actions_not_sorted`: action times must be sorted by `timeSeconds`.
- `solution_marked_placeholder`: the editor created a blank placeholder because no sidecar solution was found.
