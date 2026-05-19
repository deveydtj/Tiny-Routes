import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsItemGroup, QGraphicsLineItem, QGraphicsPolygonItem

from app.ui.node_item import NodeItem


class EdgeItem(QGraphicsItemGroup):
    """Graphics item representing a directed edge between two nodes."""

    ARROW_SIZE = 10.0
    LINE_COLOR = "#546e7a"
    ARROW_COLOR = "#546e7a"

    def __init__(self, edge_id: str, from_node: NodeItem, to_node: NodeItem) -> None:
        super().__init__()
        self.edge_id = edge_id
        self.setZValue(-1)

        from_pos = from_node.pos()
        to_pos = to_node.pos()

        radius = NodeItem.NODE_DIAMETER / 2

        # Direction vector from source to target
        dx = to_pos.x() - from_pos.x()
        dy = to_pos.y() - from_pos.y()
        length = math.hypot(dx, dy)

        if length < 1e-6:
            # Nodes are co-located; nothing useful to draw
            return

        ux = dx / length
        uy = dy / length

        # Adjust endpoints so the line starts/ends at the node circle boundary
        start = QPointF(from_pos.x() + ux * radius, from_pos.y() + uy * radius)
        end = QPointF(to_pos.x() - ux * radius, to_pos.y() - uy * radius)

        line = QGraphicsLineItem(start.x(), start.y(), end.x(), end.y())
        line.setPen(QPen(QColor(self.LINE_COLOR), 2))
        self.addToGroup(line)

        # Arrowhead at the target end
        arrow_tip = end
        arrow_left = QPointF(
            arrow_tip.x() - self.ARROW_SIZE * (ux - uy * 0.5),
            arrow_tip.y() - self.ARROW_SIZE * (uy + ux * 0.5),
        )
        arrow_right = QPointF(
            arrow_tip.x() - self.ARROW_SIZE * (ux + uy * 0.5),
            arrow_tip.y() - self.ARROW_SIZE * (uy - ux * 0.5),
        )

        arrow = QGraphicsPolygonItem(QPolygonF([arrow_tip, arrow_left, arrow_right]))
        arrow.setBrush(QColor(self.ARROW_COLOR))
        arrow.setPen(QPen(QColor(self.ARROW_COLOR), 1))
        self.addToGroup(arrow)
