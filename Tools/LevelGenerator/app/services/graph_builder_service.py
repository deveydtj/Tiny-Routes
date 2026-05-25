from __future__ import annotations

from dataclasses import dataclass, field

from ..id_allocator import IDAllocator
from ..level_editor_imports import LevelDocument, RouteEdgeModel, RouteGraphModel, RouteNodeModel
from .road_shape_service import RoadShapeService


@dataclass
class GraphBuilderService:
    id_allocator: IDAllocator = field(default_factory=IDAllocator)
    road_shape_service: RoadShapeService = field(default_factory=RoadShapeService)

    def __post_init__(self) -> None:
        self._nodes: list[RouteNodeModel] = []
        self._edges: list[RouteEdgeModel] = []
        self._node_by_id: dict[str, RouteNodeModel] = {}

    def add_node(self, node_id: str, x: float, y: float) -> RouteNodeModel:
        self.id_allocator.reserve_existing_node_id(node_id)
        node = RouteNodeModel(id=node_id, x=round(float(x), 4), y=round(float(y), 4), outgoingEdgeIDs=[])
        self._nodes.append(node)
        self._node_by_id[node_id] = node
        return node

    def add_reserved_node(self, base_name: str, x: float, y: float) -> RouteNodeModel:
        return self.add_node(self.id_allocator.reserve_node_id(base_name), x, y)

    def add_edge(
        self,
        from_node_id: str,
        to_node_id: str,
        road_shape: str | None = None,
        edge_id: str | None = None,
    ) -> RouteEdgeModel:
        if from_node_id not in self._node_by_id:
            raise ValueError(f"Unknown from node: {from_node_id}")
        if to_node_id not in self._node_by_id:
            raise ValueError(f"Unknown to node: {to_node_id}")

        if edge_id is None:
            edge_id = self.id_allocator.reserve_edge_id(from_node_id, to_node_id)
        else:
            self.id_allocator.reserve_existing_edge_id(edge_id)

        from_node = self._node_by_id[from_node_id]
        to_node = self._node_by_id[to_node_id]
        resolved_shape = self.road_shape_service.pick_for_positions(
            from_node.x,
            from_node.y,
            to_node.x,
            to_node.y,
            road_shape,
        )
        edge = RouteEdgeModel(
            id=edge_id,
            fromNodeID=from_node_id,
            toNodeID=to_node_id,
            roadShape=resolved_shape,
        )
        self._edges.append(edge)
        from_node.outgoingEdgeIDs.append(edge.id)
        return edge

    def build_level_document(
        self,
        level_id: str,
        name: str,
        start_node_id: str,
        package_node_id: str,
        destination_node_id: str,
        time_limit_seconds: int,
        par_taps: int,
    ) -> LevelDocument:
        return LevelDocument(
            id=level_id,
            name=name,
            graph=RouteGraphModel(nodes=list(self._nodes), edges=list(self._edges)),
            startNodeID=start_node_id,
            packageNodeID=package_node_id,
            destinationNodeID=destination_node_id,
            timeLimitSeconds=time_limit_seconds,
            parTaps=par_taps,
        )
