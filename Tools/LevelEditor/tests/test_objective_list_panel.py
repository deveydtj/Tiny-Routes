from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QComboBox

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.controllers import DocumentController
from app.main_window import LevelEditorMainWindow
from app.models import RouteObjective, RouteObjectiveKind
from app.services import create_default_level_document
from app.ui import ObjectiveListPanel


_QAPPLICATION = QApplication.instance() or QApplication([])


def test_panel_shows_legacy_objectives_and_emits_node_kind_edits() -> None:
    level = create_default_level_document()
    panel = ObjectiveListPanel()
    received: list[list[RouteObjective]] = []
    panel.objectives_changed.connect(received.append)

    panel.set_level(level)

    assert panel._table.rowCount() == 2
    assert "Legacy" in panel._status_label.text()
    kind_combo = panel._table.cellWidget(0, 3)
    node_combo = panel._table.cellWidget(0, 2)
    assert isinstance(kind_combo, QComboBox)
    assert isinstance(node_combo, QComboBox)
    kind_combo.setCurrentIndex(kind_combo.findData("checkpoint"))
    node_combo.setCurrentIndex(node_combo.findData(level.startNodeID))

    assert received[-1][0].kind is RouteObjectiveKind.CHECKPOINT
    assert received[-1][0].nodeID == level.startNodeID
    assert [objective.sequenceIndex for objective in received[-1]] == [0, 1]


def test_panel_reorders_objectives_and_preserves_extension_metadata() -> None:
    level = create_default_level_document()
    level._extra["schemaVersion"] = 3
    level.objectives = [
        RouteObjective(
            id="pickup",
            nodeID=level.packageNodeID,
            kind=RouteObjectiveKind.PICKUP,
            sequenceIndex=0,
            revealPolicy="always",
            displayMetadata={"title": "Parcel"},
            _extra={"futureField": True},
            _display_metadata_present=True,
        ),
        RouteObjective(
            id="finish",
            nodeID=level.destinationNodeID,
            kind=RouteObjectiveKind.DESTINATION,
            sequenceIndex=1,
            revealPolicy="whenActive",
        ),
    ]
    panel = ObjectiveListPanel()
    received: list[list[RouteObjective]] = []
    panel.objectives_changed.connect(received.append)
    panel.set_level(level)

    panel._table.selectRow(0)
    panel._move_selected(1)

    assert [objective.id for objective in received[-1]] == ["finish", "pickup"]
    assert [objective.sequenceIndex for objective in received[-1]] == [0, 1]
    moved = received[-1][1]
    assert moved.displayMetadata == {"title": "Parcel"}
    assert moved._extra == {"futureField": True}


def test_controller_objective_edit_upgrades_schema_and_is_undoable() -> None:
    level = create_default_level_document()
    controller = DocumentController()
    controller.open(level, None, saved=True)
    objectives = level.effective_objectives
    objectives.insert(1, RouteObjective(
        id="checkpoint",
        nodeID=level.startNodeID,
        kind=RouteObjectiveKind.CHECKPOINT,
        sequenceIndex=1,
        revealPolicy="whenActive",
    ))

    controller.edit_objectives(objectives)

    assert level.schema_version == 3
    assert [objective.id for objective in level.objectives] == [
        "legacy_pickup", "checkpoint", "legacy_destination"
    ]
    assert [objective.sequenceIndex for objective in level.objectives] == [0, 1, 2]

    controller.undo_stack.undo()
    assert level.schema_version == 2
    assert level.objectives is None


def test_main_window_objective_combo_edit_is_safe_and_undoable() -> None:
    level = create_default_level_document()
    window = LevelEditorMainWindow()
    try:
        window._document_controller.open(level, None, saved=True)
        kind_combo = window._objective_list_panel._table.cellWidget(0, 3)
        assert isinstance(kind_combo, QComboBox)

        kind_combo.setCurrentIndex(kind_combo.findData("checkpoint"))
        _QAPPLICATION.processEvents()

        assert level.schema_version == 3
        assert level.objectives[0].kind is RouteObjectiveKind.CHECKPOINT
        window._document_controller.undo_stack.undo()
        assert level.schema_version == 2
        assert level.objectives is None
    finally:
        window.close()
