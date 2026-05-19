# Tiny Routes GUI Level Editor Plan

## Purpose

Create an internal desktop GUI tool that makes Tiny Routes levels easier, safer, and faster to author.

The tool should help engineers and level designers create and edit `level_###.json` files visually instead of hand-editing JSON. It should also connect directly to the level validation and solvability infrastructure so a user can build a level, validate it, prove it is beatable, and commit the level files with confidence.

The goal is not to build a polished player-facing level editor. The goal is to build a practical development tool that reduces level-authoring mistakes and makes new levels easier for entry-level engineers to create and test.

## Recommended Direction

Use the following decisions as the baseline implementation strategy:

1. **Keep the GUI level editor inside the Tiny Routes repo.**
2. **Place it under `Tools/LevelEditor/` as an internal developer tool.**
3. **Build the first editor with Python 3.10+ and PySide6 / Qt.**
4. **Keep the editor separate from the iOS game target.**
5. **Do not redesign the level JSON format at the start.** Read and write the existing `LevelData` JSON shape first.
6. **Use the same validation and solvability concepts from the test infrastructure plan.** The editor should not invent separate rules.
7. **Make the editor graph-based.** Levels should be assembled from nodes, edges, switches, packages, destinations, and dead ends.
8. **Support solution sidecar files.** The editor should eventually create or update `level_###.solution.json` files.
9. **Start simple.** Build a viewer and validator first, then add editing, then solution recording, then one-click test execution.
10. **Treat the tool as a productivity layer over the real game data.** The real source of truth remains the level JSON and the real `RouteEngine` tests.

## Why Same Repo Instead of Separate Repo

Keep the editor in the same repo for now because the tool is tightly coupled to Tiny Routes level data and tests.

Benefits:

```text
Level files stay close to the game.
Schema changes happen in one place.
Editor changes and test changes can be reviewed together.
PRs can include level JSON, solution JSON, and editor updates together.
Roo / Codex / Copilot can reason across the game, tests, docs, and tooling.
The editor is less likely to drift away from the real app behavior.
```

Only split the editor into a separate repo later if one of these becomes true:

```text
The editor becomes a standalone product.
Multiple games need to share the editor.
The editor needs a very different release cycle.
The editor dependencies become too heavy for the game repo.
The Tiny Routes repo becomes difficult to manage because of tool size.
```

## Why Python + PySide6

The editor is an internal desktop authoring tool. Python is a strong fit because it can quickly handle JSON, validation, CLI execution, test orchestration, and visual tooling.

Recommended stack:

```text
Language: Python 3.10+
GUI framework: PySide6 / Qt
Canvas: QGraphicsView / QGraphicsScene
Tests: pytest
Data models: dataclasses first, optional Pydantic later
Packaging: local developer run script first, packaged app later if needed
```

PySide6 is recommended over Tkinter because the editor will need a real canvas with selectable nodes, draggable pieces, connection lines, zooming, panning, property panels, validation panels, and eventually playback controls.

Avoid building the first version directly in SwiftUI. SwiftUI can work, but it would likely slow down internal tooling development and distract from the actual iPhone game.

Avoid building the first version as a web app unless browser-based level editing becomes a hard requirement. A web editor introduces extra local-file and packaging complexity.

## Current Repository Context

Relevant current files and folders:

```text
TinyRoutes/Domain/LevelData.swift
TinyRoutes/Domain/RouteGraph.swift
TinyRoutes/Domain/RouteNode.swift
TinyRoutes/Domain/RouteEdge.swift
TinyRoutes/Gameplay/RouteEngine.swift
TinyRoutes/Gameplay/RuntimeRouteGraph.swift
TinyRoutes/Gameplay/NodeSwitchController.swift
TinyRoutes/Infrastructure/LevelRepository.swift
TinyRoutes/Resources/Levels/level_001.json ... level_010.json
TinyRoutesTests/RouteEngineTests.swift
TinyRoutesTests/LevelRepositoryTests.swift
docs/plans/
```

Recommended new files and folders:

```text
Tools/
└── LevelEditor/
    ├── README.md
    ├── run_level_editor.py
    ├── requirements.txt
    ├── docs/
    │   └── current_level_json_shape.md
    ├── app/
    │   ├── __init__.py
    │   ├── main.py
    │   ├── main_window.py
    │   ├── config.py
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── level_document.py
    │   │   ├── route_node_model.py
    │   │   ├── route_edge_model.py
    │   │   └── solution_model.py
    │   ├── repositories/
    │   │   ├── __init__.py
    │   │   ├── level_file_repository.py
    │   │   └── solution_file_repository.py
    │   ├── services/
    │   │   ├── __init__.py
    │   │   ├── level_validation_service.py
    │   │   ├── graph_layout_service.py
    │   │   ├── solution_script_service.py
    │   │   └── test_runner_service.py
    │   ├── ui/
    │   │   ├── __init__.py
    │   │   ├── canvas_view.py
    │   │   ├── canvas_scene.py
    │   │   ├── node_item.py
    │   │   ├── edge_item.py
    │   │   ├── piece_palette.py
    │   │   ├── properties_panel.py
    │   │   ├── validation_panel.py
    │   │   └── solution_panel.py
    │   └── resources/
    │       └── icons/
    └── tests/
        ├── test_level_file_repository.py
        ├── test_level_validation_service.py
        ├── test_solution_script_service.py
        └── fixtures/
            ├── valid_level.json
            ├── invalid_missing_node_level.json
            └── valid_solution.json
```

## Core Workflow

The desired final workflow should be:

```text
Engineer opens the Level Editor.
Engineer opens an existing level or creates a new level.
Engineer builds the route graph visually.
Engineer adds package, destination, switch, and dead-end behavior.
Engineer clicks Validate.
Engineer fixes any validation errors.
Engineer records or edits a solution.
Engineer clicks Run Solution Test.
Tool confirms the level is structurally valid and beatable.
Engineer commits level JSON and solution JSON.
CI proves the level still passes.
```

The editor should make it possible to create and test a level without manually playing it in the iPhone app.

Important distinction:

```text
The editor and tests prove the level is structurally valid and engine-solvable.
Manual playtesting is still needed to decide if the level is fun, fair, and visually understandable.
```

## GUI Layout

Recommended main window layout:

```text
+--------------------------------------------------------------------------------+
| File | Edit | View | Level | Validation | Tests                                |
+--------------------------------------------------------------------------------+
| Toolbar: New | Open | Save | Validate | Record Solution | Run Test | Zoom     |
+----------------------+--------------------------------------+------------------+
| Piece Palette        | Level Canvas                         | Properties Panel |
|                      |                                      |                  |
| [Start]              |        package_1                     | Selected node    |
| [Route Node]         |           |                          | Node ID          |
| [Switch]             | start -- switch_a -- route_1 -- end  | Node type        |
| [Package]            |           |                          | Edge options     |
| [Destination]        |        dead_end_1                    | Switch behavior  |
| [Finish]             |                                      |                  |
+----------------------+--------------------------------------+------------------+
| Validation / Test Results Panel                                                |
| ✅ Level file loads                                                             |
| ✅ All edge references are valid                                                |
| ❌ Missing solution file                                                        |
+--------------------------------------------------------------------------------+
```

## Editor Responsibilities

The GUI editor should be responsible for:

```text
Opening level JSON files.
Displaying the level as a graph.
Letting users create, move, edit, and connect level pieces.
Saving valid JSON back to disk.
Showing validation errors and warnings.
Helping users create solution sidecar files.
Launching validation and solvability tests.
```

The GUI editor should not be responsible for:

```text
Replacing RouteEngine.
Creating separate gameplay rules.
Silently changing level semantics.
Inventing a second level format without migration rules.
Hiding validation failures.
Claiming a level is fun just because it is solvable.
```

## Data Model Strategy

Create Python editor models that closely mirror the Swift domain models.

The first version can use Python dataclasses:

```python
@dataclass
class EditorLevelDocument:
    id: str
    title: str
    time_limit_seconds: float
    graph: EditorRouteGraph
```

```python
@dataclass
class EditorRouteNode:
    id: str
    type: str
    x: float
    y: float
    package_id: str | None = None
    destination_id: str | None = None
```

```python
@dataclass
class EditorRouteEdge:
    id: str
    from_node_id: str
    to_node_id: str
    travel_time_seconds: float | None = None
    is_default: bool = False
```

The exact fields must match the actual current `level_###.json` files. The names above are examples. The implementation task must inspect the current JSON files before finalizing the Python models.

## Validation Strategy

The editor should surface the same categories of validation used by the test infrastructure.

Minimum validation rules:

```text
Level ID exists.
Level title/name exists if required by the current schema.
Time limit exists and is greater than zero.
Exactly one start node exists.
At least one completion/destination/finish condition exists.
All node IDs are unique.
All edge IDs are unique if edge IDs are part of the schema.
Every edge references existing nodes.
Every switch references existing route options.
All required packages are reachable from the start.
All required destinations are reachable from the start.
Every required package can be collected before completion.
Dead ends are allowed but must not be the only possible route.
No orphaned nodes unless explicitly marked as disabled/test-only.
No invalid node type values.
No invalid edge type values.
Matching solution file exists for production levels.
Solution file references valid node IDs.
```

Validation severity levels:

```text
Error: Must be fixed before saving or testing.
Warning: Allowed but should be reviewed.
Info: Helpful note that does not block work.
```

Examples:

```text
Error: Edge "edge_04" references missing node "switch_c".
Error: Level has no start node.
Error: Package "pkg_1" is not reachable from the start node.
Warning: Node "dead_end_2" is unreachable.
Warning: Level has a dead end but no matching solution file.
Info: Level uses 3 switches and may need a human playability review.
```

## Solution Script Strategy

The editor should support solution sidecar files that prove levels are completable.

Recommended file naming:

```text
TinyRoutes/Resources/Levels/level_001.json
TinyRoutes/Resources/Levels/level_001.solution.json
```

Initial timed script example:

```json
{
  "levelID": "level_001",
  "expectedOutcome": "completed",
  "maxTimeSeconds": 30.0,
  "maxTaps": 3,
  "actions": [
    { "time": 0.5, "tapNodeID": "switch_a" },
    { "time": 1.7, "tapNodeID": "switch_b" }
  ]
}
```

Later high-level solution script example:

```json
{
  "levelID": "level_001",
  "expectedOutcome": "completed",
  "maxTaps": 3,
  "steps": [
    {
      "beforeDotReachesNode": "switch_a",
      "tapNodeID": "switch_a",
      "rotateCount": 1
    },
    {
      "beforeDotReachesNode": "switch_b",
      "tapNodeID": "switch_b",
      "rotateCount": 2
    }
  ]
}
```

The GUI does not need to support the high-level DSL in the first version. The first usable version can support timed scripts and then improve from there.

## Solution Recording Strategy

The most useful long-term feature is solution recording.

Target behavior:

```text
User opens a level.
User clicks Record Solution.
The editor starts a simplified playback preview.
User clicks switch nodes at the intended moments.
The editor records tap node IDs and timestamps.
User clicks Stop Recording.
The editor saves or updates level_###.solution.json.
User clicks Run Solution Test.
```

This is easier for engineers than asking them to hand-write timestamps.

The first version of solution recording can be simple and imperfect. It only needs to capture enough information to create a repeatable script for the real solvability tests.

## Test Runner Strategy

The editor should eventually run the same test path used by CI.

Recommended buttons:

```text
Validate Current Level
Validate All Levels
Run Current Level Solution Test
Run All Level Solution Tests
Open Test Report
```

The first implementation can shell out to a command instead of embedding Swift behavior directly.

Example commands the editor may eventually call:

```bash
swift test --filter LevelValidationTests
swift test --filter LevelSolvabilityTests
xcodebuild test -scheme TinyRoutes -destination 'platform=iOS Simulator,name=iPhone 16'
```

The exact command should be based on the repo's current build/test setup. Because this project currently has an Xcode project and `project.yml`, the first task should confirm the preferred local test command before wiring it into the GUI.

## Architecture Rules

Use a layered design so entry-level engineers can work safely.

### Models

Models are plain data structures.

Allowed:

```text
Represent level data.
Represent nodes, edges, switches, packages, destinations, and solutions.
Serialize/deserialize cleanly.
Expose simple helper properties.
```

Forbidden:

```text
No file dialogs.
No Qt widget code.
No subprocess calls.
No test command execution.
No validation UI formatting.
```

### Repositories

Repositories handle file I/O only.

Allowed:

```text
Load level JSON from disk.
Save level JSON to disk.
Load solution JSON from disk.
Save solution JSON to disk.
Find matching solution file path.
Return structured errors for invalid JSON.
```

Forbidden:

```text
No GUI code.
No graph validation rules.
No gameplay simulation.
No subprocess test execution.
```

### Services

Services implement business logic.

Allowed:

```text
Validate level structure.
Build canvas layout data.
Convert recorded taps into solution actions.
Create default IDs for new nodes and edges.
Build test command arguments.
Parse test output into report messages.
```

Forbidden:

```text
No direct Qt widget manipulation.
No file picker calls.
No hidden writes to disk unless explicitly requested.
```

### UI

UI classes display information and collect user input.

Allowed:

```text
Render nodes and edges.
Display dialogs.
Display validation messages.
Let users select, drag, and edit items.
Call repositories and services through clear interfaces.
```

Forbidden:

```text
No duplicate validation logic.
No custom JSON parsing spread across widgets.
No gameplay rules embedded in canvas items.
```

## Phased Implementation Plan

### Phase 0: Tool Skeleton

Create the basic Python tool folder and prove the GUI can launch.

Deliverables:

```text
Tools/LevelEditor/README.md
Tools/LevelEditor/requirements.txt
Tools/LevelEditor/run_level_editor.py
Minimal PySide6 main window
Basic pytest setup
```

Definition of done:

```text
A developer can install dependencies, launch the tool, and run Python tests.
```

### Phase 1: Level JSON Viewer

Load an existing level file and display it as a graph.

Deliverables:

```text
Level file repository
Editor data models
Read-only canvas view
Basic node rendering
Basic edge rendering
Properties panel for selected item
```

Definition of done:

```text
A developer can open an existing `level_###.json` and visually inspect nodes, edges, and selected properties.
```

### Phase 2: Validation Panel

Add validation messages for structural level problems.

Deliverables:

```text
Validation result model
Level validation service
Validation panel
Validate Current Level button
Unit tests for valid and invalid fixture levels
```

Definition of done:

```text
A developer can open a level, click Validate, and see actionable errors/warnings.
```

### Phase 3: Basic Editing

Allow users to create and modify level graph elements.

Deliverables:

```text
Add node from palette
Move node on canvas
Edit selected node properties
Connect nodes with edges
Delete selected node or edge
Save level JSON
Dirty state indicator
Unsaved changes prompt
```

Definition of done:

```text
A developer can create or edit a small level visually, save it, reopen it, and get the same graph back.
```

### Phase 4: Solution File Support

Load, display, edit, and save solution sidecar files.

Deliverables:

```text
Solution file repository
Solution data model
Solution panel
Add/remove timed tap action
Validate solution references against the level
Save matching `level_###.solution.json`
```

Definition of done:

```text
A developer can create or edit the solution script for a level without hand-editing JSON.
```

### Phase 5: Test Command Integration

Let the editor run the existing validation/solvability tests.

Deliverables:

```text
Test runner service
Run Current Level Test button
Run All Level Tests button
Test output panel
Clear pass/fail summary
```

Definition of done:

```text
A developer can click a button in the editor and see whether the level passes the same tests used by the repo.
```

### Phase 6: Solution Recording

Let users record solution scripts visually.

Deliverables:

```text
Record Solution button
Playback timer
Tap capture for switch nodes
Stop Recording button
Generated solution actions
Save recorded solution
Run test after recording
```

Definition of done:

```text
A developer can record a solution through the GUI and immediately run the solvability test for that solution.
```

### Phase 7: Human-Playability Guardrails

Add warnings for levels that are technically solvable but may be unfair.

Deliverables:

```text
Minimum tap spacing warning
Tiny reaction window warning
Too many switches warning
Time limit margin warning
Possible unclear dead-end warning
Difficulty metadata warning if supported later
```

Definition of done:

```text
The editor distinguishes engine-solvable from likely human-playable.
```

## Entry-Level Engineering Tasks

The tasks below are intentionally small and strict. Engineers should complete them in order. Each task should be its own small PR unless the team decides to batch closely related tasks.

---

## Task 001: Create the LevelEditor Tool Folder

### Goal

Create the initial folder structure for the internal GUI level editor.

### Files to create

```text
Tools/LevelEditor/README.md
Tools/LevelEditor/requirements.txt
Tools/LevelEditor/run_level_editor.py
Tools/LevelEditor/app/__init__.py
Tools/LevelEditor/app/main.py
Tools/LevelEditor/tests/__init__.py
```

### To do

- [x] Create `Tools/LevelEditor/`.
- [x] Create the initial `app/` package.
- [x] Create the initial `tests/` folder.
- [x] Add `PySide6` to `requirements.txt`.
- [x] Add `pytest` to `requirements.txt`.
- [x] Add a short README explaining that this is an internal Tiny Routes level editor.
- [x] Add a `run_level_editor.py` script that imports and calls `app.main.main()`.
- [x] Add `app/main.py` with a placeholder `main()` function.

### Acceptance criteria

- [x] The folder structure exists.
- [x] `python Tools/LevelEditor/run_level_editor.py` runs without import errors.
- [x] No game app files are modified.

---

## Task 002: Add a Minimal PySide6 Main Window

### Goal

Launch a real desktop window for the editor.

### Files to create or update

```text
Tools/LevelEditor/app/main.py
Tools/LevelEditor/app/main_window.py
```

### To do

- [x] Create `main_window.py`.
- [x] Add a `LevelEditorMainWindow` class.
- [x] Set the window title to `Tiny Routes Level Editor`.
- [x] Set a reasonable default window size.
- [x] Add a placeholder central label or widget that says `Level Editor`.
- [x] Update `main.py` to create the Qt application and show the main window.

### Acceptance criteria

- [x] Running `python Tools/LevelEditor/run_level_editor.py` opens a window.
- [x] The window title is `Tiny Routes Level Editor`.
- [x] Closing the window exits the process cleanly.

---

## Task 003: Add Editor Configuration Helpers

### Goal

Add a central place for repo-relative paths so the editor can find level files reliably.

### Files to create or update

```text
Tools/LevelEditor/app/config.py
Tools/LevelEditor/tests/test_config.py
```

### To do

- [x] Create `config.py`.
- [x] Add a helper to locate the repo root from the `Tools/LevelEditor/` folder.
- [x] Add a helper that returns the default levels directory path.
- [x] Add a helper that returns the default docs directory path.
- [x] Add unit tests for the path helpers.
- [x] Do not hard-code an absolute user-specific path.

### Acceptance criteria

- [x] Tests pass from inside `Tools/LevelEditor/`.
- [x] Tests pass from the repo root.
- [x] The default levels path resolves to `TinyRoutes/Resources/Levels`.

---

## Task 004: Inspect Current Level JSON Shape and Document Fields

### Goal

Before creating Python models, document the exact fields currently used by the real level JSON files.

### Files to create or update

```text
Tools/LevelEditor/README.md
Tools/LevelEditor/docs/current_level_json_shape.md
```

### To do

- [x] Open at least `level_001.json`, `level_002.json`, and one later level.
- [x] Document the top-level JSON fields.
- [x] Document the node fields.
- [x] Document the edge fields.
- [x] Document package/destination/switch-related fields.
- [x] Document any optional fields.
- [x] Document any fields that are present in Swift models but missing from JSON.
- [x] Add a README link to the new JSON shape document.

### Acceptance criteria

- [x] The document shows the current real JSON shape.
- [x] The document does not invent future schema fields.
- [x] Another engineer can use the document to implement Python models.

---

## Task 005: Create Python Level Data Models

### Goal

Create Python dataclasses that represent the current level JSON shape.

### Files to create or update

```text
Tools/LevelEditor/app/models/__init__.py
Tools/LevelEditor/app/models/level_document.py
Tools/LevelEditor/app/models/route_node_model.py
Tools/LevelEditor/app/models/route_edge_model.py
Tools/LevelEditor/tests/test_level_models.py
```

### To do

- [x] Create a dataclass for the full level document.
- [x] Create a dataclass for route nodes.
- [x] Create a dataclass for route edges.
- [x] Match the current JSON field names.
- [x] Add conversion from raw dictionaries into dataclasses.
- [x] Add conversion from dataclasses back into raw dictionaries.
- [x] Add tests using a small fixture level.
- [x] Preserve unknown fields if needed to avoid destructive saves.

### Acceptance criteria

- [x] A fixture level can be loaded into models.
- [x] The model can be converted back to JSON-compatible dictionaries.
- [x] Required fields are represented.
- [x] Tests prove round-trip behavior.

---

## Task 006: Add Level File Repository

### Goal

Add file I/O for loading and saving level JSON files.

### Files to create or update

```text
Tools/LevelEditor/app/repositories/__init__.py
Tools/LevelEditor/app/repositories/level_file_repository.py
Tools/LevelEditor/tests/test_level_file_repository.py
Tools/LevelEditor/tests/fixtures/valid_level.json
```

### To do

- [x] Create `LevelFileRepository`.
- [x] Add `load_level(path)`.
- [x] Add `save_level(path, level_document)`.
- [x] Return structured errors for invalid JSON.
- [x] Return structured errors for missing files.
- [x] Add tests for loading a valid file.
- [x] Add tests for missing file behavior.
- [x] Add tests for invalid JSON behavior.

### Acceptance criteria

- [x] Valid level JSON loads into the Python model.
- [x] Saved level JSON can be loaded again.
- [x] Missing or invalid files produce clear errors.
- [x] Repository code contains no Qt imports.

---

## Task 007: Add Open Level File Menu Action

### Goal

Let the user open a level JSON file from the GUI.

### Files to create or update

```text
Tools/LevelEditor/app/main_window.py
Tools/LevelEditor/app/repositories/level_file_repository.py
```

### To do

- [x] Add a `File` menu.
- [x] Add an `Open Level...` action.
- [x] Open a file picker starting in the default levels directory.
- [x] Load the selected file through `LevelFileRepository`.
- [x] Store the loaded level as the current document.
- [x] Show the loaded level ID or file name in the window title.
- [x] Show a clear error dialog if loading fails.

### Acceptance criteria

- [x] User can select an existing `level_###.json`.
- [x] The level loads without crashing.
- [x] Invalid files show a readable error.
- [x] The repository remains responsible for file I/O.

---

## Task 008: Create Canvas Scene and View Placeholders

### Goal

Create the canvas area where levels will be displayed.

### Files to create or update

```text
Tools/LevelEditor/app/ui/__init__.py
Tools/LevelEditor/app/ui/canvas_view.py
Tools/LevelEditor/app/ui/canvas_scene.py
Tools/LevelEditor/app/main_window.py
```

### To do

- [x] Create `LevelCanvasView` using `QGraphicsView`.
- [x] Create `LevelCanvasScene` using `QGraphicsScene`.
- [x] Add the canvas view to the main window central area.
- [x] Add basic zoom support if simple to implement.
- [x] Add a placeholder grid or empty-state message.
- [x] Keep canvas rendering code out of `main_window.py`.

### Acceptance criteria

- [x] The main window contains a canvas area.
- [x] The canvas is ready to render nodes and edges.
- [x] Opening a level still works.

---

## Task 009: Render Nodes on the Canvas

### Goal

Display level nodes visually.

### Files to create or update

```text
Tools/LevelEditor/app/ui/node_item.py
Tools/LevelEditor/app/ui/canvas_scene.py
```

### To do

- [x] Create a `NodeItem` graphics item.
- [x] Render each node with a visible shape.
- [x] Display the node ID as text.
- [x] Use different visual treatment for start, route, switch, package, destination, and finish nodes when that information exists.
- [x] Position nodes using coordinates from the JSON when they are finite values.
- [x] If coordinates are invalid/non-finite, place nodes using a simple fallback layout.
- [x] Clear and redraw nodes when a new level is loaded.

### Acceptance criteria

- [x] Opening a level shows nodes on the canvas.
- [x] Node labels are readable.
- [x] Different node types are distinguishable.
- [x] The app does not crash when node coordinates are invalid/non-finite.

---

## Task 010: Render Edges on the Canvas

### Goal

Display route connections between nodes.

### Files to create or update

```text
Tools/LevelEditor/app/ui/edge_item.py
Tools/LevelEditor/app/ui/canvas_scene.py
```

### To do

- [x] Create an `EdgeItem` graphics item.
- [x] Draw a line between the source node and target node.
- [x] Add an arrow or direction indicator if route direction matters.
- [x] Draw edges behind nodes.
- [x] Handle missing node references gracefully.
- [x] Redraw edges when a new level is loaded.

### Acceptance criteria

- [x] Opening a level shows the graph connections.
- [x] Edges do not cover node labels.
- [x] Bad edge references do not crash the GUI.

---

## Task 011: Add a Properties Panel for Selected Items

### Goal

Show details for the selected node or edge.

### Files to create or update

```text
Tools/LevelEditor/app/ui/properties_panel.py
Tools/LevelEditor/app/main_window.py
Tools/LevelEditor/app/ui/node_item.py
Tools/LevelEditor/app/ui/edge_item.py
```

### To do

- [x] Create a `PropertiesPanel` widget.
- [x] Add it to the right side of the main window.
- [x] Detect node selection.
- [x] Display selected node ID.
- [x] Display selected node type.
- [x] Display selected node position.
- [x] Detect edge selection.
- [x] Display selected edge source and target.
- [x] Show an empty state when nothing is selected.

### Acceptance criteria

- [x] Selecting a node updates the properties panel.
- [x] Selecting an edge updates the properties panel.
- [x] Clicking empty canvas clears or resets the panel.

---

## Task 012: Add Validation Result Models

### Goal

Create reusable models for validation messages.

### Files to create or update

```text
Tools/LevelEditor/app/services/level_validation_service.py
Tools/LevelEditor/tests/test_level_validation_service.py
```

### To do

- [x] Create a `ValidationSeverity` enum or equivalent constants.
- [x] Create a `ValidationMessage` dataclass.
- [x] Include severity, code, message, and optional related node/edge ID.
- [x] Create a `ValidationResult` container.
- [x] Add helper properties like `has_errors` and `has_warnings`.
- [x] Add unit tests for the result model.

### Acceptance criteria

- [x] Validation messages can represent errors, warnings, and info.
- [x] The result container correctly reports `has_errors` and `has_warnings`.
- [x] No Qt imports are present in the validation service.

---

## Task 013: Add Core Validation Rules

### Goal

Implement the minimum validation rules that catch structural level problems.

### Files to create or update

```text
Tools/LevelEditor/app/services/level_validation_service.py
Tools/LevelEditor/tests/test_level_validation_service.py
Tools/LevelEditor/tests/fixtures/valid_level.json
Tools/LevelEditor/tests/fixtures/invalid_missing_node_level.json
```

### To do

- [x] Validate level ID is present.
- [x] Validate level name is present.
- [x] Validate time limit is positive.
- [x] Validate exactly one start node exists.
- [x] Validate at least one destination node exists.
- [x] Validate all node IDs are unique.
- [x] Validate all edge IDs are unique.
- [x] Validate every edge references an existing node.
- [x] Add tests using fixture levels.
- [x] Test both valid and invalid fixtures.

### Acceptance criteria

- [x] All listed rules are implemented.
- [x] Valid fixture level produces no errors.
- [x] Invalid fixture level produces at least one error.
- [x] Tests do not import any Qt modules.

---

## Task 014: Add Reachability Validation

### Goal

Verify that package and destination nodes are reachable from the start node.

### Files to create or update

```text
Tools/LevelEditor/app/services/level_validation_service.py
Tools/LevelEditor/tests/test_level_validation_service.py
Tools/LevelEditor/tests/fixtures/invalid_unreachable_package.json
```

### To do

- [x] Implement graph reachability from the start node.
- [x] Validate the package node is reachable from start.
- [x] Validate the destination node is reachable from start.
- [x] Add a warning for unreachable non-critical nodes.
- [x] Add tests for reachable and unreachable cases.

### Acceptance criteria

- [x] Unreachable package produces a validation error.
- [x] Unreachable destination produces a validation error.
- [x] Unreachable side node produces a validation warning.
- [x] A fully reachable level produces no reachability errors.

---

## Task 015: Add Validation Panel to the GUI

### Goal

Display validation messages in the main window.

### Files to create or update

```text
Tools/LevelEditor/app/ui/validation_panel.py
Tools/LevelEditor/app/main_window.py
```

### To do

- [x] Create a `ValidationPanel` widget.
- [x] Add it to the bottom area of the main window.
- [x] Add a Validate button that triggers validation.
- [x] Display each validation message with its severity icon.
- [x] Clear the panel when a new level is loaded.
- [x] Use the `LevelValidationService` through the main window, not inline.

### Acceptance criteria

- [x] Clicking Validate runs validation on the current level.
- [x] Errors, warnings, and info messages are displayed.
- [x] The panel updates when a new level is opened.

---

## Task 016: Add Save Level Action

### Goal

Let the user save the current level back to disk.

### Files to create or update

```text
Tools/LevelEditor/app/main_window.py
Tools/LevelEditor/app/repositories/level_file_repository.py
```

### To do

- [ ] Add a `Save Level` menu action.
- [ ] Save to the current file path without prompting if already opened.
- [ ] Add a `Save Level As...` action to save to a new path.
- [ ] Track dirty state when the level is modified.
- [ ] Show a dirty indicator in the window title.
- [ ] Prompt to save unsaved changes when closing.

### Acceptance criteria

- [ ] Saving overwrites the original file.
- [ ] Save As creates a new file at the chosen path.
- [ ] Dirty state indicator appears when level is changed.
- [ ] Unsaved changes prompt appears on close.

---

## Task 017: Add New Level Action

### Goal

Let the user create a new empty level.

### Files to create or update

```text
Tools/LevelEditor/app/main_window.py
Tools/LevelEditor/app/services/level_validation_service.py
```

### To do

- [ ] Add a `New Level` menu action.
- [ ] Create a minimal default level with a start node.
- [ ] Assign a placeholder level ID and name.
- [ ] Set a default time limit.
- [ ] Display the new level on the canvas.
- [ ] Prompt to save unsaved changes before creating a new level.

### Acceptance criteria

- [ ] New Level action creates a minimal usable level.
- [ ] Canvas updates to show the new level.
- [ ] Unsaved changes prompt appears if the current level is dirty.

---

## Task 018: Add Node Creation from the Palette

### Goal

Let users drag or double-click palette items to add nodes to the canvas.

### Files to create or update

```text
Tools/LevelEditor/app/ui/piece_palette.py
Tools/LevelEditor/app/ui/canvas_scene.py
Tools/LevelEditor/app/main_window.py
```

### To do

- [ ] Create a `PiecePalette` widget.
- [ ] List available node types: Start, Route Node, Switch, Package, Destination.
- [ ] Allow double-click to add a node to the center of the canvas.
- [ ] Generate a unique default node ID.
- [ ] Mark the level as dirty after adding a node.

### Acceptance criteria

- [ ] All node types appear in the palette.
- [ ] Double-clicking adds the node to the canvas.
- [ ] New nodes have unique IDs.
- [ ] Level dirty state is set after adding a node.

---

## Task 019: Add Node Dragging

### Goal

Let users move nodes by dragging them on the canvas.

### Files to create or update

```text
Tools/LevelEditor/app/ui/node_item.py
Tools/LevelEditor/app/ui/canvas_scene.py
```

### To do

- [ ] Make `NodeItem` draggable.
- [ ] Update the node's coordinates in the level document when dragged.
- [ ] Update connected edges when a node is moved.
- [ ] Mark the level as dirty after dragging.

### Acceptance criteria

- [ ] Nodes can be dragged to new positions.
- [ ] Edge lines follow the node when moved.
- [ ] Level is marked dirty after dragging.

---

## Task 020: Add Edge Creation Between Nodes

### Goal

Let users connect two nodes by drawing an edge.

### Files to create or update

```text
Tools/LevelEditor/app/ui/canvas_scene.py
Tools/LevelEditor/app/ui/node_item.py
```

### To do

- [ ] Add an edge-drawing mode or right-click interaction.
- [ ] Allow users to click a source node and then a target node to create an edge.
- [ ] Assign a generated unique edge ID.
- [ ] Update the source node's `outgoingEdgeIDs` list.
- [ ] Render the new edge immediately.
- [ ] Mark the level as dirty.

### Acceptance criteria

- [ ] User can connect two nodes with an edge.
- [ ] The new edge appears on the canvas.
- [ ] Edge references are correct in the data model.
- [ ] Level is marked dirty after edge creation.

---

## Task 021: Add Delete Node and Edge Actions

### Goal

Let users delete selected items from the canvas.

### Files to create or update

```text
Tools/LevelEditor/app/ui/canvas_scene.py
Tools/LevelEditor/app/ui/node_item.py
Tools/LevelEditor/app/ui/edge_item.py
```

### To do

- [ ] Support Delete key press to remove the selected node or edge.
- [ ] When deleting a node, also delete connected edges.
- [ ] Update `outgoingEdgeIDs` lists on connected nodes.
- [ ] Mark level as dirty after deletion.

### Acceptance criteria

- [ ] Selected node is deleted with the Delete key.
- [ ] Connected edges are also removed.
- [ ] Level is marked dirty after deletion.
- [ ] Deleting the last node does not crash.

---

## Task 022: Add Solution File Repository

### Goal

Load and save solution sidecar files.

### Files to create or update

```text
Tools/LevelEditor/app/repositories/solution_file_repository.py
Tools/LevelEditor/app/models/solution_model.py
Tools/LevelEditor/tests/test_solution_file_repository.py
Tools/LevelEditor/tests/fixtures/valid_solution.json
```

### To do

- [ ] Create `SolutionFileRepository`.
- [ ] Add `load_solution(path)`.
- [ ] Add `save_solution(path, solution)`.
- [ ] Add `find_solution_path(level_path)` to locate the matching `.solution.json`.
- [ ] Add tests for loading, saving, and missing files.

### Acceptance criteria

- [ ] Valid solution JSON loads into the model.
- [ ] Saved solution JSON can be reloaded.
- [ ] Missing files produce clear errors.
- [ ] No Qt imports in the repository.

---

## Task 023: Add Solution Panel to the GUI

### Goal

Display the solution script for the current level.

### Files to create or update

```text
Tools/LevelEditor/app/ui/solution_panel.py
Tools/LevelEditor/app/main_window.py
```

### To do

- [ ] Create a `SolutionPanel` widget.
- [ ] Display the current solution's action list.
- [ ] Show tap node IDs and times for each action.
- [ ] Add an `Add Action` button.
- [ ] Add a `Remove Action` button.
- [ ] Allow editing tap node ID and time inline.
- [ ] Mark level as dirty after solution changes.

### Acceptance criteria

- [ ] Solution panel shows existing actions.
- [ ] User can add and remove actions.
- [ ] Changes mark the level dirty.

---

## Task 024: Add Test Runner Service

### Goal

Let the editor invoke the repo's existing validation and solvability tests.

### Files to create or update

```text
Tools/LevelEditor/app/services/test_runner_service.py
Tools/LevelEditor/tests/test_test_runner_service.py
```

### To do

- [ ] Create `TestRunnerService`.
- [ ] Add `build_validate_command(level_path)`.
- [ ] Add `build_solvability_command(level_path)`.
- [ ] Add `run_command(command)` that shells out and returns output.
- [ ] Parse output for pass/fail indicators.
- [ ] Add unit tests for command construction.
- [ ] Do not hard-code absolute paths.

### Acceptance criteria

- [ ] Commands are constructed correctly.
- [ ] Pass/fail detection works on sample output.
- [ ] No Qt imports in the service.

---

## Task 025: Add Run Tests Button to the GUI

### Goal

Let users run level tests from the editor with one click.

### Files to create or update

```text
Tools/LevelEditor/app/main_window.py
Tools/LevelEditor/app/ui/validation_panel.py
```

### To do

- [ ] Add a `Run Current Level Test` button.
- [ ] Call `TestRunnerService` when clicked.
- [ ] Display test output in the validation panel.
- [ ] Show pass or fail summary clearly.

### Acceptance criteria

- [ ] Clicking the button invokes the test command.
- [ ] Output appears in the validation panel.
- [ ] Pass/fail result is clearly shown.
