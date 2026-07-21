from __future__ import annotations

from collections import deque

from ..models.graph_recipe import GraphRecipe
from ..models.layout_constraints import ConstraintViolation, ReservedIconClearance
from ..models.layout_graph import GridCell, Lane, LayoutGraph
from ..models.layout_result import LayerAssignment, LayoutLayerResult
from .stateful_hub_spacing_service import StatefulHubSpacingService


class LayoutLayerService:
    """Assign deterministic portrait layers and lanes before coordinate placement."""

    def assign_layers(self, recipe: GraphRecipe) -> LayoutLayerResult:
        graph = LayoutGraph.from_recipe(recipe)
        node_ids = {node.node_id for node in graph.nodes}
        if graph.start_node_id not in node_ids or graph.destination_node_id not in node_ids:
            return LayoutLayerResult(
                assignments=(),
                violations=(ConstraintViolation("layout_layer_missing_endpoint", "Start or destination is missing."),),
            )

        primary = self._first_occurrence_route(graph.primary_route)
        layers = {node_id: index for index, node_id in enumerate(primary)}
        lanes = {node_id: 0 for node_id in primary}
        primary_edges = set(zip(primary, primary[1:]))
        outgoing = {node.node_id: node.outgoing_node_ids for node in graph.nodes}

        branch_number = 0
        for source_id in primary:
            for target_id in outgoing.get(source_id, ()):
                if (source_id, target_id) in primary_edges:
                    continue
                branch_number += 1
                branch_lane = ((branch_number + 1) // 2) * (1 if branch_number % 2 else -1)
                self._place_branch(target_id, layers[source_id] + 1, branch_lane, outgoing, layers, lanes)

        # Place disconnected or cycle-only remnants deterministically after their nearest parent.
        incoming = {node.node_id: node.incoming_node_ids for node in graph.nodes}
        pending = deque(sorted(node_ids - layers.keys()))
        while pending:
            node_id = pending.popleft()
            parents = [parent for parent in incoming.get(node_id, ()) if parent in layers]
            if parents:
                parent = min(parents, key=lambda item: (layers[item], item))
                layers[node_id] = layers[parent] + 1
                lanes[node_id] = self._next_free_lane(layers[node_id], layers, lanes)
            else:
                layers[node_id] = max(layers.values(), default=-1) + 1
                lanes[node_id] = self._next_free_lane(layers[node_id], layers, lanes)

        return_edges: list[str] = []
        return_lane = max((abs(lane) for lane in lanes.values()), default=0) + 2
        for edge in graph.edges:
            if layers[edge.to_node_id] <= layers[edge.from_node_id]:
                return_edges.append(edge.edge_id)
                # A cycle travels on an explicit outer lane, never through the primary lane.
                if lanes[edge.from_node_id] == 0 and edge.from_node_id not in {graph.destination_node_id}:
                    lanes[edge.from_node_id] = return_lane

        stateful_clearance_by_node_id = {
            rule.hub_node_id: rule.reserved_clearance
            for rule in StatefulHubSpacingService().rules_for(graph)
        }
        clearances = tuple(
            stateful_clearance_by_node_id.get(
                node.node_id,
                ReservedIconClearance(node.node_id, 2, 2),
            )
            for node in graph.nodes
            if len(node.outgoing_node_ids) >= 3 or node.is_revisited_hub
        )
        assignments = tuple(
            LayerAssignment(node_id, layers[node_id], Lane(lanes[node_id], self._lane_kind(lanes[node_id])), GridCell(lanes[node_id], layers[node_id]))
            for node_id in sorted(node_ids, key=lambda item: (layers[item], lanes[item], item))
        )
        return LayoutLayerResult(assignments, tuple(return_edges), clearances)

    def assignLayers(self, recipe: GraphRecipe) -> LayoutLayerResult:
        return self.assign_layers(recipe)

    def _place_branch(self, node_id, layer, lane, outgoing, layers, lanes) -> None:
        queue = deque([(node_id, layer)])
        visited: set[str] = set()
        while queue:
            current, current_layer = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            if current in layers:
                continue
            layers[current] = current_layer
            lanes[current] = lane
            for target in outgoing.get(current, ()):
                queue.append((target, current_layer + 1))

    def _next_free_lane(self, layer, layers, lanes) -> int:
        occupied = {lanes[node_id] for node_id, node_layer in layers.items() if node_layer == layer}
        for magnitude in range(1, len(occupied) + 2):
            for lane in (magnitude, -magnitude):
                if lane not in occupied:
                    return lane
        return 1

    def _first_occurrence_route(self, route: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        return tuple(node_id for node_id in route if not (node_id in seen or seen.add(node_id)))

    def _lane_kind(self, index: int) -> str:
        return "primary" if index == 0 else "return" if abs(index) >= 2 else "branch"
