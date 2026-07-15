"""Declarative menu and toolbar construction for the editor window."""

from PySide6.QtGui import QAction, QActionGroup, QIcon, QKeySequence
from PySide6.QtWidgets import QDoubleSpinBox, QMainWindow, QToolBar

from app.models import EditorTool


def build_menu_bar(window: QMainWindow) -> None:
    menu_bar = window.menuBar()
    window._file_menu = menu_bar.addMenu("File")
    for text, shortcut, callback in (
        ("New Level", QKeySequence.StandardKey.New, window._new_level),
        ("Open Level...", QKeySequence.StandardKey.Open, window._open_level),
        ("Save Level", QKeySequence.StandardKey.Save, window._save_level),
        ("Save Level As...", QKeySequence.StandardKey.SaveAs, window._save_level_as),
    ):
        action = window._file_menu.addAction(text)
        action.setShortcut(shortcut)
        action.triggered.connect(callback)
    window._file_menu.addAction("Save Draft...", window._save_draft)

    window._edit_menu = menu_bar.addMenu("Edit")
    window._undo_action = window._document_controller.undo_stack.createUndoAction(window, "Undo")
    window._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
    window._edit_menu.addAction(window._undo_action)
    window._redo_action = window._document_controller.undo_stack.createRedoAction(window, "Redo")
    window._redo_action.setShortcut(QKeySequence.StandardKey.Redo)
    window._edit_menu.addAction(window._redo_action)
    window._edit_menu.addSeparator()
    window._snap_selected_action = window._edit_menu.addAction("Snap Selected to Grid")
    window._snap_selected_action.triggered.connect(window._snap_selected_to_grid)
    window._edit_menu.addSeparator()
    align_menu = window._edit_menu.addMenu("Align Selected")
    for label, operation in (
        ("Left", "left"),
        ("Right", "right"),
        ("Top", "top"),
        ("Bottom", "bottom"),
        ("Horizontal Centers", "horizontal_centers"),
        ("Vertical Centers", "vertical_centers"),
    ):
        align_menu.addAction(
            label,
            lambda checked=False, selected=operation: window._arrange_selected_nodes(
                selected
            ),
        )
    distribute_menu = window._edit_menu.addMenu("Distribute Selected")
    for label, operation in (
        ("Horizontally", "horizontal"),
        ("Vertically", "vertical"),
    ):
        distribute_menu.addAction(
            label,
            lambda checked=False, selected=operation: window._arrange_selected_nodes(
                selected
            ),
        )

    window._view_menu = menu_bar.addMenu("View")
    window._view_menu.addAction("Fit View").triggered.connect(window._canvas_view.fit_level_to_view)
    window._view_menu.addAction("Zoom to Selection").triggered.connect(
        window._canvas_view.zoom_to_selection
    )
    window._view_menu.addAction("Reset Zoom").triggered.connect(window._canvas_view.reset_zoom)

    window._tools_menu = menu_bar.addMenu("Tools")
    window._edit_metadata_action = window._tools_menu.addAction("Edit Level Metadata...")
    window._edit_metadata_action.triggered.connect(window._edit_level_metadata)
    window._edit_rules_action = window._tools_menu.addAction("Edit Level Rules...")
    window._edit_rules_action.triggered.connect(window._edit_level_rules)
    window._promote_draft_action = window._tools_menu.addAction("Promote Draft to Production Level...")
    window._promote_draft_action.triggered.connect(window._promote_draft_to_production_level)
    window._repair_metadata_action = window._tools_menu.addAction("Repair Current Level Metadata...")
    window._repair_metadata_action.triggered.connect(window._repair_current_level_metadata)
    for action in (
        window._edit_metadata_action,
        window._promote_draft_action,
        window._repair_metadata_action,
        window._edit_rules_action,
    ):
        action.setEnabled(False)
    window._tools_menu.addSeparator()
    validate_action = window._tools_menu.addAction("Validate")
    validate_action.setToolTip("Validate Level + Solution References")
    validate_action.triggered.connect(window._validate_current_level)
    window._analyze_puzzle_action = window._tools_menu.addAction("Analyze Puzzle")
    window._analyze_puzzle_action.triggered.connect(window._analyze_puzzle)
    window._analyze_puzzle_action.setEnabled(False)
    window._run_all_checks_action = window._tools_menu.addAction("Run All Checks")
    window._run_all_checks_action.setToolTip(
        "Run structure, solution, front-load, quality, and Swift parity checks"
    )
    window._run_all_checks_action.triggered.connect(window._run_all_automated_checks)
    window._run_all_checks_action.setEnabled(False)
    window._run_tests_menu_action = window._tools_menu.addAction("Run Tests")
    window._run_tests_menu_action.setToolTip("Run Swift Solvability Tests")
    window._run_tests_menu_action.triggered.connect(window._run_level_tests)
    window._run_tests_menu_action.setEnabled(False)


def build_main_toolbar(window: QMainWindow) -> None:
    window._main_toolbar = QToolBar("Main Toolbar", window)
    window._main_toolbar.setObjectName("mainToolbar")
    window.addToolBar(window._main_toolbar)
    actions = (
        ("New", QKeySequence.StandardKey.New, window._new_level),
        ("Open", QKeySequence.StandardKey.Open, window._open_level),
        ("Save", QKeySequence.StandardKey.Save, window._save_level),
    )
    for text, shortcut, callback in actions:
        action = QAction(text, window)
        action.setShortcut(shortcut)
        action.triggered.connect(callback)
        window._main_toolbar.addAction(action)
    window._main_toolbar.addSeparator()
    for text, callback in (
        ("Validate", window._validate_current_level),
        ("Fit View", window._canvas_view.fit_level_to_view),
        ("Zoom to Selection", window._canvas_view.zoom_to_selection),
        ("Reset Zoom", window._canvas_view.reset_zoom),
    ):
        action = QAction(text, window)
        action.triggered.connect(callback)
        window._main_toolbar.addAction(action)
    window._main_toolbar.addSeparator()
    window._run_tests_action = QAction("Run Tests", window)
    window._run_tests_action.setToolTip("Run Swift Solvability Tests")
    window._run_tests_action.triggered.connect(window._run_level_tests)
    window._run_tests_action.setEnabled(False)
    window._main_toolbar.addAction(window._run_tests_action)


def build_tools_toolbar(window: QMainWindow) -> None:
    window._tools_toolbar = QToolBar("Editor Tools", window)
    window._tools_toolbar.setObjectName("editorToolsToolbar")
    window.addToolBar(window._tools_toolbar)
    window._tool_action_group = QActionGroup(window)
    window._tool_action_group.setExclusive(True)
    window._tool_actions = {}
    shortcuts = {EditorTool.SELECT: "V", EditorTool.PLACE_NODE: "N", EditorTool.CONNECT: "C", EditorTool.PLAYTEST: "P"}
    icons = {EditorTool.SELECT: "input-mouse", EditorTool.PLACE_NODE: "list-add", EditorTool.CONNECT: "insert-link", EditorTool.PLAYTEST: "media-playback-start"}
    for tool in EditorTool:
        action = QAction(QIcon.fromTheme(icons[tool]), tool.label, window)
        action.setCheckable(True)
        action.setShortcut(QKeySequence(shortcuts[tool]))
        action.setToolTip(f"{tool.label} ({shortcuts[tool]}) — {tool.status_message}")
        action.triggered.connect(lambda checked=False, selected=tool: window._set_active_tool(selected))
        window._tool_action_group.addAction(action)
        window._tools_toolbar.addAction(action)
        window._tool_actions[tool] = action

    window._tools_toolbar.addSeparator()
    window._playtest_pause_action = QAction("Pause", window)
    window._playtest_pause_action.triggered.connect(window._pause_or_resume_playtest)
    window._tools_toolbar.addAction(window._playtest_pause_action)
    window._playtest_reset_action = QAction("Reset", window)
    window._playtest_reset_action.triggered.connect(window._reset_playtest)
    window._tools_toolbar.addAction(window._playtest_reset_action)
    window._playtest_stop_action = QAction("Stop", window)
    window._playtest_stop_action.triggered.connect(window._stop_playtest)
    window._tools_toolbar.addAction(window._playtest_stop_action)
    window._use_playtest_solution_action = QAction("Use Run as Solution", window)
    window._use_playtest_solution_action.triggered.connect(window._use_playtest_run_as_solution)
    window._tools_toolbar.addAction(window._use_playtest_solution_action)
    window._use_playtest_solution_action.setEnabled(False)
    for action in (window._playtest_pause_action, window._playtest_reset_action, window._playtest_stop_action):
        action.setEnabled(False)
    window._tools_toolbar.addSeparator()
    window._snap_toggle_action = QAction("Snap", window)
    window._snap_toggle_action.setCheckable(True)
    window._snap_toggle_action.setToolTip("Snap node placement and completed moves to the grid")
    window._snap_toggle_action.toggled.connect(window._set_grid_snapping_enabled)
    window._tools_toolbar.addAction(window._snap_toggle_action)
    window._grid_size_spinbox = QDoubleSpinBox(window)
    window._grid_size_spinbox.setRange(0.05, 2.0)
    window._grid_size_spinbox.setSingleStep(0.05)
    window._grid_size_spinbox.setDecimals(2)
    window._grid_size_spinbox.setValue(0.25)
    window._grid_size_spinbox.setPrefix("Grid ")
    window._grid_size_spinbox.setToolTip("Grid size in level coordinates")
    window._grid_size_spinbox.valueChanged.connect(window._set_grid_size)
    window._tools_toolbar.addWidget(window._grid_size_spinbox)
    window._tools_toolbar.addSeparator()
    window._road_shape_action_group = QActionGroup(window)
    window._road_shape_action_group.setExclusive(True)
    window._road_shape_actions = {}
    for label, road_shape in (
        ("Horizontal First", "horizontalFirst"),
        ("Vertical First", "verticalFirst"),
    ):
        action = QAction(label, window)
        action.setCheckable(True)
        action.setToolTip(f"Use {label.lower()} bends while connecting nodes")
        action.triggered.connect(
            lambda checked=False, selected=road_shape: window._set_pending_road_shape(selected)
        )
        window._road_shape_action_group.addAction(action)
        window._tools_toolbar.addAction(action)
        window._road_shape_actions[road_shape] = action
    window._road_shape_actions["horizontalFirst"].setChecked(True)
    window._bidirectional_road_action = QAction("Two-Way", window)
    window._bidirectional_road_action.setCheckable(True)
    window._bidirectional_road_action.setChecked(False)
    window._bidirectional_road_action.setToolTip(
        "Create both directed roads as one undoable edit (off by default)"
    )
    window._bidirectional_road_action.toggled.connect(
        window._set_bidirectional_roads_enabled
    )
    window._tools_toolbar.addAction(window._bidirectional_road_action)
