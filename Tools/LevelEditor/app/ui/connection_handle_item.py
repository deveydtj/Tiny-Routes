from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsSceneMouseEvent


class ConnectionHandleItem(QGraphicsEllipseItem):
    """Visible drag target used to start a directed road from a node."""

    DIAMETER = 14.0

    def __init__(self, node_id: str, parent: QGraphicsItem) -> None:
        radius = self.DIAMETER / 2
        super().__init__(QRectF(-radius, -radius, self.DIAMETER, self.DIAMETER), parent)
        self.node_id = node_id
        self.setBrush(QColor("#ffffff"))
        self.setPen(QPen(QColor("#d81b60"), 2))
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setToolTip(f"Drag from {node_id} to create a directed road")
        self.setZValue(20)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        scene = self.scene()
        if scene is not None and hasattr(scene, "begin_connection_drag"):
            scene.begin_connection_drag(self.node_id, event.scenePos())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        scene = self.scene()
        if scene is not None and hasattr(scene, "update_connection_drag"):
            scene.update_connection_drag(event.scenePos(), event.modifiers())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        scene = self.scene()
        if scene is not None and hasattr(scene, "finish_connection_drag"):
            scene.finish_connection_drag(event.scenePos(), event.modifiers())
            event.accept()
            return
        super().mouseReleaseEvent(event)
