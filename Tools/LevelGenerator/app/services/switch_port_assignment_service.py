from __future__ import annotations

import math
from dataclasses import dataclass

from ..models.layout_graph import LayoutGraph, SwitchPortDirection


@dataclass(frozen=True)
class SwitchPortAssignment:
    edge_id: str
    target_node_id: str
    direction: SwitchPortDirection
    clockwise_index: int
    is_initial_route: bool = False


@dataclass(frozen=True)
class SwitchPortAssignmentResult:
    assignments_by_switch: dict[str, tuple[SwitchPortAssignment, ...]]

    @property
    def directions_by_switch(self) -> dict[str, tuple[SwitchPortDirection, ...]]:
        return {
            switch_id: tuple(item.direction for item in assignments)
            for switch_id, assignments in self.assignments_by_switch.items()
        }


class SwitchPortAssignmentService:
    """Assign stable, separated visual ports before road bends are selected."""

    _clockwise = (
        SwitchPortDirection.NORTH,
        SwitchPortDirection.NORTH_EAST,
        SwitchPortDirection.EAST,
        SwitchPortDirection.SOUTH_EAST,
        SwitchPortDirection.SOUTH,
        SwitchPortDirection.SOUTH_WEST,
        SwitchPortDirection.WEST,
        SwitchPortDirection.NORTH_WEST,
    )
    _vectors = {
        SwitchPortDirection.NORTH: (0.0, 1.0),
        SwitchPortDirection.NORTH_EAST: (1.0, 1.0),
        SwitchPortDirection.EAST: (1.0, 0.0),
        SwitchPortDirection.SOUTH_EAST: (1.0, -1.0),
        SwitchPortDirection.SOUTH: (0.0, -1.0),
        SwitchPortDirection.SOUTH_WEST: (-1.0, -1.0),
        SwitchPortDirection.WEST: (-1.0, 0.0),
        SwitchPortDirection.NORTH_WEST: (-1.0, 1.0),
    }

    def assign_ports(
        self,
        graph: LayoutGraph,
        positions: dict[str, tuple[float, float]],
    ) -> SwitchPortAssignmentResult:
        route_edges = set(zip(graph.primary_route, graph.primary_route[1:]))
        result: dict[str, tuple[SwitchPortAssignment, ...]] = {}
        for node in graph.nodes:
            outgoing = [edge for edge in graph.edges if edge.from_node_id == node.node_id]
            if len(outgoing) < 2:
                continue
            source = positions.get(node.node_id)
            if source is None or any(edge.to_node_id not in positions for edge in outgoing):
                continue
            ports = self._ports_for_count(len(outgoing))
            available = list(ports)
            chosen: list[SwitchPortAssignment] = []
            # The route edge gets first choice, then graph edge order provides a stable tie-break.
            ordered = sorted(
                enumerate(outgoing),
                key=lambda item: ((item[1].from_node_id, item[1].to_node_id) not in route_edges, item[0]),
            )
            for _, edge in ordered:
                target = positions[edge.to_node_id]
                direction = max(
                    available,
                    key=lambda port: (self._alignment(source, target, port), -self._clockwise.index(port)),
                )
                available.remove(direction)
                chosen.append(
                    SwitchPortAssignment(
                        edge_id=edge.edge_id,
                        target_node_id=edge.to_node_id,
                        direction=direction,
                        clockwise_index=self._clockwise.index(direction),
                        is_initial_route=(edge.from_node_id, edge.to_node_id) in route_edges,
                    )
                )
            result[node.node_id] = tuple(sorted(chosen, key=lambda item: item.clockwise_index))
        return SwitchPortAssignmentResult(result)

    def assignPorts(self, graph: LayoutGraph, positions: dict[str, tuple[float, float]]) -> SwitchPortAssignmentResult:
        return self.assign_ports(graph, positions)

    def _ports_for_count(self, count: int) -> tuple[SwitchPortDirection, ...]:
        if count == 2:
            return (SwitchPortDirection.NORTH_EAST, SwitchPortDirection.NORTH_WEST)
        if count == 3:
            return (SwitchPortDirection.NORTH, SwitchPortDirection.SOUTH_EAST, SwitchPortDirection.SOUTH_WEST)
        if count == 4:
            return (
                SwitchPortDirection.NORTH,
                SwitchPortDirection.EAST,
                SwitchPortDirection.SOUTH,
                SwitchPortDirection.WEST,
            )
        # Malformed graphs still receive unique deterministic directions up to the visual limit.
        return self._clockwise[: min(count, len(self._clockwise))]

    def _alignment(self, source, target, port: SwitchPortDirection) -> float:
        dx, dy = target[0] - source[0], target[1] - source[1]
        length = math.hypot(dx, dy) or 1.0
        px, py = self._vectors[port]
        port_length = math.hypot(px, py)
        return ((dx / length) * px + (dy / length) * py) / port_length
