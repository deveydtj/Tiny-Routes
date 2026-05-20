from dataclasses import dataclass

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsItemGroup, QGraphicsSimpleTextItem


@dataclass(frozen=True)
class NodeVisualStyle:
    fill_color: str
    border_color: str


NODE_TYPE_STYLES: dict[str, NodeVisualStyle] = {
    "start": NodeVisualStyle(fill_color="#2e7d32", border_color="#1b5e20"),
    "route": NodeVisualStyle(fill_color="#fafafa", border_color="#424242"),
    "switch": NodeVisualStyle(fill_color="#fff3e0", border_color="#ef6c00"),
    "package": NodeVisualStyle(fill_color="#e8f5e9", border_color="#2e7d32"),
    "destination": NodeVisualStyle(fill_color="#e3f2fd", border_color="#1565c0"),
    "finish": NodeVisualStyle(fill_color="#f3e5f5", border_color="#6a1b9a"),
}


class NodeItem(QGraphicsItemGroup):
    NODE_DIAMETER = 64.0
    PENDING_BORDER_COLOR = "#d81b60"
    PENDING_BORDER_WIDTH = 4

    def __init__(self, node_id: str, node_type: str, model_x: float = 0.0, model_y: float = 0.0) -> None:
        super().__init__()
        self.node_id = node_id
        self.node_type = node_type if node_type in NODE_TYPE_STYLES else "route"
        self.model_x = model_x
        self.model_y = model_y
        self._style = NODE_TYPE_STYLES[self.node_type]
        self._is_connection_source = False
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        radius = self.NODE_DIAMETER / 2

        circle = QGraphicsEllipseItem(QRectF(-radius, -radius, self.NODE_DIAMETER, self.NODE_DIAMETER))
        circle.setBrush(QColor(self._style.fill_color))
        self._circle = circle
        self._update_border()
        self.addToGroup(circle)

        label = QGraphicsSimpleTextItem(self.node_id)
        label_rect = label.boundingRect()
        label.setPos(-label_rect.width() / 2, -label_rect.height() / 2)
        self.addToGroup(label)

    def set_connection_source(self, is_source: bool) -> None:
        self._is_connection_source = is_source
        self._update_border()

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: object) -> object:
        result = super().itemChange(change, value)
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            scene = self.scene()
            if scene is not None and hasattr(scene, "handle_node_item_moved"):
                scene.handle_node_item_moved(self)
        return result

    def _update_border(self) -> None:
        border_color = self.PENDING_BORDER_COLOR if self._is_connection_source else self._style.border_color
        border_width = self.PENDING_BORDER_WIDTH if self._is_connection_source else 2
        self._circle.setPen(QPen(QColor(border_color), border_width))
