import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsItem, QGraphicsItemGroup, QGraphicsPathItem, QGraphicsPolygonItem, QGraphicsSimpleTextItem

from .canvas_colors import road_color
from .node_item import NodeItem


class EdgeItem(QGraphicsItemGroup):
    """Graphics item representing a directed edge between two nodes."""

    ARROW_SIZE = 10.0

    def __init__(
        self,
        edge_id: str,
        from_node: NodeItem,
        to_node: NodeItem,
        road_shape: str | None = None,
        option_number: int | None = None,
        is_initial: bool = False,
        has_warning: bool = False,
    ) -> None:
        super().__init__()
        self.edge_id = edge_id
        self._from_node = from_node
        self._to_node = to_node
        self.from_node_id = from_node.node_id
        self.to_node_id = to_node.node_id
        self.road_shape = road_shape or "horizontalFirst"
        self._is_initial = is_initial
        self._has_validation_issue = has_warning
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._path_item = QGraphicsPathItem()
        self._path_item.setPen(QPen(QColor("#16a34a") if is_initial else road_color(), 5 if is_initial else 2))
        self.addToGroup(self._path_item)
        self._arrow_item = QGraphicsPolygonItem()
        road = road_color()
        self._arrow_item.setBrush(road)
        self._arrow_item.setPen(QPen(road, 1))
        self.addToGroup(self._arrow_item)
        annotation = f"{option_number}" if option_number is not None else ""
        if has_warning:
            annotation = f"{annotation} ⚠".strip()
        self._annotation_item = QGraphicsSimpleTextItem(annotation)
        self._annotation_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self._annotation_item.setBrush(QColor("#c62828") if has_warning else QColor("#374151"))
        self._annotation_item.setToolTip("Initial active road" if is_initial else "Switch option")
        self.addToGroup(self._annotation_item)
        self.refresh_position()

    def set_validation_issue(self, has_issue: bool) -> None:
        self._has_validation_issue = has_issue
        self._path_item.setPen(QPen(
            QColor("#c62828") if has_issue else (QColor("#16a34a") if self._is_initial else road_color()),
            5 if self._is_initial else (4 if has_issue else 2),
        ))
        annotation = self._annotation_item.text().replace(" ⚠", "").replace("⚠", "").strip()
        self._annotation_item.setText(f"{annotation} ⚠".strip() if has_issue else annotation)
        self._annotation_item.setBrush(QColor("#c62828") if has_issue else QColor("#374151"))

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
        midpoint = path.pointAtPercent(0.48)
        self._annotation_item.setPos(midpoint.x() + 5, midpoint.y() - 18)

        arrow_segment = self._resolve_arrow_segment(points)
        if arrow_segment is None:
            if allow_degenerate:
                self._arrow_item.setVisible(False)
                return
            raise ValueError(f"Cannot draw arrow for degenerate edge segment (edge_id={self.edge_id!r})")

        arrow_base, arrow_tip = arrow_segment
        arrow_dx = arrow_tip.x() - arrow_base.x()
        arrow_dy = arrow_tip.y() - arrow_base.y()
        arrow_length = math.hypot(arrow_dx, arrow_dy)
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
        self._arrow_item.setVisible(True)
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

    def _resolve_arrow_segment(self, points: list[QPointF]) -> tuple[QPointF, QPointF] | None:
        for index in range(len(points) - 1, 0, -1):
            arrow_base = points[index - 1]
            arrow_tip = points[index]
            if not self._points_are_close(arrow_base, arrow_tip):
                return arrow_base, arrow_tip
        return None
