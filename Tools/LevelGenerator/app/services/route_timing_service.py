from __future__ import annotations

import math
from dataclasses import dataclass
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
        return self.road_path(from_node, to_node, road_shape).total_length

    def road_path(self, from_node, to_node, road_shape: str | None) -> "_RoadPath":
        from_x, from_y = self._point(from_node)
        to_x, to_y = self._point(to_node)
        dx = to_x - from_x
        dy = to_y - from_y

        if dx == 0 or dy == 0:
            return _RoadPath((_RoadSegment.straight(_Point(from_x, from_y), _Point(to_x, to_y)),))

        turn_radius = min(self.standard_turn_radius, abs(dx) / 2, abs(dy) / 2)
        if turn_radius <= 0:
            return _RoadPath(())

        resolved_shape = self._resolve_shape(road_shape)
        if resolved_shape == "horizontalFirst":
            return self._make_horizontal_first_path(
                _Point(from_x, from_y),
                _Point(to_x, to_y),
                turn_radius,
            )
        return self._make_vertical_first_path(
            _Point(from_x, from_y),
            _Point(to_x, to_y),
            turn_radius,
        )

    def perpendicular_connector(
        self,
        incoming_from_node,
        incoming_to_node,
        incoming_road_shape: str | None,
        outgoing_from_node,
        outgoing_to_node,
        outgoing_road_shape: str | None,
        max_trim_distance: float | None = None,
    ) -> "_PerpendicularConnector | None":
        incoming_path = self.road_path(incoming_from_node, incoming_to_node, incoming_road_shape)
        outgoing_path = self.road_path(outgoing_from_node, outgoing_to_node, outgoing_road_shape)
        incoming_length = incoming_path.total_length
        outgoing_length = outgoing_path.total_length
        if incoming_length <= 0 or outgoing_length <= 0:
            return None

        trim_distance = min(max_trim_distance or self.standard_turn_radius, incoming_length / 2, outgoing_length / 2)
        if trim_distance <= 0:
            return None

        entry_distance = incoming_length - trim_distance
        exit_distance = trim_distance
        incoming = incoming_path.tangent_at_distance(entry_distance)
        outgoing = outgoing_path.tangent_at_distance(exit_distance)
        dot_product = (incoming.x * outgoing.x) + (incoming.y * outgoing.y)
        cross_product = (incoming.x * outgoing.y) - (incoming.y * outgoing.x)
        if abs(dot_product) >= 0.35 or abs(cross_product) <= 0.7:
            return None

        start = incoming_path.point_at_distance(entry_distance)
        end = outgoing_path.point_at_distance(exit_distance)
        chord_length = math.hypot(end.x - start.x, end.y - start.y)
        if chord_length <= 0:
            return None

        control_distance = min(trim_distance * 0.552_284_749_8, chord_length * 0.6)
        control1 = _Point(
            start.x + (incoming.x * control_distance),
            start.y + (incoming.y * control_distance),
        )
        control2 = _Point(
            end.x - (outgoing.x * control_distance),
            end.y - (outgoing.y * control_distance),
        )

        return _PerpendicularConnector(
            length=_RoadSegment.smooth_turn(start, control1, control2, end).length,
            entry_distance_along_incoming_path=entry_distance,
            exit_distance_along_outgoing_path=exit_distance,
        )

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

    def _make_horizontal_first_path(self, start: "_Point", end: "_Point", turn_radius: float) -> "_RoadPath":
        x_direction = self._x_direction(end.x - start.x)
        y_direction = self._y_direction(end.y - start.y)
        corner = _Point(end.x, start.y)
        arc_start = _Point(corner.x - (x_direction * turn_radius), start.y)
        arc_end = _Point(corner.x, start.y + (y_direction * turn_radius))
        center = _Point(arc_start.x, arc_end.y)
        start_angle = -math.pi / 2 if y_direction > 0 else math.pi / 2
        signed_angle_delta = x_direction * y_direction * math.pi / 2

        return _RoadPath((
            _RoadSegment.straight(start, arc_start),
            _RoadSegment.quarter_turn(arc_start, arc_end, center, turn_radius, start_angle, signed_angle_delta),
            _RoadSegment.straight(arc_end, end),
        ))

    def _make_vertical_first_path(self, start: "_Point", end: "_Point", turn_radius: float) -> "_RoadPath":
        x_direction = self._x_direction(end.x - start.x)
        y_direction = self._y_direction(end.y - start.y)
        corner = _Point(start.x, end.y)
        arc_start = _Point(start.x, corner.y - (y_direction * turn_radius))
        arc_end = _Point(start.x + (x_direction * turn_radius), corner.y)
        center = _Point(arc_end.x, arc_start.y)
        start_angle = math.pi if x_direction > 0 else 0.0
        signed_angle_delta = -x_direction * y_direction * math.pi / 2

        return _RoadPath((
            _RoadSegment.straight(start, arc_start),
            _RoadSegment.quarter_turn(arc_start, arc_end, center, turn_radius, start_angle, signed_angle_delta),
            _RoadSegment.straight(arc_end, end),
        ))


@dataclass(frozen=True)
class _Point:
    x: float
    y: float


@dataclass(frozen=True)
class _Vector:
    x: float
    y: float


@dataclass(frozen=True)
class _PerpendicularConnector:
    length: float
    entry_distance_along_incoming_path: float
    exit_distance_along_outgoing_path: float


@dataclass(frozen=True)
class _RoadPath:
    segments: tuple["_RoadSegment", ...]

    @property
    def total_length(self) -> float:
        return sum(segment.length for segment in self.segments)

    def point_at_distance(self, distance: float) -> _Point:
        if not self.segments:
            return _Point(0.0, 0.0)
        remaining_distance = max(0.0, min(distance, self.total_length))
        for segment in self.segments:
            if remaining_distance <= segment.length:
                return segment.point_at_distance(remaining_distance)
            remaining_distance -= segment.length
        return self.segments[-1].end

    def tangent_at_distance(self, distance: float) -> _Vector:
        if not self.segments:
            return _Vector(0.0, 0.0)
        remaining_distance = max(0.0, min(distance, self.total_length))
        for segment in self.segments:
            if remaining_distance <= segment.length:
                return segment.tangent_at_distance(remaining_distance)
            remaining_distance -= segment.length
        return self.segments[-1].tangent_at_distance(self.segments[-1].length)


@dataclass(frozen=True)
class _RoadSegment:
    kind: str
    start: _Point
    end: _Point
    center: _Point | None = None
    control1: _Point | None = None
    control2: _Point | None = None
    radius: float = 0.0
    start_angle: float = 0.0
    signed_angle_delta: float = 0.0

    @classmethod
    def straight(cls, start: _Point, end: _Point) -> "_RoadSegment":
        return cls(kind="straight", start=start, end=end)

    @classmethod
    def quarter_turn(
        cls,
        start: _Point,
        end: _Point,
        center: _Point,
        radius: float,
        start_angle: float,
        signed_angle_delta: float,
    ) -> "_RoadSegment":
        return cls(
            kind="quarterTurn",
            start=start,
            end=end,
            center=center,
            radius=radius,
            start_angle=start_angle,
            signed_angle_delta=signed_angle_delta,
        )

    @classmethod
    def smooth_turn(cls, start: _Point, control1: _Point, control2: _Point, end: _Point) -> "_RoadSegment":
        return cls(kind="smoothTurn", start=start, end=end, control1=control1, control2=control2)

    @property
    def length(self) -> float:
        if self.kind == "straight":
            return math.hypot(self.end.x - self.start.x, self.end.y - self.start.y)
        if self.kind == "quarterTurn":
            return abs(self.signed_angle_delta) * self.radius
        return self._approximate_cubic_length()

    def point_at_distance(self, distance: float) -> _Point:
        segment_length = self.length
        clamped_distance = max(0.0, min(distance, segment_length))
        if self.kind == "straight":
            if segment_length <= 0:
                return self.end
            progress = clamped_distance / segment_length
            return _Point(
                self.start.x + ((self.end.x - self.start.x) * progress),
                self.start.y + ((self.end.y - self.start.y) * progress),
            )
        if self.kind == "quarterTurn":
            if self.center is None or self.radius <= 0 or segment_length <= 0:
                return self.end
            progress = clamped_distance / segment_length
            angle = self.start_angle + (self.signed_angle_delta * progress)
            return _Point(
                self.center.x + (math.cos(angle) * self.radius),
                self.center.y + (math.sin(angle) * self.radius),
            )
        if segment_length <= 0:
            return self.end
        return self._cubic_point(clamped_distance / segment_length)

    def tangent_at_distance(self, distance: float) -> _Vector:
        if self.kind == "straight":
            return self._straight_tangent()
        if self.kind == "quarterTurn":
            segment_length = self.length
            clamped_distance = max(0.0, min(distance, segment_length))
            progress = clamped_distance / segment_length if segment_length > 0 else 0.0
            angle = self.start_angle + (self.signed_angle_delta * progress)
            turn_sign = 1.0 if self.signed_angle_delta >= 0 else -1.0
            return _Vector(-math.sin(angle) * turn_sign, math.cos(angle) * turn_sign)

        segment_length = self.length
        if segment_length <= 0 or self.control1 is None or self.control2 is None:
            return self._straight_tangent()
        progress = max(0.0, min(distance, segment_length)) / segment_length
        inverse_progress = 1 - progress
        dx = (
            (3 * inverse_progress * inverse_progress * (self.control1.x - self.start.x))
            + (6 * inverse_progress * progress * (self.control2.x - self.control1.x))
            + (3 * progress * progress * (self.end.x - self.control2.x))
        )
        dy = (
            (3 * inverse_progress * inverse_progress * (self.control1.y - self.start.y))
            + (6 * inverse_progress * progress * (self.control2.y - self.control1.y))
            + (3 * progress * progress * (self.end.y - self.control2.y))
        )
        magnitude = math.hypot(dx, dy)
        if magnitude <= 0:
            return self._straight_tangent()
        return _Vector(dx / magnitude, dy / magnitude)

    def _straight_tangent(self) -> _Vector:
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        magnitude = math.hypot(dx, dy)
        if magnitude <= 0:
            return _Vector(0.0, 0.0)
        return _Vector(dx / magnitude, dy / magnitude)

    def _cubic_point(self, progress: float) -> _Point:
        if self.control1 is None or self.control2 is None:
            return self.point_at_distance(progress * self.length)
        t = max(0.0, min(progress, 1.0))
        inverse_t = 1 - t
        return _Point(
            (self.start.x * inverse_t * inverse_t * inverse_t)
            + (self.control1.x * 3 * inverse_t * inverse_t * t)
            + (self.control2.x * 3 * inverse_t * t * t)
            + (self.end.x * t * t * t),
            (self.start.y * inverse_t * inverse_t * inverse_t)
            + (self.control1.y * 3 * inverse_t * inverse_t * t)
            + (self.control2.y * 3 * inverse_t * t * t)
            + (self.end.y * t * t * t),
        )

    def _approximate_cubic_length(self, sample_count: int = 12) -> float:
        total = 0.0
        previous = self.start
        for index in range(1, sample_count + 1):
            point = self._cubic_point(index / sample_count)
            total += math.hypot(point.x - previous.x, point.y - previous.y)
            previous = point
        return total
