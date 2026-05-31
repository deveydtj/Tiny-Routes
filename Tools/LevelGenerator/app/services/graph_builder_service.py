from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product

from ..id_allocator import IDAllocator
from ..level_editor_imports import LevelDocument, RouteEdgeModel, RouteGraphModel, RouteNodeModel
from .road_shape_service import RoadShapeService
from .route_timing_service import RouteTimingService


@dataclass
class GraphBuilderService:
    id_allocator: IDAllocator = field(default_factory=IDAllocator)
    road_shape_service: RoadShapeService = field(default_factory=RoadShapeService)
    route_timing_service: RouteTimingService = field(default_factory=RouteTimingService)

    def __post_init__(self) -> None:
        self._nodes: list[RouteNodeModel] = []
        self._edges: list[RouteEdgeModel] = []
        self._node_by_id: dict[str, RouteNodeModel] = {}
        self._explicit_road_shape_edge_ids: set[str] = set()

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
        if road_shape is not None:
            self._explicit_road_shape_edge_ids.add(edge_id)
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
        self._resolve_switch_visual_road_shapes()
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

    def _resolve_switch_visual_road_shapes(self) -> None:
        edge_by_id = {edge.id: edge for edge in self._edges}
        for node in self._nodes:
            valid_edges = [
                edge_by_id[edge_id]
                for edge_id in node.outgoingEdgeIDs
                if edge_id in edge_by_id and edge_by_id[edge_id].fromNodeID == node.id
            ]
            if len(valid_edges) < 2 or len(valid_edges) > 4:
                continue

            fixed_shapes: dict[str, str] = {}
            flexible_edges: list[RouteEdgeModel] = []
            for edge in valid_edges:
                if edge.id in self._explicit_road_shape_edge_ids:
                    fixed_shapes[edge.id] = edge.roadShape
                else:
                    flexible_edges.append(edge)

            best_assignment = self._best_clear_shape_assignment(node, valid_edges, fixed_shapes, flexible_edges)
            if best_assignment is None:
                continue

            for edge in flexible_edges:
                edge.roadShape = best_assignment[edge.id]

    def _best_clear_shape_assignment(
        self,
        node: RouteNodeModel,
        valid_edges: list[RouteEdgeModel],
        fixed_shapes: dict[str, str],
        flexible_edges: list[RouteEdgeModel],
    ) -> dict[str, str] | None:
        if not flexible_edges:
            return None

        original_shapes = {edge.id: edge.roadShape for edge in flexible_edges}
        best_assignment: dict[str, str] | None = None
        best_change_count: int | None = None
        for shape_options in product(sorted(self.road_shape_service.ALLOWED_VALUES), repeat=len(flexible_edges)):
            assignment = dict(fixed_shapes)
            assignment.update(
                {
                    edge.id: shape
                    for edge, shape in zip(flexible_edges, shape_options)
                }
            )
            buckets = [
                self._visual_bucket_for_edge(node, edge, assignment[edge.id])
                for edge in valid_edges
            ]
            if any(bucket is None for bucket in buckets) or len(set(buckets)) != len(buckets):
                continue

            if best_assignment is None:
                best_assignment = assignment
                best_change_count = sum(
                    1
                    for edge in flexible_edges
                    if assignment[edge.id] != original_shapes[edge.id]
                )
                continue

            change_count = sum(
                1
                for edge in flexible_edges
                if assignment[edge.id] != original_shapes[edge.id]
            )
            if best_change_count is None or change_count < best_change_count:
                best_assignment = assignment
                best_change_count = change_count

        return best_assignment

    def _visual_bucket_for_edge(self, node: RouteNodeModel, edge: RouteEdgeModel, road_shape: str) -> str | None:
        target = self._node_by_id.get(edge.toNodeID)
        if target is None:
            return None
        try:
            angle = self.route_timing_service.direction_angle(node, target, road_shape)
        except ValueError:
            return None
        return self.route_timing_service.direction_label(angle)
