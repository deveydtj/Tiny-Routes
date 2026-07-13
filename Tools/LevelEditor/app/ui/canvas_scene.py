import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsEllipseItem,
    QGraphicsRectItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsSimpleTextItem,
)
from shiboken6 import isValid

from app.models import EditorTool, LevelDocument, RouteNodeModel
from app.models.playtest_state import PlaytestState
from tiny_routes_core.simulation import LevelOutcome
from app.services.switch_classification_service import SwitchClassificationService, SwitchNodeKind
from app.services.level_validation_service import ValidationResult

from .canvas_colors import canvas_grid_color
from .edge_item import EdgeItem
from .node_item import NodeItem
from .transition_arc_item import TransitionArcItem


class LevelCanvasScene(QGraphicsScene):
    COORDINATE_SCALE = 180.0
    FALLBACK_SPACING = 140.0
    STANDARD_TURN_RADIUS = 0.18

    # Emitted when a NodeItem is selected.  Args: node_id, node_type, model_x, model_y
    node_item_selected = Signal(str, str, float, float)
    # Emitted when an EdgeItem is selected.  Args: edge_id, from_node_id, to_node_id, road_shape
    edge_item_selected = Signal(str, str, str, str)
    # Emitted when the selection is cleared or an unrecognised item is selected
    selection_cleared = Signal()
    # Emitted when a node is repositioned. Args: node_id, model_x, model_y
    node_item_moved = Signal(str, float, float)
    # Args: edge_id, from_node_id, to_node_id, road_shape, bidirectional.
    edge_creation_requested = Signal(str, str, str, str, bool)
    # Mutation requests are handled by DocumentController.
    delete_items_requested = Signal(object, object)
    # Emitted to explain placement state and failures.
    placement_message_changed = Signal(str)
    # Args: node role, model x, model y. The controller performs the mutation.
    node_placement_requested = Signal(str, float, float)
    # Emitted when the persistent or temporary preview bend changes.
    road_shape_changed = Signal(str)
    # Emitted for left-clicked nodes while the simulator owns the canvas.
    playtest_tap_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setSceneRect(QRectF(-2000, -2000, 4000, 4000))
        self._document: LevelDocument | None = None
        self._node_items_by_id: dict[str, NodeItem] = {}
        self._edges_by_node_id: dict[str, list[EdgeItem]] = {}
        self._edge_items_by_id: dict[str, EdgeItem] = {}
        self._validation_area_items: list[QGraphicsRectItem] = []
        self._transition_arc_items: list[TransitionArcItem] = []
        self._connection_source_node_id: str | None = None
        self._pending_road_shape = "horizontalFirst"
        self._bidirectional_roads_enabled = False
        self._preview_path_item: QGraphicsPathItem | None = None
        self._preview_label_item: QGraphicsSimpleTextItem | None = None
        self._preview_arrow_item: QGraphicsPolygonItem | None = None
        self._connection_drag_active = False
        self._temporary_shape_swapped = False
        self._editor_tool = EditorTool.SELECT
        self._placement_node_type: str | None = None
        self._placement_preview: NodeItem | None = None
        self._grid_snapping_enabled = False
        self._grid_spacing = 0.25
        self._drag_start_positions: dict[str, tuple[float, float]] = {}
        self._alignment_guides: list[QGraphicsLineItem] = []
        self._is_finishing_drag = False
        self._delete_items_handler = None
        self._playtest_dot_item: QGraphicsEllipseItem | None = None
        self._active_switch_item: QGraphicsEllipseItem | None = None
        self._playtest_status_item: QGraphicsSimpleTextItem | None = None
        self._show_placeholder()
        self.selectionChanged.connect(self._on_selection_changed)

    @property
    def editor_tool(self) -> EditorTool:
        return self._editor_tool

    def set_editor_tool(self, tool: EditorTool) -> None:
        if tool is self._editor_tool:
            return
        self.cancel_current_operation()
        self._editor_tool = tool
        editing_enabled = tool is not EditorTool.PLAYTEST
        for node_item in self._node_items_by_id.values():
            node_item.setFlag(node_item.GraphicsItemFlag.ItemIsMovable, editing_enabled)
            node_item.setFlag(node_item.GraphicsItemFlag.ItemIsSelectable, editing_enabled)
            node_item.set_connection_handles_enabled(tool is EditorTool.CONNECT)
        for item in self.items():
            if isinstance(item, EdgeItem):
                item.setFlag(item.GraphicsItemFlag.ItemIsSelectable, editing_enabled)
        if not editing_enabled:
            self.clearSelection()

    def begin_node_placement(self, node_type: str) -> None:
        self.set_editor_tool(EditorTool.PLACE_NODE)
        self._placement_node_type = node_type
        self.placement_message_changed.emit(
            f"Click to place {node_type.replace('_', ' ')} nodes; right-click or Escape cancels."
        )

    def set_grid_snapping(self, enabled: bool, spacing: float | None = None) -> None:
        self._grid_snapping_enabled = enabled
        if spacing is not None:
            self._grid_spacing = min(2.0, max(0.05, spacing))
        self.update()

    @property
    def grid_spacing(self) -> float:
        return self._grid_spacing

    @property
    def grid_snapping_enabled(self) -> bool:
        return self._grid_snapping_enabled

    def cancel_current_operation(self) -> None:
        self._clear_connection_source()
        self._reset_preview_state()
        self._clear_placement_preview()
        self._placement_node_type = None

    def display_level(self, document: LevelDocument) -> None:
        self._reset_preview_state()
        self._clear_placement_preview()
        self.clear()
        self._document = document
        self._node_items_by_id = {}
        self._edges_by_node_id = {}
        self._edge_items_by_id = {}
        self._validation_area_items = []
        self._transition_arc_items = []
        self._playtest_dot_item = None
        self._active_switch_item = None
        self._playtest_status_item = None
        self._clear_connection_source()
        if not document.graph.nodes:
            self._show_placeholder("No nodes in this level")
            return

        edge_by_id = {edge.id: edge for edge in document.graph.edges}
        option_by_edge_id: dict[str, int] = {}
        initial_edge_ids: set[str] = set()
        classifier = SwitchClassificationService()
        for node in document.graph.nodes:
            classification = classifier.classify_node(node, edge_by_id)
            if classification.is_switchable:
                for option, edge_id in enumerate(classification.valid_outgoing_edge_ids, 1):
                    option_by_edge_id[edge_id] = option
                if classification.valid_outgoing_edge_ids:
                    initial_edge_ids.add(classification.valid_outgoing_edge_ids[0])

        for index, node in enumerate(document.graph.nodes):
            node_type = self._resolve_node_type(document, node)
            model_x = float(node.x) if isinstance(node.x, (int, float)) else 0.0
            model_y = float(node.y) if isinstance(node.y, (int, float)) else 0.0
            node_item = NodeItem(node_id=node.id, node_type=node_type, model_x=model_x, model_y=model_y,
                                 has_warning=False)
            node_item.setPos(self._resolve_scene_position(node, index))
            editing_enabled = self._editor_tool is not EditorTool.PLAYTEST
            node_item.setFlag(node_item.GraphicsItemFlag.ItemIsMovable, editing_enabled)
            node_item.setFlag(node_item.GraphicsItemFlag.ItemIsSelectable, editing_enabled)
            node_item.set_connection_handles_enabled(self._editor_tool is EditorTool.CONNECT)
            self.addItem(node_item)
            self._node_items_by_id[node.id] = node_item

        for edge in document.graph.edges:
            from_node = self._node_items_by_id.get(edge.fromNodeID)
            to_node = self._node_items_by_id.get(edge.toNodeID)
            if from_node is None or to_node is None:
                continue
            try:
                edge_item = EdgeItem(
                    edge_id=edge.id,
                    from_node=from_node,
                    to_node=to_node,
                    road_shape=edge.roadShape,
                    option_number=option_by_edge_id.get(edge.id),
                    is_initial=edge.id in initial_edge_ids,
                    has_warning=False,
                )
            except ValueError:
                continue
            self.addItem(edge_item)
            edge_item.setFlag(
                edge_item.GraphicsItemFlag.ItemIsSelectable,
                self._editor_tool is not EditorTool.PLAYTEST,
            )
            self._edges_by_node_id.setdefault(from_node.node_id, []).append(edge_item)
            self._edges_by_node_id.setdefault(to_node.node_id, []).append(edge_item)
            self._edge_items_by_id[edge.id] = edge_item
        self._redraw_transition_arcs()

    def apply_validation_result(self, result: ValidationResult) -> None:
        """Replace all validation styling so resolved issues disappear immediately."""
        node_ids = {message.related_node_id for message in result.messages if message.related_node_id}
        edge_ids = {message.related_edge_id for message in result.messages if message.related_edge_id}
        for node_id, item in self._node_items_by_id.items():
            item.set_validation_issue(node_id in node_ids)
        for edge_id, item in self._edge_items_by_id.items():
            item.set_validation_issue(edge_id in edge_ids)
        for item in self._validation_area_items:
            if isValid(item):
                self.removeItem(item)
        self._validation_area_items = []
        for message in result.messages:
            if message.related_area is None:
                continue
            x, y, width, height = message.related_area
            top_left = self.model_to_scene_coordinates(x, y + height)
            area = QGraphicsRectItem(QRectF(
                top_left.x(), top_left.y(), width * self.COORDINATE_SCALE, height * self.COORDINATE_SCALE
            ))
            area.setPen(QPen(QColor("#dc2626"), 3, Qt.PenStyle.DashLine))
            area.setBrush(QColor(239, 68, 68, 42))
            area.setZValue(20)
            area.setToolTip(message.message)
            self.addItem(area)
            self._validation_area_items.append(area)

    def clear_validation_overlays(self) -> None:
        self.apply_validation_result(ValidationResult())

    def update_playtest_overlay(self, state: PlaytestState) -> None:
        """Render transient runtime state without altering authored graphics."""
        if not state.running or self._document is None:
            self.clear_playtest_overlay()
            return
        self._ensure_playtest_overlay_items()
        position = self._playtest_scene_position(state)
        if self._playtest_dot_item is not None and position is not None:
            self._playtest_dot_item.setPos(position)
            self._playtest_dot_item.setVisible(True)
        elif self._playtest_dot_item is not None:
            self._playtest_dot_item.setVisible(False)

        if self._active_switch_item is not None:
            active = self._node_items_by_id.get(state.eligible_switch_id or "")
            self._active_switch_item.setVisible(active is not None)
            if active is not None:
                self._active_switch_item.setPos(active.pos())

        if self._playtest_status_item is not None:
            if state.outcome == LevelOutcome.COMPLETED:
                status = "✓ Route complete"
            elif state.outcome != LevelOutcome.IN_PROGRESS:
                status = f"✕ {state.outcome.value.replace('_', ' ')}"
            elif state.package_collected:
                status = "▣ Package collected"
            else:
                status = "Find the package"
            self._playtest_status_item.setText(f"{state.elapsed_time:0.2f}s  {status}")

    def clear_playtest_overlay(self) -> None:
        for item in (self._playtest_dot_item, self._active_switch_item, self._playtest_status_item):
            if self._is_live_graphics_item(item):
                self.removeItem(item)
        self._playtest_dot_item = None
        self._active_switch_item = None
        self._playtest_status_item = None

    def _ensure_playtest_overlay_items(self) -> None:
        if not self._is_live_graphics_item(self._playtest_dot_item):
            dot = QGraphicsEllipseItem(QRectF(-10, -10, 20, 20))
            dot.setBrush(QColor("#2563eb"))
            dot.setPen(QPen(QColor("#ffffff"), 3))
            dot.setZValue(1200)
            self.addItem(dot)
            self._playtest_dot_item = dot
        if not self._is_live_graphics_item(self._active_switch_item):
            ring = QGraphicsEllipseItem(QRectF(-42, -42, 84, 84))
            ring.setBrush(Qt.BrushStyle.NoBrush)
            ring.setPen(QPen(QColor("#f59e0b"), 5, Qt.PenStyle.DashLine))
            ring.setZValue(1100)
            self.addItem(ring)
            self._active_switch_item = ring
        if not self._is_live_graphics_item(self._playtest_status_item):
            label = self.addSimpleText("")
            label.setBrush(QColor("#111827"))
            label.setFlag(label.GraphicsItemFlag.ItemIgnoresTransformations, True)
            label.setPos(self.sceneRect().left() + 20, self.sceneRect().top() + 20)
            label.setZValue(1200)
            self._playtest_status_item = label

    def _playtest_scene_position(self, state: PlaytestState) -> QPointF | None:
        if state.current_edge_id is None:
            node = self._node_items_by_id.get(state.current_node_id or "")
            return node.pos() if node is not None else None
        edge = next((item for item in self._document.graph.edges if item.id == state.current_edge_id), None)
        if edge is None:
            return None
        start = self._node_items_by_id.get(edge.fromNodeID)
        end = self._node_items_by_id.get(edge.toNodeID)
        if start is None or end is None:
            return None
        bend = (QPointF(start.pos().x(), end.pos().y()) if edge.roadShape == "verticalFirst"
                else QPointF(end.pos().x(), start.pos().y()))
        points = [start.pos(), bend, end.pos()]
        lengths = [math.hypot(points[i + 1].x() - points[i].x(), points[i + 1].y() - points[i].y()) for i in range(2)]
        target = min(max(state.edge_progress, 0.0), 1.0) * sum(lengths)
        for index, length in enumerate(lengths):
            if target <= length or index == len(lengths) - 1:
                ratio = 0.0 if length == 0 else min(target / length, 1.0)
                return QPointF(
                    points[index].x() + (points[index + 1].x() - points[index].x()) * ratio,
                    points[index].y() + (points[index + 1].y() - points[index].y()) * ratio,
                )
            target -= length
        return end.pos()

    def scene_to_model_coordinates(self, scene_position: QPointF) -> tuple[float, float]:
        return (
            scene_position.x() / self.COORDINATE_SCALE,
            -scene_position.y() / self.COORDINATE_SCALE,
        )

    def model_to_scene_coordinates(self, model_x: float, model_y: float) -> QPointF:
        return QPointF(model_x * self.COORDINATE_SCALE, -model_y * self.COORDINATE_SCALE)

    def level_items_bounding_rect(self) -> QRectF | None:
        level_items = [
            item
            for item in self.items()
            if item.isVisible() and isinstance(item, (NodeItem, EdgeItem, TransitionArcItem))
        ]
        if not level_items:
            return None

        bounding_rect = level_items[0].sceneBoundingRect()
        for item in level_items[1:]:
            bounding_rect = bounding_rect.united(item.sceneBoundingRect())
        return bounding_rect

    def select_node_by_id(self, node_id: str) -> bool:
        node_item = self._node_items_by_id.get(node_id)
        if node_item is None:
            return False
        self.clearSelection()
        node_item.setSelected(True)
        return True

    def select_edge_by_id(self, edge_id: str) -> bool:
        for item in self.items():
            if isinstance(item, EdgeItem) and item.edge_id == edge_id:
                self.clearSelection()
                item.setSelected(True)
                return True
        return False

    def handle_node_item_moved(self, item: NodeItem) -> None:
        model_x, model_y = self.scene_to_model_coordinates(item.pos())
        item.model_x = model_x
        item.model_y = model_y

        for edge_item in self._edges_by_node_id.get(item.node_id, []):
            edge_item.refresh_position(allow_degenerate=True)
        self._redraw_transition_arcs()
        if QApplication.mouseButtons() != Qt.MouseButton.NoButton:
            self._show_alignment_guides(item)

        if item.isSelected():
            self.node_item_selected.emit(item.node_id, item.node_type, item.model_x, item.model_y)
        if QApplication.mouseButtons() == Qt.MouseButton.NoButton and not self._is_finishing_drag:
            self.node_item_moved.emit(item.node_id, item.model_x, item.model_y)

    def set_delete_items_handler(self, handler) -> None:
        self._delete_items_handler = handler

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._editor_tool is EditorTool.PLAYTEST:
            if event.button() == Qt.MouseButton.LeftButton:
                node_item = self._resolve_node_item_at_position(event.scenePos())
                if node_item is not None:
                    self.playtest_tap_requested.emit(node_item.node_id)
            event.accept()
            return
        if self._editor_tool is EditorTool.PLACE_NODE:
            if event.button() == Qt.MouseButton.RightButton:
                self.cancel_current_operation()
                self.placement_message_changed.emit("Node placement canceled.")
                event.accept()
                return
            if event.button() == Qt.MouseButton.LeftButton and self._placement_node_type:
                self.place_node_at(event.scenePos())
                event.accept()
                return
        connection_click = (
            self._editor_tool is EditorTool.CONNECT
            and event.button() == Qt.MouseButton.LeftButton
        ) or event.button() == Qt.MouseButton.RightButton
        if connection_click:
            node_item = self._resolve_node_item_at_position(event.scenePos())
            if node_item is not None:
                self._handle_connection_click(node_item)
                event.accept()
                return
            self._clear_connection_source()
            self.placement_message_changed.emit("Road placement canceled.")
            event.accept()
            return
        node_item = self._resolve_node_item_at_position(event.scenePos())
        if node_item is not None and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_positions[node_item.node_id] = (node_item.model_x, node_item.model_y)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self._is_finishing_drag = True
        super().mouseReleaseEvent(event)
        for node_id, old_position in list(self._drag_start_positions.items()):
            item = self._node_items_by_id.get(node_id)
            if item is not None:
                x, y = self._snap_model_coordinates(item.model_x, item.model_y)
                item.setPos(self.model_to_scene_coordinates(x, y))
            if item is not None and (item.model_x, item.model_y) != old_position:
                self.node_item_moved.emit(node_id, item.model_x, item.model_y)
        self._drag_start_positions.clear()
        self._is_finishing_drag = False
        self._clear_alignment_guides()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._editor_tool is EditorTool.PLACE_NODE and self._placement_node_type:
            self._update_placement_preview(event.scenePos())
        if self._connection_source_node_id is not None:
            self._update_connection_preview(event.scenePos())
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._editor_tool is EditorTool.PLACE_NODE and event.key() == Qt.Key.Key_Escape:
            self.cancel_current_operation()
            self.placement_message_changed.emit("Node placement canceled.")
            event.accept()
            return
        if (
            self._editor_tool is not EditorTool.PLAYTEST
            and event.key() in {Qt.Key.Key_Delete, Qt.Key.Key_Backspace}
            and self._delete_selected_items()
        ):
            event.accept()
            return
        if self._connection_source_node_id is not None and event.key() == Qt.Key.Key_Tab:
            self._toggle_pending_road_shape()
            event.accept()
            return
        if self._connection_source_node_id is not None and event.key() == Qt.Key.Key_Escape:
            self.cancel_current_operation()
            self.placement_message_changed.emit("Road placement canceled.")
            event.accept()
            return
        super().keyPressEvent(event)

    @property
    def pending_road_shape(self) -> str:
        return self._pending_road_shape

    def set_pending_road_shape(self, road_shape: str) -> None:
        if road_shape not in {"horizontalFirst", "verticalFirst"}:
            raise ValueError(f"Unsupported road shape: {road_shape}")
        self._pending_road_shape = road_shape
        self._update_preview_label()
        self.road_shape_changed.emit(road_shape)

    def set_bidirectional_roads_enabled(self, enabled: bool) -> None:
        self._bidirectional_roads_enabled = enabled
        self._update_preview_label()

    def begin_connection_drag(self, node_id: str, scene_position: QPointF) -> None:
        if self._editor_tool is not EditorTool.CONNECT or node_id not in self._node_items_by_id:
            return
        self._set_connection_source(node_id)
        self._connection_drag_active = True
        self._update_connection_preview(scene_position)

    def update_connection_drag(
        self, scene_position: QPointF, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier
    ) -> None:
        self._apply_temporary_shape_modifier(modifiers)
        self._update_connection_preview(scene_position)
        self._highlight_connection_target(scene_position)

    def finish_connection_drag(
        self, scene_position: QPointF, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier
    ) -> None:
        if not self._connection_drag_active:
            return
        self.update_connection_drag(scene_position, modifiers)
        target = self._resolve_node_item_at_position(scene_position)
        source_id = self._connection_source_node_id
        self._connection_drag_active = False
        self._clear_target_highlights()
        self._restore_temporary_shape()
        if target is None:
            self._clear_connection_source()
            self.placement_message_changed.emit("Road placement canceled.")
            return
        if target.node_id == source_id:
            self._clear_connection_source()
            self.placement_message_changed.emit("Road not added. Self-loops are not supported.")
            return
        self._handle_connection_click(target)

    def place_node_at(self, scene_position: QPointF) -> bool:
        """Request an undoable placement at a scene position; placement remains active."""
        if self._editor_tool is not EditorTool.PLACE_NODE or not self._placement_node_type:
            return False
        model_x, model_y = self.scene_to_model_coordinates(scene_position)
        model_x, model_y = self._snap_model_coordinates(model_x, model_y)
        self.node_placement_requested.emit(self._placement_node_type, model_x, model_y)
        return True

    def update_drop_preview(self, node_type: str, scene_position: QPointF) -> None:
        self._placement_node_type = node_type
        self._update_placement_preview(scene_position)

    def clear_drop_preview(self) -> None:
        self._clear_placement_preview()
        if self._editor_tool is not EditorTool.PLACE_NODE:
            self._placement_node_type = None

    def drop_position_is_valid(self, scene_position: QPointF) -> bool:
        if self._document is None or self._editor_tool is EditorTool.PLAYTEST:
            return False
        model_x, model_y = self.scene_to_model_coordinates(scene_position)
        model_x, model_y = self._snap_model_coordinates(model_x, model_y)
        candidate = self.model_to_scene_coordinates(model_x, model_y)
        return all(
            math.hypot(candidate.x() - item.pos().x(), candidate.y() - item.pos().y())
            >= NodeItem.NODE_DIAMETER
            for item in self._node_items_by_id.values()
        )

    def drop_node_at(self, node_type: str, scene_position: QPointF) -> bool:
        valid = self.drop_position_is_valid(scene_position)
        self.clear_drop_preview()
        if not valid:
            self.placement_message_changed.emit("Node cannot be placed on top of another node.")
            return False
        model_x, model_y = self.scene_to_model_coordinates(scene_position)
        model_x, model_y = self._snap_model_coordinates(model_x, model_y)
        self.node_placement_requested.emit(node_type, model_x, model_y)
        return True

    def snap_selected_to_grid(self) -> int:
        moved = 0
        self._is_finishing_drag = True
        try:
            for item in list(self.selectedItems()):
                if not isinstance(item, NodeItem):
                    continue
                spacing = self._grid_spacing
                x = round(item.model_x / spacing) * spacing
                y = round(item.model_y / spacing) * spacing
                if math.isclose(x, item.model_x) and math.isclose(y, item.model_y):
                    continue
                item.setPos(self.model_to_scene_coordinates(x, y))
                self.node_item_moved.emit(item.node_id, x, y)
                moved += 1
        finally:
            self._is_finishing_drag = False
        return moved

    # ------------------------------------------------------------------
    # Selection handling
    # ------------------------------------------------------------------

    def _on_selection_changed(self) -> None:
        items = self.selectedItems()
        if not items:
            self.selection_cleared.emit()
            return
        item = items[0]
        if isinstance(item, NodeItem):
            self.node_item_selected.emit(item.node_id, item.node_type, item.model_x, item.model_y)
        elif isinstance(item, EdgeItem):
            self.edge_item_selected.emit(
                item.edge_id,
                item.from_node_id,
                item.to_node_id,
                item.road_shape,
            )
        else:
            self.selection_cleared.emit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _show_placeholder(self, message: str = "Open a level to begin") -> None:
        placeholder = self.addSimpleText(message)
        placeholder.setBrush(QColor("#666666"))
        placeholder.setPos(-80, -10)

    def _snap_model_coordinates(self, x: float, y: float) -> tuple[float, float]:
        if not self._grid_snapping_enabled:
            return x, y
        spacing = self._grid_spacing
        return round(x / spacing) * spacing, round(y / spacing) * spacing

    def _update_placement_preview(self, scene_position: QPointF) -> None:
        if self._placement_node_type is None:
            return
        model_x, model_y = self.scene_to_model_coordinates(scene_position)
        model_x, model_y = self._snap_model_coordinates(model_x, model_y)
        preview_position = QPointF(model_x * self.COORDINATE_SCALE, -model_y * self.COORDINATE_SCALE)
        if self._placement_preview is None:
            preview = NodeItem("", self._placement_node_type, model_x, model_y)
            preview.setPos(preview_position)
            preview.setOpacity(0.55)
            preview.setEnabled(False)
            preview.setZValue(1000)
            self.addItem(preview)
            self._placement_preview = preview
        else:
            self._placement_preview.model_x = model_x
            self._placement_preview.model_y = model_y
            self._placement_preview.setPos(preview_position)
        self._placement_preview.set_placement_valid(self.drop_position_is_valid(scene_position))

    def _clear_placement_preview(self) -> None:
        if self._is_live_graphics_item(self._placement_preview):
            self.removeItem(self._placement_preview)
        self._placement_preview = None

    def _show_alignment_guides(self, item: NodeItem) -> None:
        self._clear_alignment_guides()
        threshold = 0.08 * self.COORDINATE_SCALE
        pen = QPen(QColor("#00a6a6"), 1, Qt.PenStyle.DashLine)
        for other in self._node_items_by_id.values():
            if other is item:
                continue
            if abs(other.pos().x() - item.pos().x()) <= threshold:
                guide = QGraphicsLineItem(item.pos().x(), -2000, item.pos().x(), 2000)
                guide.setPen(pen)
                guide.setZValue(900)
                self.addItem(guide)
                self._alignment_guides.append(guide)
            if abs(other.pos().y() - item.pos().y()) <= threshold:
                guide = QGraphicsLineItem(-2000, item.pos().y(), 2000, item.pos().y())
                guide.setPen(pen)
                guide.setZValue(900)
                self.addItem(guide)
                self._alignment_guides.append(guide)

    def _clear_alignment_guides(self) -> None:
        for guide in self._alignment_guides:
            if self._is_live_graphics_item(guide):
                self.removeItem(guide)
        self._alignment_guides = []

    def _delete_selected_items(self) -> bool:
        if self._document is None:
            return False

        selected_node_ids = {
            item.node_id for item in self.selectedItems() if isinstance(item, NodeItem)
        }
        selected_edge_ids = {
            item.edge_id for item in self.selectedItems() if isinstance(item, EdgeItem)
        }

        if not selected_node_ids and not selected_edge_ids:
            return False

        edge_ids_to_delete = selected_edge_ids | {
            edge.id
            for edge in self._document.graph.edges
            if edge.fromNodeID in selected_node_ids or edge.toNodeID in selected_node_ids
        }

        if self._connection_source_node_id in selected_node_ids:
            self._connection_source_node_id = None
        if self._delete_items_handler is not None:
            self._delete_items_handler(selected_node_ids, selected_edge_ids)
        else:
            self._document.graph.nodes = [
                node for node in self._document.graph.nodes if node.id not in selected_node_ids
            ]
            self._document.graph.edges = [
                edge for edge in self._document.graph.edges if edge.id not in edge_ids_to_delete
            ]
            for node in self._document.graph.nodes:
                node.outgoingEdgeIDs = [
                    edge_id for edge_id in node.outgoingEdgeIDs if edge_id not in edge_ids_to_delete
                ]
            self.display_level(self._document)
        self.delete_items_requested.emit(selected_node_ids, selected_edge_ids)
        return True

    def _resolve_node_item_at_position(self, scene_position: QPointF) -> NodeItem | None:
        for item in self.items(scene_position):
            current_item = item
            while current_item is not None:
                if isinstance(current_item, NodeItem):
                    return current_item
                current_item = current_item.parentItem()
        return None

    def _handle_connection_click(self, item: NodeItem) -> None:
        if self._document is None:
            return

        if self._connection_source_node_id is None:
            self._set_connection_source(item.node_id)
            item.setSelected(True)
            return

        if self._connection_source_node_id == item.node_id:
            self._clear_connection_source()
            item.setSelected(True)
            self.placement_message_changed.emit("Road placement canceled.")
            return

        from_node_id = self._connection_source_node_id
        to_node_id = item.node_id

        if self._edge_exists(from_node_id, to_node_id):
            item.setSelected(True)
            self.placement_message_changed.emit(
                f"Road not added. {from_node_id} already connects to {to_node_id}."
            )
            return

        if self._bidirectional_roads_enabled and self._edge_exists(to_node_id, from_node_id):
            item.setSelected(True)
            self.placement_message_changed.emit(
                f"Roads not added. {to_node_id} already connects to {from_node_id}."
            )
            return

        self._clear_connection_source()
        item.setSelected(True)
        edge_id = self._generate_unique_edge_id()
        self.edge_creation_requested.emit(
            edge_id,
            from_node_id,
            to_node_id,
            self._pending_road_shape,
            self._bidirectional_roads_enabled,
        )
        self.placement_message_changed.emit(
            ("Two-way roads added with " if self._bidirectional_roads_enabled else "Road added with ")
            + f"{self._describe_road_shape(self._pending_road_shape).lower()}."
        )

    def _set_connection_source(self, node_id: str) -> None:
        if self._connection_source_node_id == node_id:
            return
        self._clear_connection_source()
        source_item = self._node_items_by_id.get(node_id)
        if source_item is None:
            return
        self._connection_source_node_id = node_id
        source_item.set_connection_source(True)
        self._ensure_preview_items()
        self._update_preview_label()
        self.placement_message_changed.emit(
            "Road start selected. Right-click a destination node to place the road. "
            "Press Tab to switch the turn direction."
        )

    def _clear_connection_source(self) -> None:
        source_node_id = self._connection_source_node_id
        if source_node_id is not None:
            source_item = self._node_items_by_id.get(source_node_id)
            if source_item is not None:
                source_item.set_connection_source(False)
        self._connection_source_node_id = None
        self._connection_drag_active = False
        self._clear_target_highlights()
        self._restore_temporary_shape()
        self._remove_preview_items()

    def _edge_exists(self, from_node_id: str, to_node_id: str) -> bool:
        if self._document is None:
            return False
        return any(
            edge.fromNodeID == from_node_id and edge.toNodeID == to_node_id
            for edge in self._document.graph.edges
        )

    def _toggle_pending_road_shape(self) -> None:
        self._pending_road_shape = (
            "verticalFirst" if self._pending_road_shape == "horizontalFirst" else "horizontalFirst"
        )
        self._update_preview_label()
        self.road_shape_changed.emit(self._pending_road_shape)
        self.placement_message_changed.emit(
            f"Road preview set to {self._describe_road_shape(self._pending_road_shape)}."
        )

    def _apply_temporary_shape_modifier(self, modifiers: Qt.KeyboardModifier) -> None:
        should_swap = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        if should_swap == self._temporary_shape_swapped:
            return
        self._toggle_pending_road_shape()
        self._temporary_shape_swapped = should_swap

    def _restore_temporary_shape(self) -> None:
        if self._temporary_shape_swapped:
            self._toggle_pending_road_shape()
            self._temporary_shape_swapped = False

    def _highlight_connection_target(self, scene_position: QPointF) -> None:
        target = self._resolve_node_item_at_position(scene_position)
        source_id = self._connection_source_node_id
        for node_id, item in self._node_items_by_id.items():
            state = None
            if item is target:
                state = node_id != source_id and not self._edge_exists(source_id or "", node_id)
            item.set_connection_target_valid(state)

    def _clear_target_highlights(self) -> None:
        for item in self._node_items_by_id.values():
            item.set_connection_target_valid(None)

    def _ensure_preview_items(self) -> None:
        if not self._is_live_graphics_item(self._preview_path_item):
            self._preview_path_item = None
        if not self._is_live_graphics_item(self._preview_label_item):
            self._preview_label_item = None

        if self._preview_path_item is None:
            self._preview_path_item = QGraphicsPathItem()
            self._preview_path_item.setZValue(-0.5)
            preview_pen = QPen(QColor("#d81b60"), 3)
            preview_pen.setStyle(Qt.PenStyle.DashLine)
            self._preview_path_item.setPen(preview_pen)
            self.addItem(self._preview_path_item)
        if self._preview_arrow_item is None:
            self._preview_arrow_item = QGraphicsPolygonItem()
            self._preview_arrow_item.setBrush(QColor("#d81b60"))
            self._preview_arrow_item.setPen(QPen(QColor("#d81b60"), 1))
            self._preview_arrow_item.setZValue(0)
            self.addItem(self._preview_arrow_item)
        if self._preview_label_item is None:
            self._preview_label_item = self.addSimpleText("")
            self._preview_label_item.setBrush(QColor("#d81b60"))
            self._preview_label_item.setZValue(5)

    def _remove_preview_items(self) -> None:
        if self._is_live_graphics_item(self._preview_path_item):
            self.removeItem(self._preview_path_item)
        self._preview_path_item = None
        if self._is_live_graphics_item(self._preview_arrow_item):
            self.removeItem(self._preview_arrow_item)
        self._preview_arrow_item = None
        if self._is_live_graphics_item(self._preview_label_item):
            self.removeItem(self._preview_label_item)
        self._preview_label_item = None

    def _reset_preview_state(self) -> None:
        self._preview_path_item = None
        self._preview_arrow_item = None
        self._preview_label_item = None

    @staticmethod
    def _is_live_graphics_item(item: object | None) -> bool:
        return item is not None and isValid(item)

    def _update_connection_preview(self, scene_position: QPointF) -> None:
        source_node_id = self._connection_source_node_id
        source_item = self._node_items_by_id.get(source_node_id) if source_node_id is not None else None
        if source_item is None:
            self._remove_preview_items()
            return

        self._ensure_preview_items()

        preview_target = self._resolve_node_item_at_position(scene_position)
        target_position = preview_target.pos() if preview_target is not None else scene_position

        if self._points_are_close(source_item.pos(), target_position):
            if self._preview_path_item is not None:
                self._preview_path_item.setPath(QPainterPath())
                self._preview_path_item.setVisible(False)
            if self._preview_arrow_item is not None:
                self._preview_arrow_item.setVisible(False)
            if self._preview_label_item is not None:
                self._preview_label_item.setPos(source_item.pos().x() + 10, source_item.pos().y() - 28)
            self._update_preview_label()
            return

        preview_edge = EdgeItem(
            edge_id="_preview",
            from_node=source_item,
            to_node=_PreviewNodeItem(target_position),
            road_shape=self._pending_road_shape,
        )
        if self._preview_path_item is not None:
            self._preview_path_item.setPath(preview_edge._path_item.path())
            self._preview_path_item.setVisible(True)
        if self._preview_arrow_item is not None:
            self._preview_arrow_item.setPolygon(QPolygonF(preview_edge._arrow_item.polygon()))
            self._preview_arrow_item.setVisible(True)

        if self._preview_label_item is not None:
            self._preview_label_item.setPos(
                (source_item.pos().x() + target_position.x()) / 2 + 10,
                (source_item.pos().y() + target_position.y()) / 2 - 28,
            )
        self._update_preview_label()

    def _update_preview_label(self) -> None:
        if self._preview_label_item is None:
            return
        self._preview_label_item.setText(
            f"Road Preview: {self._describe_road_shape(self._pending_road_shape)}"
            + (" (Two-Way)" if self._bidirectional_roads_enabled else "")
        )

    @staticmethod
    def _describe_road_shape(road_shape: str) -> str:
        if road_shape == "verticalFirst":
            return "Vertical First"
        return "Horizontal First"

    def _generate_unique_edge_id(self, reserved_ids: set[str] | None = None) -> str:
        existing_edge_ids = set()
        if self._document is not None:
            existing_edge_ids = {edge.id for edge in self._document.graph.edges}
        existing_edge_ids.update(reserved_ids or set())

        base_id = "edge"
        if base_id not in existing_edge_ids:
            return base_id

        suffix = 1
        while f"{base_id}_{suffix}" in existing_edge_ids:
            suffix += 1
        return f"{base_id}_{suffix}"

    def _resolve_node_type(self, document: LevelDocument, node: RouteNodeModel) -> str:
        if node.id == document.startNodeID:
            return "start"
        if node.id == document.packageNodeID:
            return "package"
        if node.id == document.destinationNodeID:
            return "destination"
        if node.id.lower() == "finish":
            return "finish"
        edge_by_id = {edge.id: edge for edge in document.graph.edges}
        classification = SwitchClassificationService().classify_node(node, edge_by_id)
        if classification.kind is SwitchNodeKind.FOUR_WAY_INTERSECTION_SWITCH:
            return "four_way_switch"
        if classification.is_switchable:
            return "switch"
        if node.id.lower().startswith("switch"):
            return "switch"
        return "route"

    def _resolve_scene_position(self, node: RouteNodeModel, index: int) -> QPointF:
        x = node.x
        y = node.y

        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            if math.isfinite(x) and math.isfinite(y):
                return QPointF(x * self.COORDINATE_SCALE, -y * self.COORDINATE_SCALE)

        row = index // 5
        column = index % 5
        return QPointF(column * self.FALLBACK_SPACING, row * self.FALLBACK_SPACING)

    def _redraw_transition_arcs(self) -> None:
        for arc_item in self._transition_arc_items:
            self.removeItem(arc_item)
        self._transition_arc_items = []

        if self._document is None:
            return

        edges_by_id = {edge.id: edge for edge in self._document.graph.edges}
        for node in self._document.graph.nodes:
            node_item = self._node_items_by_id.get(node.id)
            if node_item is None:
                continue

            active_outgoing_edge = self._default_active_outgoing_edge(node, edges_by_id)
            if active_outgoing_edge is None:
                continue

            for incoming_edge in self._document.graph.edges:
                if incoming_edge.toNodeID != node.id:
                    continue

                arc_item = self._make_transition_arc_item(
                    node_id=node.id,
                    incoming_edge=incoming_edge,
                    outgoing_edge=active_outgoing_edge,
                    node_position=node_item.pos(),
                )
                if arc_item is None:
                    continue
                self._transition_arc_items.append(arc_item)
                self.addItem(arc_item)

    def _default_active_outgoing_edge(self, node: RouteNodeModel, edges_by_id: dict):
        for edge_id in node.outgoingEdgeIDs:
            edge = edges_by_id.get(edge_id)
            if edge is not None and edge.fromNodeID == node.id:
                return edge
        return None

    def _make_transition_arc_item(
        self,
        node_id: str,
        incoming_edge,
        outgoing_edge,
        node_position: QPointF,
    ) -> TransitionArcItem | None:
        incoming_tangent = self._edge_end_tangent(incoming_edge)
        outgoing_tangent = self._edge_start_tangent(outgoing_edge)
        if incoming_tangent is None or outgoing_tangent is None:
            return None

        dot_product = (incoming_tangent[0] * outgoing_tangent[0]) + (
            incoming_tangent[1] * outgoing_tangent[1]
        )
        cross_product = (incoming_tangent[0] * outgoing_tangent[1]) - (
            incoming_tangent[1] * outgoing_tangent[0]
        )
        if not (abs(dot_product) < 0.0001 and abs(cross_product) > 0.9999):
            return None

        incoming_length = self._edge_road_length(incoming_edge)
        outgoing_length = self._edge_road_length(outgoing_edge)
        if incoming_length <= 0 or outgoing_length <= 0:
            return None

        radius = min(
            self.STANDARD_TURN_RADIUS * self.COORDINATE_SCALE,
            incoming_length / 2,
            outgoing_length / 2,
        )
        if radius <= 0:
            return None

        start = QPointF(
            node_position.x() - (incoming_tangent[0] * radius),
            node_position.y() - (incoming_tangent[1] * radius),
        )
        end = QPointF(
            node_position.x() + (outgoing_tangent[0] * radius),
            node_position.y() + (outgoing_tangent[1] * radius),
        )
        center = QPointF(
            start.x() + (outgoing_tangent[0] * radius),
            start.y() + (outgoing_tangent[1] * radius),
        )
        start_angle = math.atan2(start.y() - center.y(), start.x() - center.x())
        signed_angle_delta = math.pi / 2 if cross_product > 0 else -math.pi / 2

        return TransitionArcItem(
            node_id=node_id,
            incoming_edge_id=incoming_edge.id,
            outgoing_edge_id=outgoing_edge.id,
            start=start,
            end=end,
            center=center,
            start_angle=start_angle,
            signed_angle_delta=signed_angle_delta,
        )

    def _edge_start_tangent(self, edge) -> tuple[float, float] | None:
        return self._edge_endpoint_tangent(edge, at_start=True)

    def _edge_end_tangent(self, edge) -> tuple[float, float] | None:
        return self._edge_endpoint_tangent(edge, at_start=False)

    def _edge_endpoint_tangent(self, edge, at_start: bool) -> tuple[float, float] | None:
        from_node = self._node_items_by_id.get(edge.fromNodeID)
        to_node = self._node_items_by_id.get(edge.toNodeID)
        if from_node is None or to_node is None:
            return None

        dx = to_node.pos().x() - from_node.pos().x()
        dy = to_node.pos().y() - from_node.pos().y()
        if math.isclose(dx, 0, abs_tol=1e-6) and math.isclose(dy, 0, abs_tol=1e-6):
            return None

        if math.isclose(dx, 0, abs_tol=1e-6):
            return (0, 1 if dy > 0 else -1)
        if math.isclose(dy, 0, abs_tol=1e-6):
            return (1 if dx > 0 else -1, 0)

        x_direction = 1 if dx > 0 else -1
        y_direction = 1 if dy > 0 else -1
        if edge.roadShape == "verticalFirst":
            return (0, y_direction) if at_start else (x_direction, 0)
        return (x_direction, 0) if at_start else (0, y_direction)

    def _edge_road_length(self, edge) -> float:
        from_node = self._node_items_by_id.get(edge.fromNodeID)
        to_node = self._node_items_by_id.get(edge.toNodeID)
        if from_node is None or to_node is None:
            return 0

        dx = abs(to_node.pos().x() - from_node.pos().x())
        dy = abs(to_node.pos().y() - from_node.pos().y())
        if math.isclose(dx, 0, abs_tol=1e-6) or math.isclose(dy, 0, abs_tol=1e-6):
            return math.hypot(dx, dy)

        turn_radius = min(self.STANDARD_TURN_RADIUS * self.COORDINATE_SCALE, dx / 2, dy / 2)
        return (dx - turn_radius) + ((math.pi / 2) * turn_radius) + (dy - turn_radius)

    @staticmethod
    def _points_are_close(first: QPointF, second: QPointF) -> bool:
        return math.isclose(first.x(), second.x(), abs_tol=1e-6) and math.isclose(
            first.y(), second.y(), abs_tol=1e-6
        )

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawBackground(painter, rect)

        grid_size = self._grid_spacing * self.COORDINATE_SCALE
        painter.setPen(QPen(canvas_grid_color()))

        left = math.floor(rect.left() / grid_size) * grid_size
        top = math.floor(rect.top() / grid_size) * grid_size

        x = left
        while x < rect.right():
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += grid_size

        y = top
        while y < rect.bottom():
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += grid_size


class _PreviewNodeItem:
    def __init__(self, position: QPointF) -> None:
        self.node_id = "_preview_target"
        self._position = position

    def pos(self) -> QPointF:
        return self._position
