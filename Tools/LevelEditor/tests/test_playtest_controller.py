import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from app.controllers import PlaytestController
from app.models import EditorTool
from app.repositories import LevelFileRepository
from app.ui import LevelCanvasScene


@pytest.fixture
def qapplication() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def level():
    path = Path(__file__).parent / "fixtures" / "valid_level.json"
    return LevelFileRepository().load_level(path)


def test_playtest_lifecycle_isolated_from_authored_document(qapplication, level) -> None:
    controller = PlaytestController()
    original_edge_order = list(level.graph.nodes[0].outgoingEdgeIDs)

    controller.start(level)
    controller.pause()
    controller.advance_by(0.25)

    assert controller.state.running is True
    assert controller.state.paused is True
    assert controller.state.elapsed_time == pytest.approx(0.25)
    assert level.graph.nodes[0].outgoingEdgeIDs == original_edge_order

    controller.reset()
    assert controller.state.elapsed_time == 0.0
    assert controller.state.accepted_taps == ()

    controller.stop()
    assert controller.state.running is False


def test_canvas_renders_and_clears_playtest_overlays(qapplication, level) -> None:
    controller = PlaytestController()
    scene = LevelCanvasScene()
    scene.display_level(level)
    scene.set_editor_tool(EditorTool.PLAYTEST)
    controller.state_changed.connect(scene.update_playtest_overlay)

    controller.start(level)
    controller.pause()

    assert scene._playtest_dot_item is not None
    assert scene._playtest_dot_item.isVisible()
    assert all(not item.flags() & item.GraphicsItemFlag.ItemIsMovable for item in scene._node_items_by_id.values())

    controller.stop()
    assert scene._playtest_dot_item is None
