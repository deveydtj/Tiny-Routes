import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import QGraphicsScene, QGraphicsSceneMouseEvent

from app.models import LevelDocument, RouteNodeModel

from .edge_item import EdgeItem
from .node_item import NodeItem


class LevelCanvasScene(QGraphicsScene):
    COORDINATE_SCALE = 180.0
    FALLBACK_SPACING = 140.0

    # Emitted when a NodeItem is selected.  Args: node_id, node_type, model_x, model_y
    node_item_selected = Signal(str, str, float, float)
    # Emitted when an EdgeItem is selected.  Args: edge_id, from_node_id, to_node_id
    edge_item_selected = Signal(str, str, str)
    # Emitted when the selection is cleared or an unrecognised item is selected
    selection_cleared = Signal()
    # Emitted when a node is repositioned. Args: node_id, model_x, model_y
    node_item_moved = Signal(str, float, float)
    # Emitted when the user creates a new edge. Args: edge_id, from_node_id, to_node_id
    edge_creation_requested = Signal(str, str, str)
    # Emitted after selected nodes and/or edges are deleted from the document.
    level_items_deleted = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setSceneRect(QRectF(-2000, -2000, 4000, 4000))
        self._document: LevelDocument | None = None
        self._node_items_by_id: dict[str, NodeItem] = {}
        self._edges_by_node_id: dict[str, list[EdgeItem]] = {}
        self._connection_source_node_id: str | None = None
        self._show_placeholder()
        self.selectionChanged.connect(self._on_selection_changed)

    def display_level(self, document: LevelDocument) -> None:
        self.clear()
        self._document = document
        self._node_items_by_id = {}
        self._edges_by_node_id = {}
        self._clear_connection_source()
        if not document.graph.nodes:
            self._show_placeholder("No nodes in this level")
            return

        for index, node in enumerate(document.graph.nodes):
            node_type = self._resolve_node_type(document, node)
            model_x = float(node.x) if isinstance(node.x, (int, float)) else 0.0
            model_y = float(node.y) if isinstance(node.y, (int, float)) else 0.0
            node_item = NodeItem(node_id=node.id, node_type=node_type, model_x=model_x, model_y=model_y)
            node_item.setPos(self._resolve_scene_position(node, index))
            self.addItem(node_item)
            self._node_items_by_id[node.id] = node_item

        for edge in document.graph.edges:
            from_node = self._node_items_by_id.get(edge.fromNodeID)
            to_node = self._node_items_by_id.get(edge.toNodeID)
            if from_node is None or to_node is None:
                continue
            try:
                edge_item = EdgeItem(edge_id=edge.id, from_node=from_node, to_node=to_node)
            except ValueError:
                continue
            self.addItem(edge_item)
            self._edges_by_node_id.setdefault(from_node.node_id, []).append(edge_item)
            self._edges_by_node_id.setdefault(to_node.node_id, []).append(edge_item)

    def scene_to_model_coordinates(self, scene_position: QPointF) -> tuple[float, float]:
        return (
            scene_position.x() / self.COORDINATE_SCALE,
            scene_position.y() / self.COORDINATE_SCALE,
        )

    def handle_node_item_moved(self, item: NodeItem) -> None:
        model_x, model_y = self.scene_to_model_coordinates(item.pos())
        item.model_x = model_x
        item.model_y = model_y

        for edge_item in self._edges_by_node_id.get(item.node_id, []):
            edge_item.refresh_position(allow_degenerate=True)

        if item.isSelected():
            self.node_item_selected.emit(item.node_id, item.node_type, item.model_x, item.model_y)
        self.node_item_moved.emit(item.node_id, item.model_x, item.model_y)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            node_item = self._resolve_node_item_at_position(event.scenePos())
            if node_item is not None:
                self._handle_connection_click(node_item)
                event.accept()
                return
            self._clear_connection_source()
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in {Qt.Key.Key_Delete, Qt.Key.Key_Backspace} and self._delete_selected_items():
            event.accept()
            return
        super().keyPressEvent(event)

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
            self.edge_item_selected.emit(item.edge_id, item.from_node_id, item.to_node_id)
        else:
            self.selection_cleared.emit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _show_placeholder(self, message: str = "Open a level to begin") -> None:
        placeholder = self.addSimpleText(message)
        placeholder.setBrush(QColor("#666666"))
        placeholder.setPos(-80, -10)

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

        if self._connection_source_node_id in selected_node_ids:
            self._connection_source_node_id = None

        self.display_level(self._document)
        self.level_items_deleted.emit()
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
            return

        from_node_id = self._connection_source_node_id
        to_node_id = item.node_id
        self._clear_connection_source()
        item.setSelected(True)

        if self._edge_exists(from_node_id, to_node_id):
            return

        edge_id = self._generate_unique_edge_id()
        self.edge_creation_requested.emit(edge_id, from_node_id, to_node_id)

    def _set_connection_source(self, node_id: str) -> None:
        if self._connection_source_node_id == node_id:
            return
        self._clear_connection_source()
        source_item = self._node_items_by_id.get(node_id)
        if source_item is None:
            return
        self._connection_source_node_id = node_id
        source_item.set_connection_source(True)

    def _clear_connection_source(self) -> None:
        if self._connection_source_node_id is None:
            return
        source_item = self._node_items_by_id.get(self._connection_source_node_id)
        if source_item is not None:
            source_item.set_connection_source(False)
        self._connection_source_node_id = None

    def _edge_exists(self, from_node_id: str, to_node_id: str) -> bool:
        if self._document is None:
            return False
        return any(
            edge.fromNodeID == from_node_id and edge.toNodeID == to_node_id
            for edge in self._document.graph.edges
        )

    def _generate_unique_edge_id(self) -> str:
        existing_edge_ids = set()
        if self._document is not None:
            existing_edge_ids = {edge.id for edge in self._document.graph.edges}

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
        if len(node.outgoingEdgeIDs) >= 2:
            return "switch"
        return "route"

    def _resolve_scene_position(self, node: RouteNodeModel, index: int) -> QPointF:
        x = node.x
        y = node.y

        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            if math.isfinite(x) and math.isfinite(y):
                return QPointF(x * self.COORDINATE_SCALE, y * self.COORDINATE_SCALE)

        row = index // 5
        column = index % 5
        return QPointF(column * self.FALLBACK_SPACING, row * self.FALLBACK_SPACING)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawBackground(painter, rect)

        grid_size = 50
        grid_color = QColor("#e8e8e8")
        painter.setPen(QPen(grid_color))

        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        x = left
        while x < int(rect.right()):
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
            x += grid_size

        y = top
        while y < int(rect.bottom()):
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)
            y += grid_size
