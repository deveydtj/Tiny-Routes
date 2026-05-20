import os
import sys
import math
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QKeyEvent, QPalette
    from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
except ImportError as exc:
    pytest.skip(f"PySide6 unavailable in this environment: {exc}", allow_module_level=True)

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.main_window import LevelEditorMainWindow
from app.models import LevelDocument, RouteEdgeModel, RouteGraphModel, RouteNodeModel, SolutionActionModel, SolutionModel
from app.services import ValidationMessage, ValidationResult, ValidationSeverity
from app.ui import (
    EdgeItem,
    LevelCanvasScene,
    LevelCanvasView,
    NodeItem,
    PiecePalette,
    PropertiesPanel,
    SolutionPanel,
    TransitionArcItem,
)
from app.ui.validation_panel import ValidationPanel
from app.ui.canvas_colors import (
    DARK_GRID_COLOR,
    DARK_ROAD_COLOR,
    LIGHT_GRID_COLOR,
    LIGHT_ROAD_COLOR,
    canvas_grid_color,
    road_color,
)
from app.ui.node_item import NODE_TYPE_STYLES


@pytest.fixture
def qapplication() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_canvas_colors_use_higher_contrast_light_palette(qapplication: QApplication) -> None:
    original_palette = qapplication.palette()
    try:
        palette = QPalette(original_palette)
        palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
        qapplication.setPalette(palette)

        assert canvas_grid_color().name() == LIGHT_GRID_COLOR
        assert road_color().name() == LIGHT_ROAD_COLOR
    finally:
        qapplication.setPalette(original_palette)


def test_canvas_colors_preserve_existing_dark_palette(qapplication: QApplication) -> None:
    original_palette = qapplication.palette()
    try:
        palette = QPalette(original_palette)
        palette.setColor(QPalette.ColorRole.Window, QColor("#202124"))
        qapplication.setPalette(palette)

        assert canvas_grid_color().name() == DARK_GRID_COLOR
        assert road_color().name() == DARK_ROAD_COLOR
    finally:
        qapplication.setPalette(original_palette)


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


def test_main_window_file_menu_includes_new_level_action(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        file_menu = next(
            (
                action.menu()
                for action in window.menuBar().actions()
                if action.menu() is not None and action.text().replace("&", "") == "File"
            ),
            None,
        )
        assert file_menu is not None
        action_texts = [action.text() for action in file_menu.actions()]
        assert "New Level" in action_texts
    finally:
        window.close()


def test_main_window_has_piece_palette(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        assert isinstance(window._piece_palette, PiecePalette)
    finally:
        window.close()


def test_main_window_has_solution_panel(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        assert isinstance(window._solution_panel, SolutionPanel)
    finally:
        window.close()


def test_piece_palette_lists_all_node_types(qapplication: QApplication) -> None:
    palette = PiecePalette()
    try:
        labels = [palette._list_widget.item(index).text() for index in range(palette._list_widget.count())]
        assert labels == ["Start", "Route Node", "Package", "Destination"]
    finally:
        palette.close()


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


def test_open_level_loads_solution_actions_into_solution_panel(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = LevelEditorMainWindow()
    document = LevelDocument(
        id="level_002",
        name="Node Drawing Level",
        graph=RouteGraphModel(),
        startNodeID="start",
        packageNodeID="package",
        destinationNodeID="destination",
        timeLimitSeconds=60,
        parTaps=2,
    )
    solution = SolutionModel(
        levelID="level_002",
        description="Test",
        expectedOutcome="completed",
        maxTaps=1,
        requiresWithinTimeLimit=True,
        actions=[SolutionActionModel(timeSeconds=0.5, tapNodeID="choice")],
    )

    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: ("/tmp/level_002.json", ""))
    monkeypatch.setattr(window._repository, "load_level", lambda path: document)
    monkeypatch.setattr(window._solution_repository, "load_solution", lambda path: solution)

    try:
        window._open_level()
        assert window._solution_panel._table.rowCount() == 1
        assert window._solution_panel._table.item(0, 0).text() == "0.5"
        assert window._solution_panel._table.item(0, 1).text() == "choice"
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


def test_canvas_scene_displays_positive_model_y_upward(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    document = LevelDocument(
        id="level_vertical",
        name="Vertical Level",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id="start", x=0.0, y=0.0, outgoingEdgeIDs=["e1"]),
                RouteNodeModel(id="destination", x=0.0, y=2.0, outgoingEdgeIDs=[]),
            ],
            edges=[
                RouteEdgeModel(id="e1", fromNodeID="start", toNodeID="destination"),
            ],
        ),
        startNodeID="start",
        packageNodeID="start",
        destinationNodeID="destination",
        timeLimitSeconds=20,
        parTaps=0,
    )

    scene.display_level(document)

    node_items = {item.node_id: item for item in scene.items() if isinstance(item, NodeItem)}
    assert node_items["start"].pos().y() == pytest.approx(0.0)
    assert node_items["destination"].pos().y() == pytest.approx(-2.0 * scene.COORDINATE_SCALE)


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


def test_solution_panel_can_add_edit_and_remove_actions(qapplication: QApplication) -> None:
    panel = SolutionPanel()
    panel.set_solution(
        SolutionModel(
            levelID="level_002",
            description="Test",
            expectedOutcome="completed",
            maxTaps=0,
            requiresWithinTimeLimit=True,
            actions=[],
        )
    )

    emitted_solutions: list[SolutionModel] = []
    panel.solution_changed.connect(emitted_solutions.append)

    try:
        panel._add_action_button.click()
        assert panel._table.rowCount() == 1
        assert emitted_solutions[-1].actions[0].tapNodeID == ""

        panel._table.item(0, 0).setText("1.25")
        panel._table.item(0, 1).setText("switch_a")
        assert emitted_solutions[-1].actions[0].timeSeconds == 1.25
        assert emitted_solutions[-1].actions[0].tapNodeID == "switch_a"

        panel._table.selectRow(0)
        panel._remove_action_button.click()
        assert panel._table.rowCount() == 0
        assert emitted_solutions[-1].actions == []
    finally:
        panel.close()


def test_solution_changes_mark_main_window_dirty(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = LevelEditorMainWindow()
    document = LevelDocument(
        id="level_002",
        name="Dirty State Level",
        graph=RouteGraphModel(),
        startNodeID="start",
        packageNodeID="package",
        destinationNodeID="destination",
        timeLimitSeconds=60,
        parTaps=2,
    )
    solution = SolutionModel(
        levelID="level_002",
        description="Test",
        expectedOutcome="completed",
        maxTaps=1,
        requiresWithinTimeLimit=True,
        actions=[SolutionActionModel(timeSeconds=0.5, tapNodeID="choice")],
    )

    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: ("/tmp/level_002.json", ""))
    monkeypatch.setattr(window._repository, "load_level", lambda path: document)
    monkeypatch.setattr(window._solution_repository, "load_solution", lambda path: solution)

    try:
        window._open_level()
        assert window._is_dirty is False

        window._solution_panel._table.item(0, 1).setText("choice_b")

        assert window._is_dirty is True
        assert window._current_solution is not None
        assert window._current_solution.actions[0].tapNodeID == "choice_b"
    finally:
        window.close()


def test_save_level_also_saves_solution_sidecar(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    window = LevelEditorMainWindow()
    level_path = tmp_path / "level_050.json"
    document = LevelDocument(
        id="level_050",
        name="Save Level",
        graph=RouteGraphModel(),
        startNodeID="start",
        packageNodeID="package",
        destinationNodeID="destination",
        timeLimitSeconds=60,
        parTaps=2,
    )
    solution = SolutionModel(
        levelID="level_050",
        description="Test",
        expectedOutcome="completed",
        maxTaps=1,
        requiresWithinTimeLimit=True,
        actions=[SolutionActionModel(timeSeconds=0.5, tapNodeID="choice")],
    )
    saved_solution: dict[str, object] = {}

    window._current_document = document
    window._current_solution = solution
    window._current_file_path = level_path

    monkeypatch.setattr(window._repository, "save_level", lambda path, doc: None)
    monkeypatch.setattr(window._solution_repository, "find_solution_path", lambda path: tmp_path / "level_050.solution.json")

    def capture_save_solution(path: Path, saved_model: SolutionModel) -> None:
        saved_solution["path"] = path
        saved_solution["model"] = saved_model

    monkeypatch.setattr(window._solution_repository, "save_solution", capture_save_solution)

    try:
        assert window._save_level() is True
        assert saved_solution["path"] == tmp_path / "level_050.solution.json"
        assert isinstance(saved_solution["model"], SolutionModel)
        assert saved_solution["model"].actions[0].tapNodeID == "choice"
    finally:
        window.close()


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


def test_canvas_scene_draws_smooth_transition_arc_for_perpendicular_default_handoff(
    qapplication: QApplication,
) -> None:
    document = LevelDocument(
        id="level_smooth_corner",
        name="Smooth Corner",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id="start", x=0.0, y=0.0, outgoingEdgeIDs=["to_corner"]),
                RouteNodeModel(id="corner", x=1.0, y=0.0, outgoingEdgeIDs=["to_end"]),
                RouteNodeModel(id="end", x=1.0, y=1.0, outgoingEdgeIDs=[]),
            ],
            edges=[
                RouteEdgeModel(id="to_corner", fromNodeID="start", toNodeID="corner"),
                RouteEdgeModel(id="to_end", fromNodeID="corner", toNodeID="end"),
            ],
        ),
        startNodeID="start",
        packageNodeID="start",
        destinationNodeID="end",
        timeLimitSeconds=10,
        parTaps=0,
    )

    scene = LevelCanvasScene()
    scene.display_level(document)

    arc_items = [item for item in scene.items() if isinstance(item, TransitionArcItem)]
    assert len(arc_items) == 1
    assert arc_items[0].node_id == "corner"
    assert arc_items[0].incoming_edge_id == "to_corner"
    assert arc_items[0].outgoing_edge_id == "to_end"

    path = arc_items[0].path()
    radius = LevelCanvasScene.STANDARD_TURN_RADIUS * LevelCanvasScene.COORDINATE_SCALE
    assert path.elementAt(0).x == pytest.approx(LevelCanvasScene.COORDINATE_SCALE - radius)
    assert path.elementAt(0).y == pytest.approx(0)
    assert path.elementAt(path.elementCount() - 1).x == pytest.approx(LevelCanvasScene.COORDINATE_SCALE)
    assert path.elementAt(path.elementCount() - 1).y == pytest.approx(radius)


def test_canvas_scene_does_not_draw_transition_arc_for_straight_handoff(
    qapplication: QApplication,
) -> None:
    document = LevelDocument(
        id="level_straight",
        name="Straight",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id="start", x=0.0, y=0.0, outgoingEdgeIDs=["to_middle"]),
                RouteNodeModel(id="middle", x=1.0, y=0.0, outgoingEdgeIDs=["to_end"]),
                RouteNodeModel(id="end", x=2.0, y=0.0, outgoingEdgeIDs=[]),
            ],
            edges=[
                RouteEdgeModel(id="to_middle", fromNodeID="start", toNodeID="middle"),
                RouteEdgeModel(id="to_end", fromNodeID="middle", toNodeID="end"),
            ],
        ),
        startNodeID="start",
        packageNodeID="start",
        destinationNodeID="end",
        timeLimitSeconds=10,
        parTaps=0,
    )

    scene = LevelCanvasScene()
    scene.display_level(document)

    arc_items = [item for item in scene.items() if isinstance(item, TransitionArcItem)]
    assert arc_items == []


def test_canvas_scene_transition_arc_uses_first_valid_outgoing_edge_as_default(
    qapplication: QApplication,
) -> None:
    document = LevelDocument(
        id="level_switch_default",
        name="Switch Default",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id="start", x=0.0, y=0.0, outgoingEdgeIDs=["to_switch"]),
                RouteNodeModel(id="switch", x=1.0, y=0.0, outgoingEdgeIDs=["to_straight", "to_turn"]),
                RouteNodeModel(id="straight", x=2.0, y=0.0, outgoingEdgeIDs=[]),
                RouteNodeModel(id="turn", x=1.0, y=1.0, outgoingEdgeIDs=[]),
            ],
            edges=[
                RouteEdgeModel(id="to_switch", fromNodeID="start", toNodeID="switch"),
                RouteEdgeModel(id="to_straight", fromNodeID="switch", toNodeID="straight"),
                RouteEdgeModel(id="to_turn", fromNodeID="switch", toNodeID="turn"),
            ],
        ),
        startNodeID="start",
        packageNodeID="start",
        destinationNodeID="turn",
        timeLimitSeconds=10,
        parTaps=0,
    )

    scene = LevelCanvasScene()
    scene.display_level(document)

    arc_items = [item for item in scene.items() if isinstance(item, TransitionArcItem)]
    assert arc_items == []


# ---------------------------------------------------------------------------
# Task 011: Properties panel tests
# ---------------------------------------------------------------------------

def _make_two_node_one_edge_document() -> LevelDocument:
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


def test_main_window_has_validation_panel(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        assert isinstance(window._validation_panel, ValidationPanel)
    finally:
        window.close()


def test_validation_panel_displays_messages_with_icons(qapplication: QApplication) -> None:
    panel = ValidationPanel()
    try:
        panel.show_result(
            ValidationResult(
                messages=[
                    ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        code="missing_level_id",
                        message="Level ID is missing or empty.",
                    ),
                    ValidationMessage(
                        severity=ValidationSeverity.WARNING,
                        code="unreachable_non_critical_node",
                        message="Node 'side' is not reachable from start node 'start'.",
                    ),
                    ValidationMessage(
                        severity=ValidationSeverity.INFO,
                        code="ok",
                        message="Validation completed.",
                    ),
                ]
            )
        )

        assert not panel._empty_label.isVisibleTo(panel)
        assert panel._message_list.isVisibleTo(panel)
        assert panel._message_list.count() == 3
        assert panel._message_list.item(0).text() == "Level ID is missing or empty."
        assert not panel._message_list.item(0).icon().isNull()
        assert not panel._message_list.item(1).icon().isNull()
        assert not panel._message_list.item(2).icon().isNull()
    finally:
        panel.close()


def test_validate_button_runs_validation_service_for_current_level(
    qapplication: QApplication,
) -> None:
    window = LevelEditorMainWindow()
    document = _make_two_node_one_edge_document()
    received: list[LevelDocument] = []

    def fake_validate(level: LevelDocument) -> ValidationResult:
        received.append(level)
        return ValidationResult(
            messages=[
                ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    code="unreachable_non_critical_node",
                    message="Node 'side' is not reachable from start node 'start'.",
                )
            ]
        )

    window._current_document = document
    window._validation_service.validate = fake_validate

    try:
        window._validation_panel._validate_button.click()
        qapplication.processEvents()

        assert received == [document]
        assert window._validation_panel._message_list.count() == 1
        assert (
            window._validation_panel._message_list.item(0).text()
            == "Node 'side' is not reachable from start node 'start'."
        )
    finally:
        window.close()


def test_properties_panel_initial_state_is_empty(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    panel = window._properties_panel
    try:
        assert panel._empty_label.isVisibleTo(panel)
        assert not panel._form_widget.isVisibleTo(panel)
    finally:
        window.close()


def test_selecting_node_item_updates_properties_panel(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        scene = window._canvas_view.scene()
        scene.display_level(_make_two_node_one_edge_document())

        node_items = [item for item in scene.items() if isinstance(item, NodeItem)]
        start_item = next(item for item in node_items if item.node_id == "start")

        scene.clearSelection()
        start_item.setSelected(True)
        qapplication.processEvents()

        panel = window._properties_panel
        assert not panel._empty_label.isVisibleTo(panel)
        assert panel._form_widget.isVisibleTo(panel)

        labels = [panel._form_layout.itemAt(i).widget().text()
                  for i in range(panel._form_layout.count())
                  if panel._form_layout.itemAt(i).widget() is not None]
        assert "ID:" in labels
        assert "Type:" in labels
        assert labels.count("start") == 2  # appears in both the ID row and the Type row
    finally:
        window.close()


def test_selecting_node_item_shows_correct_type_and_position(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        scene = window._canvas_view.scene()
        scene.display_level(_make_two_node_one_edge_document())

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
        scene.display_level(_make_two_node_one_edge_document())

        edge_items = [item for item in scene.items() if isinstance(item, EdgeItem)]
        assert len(edge_items) == 1
        edge_item = edge_items[0]

        scene.clearSelection()
        edge_item.setSelected(True)
        qapplication.processEvents()

        panel = window._properties_panel
        assert not panel._empty_label.isVisibleTo(panel)
        assert panel._form_widget.isVisibleTo(panel)

        labels = [panel._form_layout.itemAt(i).widget().text()
                  for i in range(panel._form_layout.count())
                  if panel._form_layout.itemAt(i).widget() is not None]
        assert "e1" in labels
        assert "start" in labels
        assert "destination" in labels
        assert "Horizontal First" in labels
    finally:
        window.close()


def test_clearing_selection_resets_properties_panel(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        scene = window._canvas_view.scene()
        scene.display_level(_make_two_node_one_edge_document())

        node_items = [item for item in scene.items() if isinstance(item, NodeItem)]
        node_items[0].setSelected(True)
        qapplication.processEvents()

        # Now clear the selection
        scene.clearSelection()
        qapplication.processEvents()

        panel = window._properties_panel
        assert panel._empty_label.isVisibleTo(panel)
        assert not panel._form_widget.isVisibleTo(panel)
    finally:
        window.close()


def test_loading_new_level_clears_properties_panel(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = LevelEditorMainWindow()
    document = _make_two_node_one_edge_document()

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
        assert panel._empty_label.isVisibleTo(panel)
        assert not panel._form_widget.isVisibleTo(panel)
    finally:
        window.close()


def test_loading_new_level_clears_validation_panel(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = LevelEditorMainWindow()
    document = _make_two_node_one_edge_document()

    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: ("/tmp/level_props.json", ""))
    monkeypatch.setattr(window._repository, "load_level", lambda path: document)

    window._validation_panel.show_result(
        ValidationResult(
            messages=[
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="missing_level_name",
                    message="Level name is missing or empty.",
                )
            ]
        )
    )

    try:
        window._open_level()
        qapplication.processEvents()

        panel = window._validation_panel
        assert panel._empty_label.isVisibleTo(panel)
        assert not panel._message_list.isVisibleTo(panel)
        assert panel._message_list.count() == 0
    finally:
        window.close()


def test_new_level_creates_minimal_document_and_updates_canvas(
    qapplication: QApplication,
) -> None:
    window = LevelEditorMainWindow()

    try:
        window._new_level()
        qapplication.processEvents()

        assert window._current_document is not None
        assert window._current_document.id == "new_level"
        assert window._current_document.name == "New Level"
        assert window._current_document.startNodeID == "start"
        assert window._current_document.packageNodeID == "start"
        assert window._current_document.destinationNodeID == "start"
        assert window._current_document.timeLimitSeconds == 30
        assert window._current_file_path is None
        assert window._is_dirty is True

        node_items = [item for item in window._canvas_view.scene().items() if isinstance(item, NodeItem)]
        assert {item.node_id for item in node_items} == {"start"}
    finally:
        window.close()


def test_palette_double_click_adds_unique_node_to_canvas_center_and_marks_dirty(
    qapplication: QApplication,
) -> None:
    window = LevelEditorMainWindow()

    try:
        window._new_level()
        window._set_dirty(False)

        route_item = next(
            window._piece_palette._list_widget.item(index)
            for index in range(window._piece_palette._list_widget.count())
            if window._piece_palette._list_widget.item(index).text() == "Route Node"
        )

        center_scene_point = window._canvas_view.mapToScene(window._canvas_view.viewport().rect().center())
        expected_model_x = center_scene_point.x() / window._canvas_view.scene().COORDINATE_SCALE
        expected_model_y = -center_scene_point.y() / window._canvas_view.scene().COORDINATE_SCALE

        window._piece_palette._list_widget.itemDoubleClicked.emit(route_item)
        window._piece_palette._list_widget.itemDoubleClicked.emit(route_item)
        qapplication.processEvents()

        assert window._current_document is not None
        node_ids = [node.id for node in window._current_document.graph.nodes]
        assert "node" in node_ids
        assert "node_1" in node_ids

        created_node = next(node for node in window._current_document.graph.nodes if node.id == "node")
        assert created_node.x == pytest.approx(expected_model_x)
        assert created_node.y == pytest.approx(expected_model_y)

        canvas_node_ids = {
            item.node_id
            for item in window._canvas_view.scene().items()
            if isinstance(item, NodeItem)
        }
        assert "node" in canvas_node_ids
        assert "node_1" in canvas_node_ids
        assert window._is_dirty is True
    finally:
        window.close()


@pytest.mark.parametrize(
    ("palette_label", "document_id_field"),
    [
        ("Start", "startNodeID"),
        ("Package", "packageNodeID"),
        ("Destination", "destinationNodeID"),
    ],
)
def test_palette_double_click_updates_special_node_ids(
    qapplication: QApplication,
    palette_label: str,
    document_id_field: str,
) -> None:
    window = LevelEditorMainWindow()

    try:
        window._new_level()
        window._set_dirty(False)

        initial_node_count = len(window._current_document.graph.nodes) if window._current_document else 0
        target_item = next(
            window._piece_palette._list_widget.item(index)
            for index in range(window._piece_palette._list_widget.count())
            if window._piece_palette._list_widget.item(index).text() == palette_label
        )

        window._piece_palette._list_widget.itemDoubleClicked.emit(target_item)
        qapplication.processEvents()

        assert window._current_document is not None
        created_node = window._current_document.graph.nodes[-1]
        assert len(window._current_document.graph.nodes) == initial_node_count + 1
        assert getattr(window._current_document, document_id_field) == created_node.id
    finally:
        window.close()


def test_new_level_respects_unsaved_changes_prompt_cancel(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = LevelEditorMainWindow()
    existing_document = _make_two_node_one_edge_document()
    window._current_document = existing_document
    window._set_dirty(True)
    prompted = False

    def fake_prompt() -> bool:
        nonlocal prompted
        prompted = True
        return False

    monkeypatch.setattr(window, "_prompt_to_save_unsaved_changes", fake_prompt)

    try:
        window._new_level()
        assert prompted is True
        assert window._current_document is existing_document
    finally:
        window.close()


def test_open_level_respects_unsaved_changes_prompt_cancel(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = LevelEditorMainWindow()
    existing_document = _make_two_node_one_edge_document()
    window._current_document = existing_document
    window._set_dirty(True)
    prompted = False

    def fake_prompt() -> bool:
        nonlocal prompted
        prompted = True
        return False

    monkeypatch.setattr(window, "_prompt_to_save_unsaved_changes", fake_prompt)
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: pytest.fail("Open file dialog should not be shown when prompt is canceled"),
    )

    try:
        window._open_level()
        assert prompted is True
        assert window._current_document is existing_document
    finally:
        window.close()


def test_save_level_writes_to_current_path_without_prompt(
    qapplication: QApplication,
    tmp_path: Path,
) -> None:
    window = LevelEditorMainWindow()
    document = _make_two_node_one_edge_document()
    save_path = tmp_path / "save_current.json"
    received: list[tuple[Path, LevelDocument]] = []

    window._current_document = document
    window._current_file_path = save_path
    window._set_dirty(True)

    def fake_save(path: Path, level_document: LevelDocument) -> None:
        received.append((path, level_document))

    window._repository.save_level = fake_save

    try:
        assert window._save_level() is True
        assert received == [(save_path, document)]
        assert window._is_dirty is False
    finally:
        window.close()


def test_save_level_as_prompts_for_new_path_and_updates_current_path(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    window = LevelEditorMainWindow()
    document = _make_two_node_one_edge_document()
    save_path = tmp_path / "save_as.json"
    received: list[tuple[Path, LevelDocument]] = []

    window._current_document = document
    window._set_dirty(True)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(save_path), ""))

    def fake_save(path: Path, level_document: LevelDocument) -> None:
        received.append((path, level_document))

    window._repository.save_level = fake_save

    try:
        assert window._save_level_as() is True
        assert received == [(save_path, document)]
        assert window._current_file_path == save_path
        assert window._is_dirty is False
    finally:
        window.close()


def test_dirty_indicator_appears_in_window_title(
    qapplication: QApplication,
) -> None:
    window = LevelEditorMainWindow()
    document = _make_two_node_one_edge_document()
    window._current_document = document
    window._set_dirty(False)

    try:
        assert window.windowTitle() == "Tiny Routes Level Editor — level_props"
        window._mark_document_dirty()
        assert window.windowTitle() == "Tiny Routes Level Editor — level_props *"
    finally:
        window.close()


def test_close_prompt_cancel_keeps_window_open(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = LevelEditorMainWindow()
    window._current_document = _make_two_node_one_edge_document()
    window._set_dirty(True)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Cancel)

    try:
        assert window._prompt_to_save_unsaved_changes() is False
    finally:
        window.close()


def test_close_prompt_save_invokes_save(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = LevelEditorMainWindow()
    window._current_document = _make_two_node_one_edge_document()
    window._set_dirty(True)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Save)
    monkeypatch.setattr(window, "_save_level", lambda: True)

    try:
        assert window._prompt_to_save_unsaved_changes() is True
    finally:
        window.close()


def test_unsaved_changes_prompt_uses_generic_message(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = LevelEditorMainWindow()
    window._current_document = _make_two_node_one_edge_document()
    window._set_dirty(True)
    captured_text: str | None = None

    def fake_question(*args, **kwargs):
        nonlocal captured_text
        captured_text = args[2]
        return QMessageBox.StandardButton.Discard

    monkeypatch.setattr(QMessageBox, "question", fake_question)

    try:
        assert window._prompt_to_save_unsaved_changes() is True
        assert captured_text == "You have unsaved changes. Save before continuing?"
    finally:
        window.close()


def test_node_item_stores_model_coordinates() -> None:
    item = NodeItem(node_id="n1", node_type="route", model_x=3.5, model_y=-1.2)
    assert item.model_x == 3.5
    assert item.model_y == -1.2


def test_node_item_is_draggable() -> None:
    item = NodeItem(node_id="n1", node_type="route")
    assert item.flags() & item.GraphicsItemFlag.ItemIsMovable


def test_node_item_connection_source_updates_border(qapplication: QApplication) -> None:
    item = NodeItem(node_id="n1", node_type="route")

    default_pen = item._circle.pen()
    assert default_pen.color().name() == NODE_TYPE_STYLES["route"].border_color
    assert default_pen.width() == 2

    item.set_connection_source(True)
    pending_pen = item._circle.pen()
    assert pending_pen.color().name() == item.PENDING_BORDER_COLOR
    assert pending_pen.width() == item.PENDING_BORDER_WIDTH

    item.set_connection_source(False)
    restored_pen = item._circle.pen()
    assert restored_pen.color().name() == NODE_TYPE_STYLES["route"].border_color
    assert restored_pen.width() == 2


def test_edge_item_stores_source_and_target_node_ids(qapplication: QApplication) -> None:
    from_node = NodeItem(node_id="alpha", node_type="start")
    from_node.setPos(0, 0)
    to_node = NodeItem(node_id="beta", node_type="route")
    to_node.setPos(200, 0)
    edge = EdgeItem(edge_id="e_ab", from_node=from_node, to_node=to_node)
    assert edge.from_node_id == "alpha"
    assert edge.to_node_id == "beta"


def test_edge_item_uses_orthogonal_path_for_horizontal_first(qapplication: QApplication) -> None:
    from_node = NodeItem(node_id="alpha", node_type="start")
    from_node.setPos(0, 0)
    to_node = NodeItem(node_id="beta", node_type="route")
    to_node.setPos(180, 180)

    edge = EdgeItem(
        edge_id="e_ab",
        from_node=from_node,
        to_node=to_node,
        road_shape="horizontalFirst",
    )

    path = edge._path_item.path()
    assert path.elementCount() == 3
    assert path.elementAt(1).y == pytest.approx(path.elementAt(0).y)
    assert path.elementAt(1).x == pytest.approx(path.elementAt(2).x)


def test_edge_item_uses_orthogonal_path_for_vertical_first(qapplication: QApplication) -> None:
    from_node = NodeItem(node_id="alpha", node_type="start")
    from_node.setPos(0, 0)
    to_node = NodeItem(node_id="beta", node_type="route")
    to_node.setPos(180, 180)

    edge = EdgeItem(
        edge_id="e_ab",
        from_node=from_node,
        to_node=to_node,
        road_shape="verticalFirst",
    )

    path = edge._path_item.path()
    assert path.elementCount() == 3
    assert path.elementAt(1).x == pytest.approx(path.elementAt(0).x)
    assert path.elementAt(1).y == pytest.approx(path.elementAt(2).y)


def test_scene_emits_node_selected_signal(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    scene.display_level(_make_two_node_one_edge_document())

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
    scene.display_level(_make_two_node_one_edge_document())

    received: list[tuple] = []
    scene.edge_item_selected.connect(lambda *args: received.append(args))

    edge_items = [item for item in scene.items() if isinstance(item, EdgeItem)]
    edge_items[0].setSelected(True)
    qapplication.processEvents()

    assert len(received) == 1
    edge_id, from_id, to_id, road_shape = received[0]
    assert edge_id == "e1"
    assert from_id == "start"
    assert to_id == "destination"
    assert road_shape == "horizontalFirst"


def test_scene_emits_selection_cleared_signal(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    scene.display_level(_make_two_node_one_edge_document())

    cleared: list[bool] = []
    scene.selection_cleared.connect(lambda: cleared.append(True))

    node_items = [item for item in scene.items() if isinstance(item, NodeItem)]
    node_items[0].setSelected(True)
    qapplication.processEvents()

    scene.clearSelection()
    qapplication.processEvents()

    assert len(cleared) >= 1


def test_dragging_node_updates_model_coordinates_and_connected_edge(
    qapplication: QApplication,
) -> None:
    scene = LevelCanvasScene()
    scene.display_level(_make_two_node_one_edge_document())

    moved: list[tuple[str, float, float]] = []
    scene.node_item_moved.connect(lambda *args: moved.append(args))

    node_items = [item for item in scene.items() if isinstance(item, NodeItem)]
    start_item = next(item for item in node_items if item.node_id == "start")
    edge_item = next(item for item in scene.items() if isinstance(item, EdgeItem))
    original_path = edge_item._path_item.path()

    start_item.setSelected(True)
    start_item.setPos(180.0, -90.0)
    qapplication.processEvents()

    assert start_item.model_x == pytest.approx(1.0)
    assert start_item.model_y == pytest.approx(0.5)
    assert moved[-1] == ("start", pytest.approx(1.0), pytest.approx(0.5))

    updated_path = edge_item._path_item.path()
    assert updated_path != original_path


def test_dragging_selected_node_updates_properties_panel_position(
    qapplication: QApplication,
) -> None:
    window = LevelEditorMainWindow()
    try:
        scene = window._canvas_view.scene()
        scene.display_level(_make_two_node_one_edge_document())

        node_items = [item for item in scene.items() if isinstance(item, NodeItem)]
        start_item = next(item for item in node_items if item.node_id == "start")

        start_item.setSelected(True)
        start_item.setPos(180.0, -90.0)
        qapplication.processEvents()

        labels = [
            window._properties_panel._form_layout.itemAt(i).widget().text()
            for i in range(window._properties_panel._form_layout.count())
            if window._properties_panel._form_layout.itemAt(i).widget() is not None
        ]
        assert any("(1.00, 0.50)" == label for label in labels)
    finally:
        window.close()


def test_dragging_node_updates_current_document_and_marks_dirty(
    qapplication: QApplication,
) -> None:
    window = LevelEditorMainWindow()
    try:
        window._current_document = _make_two_node_one_edge_document()
        window._canvas_view.scene().display_level(window._current_document)
        window._validation_panel.show_result(
            ValidationResult(
                messages=[
                    ValidationMessage(
                        severity=ValidationSeverity.INFO,
                        code="validated",
                        message="Validation completed.",
                    )
                ]
            )
        )
        window._set_dirty(False)

        node_items = [item for item in window._canvas_view.scene().items() if isinstance(item, NodeItem)]
        start_item = next(item for item in node_items if item.node_id == "start")

        start_item.setPos(180.0, -90.0)
        qapplication.processEvents()

        moved_node = next(node for node in window._current_document.graph.nodes if node.id == "start")
        assert moved_node.x == pytest.approx(1.0)
        assert moved_node.y == pytest.approx(0.5)
        assert window._is_dirty is True
        assert window._validation_panel._message_list.count() == 0
        assert window._validation_panel._empty_label.isVisibleTo(window._validation_panel)
    finally:
        window.close()


def test_delete_key_removes_selected_edge_and_updates_outgoing_edge_ids(
    qapplication: QApplication,
) -> None:
    scene = LevelCanvasScene()
    document = _make_two_node_one_edge_document()
    scene.display_level(document)

    edge_item = next(item for item in scene.items() if isinstance(item, EdgeItem))
    edge_item.setSelected(True)
    qapplication.processEvents()

    scene.keyPressEvent(
        QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
    )
    qapplication.processEvents()

    assert document.graph.edges == []
    start_node = next(node for node in document.graph.nodes if node.id == "start")
    assert start_node.outgoingEdgeIDs == []
    assert [item for item in scene.items() if isinstance(item, EdgeItem)] == []


def test_delete_key_removes_selected_node_and_connected_edges(
    qapplication: QApplication,
) -> None:
    scene = LevelCanvasScene()
    document = _make_two_node_one_edge_document()
    scene.display_level(document)

    start_item = next(
        item for item in scene.items() if isinstance(item, NodeItem) and item.node_id == "start"
    )
    start_item.setSelected(True)
    qapplication.processEvents()

    scene.keyPressEvent(
        QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
    )
    qapplication.processEvents()

    remaining_node_ids = {node.id for node in document.graph.nodes}
    assert remaining_node_ids == {"destination"}
    assert document.graph.edges == []
    assert [item for item in scene.items() if isinstance(item, EdgeItem)] == []


def test_delete_key_marks_main_window_dirty_and_clears_validation(
    qapplication: QApplication,
) -> None:
    window = LevelEditorMainWindow()
    try:
        window._current_document = _make_two_node_one_edge_document()
        window._canvas_view.scene().display_level(window._current_document)
        window._validation_panel.show_result(
            ValidationResult(
                messages=[
                    ValidationMessage(
                        severity=ValidationSeverity.INFO,
                        code="validated",
                        message="Validation completed.",
                    )
                ]
            )
        )
        window._set_dirty(False)

        edge_item = next(
            item for item in window._canvas_view.scene().items() if isinstance(item, EdgeItem)
        )
        edge_item.setSelected(True)
        qapplication.processEvents()

        window._canvas_view.scene().keyPressEvent(
            QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
        )
        qapplication.processEvents()

        assert window._is_dirty is True
        assert window._current_document.graph.edges == []
        assert window._validation_panel._message_list.count() == 0
        assert window._validation_panel._empty_label.isVisibleTo(window._validation_panel)
    finally:
        window.close()


def test_canvas_view_forwards_delete_key_to_scene(
    qapplication: QApplication,
) -> None:
    view = LevelCanvasView()
    try:
        document = _make_two_node_one_edge_document()
        view.scene().display_level(document)

        edge_item = next(item for item in view.scene().items() if isinstance(item, EdgeItem))
        edge_item.setSelected(True)
        qapplication.processEvents()

        view.keyPressEvent(
            QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
        )
        qapplication.processEvents()

        assert document.graph.edges == []
    finally:
        view.close()


def test_deleting_last_node_does_not_crash(
    qapplication: QApplication,
) -> None:
    scene = LevelCanvasScene()
    document = LevelDocument(
        id="single_node_level",
        name="Single Node Level",
        graph=RouteGraphModel(
            nodes=[RouteNodeModel(id="start", x=0.0, y=0.0, outgoingEdgeIDs=[])]
        ),
        startNodeID="start",
        packageNodeID="start",
        destinationNodeID="start",
        timeLimitSeconds=10,
        parTaps=0,
    )
    scene.display_level(document)

    start_item = next(item for item in scene.items() if isinstance(item, NodeItem))
    start_item.setSelected(True)
    qapplication.processEvents()

    scene.keyPressEvent(
        QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
    )
    qapplication.processEvents()

    assert document.graph.nodes == []
    text_items = [item.text() for item in scene.items() if hasattr(item, "text")]
    assert "No nodes in this level" in text_items


def test_scene_duplicate_edge_attempt_emits_clear_message(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    scene.display_level(_make_two_node_one_edge_document())

    messages: list[str] = []
    scene.placement_message_changed.connect(messages.append)

    node_items = {item.node_id: item for item in scene.items() if isinstance(item, NodeItem)}
    scene._handle_connection_click(node_items["start"])
    scene._handle_connection_click(node_items["destination"])

    assert messages[-1] == "Road not added. start already connects to destination."


def test_main_window_edge_creation_persists_selected_road_shape(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        window._current_document = LevelDocument(
            id="level_new_edge",
            name="New Edge",
            graph=RouteGraphModel(
                nodes=[
                    RouteNodeModel(id="start", x=0.0, y=0.0, outgoingEdgeIDs=[]),
                    RouteNodeModel(id="destination", x=2.0, y=1.0, outgoingEdgeIDs=[]),
                ],
                edges=[],
            ),
            startNodeID="start",
            packageNodeID="start",
            destinationNodeID="destination",
            timeLimitSeconds=30,
            parTaps=0,
        )

        window._on_edge_creation_requested("edge", "start", "destination", "verticalFirst")

        assert window._current_document.graph.edges[0].roadShape == "verticalFirst"
        assert window._current_document.graph.nodes[0].outgoingEdgeIDs == ["edge"]
    finally:
        window.close()


def test_scene_tab_toggles_preview_shape_and_emits_message(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    scene.display_level(_make_two_node_one_edge_document())

    messages: list[str] = []
    scene.placement_message_changed.connect(messages.append)

    start_item = next(
        item for item in scene.items() if isinstance(item, NodeItem) and item.node_id == "start"
    )
    scene._handle_connection_click(start_item)
    scene.keyPressEvent(
        QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier)
    )

    assert scene._pending_road_shape == "verticalFirst"
    assert messages[-1] == "Road preview set to Vertical First."


def test_connection_preview_hides_when_cursor_is_on_source_node(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    scene.display_level(_make_two_node_one_edge_document())

    start_item = next(
        item for item in scene.items() if isinstance(item, NodeItem) and item.node_id == "start"
    )
    scene._handle_connection_click(start_item)

    scene._update_connection_preview(start_item.pos())

    assert scene._preview_path_item is not None
    assert scene._preview_path_item.path().isEmpty()
    assert scene._preview_path_item.isVisible() is False
