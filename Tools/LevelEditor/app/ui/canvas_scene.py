import math

from PySide6.QtCore import QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsScene

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

    def __init__(self) -> None:
        super().__init__()
        self.setSceneRect(QRectF(-2000, -2000, 4000, 4000))
        self._show_placeholder()
        self.selectionChanged.connect(self._on_selection_changed)

    def display_level(self, document: LevelDocument) -> None:
        self.clear()
        if not document.graph.nodes:
            self._show_placeholder("No nodes in this level")
            return

        node_items: dict[str, NodeItem] = {}
        for index, node in enumerate(document.graph.nodes):
            node_type = self._resolve_node_type(document, node)
            model_x = float(node.x) if isinstance(node.x, (int, float)) else 0.0
            model_y = float(node.y) if isinstance(node.y, (int, float)) else 0.0
            node_item = NodeItem(node_id=node.id, node_type=node_type, model_x=model_x, model_y=model_y)
            node_item.setPos(self._resolve_scene_position(node, index))
            self.addItem(node_item)
            node_items[node.id] = node_item

        for edge in document.graph.edges:
            from_node = node_items.get(edge.fromNodeID)
            to_node = node_items.get(edge.toNodeID)
            if from_node is None or to_node is None:
                continue
            try:
                edge_item = EdgeItem(edge_id=edge.id, from_node=from_node, to_node=to_node)
            except ValueError:
                continue
            self.addItem(edge_item)

    def scene_to_model_coordinates(self, scene_position: QPointF) -> tuple[float, float]:
        return (
            scene_position.x() / self.COORDINATE_SCALE,
            scene_position.y() / self.COORDINATE_SCALE,
        )

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
