from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QMessageBox

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.main_window import LevelEditorMainWindow
from app.models import EditorTool
from app.services import ValidationMessage, ValidationResult, ValidationSeverity
from app.ui import NodeItem


_QAPPLICATION = QApplication.instance() or QApplication([])


@pytest.fixture
def qapplication() -> QApplication:
    # Keep a module-level reference so PySide cannot destroy the application
    # between this workflow and later editor test modules.
    return _QAPPLICATION


@pytest.fixture(autouse=True)
def discard_unsaved_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Discard,
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)


def test_editor_authoring_playtest_and_round_trip_smoke(
    qapplication: QApplication,
    tmp_path: Path,
) -> None:
    """Exercise the critical authoring workflow through the main window."""

    window = LevelEditorMainWindow()
    level_path = tmp_path / "editor_smoke.json"

    try:
        # New level creation and click-to-place commands.
        window._new_level()
        scene = window._canvas_view.scene()
        window._add_node_from_palette("package")
        assert scene.place_node_at(scene.model_to_scene_coordinates(1.5, 0.0))
        window._add_node_from_palette("destination")
        assert scene.place_node_at(scene.model_to_scene_coordinates(3.0, 0.0))

        document = window._current_document
        assert document is not None
        assert [node.id for node in document.graph.nodes] == [
            "start",
            "package",
            "destination",
        ]

        # Edge creation commands and inspector-backed property editing.
        window._on_edge_creation_requested(
            "e_start_package", "start", "package", "horizontalFirst"
        )
        window._on_edge_creation_requested(
            "e_package_destination",
            "package",
            "destination",
            "horizontalFirst",
        )
        window._on_node_position_changed("package", 1.25, 0.25)
        package = next(node for node in document.graph.nodes if node.id == "package")
        assert (package.x, package.y) == (1.25, 0.25)

        # The property edit must round-trip through the shared undo stack.
        window._document_controller.undo_stack.undo()
        package = next(node for node in document.graph.nodes if node.id == "package")
        assert (package.x, package.y) == (1.5, 0.0)
        window._document_controller.undo_stack.redo()
        package = next(node for node in document.graph.nodes if node.id == "package")
        assert (package.x, package.y) == (1.25, 0.25)

        # Complete a deterministic playtest and promote the recorded run.
        window._set_active_tool(EditorTool.PLAYTEST)
        window._playtest_controller.pause()
        window._playtest_controller.advance_by(10.0)
        recorded = window._playtest_controller.recorded_solution()
        assert recorded is not None
        assert recorded.levelID == document.id
        assert recorded.actions == []
        window._use_playtest_run_as_solution()
        assert window._current_solution is not None
        assert window._current_solution.isPlaceholder is False
        window._set_active_tool(EditorTool.SELECT)

        # Save both files and reopen them through the normal bundle loader.
        window._current_file_path = level_path
        assert window._save_level()
        assert level_path.is_file()
        assert (tmp_path / "editor_smoke.solution.json").is_file()
        assert window.open_level_bundle(level_path)

        reopened = window._current_document
        assert reopened is not None
        reopened_package = next(
            node for node in reopened.graph.nodes if node.id == "package"
        )
        assert (reopened_package.x, reopened_package.y) == (1.25, 0.25)
        assert [edge.id for edge in reopened.graph.edges] == [
            "e_start_package",
            "e_package_destination",
        ]

        # Validation message activation must focus the related canvas object.
        message = ValidationMessage(
            severity=ValidationSeverity.ERROR,
            code="smoke_focus_package",
            message="Focus the package node.",
            related_node_id="package",
        )
        window._validation_panel.show_result(ValidationResult(messages=[message]))
        item = window._validation_panel._message_list.item(0)
        window._validation_panel._message_list.itemDoubleClicked.emit(item)
        qapplication.processEvents()

        selected_node_ids = {
            item.node_id
            for item in scene.selectedItems()
            if isinstance(item, NodeItem)
        }
        assert selected_node_ids == {"package"}
        assert "Selected node 'package'" in window.statusBar().currentMessage()
    finally:
        window._autosave_timer.stop()
        window._validation_controller.cancel()
        window._puzzle_analysis_controller.cancel()
        window._playtest_controller.stop()
        window._set_dirty(False)
        window.close()
        window.deleteLater()
        qapplication.processEvents()
