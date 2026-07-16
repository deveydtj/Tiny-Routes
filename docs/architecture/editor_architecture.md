# Level Editor Architecture

## Process and dependency layers

The PySide6 editor starts in `Tools/LevelEditor/run_level_editor.py` and creates
`LevelEditorMainWindow`. The window composes four layers:

- **Models:** lossless `tiny_routes_core` level/solution models plus small
  editor-state models such as `EditorTool` and `PlaytestState`.
- **Controllers and commands:** document mutation, validation, analysis, and
  playtest workflows.
- **Services and repositories:** file I/O, validation, rename/reference safety,
  runtime replay/search, autosave, analysis, and external checks.
- **UI:** canvas scene/view/items, toolbars, palette, properties, solution,
  validation, and puzzle-analysis panels.

Qt types stay out of shared models and core validation. Generator and headless
tests can therefore reuse those layers without launching the UI.

## Document ownership and mutation

`DocumentController` owns the active `LevelDocument`, optional `SolutionModel`,
and `QUndoStack`. It is the only graph/metadata mutation boundary. Canvas,
properties, solution, alignment, rename, and delete actions call controller
methods; commands snapshot before/after state and publish `document_changed`.

This boundary guarantees:

- every mutating editor action is undoable and redoable;
- dirty state is `not undo_stack.isClean()` rather than an independent flag;
- node/edge renames update graph references and solution tap IDs together; and
- save marks the current undo index clean without discarding history.

New editing features must add a controller method and an appropriate command;
they must not mutate `_current_document` or scene items directly.

## File and model round trips

`LevelFileRepository` and `SolutionFileRepository` handle UTF-8 JSON, typed
repository errors, and canonical pretty printing. Shared core models retain
unknown top-level, graph, node, edge, rules, solution, and action fields in
`_extra`, so opening and saving does not erase extensions.

The level and solution are separate files. The solution repository first looks
for a sibling `<level>.solution.json`, then the test-resource sidecar directory.
Production-like IDs and filenames are normalized by `LevelIdentityService`.

## Tools and canvas

The editor has explicit Select, Place Node, Connect, and Playtest modes.
`LevelCanvasView` owns viewport zoom/pan and delegates model interaction to its
scene. The scene renders nodes, orthogonal roads, connection handles, grid and
snap feedback, selection, validation overlays, and playtest overlays. Drag/drop
palette placement and click placement both resolve model coordinates before
asking the window/controller to create a node.

Connection handles create directed roads; visible toolbar state selects road
shape and optional bidirectional creation. Scene items are projections of the
document and are rebuilt or updated after controller signals.

## Validation and analysis

`ValidationController` deep-copies the current document/solution, debounces
lightweight checks, and discards superseded generations. It merges:

- structural and package-state validation;
- solution-sidecar validation; and
- inexpensive layout overlays.

Messages carry related node, edge, or area data so the validation panel can
focus the canvas. Error/warning definitions are shared with generator imports
where practical.

`PuzzleAnalysisController` separately debounces more expensive runtime and
decision analysis. `AutomatedChecksService` combines structure validation,
verified-solution search, saved-solution replay, front-load diagnostics,
decision quality, and the Swift test command for an explicit full check.

## Playtest and solution recording

`PlaytestController` wraps `tiny_routes_core.simulation.RuntimeSimulator`. It
owns a copied level, incremental runtime result, Qt clock/timer, accepted and
rejected tap records, replay actions, and published `PlaytestState`.

Canvas taps in Playtest mode go to the simulator. The overlay displays dot
position, package/outcome state, current roads, and the eligible switch. A
recorded solution is emitted only after the run completes and the accepted taps
replay cleanly from time zero. Timeline replay and scrubbing rebuild state from
the deterministic action stream rather than mutating an old snapshot.

The editor simulator is a fast authoring check, not permission to skip Swift
production replay.

## Autosave and recovery

The main window periodically asks `AutosaveRecoveryService` to store dirty
document state outside production resources. Recovery is offered on startup and
does not silently overwrite the source file. Normal save writes the level and
sidecar through their repositories and marks the controller clean only after
both operations succeed.

## Adding editor behavior safely

For a new mutating feature:

1. add or reuse a command type;
2. expose it through `DocumentController`;
3. update the projection through controller signals;
4. schedule validation/analysis after the change;
5. test mutation, undo, redo, save, and reopen; and
6. extend the headless editor smoke workflow when it is a primary action.

For a new serialized field, update shared core models first and add an unknown-
field round-trip regression before adding inspector controls.

