from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QFrame,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class _InspectableComboBox(QComboBox):
    """Combo box with a text accessor retained for inspector compatibility."""

    def __init__(self, *, use_display_text: bool = False) -> None:
        super().__init__()
        self._use_display_text = use_display_text

    def text(self) -> str:
        return self.currentText() if self._use_display_text else str(self.currentData() or "")


class _CoordinateEditor(QWidget):
    def __init__(self, x_spinbox: QDoubleSpinBox, y_spinbox: QDoubleSpinBox) -> None:
        super().__init__()
        self.x_spinbox = x_spinbox
        self.y_spinbox = y_spinbox

    def text(self) -> str:
        return f"({self.x_spinbox.value():.2f}, {self.y_spinbox.value():.2f})"


class PropertiesPanel(QWidget):
    """Panel that displays properties of the currently selected canvas item.

    Call ``show_node``, ``show_edge``, or ``clear`` to update the content.
    """

    outgoing_edge_order_changed = Signal(str, list)
    node_id_changed = Signal(str, str)
    node_role_changed = Signal(str, str)
    node_position_changed = Signal(str, float, float)
    initial_route_changed = Signal(str, str)
    edge_id_changed = Signal(str, str)
    edge_properties_changed = Signal(str, str, str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(200)
        self._current_node_id: str | None = None
        self._outgoing_edge_rows: list[dict[str, object]] = []
        self._outgoing_table: QTableWidget | None = None
        self._move_up_button: QPushButton | None = None
        self._move_down_button: QPushButton | None = None
        self._node_x_spinbox: QDoubleSpinBox | None = None
        self._node_y_spinbox: QDoubleSpinBox | None = None
        self._current_edge_id: str | None = None

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
        available_node_ids: list[str] | None = None,
    ) -> None:
        """Display properties for the selected node."""
        self._reset_form()
        self._current_node_id = node_id
        self._outgoing_edge_rows = list(outgoing_edge_order or [])
        id_edit = QLineEdit(node_id)
        id_edit.setObjectName("nodeIdEdit")
        id_edit.editingFinished.connect(
            lambda: self.node_id_changed.emit(self._current_node_id or node_id, id_edit.text())
        )
        self._form_layout.addRow("ID:", id_edit)

        role_combo = _InspectableComboBox()
        role_combo.setObjectName("nodeRoleCombo")
        for label, value in (("Route", "route"), ("Start", "start"), ("Package", "package"), ("Destination", "destination")):
            role_combo.addItem(label, value)
        role = node_type if node_type in {"start", "package", "destination"} else "route"
        role_combo.setCurrentIndex(role_combo.findData(role))
        role_combo.currentIndexChanged.connect(
            lambda: self.node_role_changed.emit(self._current_node_id or node_id, str(role_combo.currentData()))
        )
        self._form_layout.addRow("Type:", role_combo)
        if switch_classification is not None:
            self._form_layout.addRow("Switch:", QLabel(switch_classification))
        self._node_x_spinbox = self._coordinate_spinbox(model_x, "nodeXSpinBox")
        self._node_y_spinbox = self._coordinate_spinbox(model_y, "nodeYSpinBox")
        coordinates = _CoordinateEditor(self._node_x_spinbox, self._node_y_spinbox)
        coordinate_layout = QHBoxLayout(coordinates)
        coordinate_layout.setContentsMargins(0, 0, 0, 0)
        coordinate_layout.addWidget(QLabel("X"))
        coordinate_layout.addWidget(self._node_x_spinbox)
        coordinate_layout.addWidget(QLabel("Y"))
        coordinate_layout.addWidget(self._node_y_spinbox)
        self._node_x_spinbox.editingFinished.connect(self._emit_node_position)
        self._node_y_spinbox.editingFinished.connect(self._emit_node_position)
        self._form_layout.addRow("Position:", coordinates)
        if self._outgoing_edge_rows:
            self._add_outgoing_edge_order_section()
            if len(self._outgoing_edge_rows) > 1:
                warning = QLabel(
                    "Changing the outgoing order or initial route changes switch gameplay."
                )
                warning.setObjectName("outgoingOrderWarning")
                warning.setWordWrap(True)
                self._form_layout.addRow("Warning:", warning)
        self._empty_label.setVisible(False)
        self._form_widget.setVisible(True)

    def show_edge(
        self,
        edge_id: str,
        from_node_id: str,
        to_node_id: str,
        road_shape: str,
        available_node_ids: list[str] | None = None,
    ) -> None:
        """Display properties for the selected edge."""
        self._reset_form()
        self._current_edge_id = edge_id
        id_edit = QLineEdit(edge_id)
        id_edit.setObjectName("edgeIdEdit")
        id_edit.editingFinished.connect(
            lambda: self.edge_id_changed.emit(self._current_edge_id or edge_id, id_edit.text())
        )
        self._form_layout.addRow("ID:", id_edit)
        node_ids = list(available_node_ids or sorted({from_node_id, to_node_id}))
        from_combo = self._node_combo(node_ids, from_node_id, "edgeFromCombo")
        to_combo = self._node_combo(node_ids, to_node_id, "edgeToCombo")
        shape_combo = _InspectableComboBox(use_display_text=True)
        shape_combo.setObjectName("edgeRoadShapeCombo")
        shape_combo.addItem("Horizontal First", "horizontalFirst")
        shape_combo.addItem("Vertical First", "verticalFirst")
        shape_combo.setCurrentIndex(max(0, shape_combo.findData(road_shape)))
        emit = lambda: self.edge_properties_changed.emit(
            self._current_edge_id or edge_id,
            str(from_combo.currentData()),
            str(to_combo.currentData()),
            str(shape_combo.currentData()),
        )
        from_combo.currentIndexChanged.connect(emit)
        to_combo.currentIndexChanged.connect(emit)
        shape_combo.currentIndexChanged.connect(emit)
        self._form_layout.addRow("From:", from_combo)
        self._form_layout.addRow("To:", to_combo)
        self._form_layout.addRow("Road Shape:", shape_combo)
        self._empty_label.setVisible(False)
        self._form_widget.setVisible(True)

    def clear(self) -> None:
        """Reset the panel to the no-selection empty state."""
        self._reset_form()
        self._current_node_id = None
        self._current_edge_id = None
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
        self._node_x_spinbox = None
        self._node_y_spinbox = None
        while self._form_layout.rowCount() > 0:
            taken = self._form_layout.takeRow(0)
            if taken.labelItem and taken.labelItem.widget():
                taken.labelItem.widget().deleteLater()
            if taken.fieldItem and taken.fieldItem.widget():
                taken.fieldItem.widget().deleteLater()

    def _add_outgoing_edge_order_section(self) -> None:
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["#", "Edge", "Target", "Dir", "Shape"])
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

        initial_button = QPushButton("Set as Initial Route")
        initial_button.setObjectName("setInitialRouteButton")
        initial_button.clicked.connect(self._set_selected_initial_route)
        controls_layout.addWidget(initial_button)

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
                self._format_road_shape(str(row.get("road_shape", "horizontalFirst"))),
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

    def _set_selected_initial_route(self) -> None:
        row = self._selected_outgoing_row()
        if row is None or self._current_node_id is None:
            return
        edge_id = str(self._outgoing_edge_rows[row].get("edge_id", ""))
        if edge_id:
            self.initial_route_changed.emit(self._current_node_id, edge_id)

    def _emit_node_position(self) -> None:
        if self._current_node_id and self._node_x_spinbox and self._node_y_spinbox:
            self.node_position_changed.emit(
                self._current_node_id, self._node_x_spinbox.value(), self._node_y_spinbox.value()
            )

    @staticmethod
    def _coordinate_spinbox(value: float, object_name: str) -> QDoubleSpinBox:
        spinbox = QDoubleSpinBox()
        spinbox.setObjectName(object_name)
        spinbox.setRange(-10000.0, 10000.0)
        spinbox.setDecimals(3)
        spinbox.setValue(value)
        return spinbox

    @staticmethod
    def _node_combo(node_ids: list[str], selected: str, object_name: str) -> QComboBox:
        combo = _InspectableComboBox()
        combo.setObjectName(object_name)
        for node_id in node_ids:
            combo.addItem(node_id, node_id)
        combo.setCurrentIndex(max(0, combo.findData(selected)))
        return combo

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
