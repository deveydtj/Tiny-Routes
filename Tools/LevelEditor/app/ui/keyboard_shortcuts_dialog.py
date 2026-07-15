"""Discoverable keyboard and mouse controls for the level editor."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.models import EditorTool


MODE_SHORTCUTS: dict[EditorTool, str] = {
    EditorTool.SELECT: "V",
    EditorTool.PLACE_NODE: "N",
    EditorTool.CONNECT: "C",
    EditorTool.PLAYTEST: "P",
}


SHORTCUT_GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "Modes",
        (
            ("V", "Select and move level items"),
            ("N", "Enter Place Node mode; choose a palette item, then click the canvas"),
            ("C", "Enter Connect mode; choose a source node, then a destination"),
            ("P", "Enter Playtest mode"),
        ),
    ),
    (
        "Files and history",
        (
            ("Ctrl/Cmd+N", "Create a new level"),
            ("Ctrl/Cmd+O", "Open a level"),
            ("Ctrl/Cmd+S", "Save the current level and solution"),
            ("Ctrl/Cmd+Shift+S", "Save as"),
            ("Ctrl/Cmd+Z", "Undo the last edit"),
            ("Ctrl/Cmd+Shift+Z", "Redo the last undone edit"),
        ),
    ),
    (
        "Selection and editing",
        (
            ("Shift+click", "Add or remove an item from the selection"),
            ("Delete / Backspace", "Delete selected nodes or roads"),
            ("Arrow keys", "Nudge selected nodes by 0.05 level units"),
            ("Shift+Arrow", "Nudge selected nodes by 0.25 level units"),
        ),
    ),
    (
        "Connect mode",
        (
            ("Tab", "Toggle the pending road between Horizontal First and Vertical First"),
            ("Escape", "Cancel the pending road; press again to return to Select mode"),
        ),
    ),
    (
        "Canvas navigation",
        (
            ("Space+drag", "Pan the canvas with the left mouse button"),
            ("Middle-drag", "Pan the canvas"),
        ),
    ),
    (
        "Cancel",
        (
            ("Escape", "Cancel the current placement or connection; otherwise return to Select mode"),
        ),
    ),
)


class KeyboardShortcutsDialog(QDialog):
    """Show all editor shortcuts without requiring external documentation."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.resize(700, 520)

        layout = QVBoxLayout(self)
        introduction = QLabel(
            "Mode shortcuts work whenever the main editor window is active. "
            "Context-specific shortcuts apply while the canvas has focus."
        )
        introduction.setWordWrap(True)
        layout.addWidget(introduction)

        row_count = sum(len(entries) for _, entries in SHORTCUT_GROUPS)
        self.shortcut_table = QTableWidget(row_count, 3, self)
        self.shortcut_table.setObjectName("keyboardShortcutsTable")
        self.shortcut_table.setHorizontalHeaderLabels(
            ["Context", "Shortcut", "Behavior"]
        )
        self.shortcut_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.shortcut_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.shortcut_table.setAlternatingRowColors(True)

        row = 0
        for group, entries in SHORTCUT_GROUPS:
            for shortcut, behavior in entries:
                for column, value in enumerate((group, shortcut, behavior)):
                    item = QTableWidgetItem(value)
                    if column == 1:
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignCenter
                            | Qt.AlignmentFlag.AlignVCenter
                        )
                    self.shortcut_table.setItem(row, column, item)
                row += 1

        header = self.shortcut_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.shortcut_table.resizeRowsToContents()
        layout.addWidget(self.shortcut_table)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
