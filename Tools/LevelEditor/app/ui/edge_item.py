import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsItemGroup, QGraphicsPathItem, QGraphicsPolygonItem

from .node_item import NodeItem


class EdgeItem(QGraphicsItemGroup):
    """Graphics item representing a directed edge between two nodes."""

    ARROW_SIZE = 10.0
    LINE_COLOR = "#546e7a"
    ARROW_COLOR = "#546e7a"

    def __init__(
        self,
        edge_id: str,
        from_node: NodeItem,
        to_node: NodeItem,
        road_shape: str | None = None,
    ) -> None:
        super().__init__()
        self.edge_id = edge_id
        self._from_node = from_node
        self._to_node = to_node
        self.from_node_id = from_node.node_id
        self.to_node_id = to_node.node_id
        self.road_shape = road_shape or "horizontalFirst"
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._path_item = QGraphicsPathItem()
        self._path_item.setPen(QPen(QColor(self.LINE_COLOR), 2))
        self.addToGroup(self._path_item)
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

        points = self._build_path_points(from_pos, to_pos, radius)
        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)
        self._path_item.setPath(path)

        arrow_base = points[-2]
        arrow_tip = points[-1]
        arrow_dx = arrow_tip.x() - arrow_base.x()
        arrow_dy = arrow_tip.y() - arrow_base.y()
        arrow_length = math.hypot(arrow_dx, arrow_dy)
        if arrow_length < 1e-6:
            raise ValueError(f"Cannot draw arrow for degenerate edge segment (edge_id={self.edge_id!r})")
        ux = arrow_dx / arrow_length
        uy = arrow_dy / arrow_length
        arrow_left = QPointF(
            arrow_tip.x() - self.ARROW_SIZE * (ux - uy * 0.5),
            arrow_tip.y() - self.ARROW_SIZE * (uy + ux * 0.5),
        )
        arrow_right = QPointF(
            arrow_tip.x() - self.ARROW_SIZE * (ux + uy * 0.5),
            arrow_tip.y() - self.ARROW_SIZE * (uy - ux * 0.5),
        )
        self._arrow_item.setPolygon(QPolygonF([arrow_tip, arrow_left, arrow_right]))

    def _build_path_points(
        self,
        from_pos: QPointF,
        to_pos: QPointF,
        radius: float,
    ) -> list[QPointF]:
        dx = to_pos.x() - from_pos.x()
        dy = to_pos.y() - from_pos.y()
        length = math.hypot(dx, dy)
        ux = dx / length
        uy = dy / length

        start = QPointF(from_pos.x() + ux * radius, from_pos.y() + uy * radius)
        end = QPointF(to_pos.x() - ux * radius, to_pos.y() - uy * radius)

        if self.road_shape == "verticalFirst":
            bend = QPointF(start.x(), end.y())
        else:
            bend = QPointF(end.x(), start.y())

        if self._points_are_close(start, bend) or self._points_are_close(bend, end):
            return [start, end]
        return [start, bend, end]

    @staticmethod
    def _points_are_close(first: QPointF, second: QPointF) -> bool:
        return math.isclose(first.x(), second.x(), abs_tol=1e-6) and math.isclose(
            first.y(), second.y(), abs_tol=1e-6
        )
