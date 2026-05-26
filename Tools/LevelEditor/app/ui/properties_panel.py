from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class PropertiesPanel(QWidget):
    """Panel that displays properties of the currently selected canvas item.

    Call ``show_node``, ``show_edge``, or ``clear`` to update the content.
    """

    outgoing_edge_order_changed = Signal(str, list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(200)
        self._current_node_id: str | None = None
        self._outgoing_edge_rows: list[dict[str, object]] = []
        self._outgoing_table: QTableWidget | None = None
        self._move_up_button: QPushButton | None = None
        self._move_down_button: QPushButton | None = None

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

    def show_node(
        self,
        node_id: str,
        node_type: str,
        model_x: float,
        model_y: float,
        switch_classification: str | None = None,
        outgoing_edge_order: list[dict[str, object]] | None = None,
    ) -> None:
        """Display properties for the selected node."""
        self._reset_form()
        self._current_node_id = node_id
        self._outgoing_edge_rows = list(outgoing_edge_order or [])
        self._form_layout.addRow("ID:", QLabel(node_id))
        self._form_layout.addRow("Type:", QLabel(node_type))
        if switch_classification is not None:
            self._form_layout.addRow("Switch:", QLabel(switch_classification))
        self._form_layout.addRow("Position:", QLabel(f"({model_x:.2f}, {model_y:.2f})"))
        if self._outgoing_edge_rows:
            self._add_outgoing_edge_order_section()
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
        self._current_node_id = None
        self._outgoing_edge_rows = []
        self._empty_label.setVisible(True)
        self._form_widget.setVisible(False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reset_form(self) -> None:
        self._outgoing_table = None
        self._move_up_button = None
        self._move_down_button = None
        while self._form_layout.rowCount() > 0:
            taken = self._form_layout.takeRow(0)
            if taken.labelItem and taken.labelItem.widget():
                taken.labelItem.widget().deleteLater()
            if taken.fieldItem and taken.fieldItem.widget():
                taken.fieldItem.widget().deleteLater()

    def _add_outgoing_edge_order_section(self) -> None:
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["#", "Edge", "Target", "Dir"])
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.itemSelectionChanged.connect(self._update_reorder_button_states)
        table.setMinimumHeight(132)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._outgoing_table = table
        self._reload_outgoing_table()

        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        self._move_up_button = QPushButton("Move Up")
        self._move_up_button.clicked.connect(lambda: self._move_selected_outgoing_edge(-1))
        controls_layout.addWidget(self._move_up_button)

        self._move_down_button = QPushButton("Move Down")
        self._move_down_button.clicked.connect(lambda: self._move_selected_outgoing_edge(1))
        controls_layout.addWidget(self._move_down_button)

        sort_clockwise_button = QPushButton("Sort Clockwise")
        sort_clockwise_button.clicked.connect(self._sort_outgoing_edges_clockwise)
        controls_layout.addWidget(sort_clockwise_button)

        sort_cardinal_button = QPushButton("Sort Cardinal")
        sort_cardinal_button.clicked.connect(self._sort_outgoing_edges_cardinal)
        controls_layout.addWidget(sort_cardinal_button)

        self._form_layout.addRow("Outgoing Edge Order:", table)
        self._form_layout.addRow("", controls)
        self._update_reorder_button_states()

    def _reload_outgoing_table(self) -> None:
        if self._outgoing_table is None:
            return

        self._outgoing_table.setRowCount(0)
        for row_index, row in enumerate(self._outgoing_edge_rows):
            self._outgoing_table.insertRow(row_index)
            prefix = "default" if row.get("is_default") else str(row_index + 1)
            values = [
                prefix,
                str(row.get("edge_id", "")),
                str(row.get("target_node_id", "")),
                str(row.get("direction_label", "")),
            ]
            for column_index, value in enumerate(values):
                self._outgoing_table.setItem(row_index, column_index, QTableWidgetItem(value))
        self._outgoing_table.resizeColumnsToContents()

    def _move_selected_outgoing_edge(self, offset: int) -> None:
        selected_row = self._selected_outgoing_row()
        if selected_row is None:
            return
        target_row = selected_row + offset
        if target_row < 0 or target_row >= len(self._outgoing_edge_rows):
            return

        self._outgoing_edge_rows[selected_row], self._outgoing_edge_rows[target_row] = (
            self._outgoing_edge_rows[target_row],
            self._outgoing_edge_rows[selected_row],
        )
        self._emit_outgoing_edge_order()
        self._reload_outgoing_table()
        if self._outgoing_table is not None:
            self._outgoing_table.selectRow(target_row)

    def _sort_outgoing_edges_clockwise(self) -> None:
        self._outgoing_edge_rows.sort(key=lambda row: float(row.get("clockwise_sort_key", 0.0)))
        self._emit_outgoing_edge_order()
        self._reload_outgoing_table()

    def _sort_outgoing_edges_cardinal(self) -> None:
        order = {
            "Up": 0,
            "Up-Right": 1,
            "Right": 2,
            "Down-Right": 3,
            "Down": 4,
            "Down-Left": 5,
            "Left": 6,
            "Up-Left": 7,
        }
        self._outgoing_edge_rows.sort(
            key=lambda row: (
                order.get(str(row.get("direction_label", "")), 99),
                str(row.get("edge_id", "")),
            )
        )
        self._emit_outgoing_edge_order()
        self._reload_outgoing_table()

    def _emit_outgoing_edge_order(self) -> None:
        if self._current_node_id is None:
            return
        edge_ids = [str(row.get("edge_id", "")) for row in self._outgoing_edge_rows if row.get("edge_id")]
        self.outgoing_edge_order_changed.emit(self._current_node_id, edge_ids)

    def _selected_outgoing_row(self) -> int | None:
        if self._outgoing_table is None or self._outgoing_table.selectionModel() is None:
            return None
        selected_rows = self._outgoing_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        return selected_rows[0].row()

    def _update_reorder_button_states(self) -> None:
        selected_row = self._selected_outgoing_row()
        has_selection = selected_row is not None
        if self._move_up_button is not None:
            self._move_up_button.setEnabled(has_selection and selected_row > 0)
        if self._move_down_button is not None:
            self._move_down_button.setEnabled(
                has_selection and selected_row < len(self._outgoing_edge_rows) - 1
            )

    @staticmethod
    def _format_road_shape(road_shape: str) -> str:
        if road_shape == "verticalFirst":
            return "Vertical First"
        return "Horizontal First"
