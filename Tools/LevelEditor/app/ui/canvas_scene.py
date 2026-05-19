import math

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsScene

from app.models import LevelDocument, RouteNodeModel

from .node_item import NodeItem


class LevelCanvasScene(QGraphicsScene):
    COORDINATE_SCALE = 180.0
    FALLBACK_SPACING = 140.0

    def __init__(self) -> None:
        super().__init__()
        self.setSceneRect(QRectF(-2000, -2000, 4000, 4000))
        self._show_placeholder()

    def display_level(self, document: LevelDocument) -> None:
        self.clear()

        for index, node in enumerate(document.graph.nodes):
            node_type = self._resolve_node_type(document, node)
            node_item = NodeItem(node_id=node.id, node_type=node_type)
            node_item.setPos(self._resolve_scene_position(node, index))
            self.addItem(node_item)

    def _show_placeholder(self) -> None:
        placeholder = self.addSimpleText("Open a level to begin")
        placeholder.setBrush(QColor("#666666"))
        placeholder.setPos(-70, -10)

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
