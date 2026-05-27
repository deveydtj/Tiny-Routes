from __future__ import annotations

import math
from typing import Any


class RouteTimingService:
    standard_turn_radius = 0.18
    _supported_shapes = {None, "horizontalFirst", "verticalFirst"}
    _direction_labels = {
        0.0: "east",
        -math.pi / 2: "north",
        math.pi: "west",
        math.pi / 2: "south",
    }

    def edge_length(self, from_node, to_node, road_shape: str | None) -> float:
        from_x, from_y = self._point(from_node)
        to_x, to_y = self._point(to_node)
        dx = to_x - from_x
        dy = to_y - from_y

        if dx == 0 or dy == 0:
            return math.hypot(dx, dy)

        turn_radius = min(self.standard_turn_radius, abs(dx) / 2, abs(dy) / 2)
        if turn_radius <= 0:
            return 0.0

        resolved_shape = self._resolve_shape(road_shape)
        if resolved_shape == "horizontalFirst":
            first_straight = max(abs(dx) - turn_radius, 0.0)
            final_straight = max(abs(dy) - turn_radius, 0.0)
            signed_angle_delta = self._x_direction(dx) * self._y_direction(dy) * math.pi / 2
        else:
            first_straight = max(abs(dy) - turn_radius, 0.0)
            final_straight = max(abs(dx) - turn_radius, 0.0)
            signed_angle_delta = -self._x_direction(dx) * self._y_direction(dy) * math.pi / 2

        return first_straight + (abs(signed_angle_delta) * turn_radius) + final_straight

    def route_arrival_times(
        self,
        route_node_ids: list[str],
        positions: dict[str, tuple[float, float]],
        edges_by_route_pair: dict[tuple[str, str], str | None] | None = None,
    ) -> list[float]:
        if not route_node_ids:
            return []

        arrival_times = [0.0]
        elapsed = 0.0
        for from_node_id, to_node_id in zip(route_node_ids, route_node_ids[1:]):
            elapsed += self.edge_length(
                positions[from_node_id],
                positions[to_node_id],
                (edges_by_route_pair or {}).get((from_node_id, to_node_id)),
            )
            arrival_times.append(elapsed)
        return arrival_times

    def direction_angle(self, from_node, to_node, road_shape: str | None) -> float:
        from_x, from_y = self._point(from_node)
        to_x, to_y = self._point(to_node)
        dx = to_x - from_x
        dy = to_y - from_y
        resolved_shape = self._resolve_shape(road_shape)

        if dx == 0 and dy == 0:
            return 0.0

        tangent_x = dx
        tangent_y = dy
        if dx != 0 and dy != 0:
            if resolved_shape == "horizontalFirst":
                tangent_x = self._x_direction(dx)
                tangent_y = 0.0
            else:
                tangent_x = 0.0
                tangent_y = self._y_direction(dy)

        if abs(tangent_x) < 1e-9 and abs(tangent_y) < 1e-9:
            tangent_x = dx
            tangent_y = dy

        return self._snapped_axis_angle(tangent_x, tangent_y)

    def direction_label(self, angle: float) -> str:
        normalized = self._normalized_angle(angle)
        return min(
            self._direction_labels.items(),
            key=lambda item: abs(self._normalized_angle(normalized - item[0])),
        )[1]

    def angles_match(self, first: float, second: float, tolerance: float = 0.001) -> bool:
        return abs(self._normalized_angle(first - second)) <= tolerance

    def _resolve_shape(self, road_shape: str | None) -> str:
        if road_shape not in self._supported_shapes:
            raise ValueError(f"Invalid roadShape: {road_shape}")
        return road_shape or "horizontalFirst"

    def _point(self, node: Any) -> tuple[float, float]:
        if isinstance(node, tuple) and len(node) == 2:
            return float(node[0]), float(node[1])
        if isinstance(node, dict):
            return float(node["x"]), float(node["y"])
        return float(node.x), float(node.y)

    def _snapped_axis_angle(self, x: float, y: float) -> float:
        if abs(x) >= abs(y):
            return 0.0 if x >= 0 else math.pi
        return -math.pi / 2 if y >= 0 else math.pi / 2

    def _normalized_angle(self, angle: float) -> float:
        normalized = angle
        while normalized <= -math.pi:
            normalized += 2 * math.pi
        while normalized > math.pi:
            normalized -= 2 * math.pi
        return normalized

    def _x_direction(self, dx: float) -> float:
        return 1.0 if dx > 0 else -1.0

    def _y_direction(self, dy: float) -> float:
        return 1.0 if dy > 0 else -1.0
