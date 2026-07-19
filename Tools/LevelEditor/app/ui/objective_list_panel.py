from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tiny_routes_core.models import LevelDocument, RouteObjective, RouteObjectiveKind


class ObjectiveListPanel(QWidget):
    """Edits the ordered schema-3 objective sequence as one undoable value."""

    objectives_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(330)
        self._node_ids: list[str] = []
        self._objective_templates: list[RouteObjective] = []
        self._updating = False
        self._emitting = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._status_label = QLabel("Open a level to edit objectives.")
        self._status_label.setObjectName("objectiveStatusLabel")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        self._table = QTableWidget(0, 5)
        self._table.setObjectName("objectiveTable")
        self._table.setHorizontalHeaderLabels(["#", "ID", "Node", "Kind", "Reveal"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.itemSelectionChanged.connect(self._update_button_states)
        layout.addWidget(self._table)

        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        self._add_button = QPushButton("Add")
        self._add_button.setObjectName("addObjectiveButton")
        self._add_button.clicked.connect(self._add_objective)
        self._remove_button = QPushButton("Remove")
        self._remove_button.setObjectName("removeObjectiveButton")
        self._remove_button.clicked.connect(self._remove_selected)
        self._move_up_button = QPushButton("Move Up")
        self._move_up_button.setObjectName("moveObjectiveUpButton")
        self._move_up_button.clicked.connect(lambda: self._move_selected(-1))
        self._move_down_button = QPushButton("Move Down")
        self._move_down_button.setObjectName("moveObjectiveDownButton")
        self._move_down_button.clicked.connect(lambda: self._move_selected(1))
        for button in (
            self._add_button,
            self._remove_button,
            self._move_up_button,
            self._move_down_button,
        ):
            controls_layout.addWidget(button)
        layout.addWidget(controls)
        self._set_controls_enabled(False)

    def set_level(self, level: LevelDocument | None) -> None:
        self._node_ids = sorted(node.id for node in level.graph.nodes) if level else []
        if level is None:
            self._status_label.setText("Open a level to edit objectives.")
            self._reload([])
            self._set_controls_enabled(False)
            return

        objectives = level.objectives
        if objectives is None:
            objectives = level.effective_objectives
            self._status_label.setText(
                "Legacy package/destination objectives are shown. Any edit upgrades this level to schema 3."
            )
        else:
            self._status_label.setText(
                "Objectives run from top to bottom. The destination must remain last."
            )
        self._reload(objectives)
        self._set_controls_enabled(True)

    @property
    def is_emitting(self) -> bool:
        return self._emitting

    def objectives(self) -> list[RouteObjective]:
        objectives: list[RouteObjective] = []
        for row in range(self._table.rowCount()):
            id_editor = self._table.cellWidget(row, 1)
            node_combo = self._table.cellWidget(row, 2)
            kind_combo = self._table.cellWidget(row, 3)
            reveal_combo = self._table.cellWidget(row, 4)
            if not isinstance(id_editor, QLineEdit):
                continue
            objective = deepcopy(self._objective_templates[row])
            objective.id = id_editor.text().strip()
            objective.nodeID = str(node_combo.currentData())
            objective.kind = RouteObjectiveKind(str(kind_combo.currentData()))
            objective.sequenceIndex = row
            objective.revealPolicy = str(reveal_combo.currentData())
            objectives.append(objective)
        return objectives

    def _reload(self, objectives: list[RouteObjective]) -> None:
        self._updating = True
        self._objective_templates = [deepcopy(objective) for objective in objectives]
        self._table.setRowCount(0)
        for row, objective in enumerate(objectives):
            self._insert_row(row, deepcopy(objective))
        self._table.resizeColumnsToContents()
        self._updating = False
        self._update_button_states()

    def _insert_row(self, row: int, objective: RouteObjective) -> None:
        self._table.insertRow(row)
        order_item = QTableWidgetItem(str(row + 1))
        order_item.setFlags(order_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, 0, order_item)

        id_editor = QLineEdit(objective.id)
        id_editor.setObjectName(f"objectiveIdEdit_{row}")
        id_editor.editingFinished.connect(self._emit_objectives)
        self._table.setCellWidget(row, 1, id_editor)

        node_combo = QComboBox()
        node_combo.setObjectName(f"objectiveNodeCombo_{row}")
        for node_id in self._node_ids:
            node_combo.addItem(node_id, node_id)
        if node_combo.findData(objective.nodeID) < 0:
            node_combo.addItem(objective.nodeID, objective.nodeID)
        node_combo.setCurrentIndex(max(0, node_combo.findData(objective.nodeID)))
        node_combo.currentIndexChanged.connect(self._emit_objectives)
        self._table.setCellWidget(row, 2, node_combo)

        kind_combo = QComboBox()
        kind_combo.setObjectName(f"objectiveKindCombo_{row}")
        for kind in RouteObjectiveKind:
            kind_combo.addItem(kind.value.title(), kind.value)
        kind_combo.setCurrentIndex(max(0, kind_combo.findData(objective.kind.value)))
        kind_combo.currentIndexChanged.connect(self._emit_objectives)
        self._table.setCellWidget(row, 3, kind_combo)

        reveal_combo = QComboBox()
        reveal_combo.setObjectName(f"objectiveRevealCombo_{row}")
        reveal_policies = ["always", "whenActive", "afterPrevious"]
        if objective.revealPolicy not in reveal_policies:
            reveal_policies.append(objective.revealPolicy)
        for policy in reveal_policies:
            reveal_combo.addItem(policy, policy)
        reveal_combo.setCurrentIndex(max(0, reveal_combo.findData(objective.revealPolicy)))
        reveal_combo.currentIndexChanged.connect(self._emit_objectives)
        self._table.setCellWidget(row, 4, reveal_combo)

    def _add_objective(self) -> None:
        objectives = self.objectives()
        used_ids = {objective.id for objective in objectives}
        suffix = 1
        while f"objective_{suffix}" in used_ids:
            suffix += 1
        insert_at = next(
            (index for index, objective in enumerate(objectives)
             if objective.kind is RouteObjectiveKind.DESTINATION),
            len(objectives),
        )
        used_nodes = {objective.nodeID for objective in objectives}
        node_id = next(
            (candidate for candidate in self._node_ids if candidate not in used_nodes),
            self._node_ids[0] if self._node_ids else "",
        )
        objectives.insert(insert_at, RouteObjective(
            id=f"objective_{suffix}",
            nodeID=node_id,
            kind=RouteObjectiveKind.CHECKPOINT,
            sequenceIndex=insert_at,
            revealPolicy="whenActive",
        ))
        self._reload(objectives)
        self._table.selectRow(insert_at)
        self._emit_objectives()

    def _remove_selected(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        objectives = self.objectives()
        objectives.pop(row)
        self._reload(objectives)
        if objectives:
            self._table.selectRow(min(row, len(objectives) - 1))
        self._emit_objectives()

    def _move_selected(self, offset: int) -> None:
        row = self._selected_row()
        if row is None:
            return
        target = row + offset
        objectives = self.objectives()
        if target < 0 or target >= len(objectives):
            return
        objectives[row], objectives[target] = objectives[target], objectives[row]
        self._reload(objectives)
        self._table.selectRow(target)
        self._emit_objectives()

    def _emit_objectives(self, *_args) -> None:
        if not self._updating:
            self._emitting = True
            try:
                self.objectives_changed.emit(self.objectives())
            finally:
                self._emitting = False

    def _selected_row(self) -> int | None:
        rows = self._table.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._table.setEnabled(enabled)
        self._add_button.setEnabled(enabled and bool(self._node_ids))
        if not enabled:
            self._remove_button.setEnabled(False)
            self._move_up_button.setEnabled(False)
            self._move_down_button.setEnabled(False)
        else:
            self._update_button_states()

    def _update_button_states(self) -> None:
        row = self._selected_row()
        has_selection = row is not None and self._table.isEnabled()
        self._remove_button.setEnabled(has_selection)
        self._move_up_button.setEnabled(has_selection and row > 0)
        self._move_down_button.setEnabled(
            has_selection and row < self._table.rowCount() - 1
        )
