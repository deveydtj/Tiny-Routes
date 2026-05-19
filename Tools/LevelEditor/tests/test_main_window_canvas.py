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
from app.models import LevelDocument, RouteEdgeModel, RouteGraphModel, RouteNodeModel
from app.ui import EdgeItem, LevelCanvasScene, LevelCanvasView, NodeItem, PropertiesPanel
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


# ---------------------------------------------------------------------------
# Task 010: Edge rendering tests
# ---------------------------------------------------------------------------

def _make_two_node_document() -> LevelDocument:
    return LevelDocument(
        id="level_edges",
        name="Edge Level",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id="start", x=0.0, y=0.0, outgoingEdgeIDs=["e1"]),
                RouteNodeModel(id="destination", x=2.0, y=0.0, outgoingEdgeIDs=[]),
            ],
            edges=[
                RouteEdgeModel(id="e1", fromNodeID="start", toNodeID="destination"),
            ],
        ),
        startNodeID="start",
        packageNodeID="start",
        destinationNodeID="destination",
        timeLimitSeconds=30,
        parTaps=0,
    )


def test_canvas_scene_draws_edge_items(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    scene.display_level(_make_two_node_document())
    edge_items = [item for item in scene.items() if isinstance(item, EdgeItem)]
    assert len(edge_items) == 1
    assert edge_items[0].edge_id == "e1"


def test_edge_items_are_behind_node_items(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    scene.display_level(_make_two_node_document())
    edge_z = max(item.zValue() for item in scene.items() if isinstance(item, EdgeItem))
    node_z = min(item.zValue() for item in scene.items() if isinstance(item, NodeItem))
    assert edge_z < node_z


def test_canvas_scene_ignores_edge_with_missing_node(qapplication: QApplication) -> None:
    document = LevelDocument(
        id="level_bad_edge",
        name="Bad Edge Level",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id="start", x=0.0, y=0.0, outgoingEdgeIDs=["e_missing"]),
            ],
            edges=[
                RouteEdgeModel(id="e_missing", fromNodeID="start", toNodeID="nonexistent"),
            ],
        ),
        startNodeID="start",
        packageNodeID="start",
        destinationNodeID="start",
        timeLimitSeconds=10,
        parTaps=0,
    )
    scene = LevelCanvasScene()
    scene.display_level(document)
    edge_items = [item for item in scene.items() if isinstance(item, EdgeItem)]
    assert len(edge_items) == 0


def test_canvas_scene_clears_and_redraws_edges(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()

    first_document = _make_two_node_document()
    scene.display_level(first_document)
    first_edges = [item for item in scene.items() if isinstance(item, EdgeItem)]
    assert len(first_edges) == 1

    second_document = LevelDocument(
        id="level_no_edges",
        name="No Edges",
        graph=RouteGraphModel(
            nodes=[RouteNodeModel(id="node_a", x=0.0, y=0.0, outgoingEdgeIDs=[])],
            edges=[],
        ),
        startNodeID="node_a",
        packageNodeID="node_a",
        destinationNodeID="node_a",
        timeLimitSeconds=10,
        parTaps=0,
    )
    scene.display_level(second_document)
    second_edges = [item for item in scene.items() if isinstance(item, EdgeItem)]
    assert len(second_edges) == 0


def test_canvas_scene_skips_edge_between_colocated_nodes(qapplication: QApplication) -> None:
    document = LevelDocument(
        id="level_colocated",
        name="Co-located Nodes",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id="start", x=1.0, y=1.0, outgoingEdgeIDs=["e_same"]),
                RouteNodeModel(id="destination", x=1.0, y=1.0, outgoingEdgeIDs=[]),
            ],
            edges=[
                RouteEdgeModel(id="e_same", fromNodeID="start", toNodeID="destination"),
            ],
        ),
        startNodeID="start",
        packageNodeID="start",
        destinationNodeID="destination",
        timeLimitSeconds=10,
        parTaps=0,
    )
    scene = LevelCanvasScene()
    scene.display_level(document)
    edge_items = [item for item in scene.items() if isinstance(item, EdgeItem)]
    assert len(edge_items) == 0


# ---------------------------------------------------------------------------
# Task 011: Properties panel tests
# ---------------------------------------------------------------------------

def _make_two_node_two_edge_document() -> LevelDocument:
    return LevelDocument(
        id="level_props",
        name="Properties Test Level",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id="start", x=0.0, y=0.0, outgoingEdgeIDs=["e1"]),
                RouteNodeModel(id="destination", x=2.0, y=1.5, outgoingEdgeIDs=[]),
            ],
            edges=[
                RouteEdgeModel(id="e1", fromNodeID="start", toNodeID="destination"),
            ],
        ),
        startNodeID="start",
        packageNodeID="start",
        destinationNodeID="destination",
        timeLimitSeconds=30,
        parTaps=0,
    )


def test_main_window_has_properties_panel(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        assert isinstance(window._properties_panel, PropertiesPanel)
    finally:
        window.close()


def test_properties_panel_initial_state_is_empty(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        assert window._properties_panel._empty_label.isVisible()
        assert not window._properties_panel._form_widget.isVisible()
    finally:
        window.close()


def test_selecting_node_item_updates_properties_panel(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        scene = window._canvas_view.scene()
        scene.display_level(_make_two_node_two_edge_document())

        node_items = [item for item in scene.items() if isinstance(item, NodeItem)]
        start_item = next(item for item in node_items if item.node_id == "start")

        scene.clearSelection()
        start_item.setSelected(True)
        qapplication.processEvents()

        panel = window._properties_panel
        assert not panel._empty_label.isVisible()
        assert panel._form_widget.isVisible()

        labels = [panel._form_layout.itemAt(i).widget().text()
                  for i in range(panel._form_layout.count())
                  if panel._form_layout.itemAt(i).widget() is not None]
        assert "start" in labels
        assert "start" in labels  # node_id value row
    finally:
        window.close()


def test_selecting_node_item_shows_correct_type_and_position(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        scene = window._canvas_view.scene()
        scene.display_level(_make_two_node_two_edge_document())

        node_items = [item for item in scene.items() if isinstance(item, NodeItem)]
        dest_item = next(item for item in node_items if item.node_id == "destination")

        scene.clearSelection()
        dest_item.setSelected(True)
        qapplication.processEvents()

        panel = window._properties_panel
        labels = [panel._form_layout.itemAt(i).widget().text()
                  for i in range(panel._form_layout.count())
                  if panel._form_layout.itemAt(i).widget() is not None]

        # Destination node should show its type and position values
        assert "destination" in labels  # node_id or type value
        assert any("2.00" in lbl for lbl in labels)   # model_x = 2.0
        assert any("1.50" in lbl for lbl in labels)   # model_y = 1.5
    finally:
        window.close()


def test_selecting_edge_item_updates_properties_panel(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        scene = window._canvas_view.scene()
        scene.display_level(_make_two_node_two_edge_document())

        edge_items = [item for item in scene.items() if isinstance(item, EdgeItem)]
        assert len(edge_items) == 1
        edge_item = edge_items[0]

        scene.clearSelection()
        edge_item.setSelected(True)
        qapplication.processEvents()

        panel = window._properties_panel
        assert not panel._empty_label.isVisible()
        assert panel._form_widget.isVisible()

        labels = [panel._form_layout.itemAt(i).widget().text()
                  for i in range(panel._form_layout.count())
                  if panel._form_layout.itemAt(i).widget() is not None]
        assert "e1" in labels
        assert "start" in labels
        assert "destination" in labels
    finally:
        window.close()


def test_clearing_selection_resets_properties_panel(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        scene = window._canvas_view.scene()
        scene.display_level(_make_two_node_two_edge_document())

        node_items = [item for item in scene.items() if isinstance(item, NodeItem)]
        node_items[0].setSelected(True)
        qapplication.processEvents()

        # Now clear the selection
        scene.clearSelection()
        qapplication.processEvents()

        panel = window._properties_panel
        assert panel._empty_label.isVisible()
        assert not panel._form_widget.isVisible()
    finally:
        window.close()


def test_loading_new_level_clears_properties_panel(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = LevelEditorMainWindow()
    document = _make_two_node_two_edge_document()

    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: ("/tmp/level_props.json", ""))
    monkeypatch.setattr(window._repository, "load_level", lambda path: document)

    try:
        # Select a node first
        scene = window._canvas_view.scene()
        scene.display_level(document)
        node_items = [item for item in scene.items() if isinstance(item, NodeItem)]
        if node_items:
            node_items[0].setSelected(True)
            qapplication.processEvents()

        # Load a new level; the properties panel should be cleared
        window._open_level()
        qapplication.processEvents()

        panel = window._properties_panel
        assert panel._empty_label.isVisible()
        assert not panel._form_widget.isVisible()
    finally:
        window.close()


def test_node_item_stores_model_coordinates() -> None:
    item = NodeItem(node_id="n1", node_type="route", model_x=3.5, model_y=-1.2)
    assert item.model_x == 3.5
    assert item.model_y == -1.2


def test_edge_item_stores_source_and_target_node_ids(qapplication: QApplication) -> None:
    from_node = NodeItem(node_id="alpha", node_type="start")
    from_node.setPos(0, 0)
    to_node = NodeItem(node_id="beta", node_type="route")
    to_node.setPos(200, 0)
    edge = EdgeItem(edge_id="e_ab", from_node=from_node, to_node=to_node)
    assert edge.from_node_id == "alpha"
    assert edge.to_node_id == "beta"


def test_scene_emits_node_selected_signal(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    scene.display_level(_make_two_node_two_edge_document())

    received: list[tuple] = []
    scene.node_item_selected.connect(lambda *args: received.append(args))

    node_items = [item for item in scene.items() if isinstance(item, NodeItem)]
    start_item = next(item for item in node_items if item.node_id == "start")
    start_item.setSelected(True)
    qapplication.processEvents()

    assert len(received) == 1
    node_id, node_type, mx, my = received[0]
    assert node_id == "start"
    assert node_type == "start"
    assert mx == 0.0
    assert my == 0.0


def test_scene_emits_edge_selected_signal(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    scene.display_level(_make_two_node_two_edge_document())

    received: list[tuple] = []
    scene.edge_item_selected.connect(lambda *args: received.append(args))

    edge_items = [item for item in scene.items() if isinstance(item, EdgeItem)]
    edge_items[0].setSelected(True)
    qapplication.processEvents()

    assert len(received) == 1
    edge_id, from_id, to_id = received[0]
    assert edge_id == "e1"
    assert from_id == "start"
    assert to_id == "destination"


def test_scene_emits_selection_cleared_signal(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    scene.display_level(_make_two_node_two_edge_document())

    cleared: list[bool] = []
    scene.selection_cleared.connect(lambda: cleared.append(True))

    node_items = [item for item in scene.items() if isinstance(item, NodeItem)]
    node_items[0].setSelected(True)
    qapplication.processEvents()

    scene.clearSelection()
    qapplication.processEvents()

    assert len(cleared) >= 1

