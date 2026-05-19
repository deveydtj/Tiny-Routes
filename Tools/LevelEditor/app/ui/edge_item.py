import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsItemGroup, QGraphicsLineItem, QGraphicsPolygonItem

from .node_item import NodeItem


class EdgeItem(QGraphicsItemGroup):
    """Graphics item representing a directed edge between two nodes."""

    ARROW_SIZE = 10.0
    LINE_COLOR = "#546e7a"
    ARROW_COLOR = "#546e7a"

    def __init__(self, edge_id: str, from_node: NodeItem, to_node: NodeItem) -> None:
        super().__init__()
        self.edge_id = edge_id
        self._from_node = from_node
        self._to_node = to_node
        self.from_node_id = from_node.node_id
        self.to_node_id = to_node.node_id
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._line_item = QGraphicsLineItem()
        self._line_item.setPen(QPen(QColor(self.LINE_COLOR), 2))
        self.addToGroup(self._line_item)
        self._arrow_item = QGraphicsPolygonItem()
        self._arrow_item.setBrush(QColor(self.ARROW_COLOR))
        self._arrow_item.setPen(QPen(QColor(self.ARROW_COLOR), 1))
        self.addToGroup(self._arrow_item)
        self.refresh_position()

    def refresh_position(self, allow_degenerate: bool = False) -> None:
        from_pos = self._from_node.pos()
        to_pos = self._to_node.pos()

        radius = NodeItem.NODE_DIAMETER / 2

        dx = to_pos.x() - from_pos.x()
        dy = to_pos.y() - from_pos.y()
        length = math.hypot(dx, dy)

        if length < 1e-6:
            if allow_degenerate:
                self.setVisible(False)
                return
            raise ValueError(f"Cannot draw edge for co-located nodes (edge_id={self.edge_id!r})")

        self.setVisible(True)

        ux = dx / length
        uy = dy / length

        start = QPointF(from_pos.x() + ux * radius, from_pos.y() + uy * radius)
        end = QPointF(to_pos.x() - ux * radius, to_pos.y() - uy * radius)
        self._line_item.setLine(start.x(), start.y(), end.x(), end.y())
        arrow_tip = end
        arrow_left = QPointF(
            arrow_tip.x() - self.ARROW_SIZE * (ux - uy * 0.5),
            arrow_tip.y() - self.ARROW_SIZE * (uy + ux * 0.5),
        )
        arrow_right = QPointF(
            arrow_tip.x() - self.ARROW_SIZE * (ux + uy * 0.5),
            arrow_tip.y() - self.ARROW_SIZE * (uy - ux * 0.5),
        )
        self._arrow_item.setPolygon(QPolygonF([arrow_tip, arrow_left, arrow_right]))
