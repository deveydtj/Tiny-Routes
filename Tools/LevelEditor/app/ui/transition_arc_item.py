import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem

from .canvas_colors import road_color


class TransitionArcItem(QGraphicsPathItem):
    """Editor-only preview of RouteEngine's runtime node transition arc."""

    def __init__(
        self,
        node_id: str,
        incoming_edge_id: str,
        outgoing_edge_id: str,
        start: QPointF,
        end: QPointF,
        center: QPointF,
        start_angle: float,
        signed_angle_delta: float,
    ) -> None:
        super().__init__()
        self.node_id = node_id
        self.incoming_edge_id = incoming_edge_id
        self.outgoing_edge_id = outgoing_edge_id
        self.setZValue(1)
        self.setPen(QPen(road_color(), 2))

        path = QPainterPath(start)
        sample_count = 12
        radius = math.hypot(start.x() - center.x(), start.y() - center.y())
        for index in range(1, sample_count + 1):
            progress = index / sample_count
            angle = start_angle + (signed_angle_delta * progress)
            path.lineTo(
                QPointF(
                    center.x() + (math.cos(angle) * radius),
                    center.y() + (math.sin(angle) * radius),
                )
            )
        path.lineTo(end)
        self.setPath(path)
