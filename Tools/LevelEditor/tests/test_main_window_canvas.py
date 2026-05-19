import os
import sys
import math
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QFileDialog
except ImportError as exc:
    pytest.skip(f"PySide6 unavailable in this environment: {exc}", allow_module_level=True)

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.main_window import LevelEditorMainWindow
from app.models import LevelDocument, RouteGraphModel, RouteNodeModel
from app.ui import LevelCanvasScene, LevelCanvasView, NodeItem
from app.ui.node_item import NODE_TYPE_STYLES


@pytest.fixture
def qapplication() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_level_canvas_scene_has_empty_state_message(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    text_items = [item.text() for item in scene.items() if hasattr(item, "text")]

    assert "Open a level to begin" in text_items


def test_main_window_uses_canvas_view_as_central_widget(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        assert isinstance(window.centralWidget(), LevelCanvasView)
    finally:
        window.close()


def test_level_canvas_view_starts_centered_on_origin(qapplication: QApplication) -> None:
    view = LevelCanvasView()
    try:
        view.resize(800, 600)
        view.show()
        qapplication.processEvents()

        center_point = view.mapToScene(view.viewport().rect().center())
        assert abs(center_point.x()) < 10
        assert abs(center_point.y()) < 10
    finally:
        view.close()


def test_open_level_still_loads_document_with_canvas_central_widget(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = LevelEditorMainWindow()
    document = LevelDocument(
        id="level_123",
        name="Sample Level",
        graph=RouteGraphModel(),
        startNodeID="start",
        packageNodeID="package",
        destinationNodeID="destination",
        timeLimitSeconds=60,
        parTaps=3,
    )

    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: ("/tmp/level_123.json", ""))
    monkeypatch.setattr(window._repository, "load_level", lambda path: document)

    try:
        assert isinstance(window.centralWidget(), LevelCanvasView)
        window._open_level()
        assert window.windowTitle() == "Tiny Routes Level Editor — level_123"
        assert isinstance(window.centralWidget(), LevelCanvasView)
        text_items = [item.text() for item in window._canvas_view.scene().items() if hasattr(item, "text")]
        assert "No nodes in this level" in text_items
    finally:
        window.close()


def test_open_level_draws_nodes_on_canvas(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = LevelEditorMainWindow()
    document = LevelDocument(
        id="level_456",
        name="Node Drawing Level",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id="start", x=0.0, y=0.0, outgoingEdgeIDs=["e1"]),
                RouteNodeModel(id="switch_a", x=1.0, y=0.0, outgoingEdgeIDs=["e2", "e3"]),
                RouteNodeModel(id="package", x=2.0, y=0.0, outgoingEdgeIDs=["e4"]),
                RouteNodeModel(id="destination", x=3.0, y=0.0, outgoingEdgeIDs=[]),
            ],
        ),
        startNodeID="start",
        packageNodeID="package",
        destinationNodeID="destination",
        timeLimitSeconds=60,
        parTaps=2,
    )

    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: ("/tmp/level_456.json", ""))
    monkeypatch.setattr(window._repository, "load_level", lambda path: document)

    try:
        window._open_level()
        node_items = [item for item in window._canvas_view.scene().items() if isinstance(item, NodeItem)]
        assert {item.node_id for item in node_items} == {"start", "switch_a", "package", "destination"}
        assert all(item.childItems() for item in node_items)
    finally:
        window.close()


def test_canvas_scene_uses_fallback_layout_for_non_finite_coordinates(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    document = LevelDocument(
        id="level_invalid_coords",
        name="Invalid Coordinates",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id="start", x=0.0, y=0.0, outgoingEdgeIDs=["e_start_route"]),
                RouteNodeModel(id="route_a", x=math.nan, y=math.inf, outgoingEdgeIDs=[]),
            ],
        ),
        startNodeID="start",
        packageNodeID="route_a",
        destinationNodeID="route_a",
        timeLimitSeconds=20,
        parTaps=0,
    )

    scene.display_level(document)
    node_items = {item.node_id: item for item in scene.items() if isinstance(item, NodeItem)}
    assert node_items["route_a"].pos().x() == scene.FALLBACK_SPACING
    assert node_items["route_a"].pos().y() == 0.0


def test_canvas_scene_shows_no_nodes_message_for_empty_document(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    empty_document = LevelDocument(
        id="empty_level",
        name="Empty",
        graph=RouteGraphModel(),
        startNodeID="start",
        packageNodeID="package",
        destinationNodeID="destination",
        timeLimitSeconds=10,
        parTaps=0,
    )

    scene.display_level(empty_document)
    text_items = [item.text() for item in scene.items() if hasattr(item, "text")]
    assert "No nodes in this level" in text_items


def test_node_types_have_distinct_styles() -> None:
    assert len(set(NODE_TYPE_STYLES.values())) == len(NODE_TYPE_STYLES)


def test_canvas_scene_clears_and_redraws_nodes(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    first_document = LevelDocument(
        id="first_level",
        name="First",
        graph=RouteGraphModel(nodes=[RouteNodeModel(id="start", x=0.0, y=0.0, outgoingEdgeIDs=[])]),
        startNodeID="start",
        packageNodeID="start",
        destinationNodeID="start",
        timeLimitSeconds=10,
        parTaps=0,
    )
    second_document = LevelDocument(
        id="second_level",
        name="Second",
        graph=RouteGraphModel(nodes=[RouteNodeModel(id="node_b", x=1.0, y=1.0, outgoingEdgeIDs=[])]),
        startNodeID="node_b",
        packageNodeID="node_b",
        destinationNodeID="node_b",
        timeLimitSeconds=10,
        parTaps=0,
    )

    scene.display_level(first_document)
    first_node_ids = {item.node_id for item in scene.items() if isinstance(item, NodeItem)}
    assert first_node_ids == {"start"}

    scene.display_level(second_document)
    second_node_ids = {item.node_id for item in scene.items() if isinstance(item, NodeItem)}
    assert second_node_ids == {"node_b"}
