from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models import LevelDocument, SolutionActionModel, SolutionModel


class SolutionPanel(QWidget):
    solution_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)

        self._solution: SolutionModel | None = None
        self._level: LevelDocument | None = None
        self._is_updating_table = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        header_row = QHBoxLayout()
        header = QLabel("Solution")
        header.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        header_row.addWidget(header)
        header_row.addStretch()

        self._add_action_button = QPushButton("Add Action")
        self._add_action_button.clicked.connect(self._add_action)
        header_row.addWidget(self._add_action_button)

        self._remove_action_button = QPushButton("Remove Action")
        self._remove_action_button.clicked.connect(self._remove_selected_actions)
        header_row.addWidget(self._remove_action_button)
        outer.addLayout(header_row)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        outer.addWidget(separator)

        self._empty_label = QLabel("No solution actions")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self._empty_label)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Time (s)", "Tap Node ID"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.itemChanged.connect(self._on_item_changed)
        self._table.itemSelectionChanged.connect(self._update_button_states)
        self._table.setVisible(False)
        header_view = self._table.horizontalHeader()
        header_view.setStretchLastSection(True)
        outer.addWidget(self._table)

        self._timeline_label = QLabel("Switch Timeline")
        outer.addWidget(self._timeline_label)

        self._timeline_table = QTableWidget(0, 4)
        self._timeline_table.setHorizontalHeaderLabels(["Tap Node", "Previous Edge", "Next Edge", "Target"])
        self._timeline_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._timeline_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._timeline_table.setVisible(False)
        self._timeline_table.horizontalHeader().setStretchLastSection(True)
        outer.addWidget(self._timeline_table)

        self._update_empty_state()
        self._reload_timeline()

    def set_level(self, level: LevelDocument | None) -> None:
        self._level = deepcopy(level) if level is not None else None
        self._reload_timeline()

    def set_solution(self, solution: SolutionModel | None) -> None:
        self._solution = deepcopy(solution) if solution is not None else None
        self._reload_table()
        self._reload_timeline()

    def clear(self) -> None:
        self._level = None
        self.set_solution(None)

    def current_solution(self) -> SolutionModel | None:
        return deepcopy(self._solution) if self._solution is not None else None

    def _reload_table(self) -> None:
        self._is_updating_table = True
        try:
            self._table.setRowCount(0)
            actions = self._solution.actions if self._solution is not None else []
            for row_index, action in enumerate(actions):
                self._table.insertRow(row_index)
                self._populate_row(row_index, action)
        finally:
            self._is_updating_table = False

        self._update_empty_state()
        self._update_button_states()
        self._reload_timeline()

    def _populate_row(self, row_index: int, action: SolutionActionModel) -> None:
        time_item = QTableWidgetItem(self._format_time_value(action.timeSeconds))
        node_item = QTableWidgetItem(action.tapNodeID)
        self._table.setItem(row_index, 0, time_item)
        self._table.setItem(row_index, 1, node_item)

    def _update_empty_state(self) -> None:
        has_solution = self._solution is not None
        has_actions = has_solution and bool(self._solution.actions)
        self._empty_label.setText("Open or create a level to edit its solution." if not has_solution else "No solution actions")
        self._empty_label.setVisible(not has_actions)
        self._table.setVisible(bool(has_actions))

    def _update_button_states(self) -> None:
        has_solution = self._solution is not None
        has_selection = bool(self._table.selectionModel() and self._table.selectionModel().selectedRows())
        self._add_action_button.setEnabled(has_solution)
        self._remove_action_button.setEnabled(has_solution and has_selection)

    def _add_action(self) -> None:
        if self._solution is None:
            return

        new_action = SolutionActionModel(timeSeconds=0.0, tapNodeID="")
        self._solution.actions.append(new_action)
        self._solution.maxTaps = len(self._solution.actions)

        row_index = len(self._solution.actions) - 1
        self._is_updating_table = True
        try:
            self._table.insertRow(row_index)
            self._populate_row(row_index, new_action)
        finally:
            self._is_updating_table = False

        self._empty_label.setVisible(False)
        self._table.setVisible(True)
        self._table.selectRow(row_index)
        self._emit_solution_changed()

    def _remove_selected_actions(self) -> None:
        if self._solution is None:
            return

        selection_model = self._table.selectionModel()
        if selection_model is None:
            return

        selected_rows = sorted((index.row() for index in selection_model.selectedRows()), reverse=True)
        if not selected_rows:
            return

        for row_index in selected_rows:
            if 0 <= row_index < len(self._solution.actions):
                del self._solution.actions[row_index]
            self._table.removeRow(row_index)

        self._solution.maxTaps = len(self._solution.actions)
        self._update_empty_state()
        self._update_button_states()
        self._reload_timeline()
        self._emit_solution_changed()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._is_updating_table or self._solution is None:
            return

        row_index = item.row()
        column_index = item.column()
        if not (0 <= row_index < len(self._solution.actions)):
            return

        action = self._solution.actions[row_index]
        if column_index == 0:
            parsed_time = self._parse_time_value(item.text())
            if parsed_time is None:
                self._reset_item_text(item, self._format_time_value(action.timeSeconds))
                return
            if action.timeSeconds == parsed_time:
                normalized = self._format_time_value(parsed_time)
                if item.text() != normalized:
                    self._reset_item_text(item, normalized)
                return
            action.timeSeconds = parsed_time
            self._reset_item_text(item, self._format_time_value(parsed_time))
        elif column_index == 1:
            updated_node_id = item.text().strip()
            if action.tapNodeID == updated_node_id:
                if item.text() != updated_node_id:
                    self._reset_item_text(item, updated_node_id)
                return
            action.tapNodeID = updated_node_id
            if item.text() != updated_node_id:
                self._reset_item_text(item, updated_node_id)
        else:
            return

        self._solution.maxTaps = len(self._solution.actions)
        self._reload_timeline()
        self._emit_solution_changed()

    def _emit_solution_changed(self) -> None:
        if self._solution is None:
            return
        self.solution_changed.emit(deepcopy(self._solution))

    def _reload_timeline(self) -> None:
        self._timeline_table.setRowCount(0)
        rows = self._switch_timeline_rows()
        for row_index, row in enumerate(rows):
            self._timeline_table.insertRow(row_index)
            for column_index, value in enumerate(row):
                self._timeline_table.setItem(row_index, column_index, QTableWidgetItem(value))
        self._timeline_table.resizeColumnsToContents()
        self._timeline_label.setVisible(bool(rows))
        self._timeline_table.setVisible(bool(rows))

    def _switch_timeline_rows(self) -> list[tuple[str, str, str, str]]:
        if self._level is None or self._solution is None:
            return []

        node_by_id = {node.id: node for node in self._level.graph.nodes}
        edge_by_id = {edge.id: edge for edge in self._level.graph.edges}
        active_edge_by_node_id: dict[str, str | None] = {}
        rows: list[tuple[str, str, str, str]] = []

        for node in self._level.graph.nodes:
            valid_edge_ids = [
                edge_id
                for edge_id in node.outgoingEdgeIDs
                if edge_id in edge_by_id and edge_by_id[edge_id].fromNodeID == node.id
            ]
            active_edge_by_node_id[node.id] = valid_edge_ids[0] if valid_edge_ids else None

        for action in sorted(self._solution.actions, key=lambda value: float(value.timeSeconds)):
            node = node_by_id.get(action.tapNodeID)
            if node is None:
                continue

            valid_edge_ids = [
                edge_id
                for edge_id in node.outgoingEdgeIDs
                if edge_id in edge_by_id and edge_by_id[edge_id].fromNodeID == node.id
            ]
            if len(valid_edge_ids) < 2:
                continue

            previous_edge_id = active_edge_by_node_id.get(node.id)
            if previous_edge_id in valid_edge_ids:
                next_edge_id = valid_edge_ids[(valid_edge_ids.index(previous_edge_id) + 1) % len(valid_edge_ids)]
            else:
                next_edge_id = valid_edge_ids[0]
            active_edge_by_node_id[node.id] = next_edge_id
            target_node_id = edge_by_id[next_edge_id].toNodeID
            rows.append(
                (
                    action.tapNodeID,
                    previous_edge_id or "(none)",
                    next_edge_id,
                    target_node_id,
                )
            )

        return rows

    def _reset_item_text(self, item: QTableWidgetItem, text: str) -> None:
        self._is_updating_table = True
        try:
            item.setText(text)
        finally:
            self._is_updating_table = False

    @staticmethod
    def _parse_time_value(raw_value: str) -> float | None:
        try:
            return float(raw_value.strip())
        except ValueError:
            return None

    @staticmethod
    def _format_time_value(value: int | float) -> str:
        return format(float(value), "g")
