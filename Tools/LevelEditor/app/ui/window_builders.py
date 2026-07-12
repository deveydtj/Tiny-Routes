"""Declarative menu and toolbar construction for the editor window."""

from PySide6.QtGui import QAction, QActionGroup, QIcon, QKeySequence
from PySide6.QtWidgets import QMainWindow, QToolBar

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

    window._edit_menu = menu_bar.addMenu("Edit")
    window._undo_action = window._document_controller.undo_stack.createUndoAction(window, "Undo")
    window._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
    window._edit_menu.addAction(window._undo_action)
    window._redo_action = window._document_controller.undo_stack.createRedoAction(window, "Redo")
    window._redo_action.setShortcut(QKeySequence.StandardKey.Redo)
    window._edit_menu.addAction(window._redo_action)

    window._view_menu = menu_bar.addMenu("View")
    window._view_menu.addAction("Fit View").triggered.connect(window._canvas_view.fit_level_to_view)
    window._view_menu.addAction("Reset Zoom").triggered.connect(window._canvas_view.reset_zoom)

    window._tools_menu = menu_bar.addMenu("Tools")
    window._edit_metadata_action = window._tools_menu.addAction("Edit Level Metadata...")
    window._edit_metadata_action.triggered.connect(window._edit_level_metadata)
    window._promote_draft_action = window._tools_menu.addAction("Promote Draft to Production Level...")
    window._promote_draft_action.triggered.connect(window._promote_draft_to_production_level)
    window._repair_metadata_action = window._tools_menu.addAction("Repair Current Level Metadata...")
    window._repair_metadata_action.triggered.connect(window._repair_current_level_metadata)
    for action in (
        window._edit_metadata_action,
        window._promote_draft_action,
        window._repair_metadata_action,
    ):
        action.setEnabled(False)
    window._tools_menu.addSeparator()
    validate_action = window._tools_menu.addAction("Validate")
    validate_action.setToolTip("Validate Level + Solution References")
    validate_action.triggered.connect(window._validate_current_level)
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
