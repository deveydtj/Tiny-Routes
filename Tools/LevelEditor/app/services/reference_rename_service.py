from __future__ import annotations

from typing import Any

from app.models import LevelDocument, Solution


class ReferenceRenameService:
    """Renames graph identifiers and every supported reference atomically."""

    _NODE_SCALAR_KEYS = {
        "nodeID", "tapNodeID", "startNodeID", "packageNodeID", "destinationNodeID",
        "fromNodeID", "toNodeID",
    }
    _NODE_LIST_KEYS = {"nodeIDs", "tapNodeIDs", "solutionRoute", "requiredPath", "requiredTapOrder"}
    _EDGE_SCALAR_KEYS = {"edgeID", "expectedEdgeAfterTap", "incomingEdgeID", "outgoingEdgeID"}
    _EDGE_LIST_KEYS = {"edgeIDs", "outgoingEdgeIDs"}

    def rename_node(
        self,
        document: LevelDocument,
        solution: Solution | None,
        old_id: str,
        new_id: str,
    ) -> None:
        node = next((item for item in document.graph.nodes if item.id == old_id), None)
        if node is None:
            raise ValueError(f"Unknown node ID: {old_id}")
        self._validate_new_id(new_id)
        if old_id == new_id:
            return
        if any(item.id == new_id for item in document.graph.nodes):
            raise ValueError(f"Node ID already exists: {new_id}")

        node.id = new_id
        for field_name in ("startNodeID", "packageNodeID", "destinationNodeID"):
            if getattr(document, field_name) == old_id:
                setattr(document, field_name, new_id)
        for edge in document.graph.edges:
            if edge.fromNodeID == old_id:
                edge.fromNodeID = new_id
            if edge.toNodeID == old_id:
                edge.toNodeID = new_id
            self._replace_metadata(edge._extra, old_id, new_id, "node")
        if document.solution is not None:
            document.solution.tapNodeIDs = [new_id if value == old_id else value for value in document.solution.tapNodeIDs]
            self._replace_metadata(document.solution._extra, old_id, new_id, "node")
        if solution is not None:
            for action in solution.actions:
                if action.tapNodeID == old_id:
                    action.tapNodeID = new_id
                self._replace_metadata(action._extra, old_id, new_id, "node")
            self._replace_metadata(solution._extra, old_id, new_id, "node")
        self._replace_all_extras(document, old_id, new_id, "node")

    def rename_edge(
        self,
        document: LevelDocument,
        solution: Solution | None,
        old_id: str,
        new_id: str,
    ) -> None:
        edge = next((item for item in document.graph.edges if item.id == old_id), None)
        if edge is None:
            raise ValueError(f"Unknown edge ID: {old_id}")
        self._validate_new_id(new_id)
        if old_id == new_id:
            return
        if any(item.id == new_id for item in document.graph.edges):
            raise ValueError(f"Edge ID already exists: {new_id}")

        edge.id = new_id
        for node in document.graph.nodes:
            node.outgoingEdgeIDs = [new_id if value == old_id else value for value in node.outgoingEdgeIDs]
        self._replace_all_extras(document, old_id, new_id, "edge")
        if solution is not None:
            self._replace_metadata(solution._extra, old_id, new_id, "edge")
            for action in solution.actions:
                self._replace_metadata(action._extra, old_id, new_id, "edge")

    @staticmethod
    def _validate_new_id(new_id: str) -> None:
        if not new_id or new_id != new_id.strip():
            raise ValueError("ID must be non-empty and contain no surrounding whitespace")

    def _replace_all_extras(self, document, old_id: str, new_id: str, kind: str) -> None:
        self._replace_metadata(document._extra, old_id, new_id, kind)
        self._replace_metadata(document.graph._extra, old_id, new_id, kind)
        for node in document.graph.nodes:
            self._replace_metadata(node._extra, old_id, new_id, kind)
        for edge in document.graph.edges:
            self._replace_metadata(edge._extra, old_id, new_id, kind)
        if document.solution is not None:
            self._replace_metadata(document.solution._extra, old_id, new_id, kind)

    def _replace_metadata(self, value: Any, old_id: str, new_id: str, kind: str) -> None:
        scalar_keys = self._NODE_SCALAR_KEYS if kind == "node" else self._EDGE_SCALAR_KEYS
        list_keys = self._NODE_LIST_KEYS if kind == "node" else self._EDGE_LIST_KEYS
        if isinstance(value, dict):
            for key, child in value.items():
                if key in scalar_keys and child == old_id:
                    value[key] = new_id
                elif key in list_keys and isinstance(child, list):
                    value[key] = [new_id if item == old_id else item for item in child]
                else:
                    self._replace_metadata(child, old_id, new_id, kind)
        elif isinstance(value, list):
            for child in value:
                self._replace_metadata(child, old_id, new_id, kind)
