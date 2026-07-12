from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QUndoStack

from app.commands import (
    AddEdgeCommand,
    AddNodeCommand,
    DeleteItemsCommand,
    EditMetadataCommand,
    EditSolutionCommand,
    MoveNodeCommand,
    ReorderEdgesCommand,
)
from app.models import LevelDocument, RouteEdgeModel, RouteNodeModel, SolutionModel


class DocumentController(QObject):
    """Owns editor document state and is the only graph mutation boundary."""

    document_changed = Signal(object, object)
    dirty_changed = Signal(bool)
    validation_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.document: LevelDocument | None = None
        self.solution: SolutionModel | None = None
        self.undo_stack = QUndoStack(self)
        self._validation_timer = QTimer(self)
        self._validation_timer.setSingleShot(True)
        self._validation_timer.setInterval(250)
        self._validation_timer.timeout.connect(self.validation_requested)
        self.undo_stack.cleanChanged.connect(self._on_clean_changed)

    @property
    def is_dirty(self) -> bool:
        return not self.undo_stack.isClean()

    def open(self, document: LevelDocument, solution: SolutionModel | None, *, saved: bool) -> None:
        self.undo_stack.clear()
        self.document = document
        self.solution = solution
        self._emit_change()
        if saved:
            self.undo_stack.setClean()
        else:
            before = deepcopy(self.document)
            after = deepcopy(self.document)
            # A newly created document is intentionally one step from the clean index.
            after.name = after.name
            command = EditMetadataCommand(self, "Create level", before, after, self.solution, self.solution)
            self.undo_stack.push(command)
        self.dirty_changed.emit(self.is_dirty)

    def mark_saved(self) -> None:
        self.undo_stack.setClean()

    def add_node(self, node: RouteNodeModel, node_type: str) -> None:
        self._mutate(AddNodeCommand, f"Add {node.id}", lambda document, solution: self._add_node(document, node, node_type))

    def move_node(self, node_id: str, x: float, y: float) -> None:
        def mutation(document, solution):
            node = next((item for item in document.graph.nodes if item.id == node_id), None)
            if node is not None:
                node.x, node.y = x, y
        self._mutate(MoveNodeCommand, f"Move {node_id}", mutation)

    def delete_items(self, node_ids: set[str], edge_ids: set[str]) -> None:
        def mutation(document, solution):
            removed_edges = edge_ids | {
                edge.id for edge in document.graph.edges
                if edge.fromNodeID in node_ids or edge.toNodeID in node_ids
            }
            document.graph.nodes = [node for node in document.graph.nodes if node.id not in node_ids]
            document.graph.edges = [edge for edge in document.graph.edges if edge.id not in removed_edges]
            for node in document.graph.nodes:
                node.outgoingEdgeIDs = [edge_id for edge_id in node.outgoingEdgeIDs if edge_id not in removed_edges]
        self._mutate(DeleteItemsCommand, "Delete items", mutation)

    def add_edge(self, edge: RouteEdgeModel) -> None:
        def mutation(document, solution):
            source = next(node for node in document.graph.nodes if node.id == edge.fromNodeID)
            source.outgoingEdgeIDs.append(edge.id)
            document.graph.edges.append(deepcopy(edge))
        self._mutate(AddEdgeCommand, f"Add {edge.id}", mutation)

    def reorder_edges(self, node_id: str, ordered_ids: list[str], valid_ids: list[str]) -> None:
        def mutation(document, solution):
            node = next(item for item in document.graph.nodes if item.id == node_id)
            remaining = [edge_id for edge_id in node.outgoingEdgeIDs if edge_id not in valid_ids]
            node.outgoingEdgeIDs = list(ordered_ids) + remaining
        self._mutate(ReorderEdgesCommand, f"Reorder roads from {node_id}", mutation)

    def edit_metadata(self, mutation) -> None:
        self._mutate(EditMetadataCommand, "Edit level metadata", mutation)

    def edit_solution(self, solution: SolutionModel) -> None:
        self._mutate(EditSolutionCommand, "Edit solution", lambda document, current: solution)

    def _mutate(self, command_type, text: str, mutation) -> None:
        if self.document is None:
            return
        before_document, before_solution = deepcopy(self.document), deepcopy(self.solution)
        after_document, after_solution = deepcopy(self.document), deepcopy(self.solution)
        result = mutation(after_document, after_solution)
        if result is not None:
            after_solution = result
        if after_document == before_document and after_solution == before_solution:
            return
        self.undo_stack.push(command_type(
            self, text, before_document, after_document, before_solution, after_solution
        ))

    @staticmethod
    def _add_node(document: LevelDocument, node: RouteNodeModel, node_type: str) -> None:
        document.graph.nodes.append(deepcopy(node))
        if node_type == "start":
            document.startNodeID = node.id
        elif node_type == "package":
            document.packageNodeID = node.id
        elif node_type == "destination":
            document.destinationNodeID = node.id

    def _restore_state(self, document: LevelDocument, solution: SolutionModel | None) -> None:
        if self.document is None:
            self.document = deepcopy(document)
        else:
            for field_name in vars(document):
                setattr(self.document, field_name, deepcopy(getattr(document, field_name)))
        if solution is None:
            self.solution = None
        elif self.solution is None:
            self.solution = deepcopy(solution)
        else:
            for field_name in vars(solution):
                setattr(self.solution, field_name, deepcopy(getattr(solution, field_name)))
        self._emit_change()

    def _emit_change(self) -> None:
        self.document_changed.emit(self.document, self.solution)
        self._validation_timer.start()

    def _on_clean_changed(self, clean: bool) -> None:
        self.dirty_changed.emit(not clean)
