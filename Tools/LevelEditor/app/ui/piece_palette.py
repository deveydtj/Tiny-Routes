from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class PiecePalette(QWidget):
    node_type_activated = Signal(str)

    _PALETTE_ITEMS: list[tuple[str, str]] = [
        ("Start", "start"),
        ("Route Node", "route"),
        ("Package", "package"),
        ("Destination", "destination"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._list_widget = QListWidget()
        for label, node_type in self._PALETTE_ITEMS:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, node_type)
            self._list_widget.addItem(item)

        self._list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._list_widget)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        node_type = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(node_type, str) and node_type:
            self.node_type_activated.emit(node_type)
