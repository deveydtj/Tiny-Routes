from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QFrame, QLabel, QVBoxLayout, QWidget


class PropertiesPanel(QWidget):
    """Panel that displays properties of the currently selected canvas item.

    Call ``show_node``, ``show_edge``, or ``clear`` to update the content.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(200)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        header = QLabel("Properties")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(header)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        outer.addWidget(separator)

        self._empty_label = QLabel("No selection")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self._empty_label)

        self._form_widget = QWidget()
        self._form_layout = QFormLayout(self._form_widget)
        self._form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._form_widget.setVisible(False)
        outer.addWidget(self._form_widget)

        outer.addStretch()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_node(self, node_id: str, node_type: str, model_x: float, model_y: float) -> None:
        """Display properties for the selected node."""
        self._reset_form()
        self._form_layout.addRow("ID:", QLabel(node_id))
        self._form_layout.addRow("Type:", QLabel(node_type))
        self._form_layout.addRow("Position:", QLabel(f"({model_x:.2f}, {model_y:.2f})"))
        self._empty_label.setVisible(False)
        self._form_widget.setVisible(True)

    def show_edge(
        self,
        edge_id: str,
        from_node_id: str,
        to_node_id: str,
        road_shape: str,
    ) -> None:
        """Display properties for the selected edge."""
        self._reset_form()
        self._form_layout.addRow("ID:", QLabel(edge_id))
        self._form_layout.addRow("From:", QLabel(from_node_id))
        self._form_layout.addRow("To:", QLabel(to_node_id))
        self._form_layout.addRow("Road Shape:", QLabel(self._format_road_shape(road_shape)))
        self._empty_label.setVisible(False)
        self._form_widget.setVisible(True)

    def clear(self) -> None:
        """Reset the panel to the no-selection empty state."""
        self._reset_form()
        self._empty_label.setVisible(True)
        self._form_widget.setVisible(False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reset_form(self) -> None:
        while self._form_layout.rowCount() > 0:
            taken = self._form_layout.takeRow(0)
            if taken.labelItem and taken.labelItem.widget():
                taken.labelItem.widget().deleteLater()
            if taken.fieldItem and taken.fieldItem.widget():
                taken.fieldItem.widget().deleteLater()

    @staticmethod
    def _format_road_shape(road_shape: str) -> str:
        if road_shape == "verticalFirst":
            return "Vertical First"
        return "Horizontal First"
