from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoStack

from app.commands import (
    AddEdgeCommand,
    AddNodeCommand,
    DeleteItemsCommand,
    EditEdgeCommand,
    EditMetadataCommand,
    EditNodeCommand,
    EditSolutionCommand,
    EditRulesCommand,
    MoveNodeCommand,
    ReorderEdgesCommand,
    RenameReferencesCommand,
)
from app.models import (
    EdgeAvailabilityRule,
    LevelDocument,
    RouteEdge,
    RouteNode,
    RouteObjective,
    RouteObjectiveKind,
    Solution,
)
from app.services.reference_rename_service import ReferenceRenameService


class DocumentController(QObject):
    """Owns editor document state and is the only graph mutation boundary."""

    document_changed = Signal(object, object)
    dirty_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.document: LevelDocument | None = None
        self.solution: Solution | None = None
        self.undo_stack = QUndoStack(self)
        self.undo_stack.cleanChanged.connect(self._on_clean_changed)
        self._reference_rename_service = ReferenceRenameService()

    @property
    def is_dirty(self) -> bool:
        return not self.undo_stack.isClean()

    def open(self, document: LevelDocument, solution: Solution | None, *, saved: bool) -> None:
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

    def add_node(self, node: RouteNode, node_type: str) -> None:
        self._mutate(AddNodeCommand, f"Add {node.id}", lambda document, solution: self._add_node(document, node, node_type))

    def move_node(self, node_id: str, x: float, y: float) -> None:
        def mutation(document, solution):
            node = next((item for item in document.graph.nodes if item.id == node_id), None)
            if node is not None:
                node.x, node.y = x, y
        self._mutate(MoveNodeCommand, f"Move {node_id}", mutation)

    def move_nodes(
        self,
        positions: dict[str, tuple[float, float]],
        *,
        command_text: str,
    ) -> None:
        def mutation(document, solution):
            for node in document.graph.nodes:
                if node.id in positions:
                    node.x, node.y = positions[node.id]
        self._mutate(MoveNodeCommand, command_text, mutation)

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

    def add_edge(self, edge: RouteEdge) -> None:
        self.add_edges([edge])

    def add_edges(self, edges: list[RouteEdge]) -> None:
        def mutation(document, solution):
            for edge in edges:
                source = next(node for node in document.graph.nodes if node.id == edge.fromNodeID)
                source.outgoingEdgeIDs.append(edge.id)
                document.graph.edges.append(deepcopy(edge))
        text = f"Add {edges[0].id}" if len(edges) == 1 else "Add two-way road"
        self._mutate(AddEdgeCommand, text, mutation)

    def reorder_edges(self, node_id: str, ordered_ids: list[str], valid_ids: list[str]) -> None:
        def mutation(document, solution):
            node = next(item for item in document.graph.nodes if item.id == node_id)
            remaining = [edge_id for edge_id in node.outgoingEdgeIDs if edge_id not in valid_ids]
            node.outgoingEdgeIDs = list(ordered_ids) + remaining
        self._mutate(ReorderEdgesCommand, f"Reorder roads from {node_id}", mutation)

    def rename_node(self, old_id: str, new_id: str) -> None:
        self._mutate(
            RenameReferencesCommand,
            f"Rename node {old_id} to {new_id}",
            lambda document, solution: self._reference_rename_service.rename_node(
                document, solution, old_id, new_id
            ),
        )

    def rename_edge(self, old_id: str, new_id: str) -> None:
        self._mutate(
            RenameReferencesCommand,
            f"Rename road {old_id} to {new_id}",
            lambda document, solution: self._reference_rename_service.rename_edge(
                document, solution, old_id, new_id
            ),
        )

    def edit_node_position(self, node_id: str, x: float, y: float) -> None:
        def mutation(document, solution):
            node = next((item for item in document.graph.nodes if item.id == node_id), None)
            if node is None:
                raise ValueError(f"Unknown node ID: {node_id}")
            node.x, node.y = float(x), float(y)
        self._mutate(EditNodeCommand, f"Edit {node_id} position", mutation)

    def set_node_role(self, node_id: str, role: str) -> None:
        role_fields = {
            "start": "startNodeID",
            "package": "packageNodeID",
            "destination": "destinationNodeID",
        }
        if role not in {"route", *role_fields}:
            raise ValueError(f"Unknown node role: {role}")

        def mutation(document, solution):
            if not any(node.id == node_id for node in document.graph.nodes):
                raise ValueError(f"Unknown node ID: {node_id}")
            if role == "route":
                if any(getattr(document, field) == node_id for field in role_fields.values()):
                    raise ValueError(
                        "Assign this role to another node instead; levels must keep start, package, and destination nodes"
                    )
            else:
                target_field = role_fields[role]
                previous_target_id = getattr(document, target_field)
                for field in role_fields.values():
                    if field != target_field and getattr(document, field) == node_id:
                        setattr(document, field, previous_target_id)
                setattr(document, target_field, node_id)
        self._mutate(EditNodeCommand, f"Set {node_id} role to {role}", mutation)

    def edit_edge(
        self,
        edge_id: str,
        from_node_id: str,
        to_node_id: str,
        road_shape: str,
        availability: str = "always",
    ) -> None:
        if road_shape not in {"horizontalFirst", "verticalFirst"}:
            raise ValueError(f"Unknown road shape: {road_shape}")
        if availability not in {"always", "beforePackage", "afterPackage"}:
            raise ValueError(f"Unknown road availability: {availability}")

        def mutation(document, solution):
            edge = next((item for item in document.graph.edges if item.id == edge_id), None)
            if edge is None:
                raise ValueError(f"Unknown edge ID: {edge_id}")
            node_by_id = {node.id: node for node in document.graph.nodes}
            if from_node_id not in node_by_id or to_node_id not in node_by_id:
                raise ValueError("Road endpoints must reference existing nodes")
            if any(
                item.id != edge_id
                and item.fromNodeID == from_node_id
                and item.toNodeID == to_node_id
                for item in document.graph.edges
            ):
                raise ValueError(f"A road from {from_node_id} to {to_node_id} already exists")

            old_source = node_by_id.get(edge.fromNodeID)
            insertion_index = len(node_by_id[from_node_id].outgoingEdgeIDs)
            if old_source is not None and edge_id in old_source.outgoingEdgeIDs:
                insertion_index = old_source.outgoingEdgeIDs.index(edge_id)
                old_source.outgoingEdgeIDs.remove(edge_id)
            new_source = node_by_id[from_node_id]
            insertion_index = min(insertion_index, len(new_source.outgoingEdgeIDs))
            new_source.outgoingEdgeIDs.insert(insertion_index, edge_id)
            edge.fromNodeID = from_node_id
            edge.toNodeID = to_node_id
            edge.roadShape = road_shape
            edge.availability = availability
            edge._availability_present = availability != "always"
        self._mutate(EditEdgeCommand, f"Edit road {edge_id}", mutation)

    def edit_edge_availability_rule(
        self,
        edge_id: str,
        rule: EdgeAvailabilityRule | None,
    ) -> None:
        """Set a structured schema-3 road rule as one undoable edit."""

        def mutation(document, solution):
            edge = next((item for item in document.graph.edges if item.id == edge_id), None)
            if edge is None:
                raise ValueError(f"Unknown edge ID: {edge_id}")

            if rule is not None:
                if document.schema_version < 3:
                    document.objectives = document.effective_objectives
                required = list(rule.requiredCompletedObjectiveIDs)
                forbidden = list(rule.forbiddenCompletedObjectiveIDs)
                if len(required) != len(set(required)):
                    raise ValueError("Required objective IDs must be unique")
                if len(forbidden) != len(set(forbidden)):
                    raise ValueError("Forbidden objective IDs must be unique")
                overlap = sorted(set(required).intersection(forbidden))
                if overlap:
                    raise ValueError(
                        "An objective cannot be both required and forbidden: "
                        + ", ".join(overlap)
                    )

                known_objective_ids = {
                    objective.id for objective in document.effective_objectives
                }
                unknown = sorted((set(required) | set(forbidden)) - known_objective_ids)
                if unknown:
                    raise ValueError(
                        "Road rules reference unknown objective IDs: " + ", ".join(unknown)
                    )
                if (
                    rule.minimumObjectiveIndex is not None
                    and rule.minimumObjectiveIndex < 0
                ):
                    raise ValueError("Minimum objective index cannot be negative")
                if (
                    rule.maximumObjectiveIndex is not None
                    and rule.maximumObjectiveIndex < 0
                ):
                    raise ValueError("Maximum objective index cannot be negative")
                objective_count = len(document.objectives or ())
                for label, index in (
                    ("Minimum", rule.minimumObjectiveIndex),
                    ("Maximum", rule.maximumObjectiveIndex),
                ):
                    if index is not None and index >= objective_count:
                        raise ValueError(
                            f"{label} objective index must be less than {objective_count}"
                        )
                if (
                    rule.minimumObjectiveIndex is not None
                    and rule.maximumObjectiveIndex is not None
                    and rule.minimumObjectiveIndex > rule.maximumObjectiveIndex
                ):
                    raise ValueError(
                        "Minimum objective index cannot exceed maximum objective index"
                    )
                if rule.usageLimit is not None and rule.usageLimit <= 0:
                    raise ValueError("Usage limit must be greater than zero")

                document._extra["schemaVersion"] = 3
                edge.availability = "always"
                edge._availability_present = False
            edge.availabilityRule = deepcopy(rule)

        self._mutate(EditEdgeCommand, f"Edit road {edge_id} condition", mutation)

    def edit_metadata(self, mutation) -> None:
        self._mutate(EditMetadataCommand, "Edit level metadata", mutation)

    def edit_rules(self, rules, schema_version: int = 2) -> None:
        def mutation(document, solution):
            document.rules = deepcopy(rules)
            document._rules_present = True
            document._extra["schemaVersion"] = schema_version
        self._mutate(EditRulesCommand, "Edit level rules", mutation)

    def edit_objectives(self, objectives: list[RouteObjective]) -> None:
        """Replace and renumber ordered objectives, upgrading the document to schema 3."""

        def mutation(document, solution):
            document.objectives = deepcopy(objectives)
            for sequence_index, objective in enumerate(document.objectives):
                objective.sequenceIndex = sequence_index
            document._extra["schemaVersion"] = 3

            first_pickup = next(
                (objective for objective in document.objectives
                 if objective.kind is RouteObjectiveKind.PICKUP),
                None,
            )
            destination = next(
                (objective for objective in reversed(document.objectives)
                 if objective.kind is RouteObjectiveKind.DESTINATION),
                None,
            )
            if first_pickup is not None:
                document.packageNodeID = first_pickup.nodeID
            if destination is not None:
                document.destinationNodeID = destination.nodeID

        self._mutate(EditMetadataCommand, "Edit ordered objectives", mutation)

    def edit_solution(self, solution: Solution) -> None:
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
    def _add_node(document: LevelDocument, node: RouteNode, node_type: str) -> None:
        document.graph.nodes.append(deepcopy(node))
        if node_type == "start":
            document.startNodeID = node.id
        elif node_type == "package":
            document.packageNodeID = node.id
        elif node_type == "destination":
            document.destinationNodeID = node.id

    def _restore_state(self, document: LevelDocument, solution: Solution | None) -> None:
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

    def _on_clean_changed(self, clean: bool) -> None:
        self.dirty_changed.emit(not clean)
