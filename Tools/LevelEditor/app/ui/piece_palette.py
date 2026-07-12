from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

NODE_ROLE_MIME_TYPE = "application/x-tiny-routes-node-role"


class PaletteListWidget(QListWidget):
    def startDrag(self, supported_actions: Qt.DropAction) -> None:
        item = self.currentItem()
        node_type = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if not isinstance(node_type, str) or not node_type:
            return
        mime_data = QMimeData()
        mime_data.setData(NODE_ROLE_MIME_TYPE, node_type.encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)


class PiecePalette(QWidget):
    node_type_activated = Signal(str)

    _PALETTE_ITEMS: list[tuple[str, str]] = [
        ("Start", "start"),
        ("Route Node", "route"),
        ("Switch", "switch"),
        ("Package", "package"),
        ("Destination", "destination"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._list_widget = PaletteListWidget()
        self._list_widget.setDragEnabled(True)
        for label, node_type in self._PALETTE_ITEMS:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, node_type)
            self._list_widget.addItem(item)

        self._list_widget.itemClicked.connect(self._activate_item)
        self._list_widget.itemDoubleClicked.connect(self._activate_item)
        layout.addWidget(self._list_widget)

    def _activate_item(self, item: QListWidgetItem) -> None:
        node_type = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(node_type, str) and node_type:
            self.node_type_activated.emit(node_type)
