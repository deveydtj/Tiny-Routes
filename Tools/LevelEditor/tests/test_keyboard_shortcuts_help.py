import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
except ImportError as exc:
    pytest.skip(f"PySide6 unavailable in this environment: {exc}", allow_module_level=True)

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.main_window import LevelEditorMainWindow
from app.models import EditorTool
from app.ui.keyboard_shortcuts_dialog import KeyboardShortcutsDialog


@pytest.fixture
def qapplication() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_help_menu_opens_keyboard_shortcuts_dialog(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[str] = []
    monkeypatch.setattr(
        KeyboardShortcutsDialog,
        "exec",
        lambda self: opened.append(self.windowTitle()),
    )
    window = LevelEditorMainWindow()
    try:
        assert window._help_menu.title() == "Help"
        assert window._keyboard_shortcuts_action.text() == "Keyboard Shortcuts..."

        window._keyboard_shortcuts_action.trigger()

        assert opened == ["Keyboard Shortcuts"]
    finally:
        window.close()


def test_shortcuts_dialog_documents_connect_toggle_and_cancel(
    qapplication: QApplication,
) -> None:
    dialog = KeyboardShortcutsDialog()
    try:
        rows = [
            tuple(
                dialog.shortcut_table.item(row, column).text()
                for column in range(dialog.shortcut_table.columnCount())
            )
            for row in range(dialog.shortcut_table.rowCount())
        ]

        assert (
            "Connect mode",
            "Tab",
            "Toggle the pending road between Horizontal First and Vertical First",
        ) in rows
        assert (
            "Connect mode",
            "Escape",
            "Cancel the pending road; press again to return to Select mode",
        ) in rows
    finally:
        dialog.close()


def test_mode_tooltips_show_every_mode_shortcut(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        expected = {
            EditorTool.SELECT: "V",
            EditorTool.PLACE_NODE: "N",
            EditorTool.CONNECT: "C",
            EditorTool.PLAYTEST: "P",
        }
        for tool, shortcut in expected.items():
            assert f"({shortcut})" in window._tool_actions[tool].toolTip()
    finally:
        window.close()
