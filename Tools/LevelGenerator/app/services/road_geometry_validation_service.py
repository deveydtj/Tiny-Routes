from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

from ..models.difficulty_preset import DifficultyPreset
from .road_shape_service import RoadShapeService


RoadGeometrySeverity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class RoadGeometryIssue:
    severity: RoadGeometrySeverity
    code: str
    message: str
    related_node_id: str | None = None
    related_edge_id: str | None = None
    related_edge_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RoadGeometryReport:
    issues: tuple[RoadGeometryIssue, ...]
    metadata: dict

    @property
    def errors(self) -> tuple[RoadGeometryIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


@dataclass(frozen=True)
class _SegmentRef:
    edge_id: str
    from_node_id: str
    to_node_id: str
    start: tuple[float, float]
    end: tuple[float, float]
    index: int
    required_path_edge: bool


class RoadGeometryValidationService:
    MIN_NON_ADJACENT_SEGMENT_SPACING = 0.18
    MIN_RETURN_LOOP_CORRIDOR_SPACING = 0.28
    point_tolerance = 1e-9
    _minimum_loop_area = 0.45
    _minimum_loop_fill_ratio = 0.42
    _circle_aspect_ratio_range = (0.55, 1.80)
    _parallel_overlap_minimum = 0.12

    def __init__(self) -> None:
        self.road_shape_service = RoadShapeService()

    def report_for_generated_level(
        self,
        generated_level,
        preset: DifficultyPreset | None = None,
    ) -> RoadGeometryReport:
        required_path = tuple(getattr(getattr(generated_level, "abstract_solution_metadata", None), "required_path", ()) or ())
        if not required_path:
            required_path = self._required_path_from_solution(generated_level.solution)
        return self.report_for_level(generated_level.level_document, required_path=required_path, preset=preset)

    def report_for_level(
        self,
        level,
        *,
        required_path: tuple[str, ...] = (),
        preset: DifficultyPreset | None = None,
    ) -> RoadGeometryReport:
        positions = {node.id: (float(node.x), float(node.y)) for node in level.graph.nodes}
        edge_by_pair = {
            (edge.fromNodeID, edge.toNodeID): edge
            for edge in level.graph.edges
        }
        required_edge_pairs = set(zip(required_path, required_path[1:]))
        required_edge_ids = {
            edge.id
            for edge in level.graph.edges
            if (edge.fromNodeID, edge.toNodeID) in required_edge_pairs
        }
        segments = self._segments_for_level(level, positions, required_edge_ids)
        segments_by_edge_id: dict[str, list[_SegmentRef]] = {}
        for segment in segments:
            segments_by_edge_id.setdefault(segment.edge_id, []).append(segment)

        issues: list[RoadGeometryIssue] = []
        issues.extend(self._non_adjacent_spacing_issues(segments, preset))
        issues.extend(
            self._revisited_route_issues(
                required_path,
                positions,
                edge_by_pair,
                segments_by_edge_id,
                preset,
            )
        )

        deduped_issues = tuple(dict.fromkeys(issues))
        return RoadGeometryReport(
            issues=deduped_issues,
            metadata={
                "requiredPath": list(required_path),
                "segmentCount": len(segments),
                "issueCounts": dict(Counter(issue.code for issue in deduped_issues)),
            },
        )

    def _segments_for_level(
        self,
        level,
        positions: dict[str, tuple[float, float]],
        required_edge_ids: set[str],
    ) -> tuple[_SegmentRef, ...]:
        segments: list[_SegmentRef] = []
        for edge in level.graph.edges:
            if edge.fromNodeID not in positions or edge.toNodeID not in positions:
                continue
            if not self.road_shape_service.is_allowed(edge.roadShape):
                continue
            edge_segments = self.road_shape_service._segments_for_edge(
                positions[edge.fromNodeID],
                positions[edge.toNodeID],
                edge.roadShape,
            )
            for index, (start, end) in enumerate(edge_segments):
                segments.append(
                    _SegmentRef(
                        edge_id=edge.id,
                        from_node_id=edge.fromNodeID,
                        to_node_id=edge.toNodeID,
                        start=start,
                        end=end,
                        index=index,
                        required_path_edge=edge.id in required_edge_ids,
                    )
                )
        return tuple(segments)

    def _non_adjacent_spacing_issues(
        self,
        segments: tuple[_SegmentRef, ...],
        preset: DifficultyPreset | None,
    ) -> list[RoadGeometryIssue]:
        issues: list[RoadGeometryIssue] = []
        minimum_spacing = self._non_adjacent_spacing(preset)
        emitted_pairs: set[tuple[str, str]] = set()

        for first_index, first in enumerate(segments):
            for second in segments[first_index + 1:]:
                if first.edge_id == second.edge_id:
                    continue
                if {first.from_node_id, first.to_node_id} & {second.from_node_id, second.to_node_id}:
                    continue
                if not self._should_compare_non_adjacent_segments(first, second):
                    continue
                if self._segments_distance((first.start, first.end), (second.start, second.end)) + self.point_tolerance >= minimum_spacing:
                    continue
                pair_key = tuple(sorted((first.edge_id, second.edge_id)))
                if pair_key in emitted_pairs:
                    continue
                emitted_pairs.add(pair_key)
                issues.append(
                    RoadGeometryIssue(
                        severity="error",
                        code="non_adjacent_roads_too_close",
                        message=(
                            f"Edges '{first.edge_id}' and '{second.edge_id}' have non-adjacent "
                            "road corridors that are too close together."
                        ),
                        related_edge_id=first.edge_id,
                        related_edge_ids=(first.edge_id, second.edge_id),
                    )
                )
        return issues

    def _should_compare_non_adjacent_segments(self, first: _SegmentRef, second: _SegmentRef) -> bool:
        if first.required_path_edge or second.required_path_edge:
            return True
        first_segment = (first.start, first.end)
        second_segment = (second.start, second.end)
        return (
            self._segments_are_parallel(first_segment, second_segment)
            and self._projection_overlap_length(first_segment, second_segment) > self._parallel_overlap_minimum
        )

    def _revisited_route_issues(
        self,
        required_path: tuple[str, ...],
        positions: dict[str, tuple[float, float]],
        edge_by_pair: dict[tuple[str, str], object],
        segments_by_edge_id: dict[str, list[_SegmentRef]],
        preset: DifficultyPreset | None,
    ) -> list[RoadGeometryIssue]:
        if len(required_path) < 4 or len(set(required_path)) == len(required_path):
            return []

        issues: list[RoadGeometryIssue] = []
        repeated_node_ids = [
            node_id
            for node_id, count in Counter(required_path).items()
            if count > 1 and node_id in positions
        ]
        emitted: set[tuple[str, str, str]] = set()

        for repeated_node_id in repeated_node_ids:
            repeated_indexes = [
                index
                for index, node_id in enumerate(required_path)
                if node_id == repeated_node_id
            ]
            for first_occurrence, repeated_index in zip(repeated_indexes, repeated_indexes[1:]):
                if repeated_index <= first_occurrence + 1:
                    continue
                cycle_edges = [
                    edge_by_pair.get((from_node_id, to_node_id))
                    for from_node_id, to_node_id in zip(required_path[first_occurrence:repeated_index], required_path[first_occurrence + 1:repeated_index + 1])
                ]
                cycle_edges = [edge for edge in cycle_edges if edge is not None]
                if len(cycle_edges) < 3:
                    continue

                circle_issue = self._visual_circle_issue(
                    repeated_node_id,
                    first_occurrence,
                    repeated_index,
                    required_path,
                    edge_by_pair,
                    segments_by_edge_id,
                    preset,
                )
                if circle_issue is not None and (circle_issue.code, repeated_node_id, str(repeated_index)) not in emitted:
                    emitted.add((circle_issue.code, repeated_node_id, str(repeated_index)))
                    issues.append(circle_issue)

                return_edge = edge_by_pair.get((required_path[repeated_index - 1], repeated_node_id))
                if return_edge is None:
                    continue
                previous_route_edge = (
                    edge_by_pair.get((required_path[repeated_index - 2], required_path[repeated_index - 1]))
                    if repeated_index >= 2
                    else None
                )
                return_segments = tuple(segments_by_edge_id.get(return_edge.id, ()))
                ignored_return_nodes = tuple(
                    positions[node_id]
                    for node_id in (required_path[repeated_index - 1], repeated_node_id)
                    if node_id in positions
                )
                for edge in cycle_edges:
                    if edge.id == return_edge.id or (previous_route_edge is not None and edge.id == previous_route_edge.id):
                        continue
                    other_segments = tuple(segments_by_edge_id.get(edge.id, ()))
                    if not other_segments:
                        continue
                    if self._segment_sets_too_close(
                        return_segments,
                        other_segments,
                        self._return_loop_spacing(preset),
                        ignored_return_nodes,
                    ):
                        key = ("revisited_switch_corridor_too_tight", return_edge.id, edge.id)
                        if key not in emitted:
                            emitted.add(key)
                            issues.append(
                                RoadGeometryIssue(
                                    severity="error",
                                    code="revisited_switch_corridor_too_tight",
                                    message=(
                                        f"Return edge '{return_edge.id}' comes too close to edge '{edge.id}' "
                                        f"while revisiting switch '{repeated_node_id}'."
                                    ),
                                    related_node_id=repeated_node_id,
                                    related_edge_id=return_edge.id,
                                    related_edge_ids=(return_edge.id, edge.id),
                                )
                            )
                        break

                if repeated_index + 1 < len(required_path):
                    destination_edge = edge_by_pair.get((repeated_node_id, required_path[repeated_index + 1]))
                    if destination_edge is not None:
                        destination_segments = tuple(segments_by_edge_id.get(destination_edge.id, ()))
                        if self._return_path_too_close_to_destination_branch(
                            return_segments,
                            destination_segments,
                            positions[repeated_node_id],
                            preset,
                        ):
                            key = ("return_path_too_close_to_destination_branch", return_edge.id, destination_edge.id)
                            if key not in emitted:
                                emitted.add(key)
                                issues.append(
                                    RoadGeometryIssue(
                                        severity="error",
                                        code="return_path_too_close_to_destination_branch",
                                        message=(
                                            f"Return edge '{return_edge.id}' visually crowds destination edge "
                                            f"'{destination_edge.id}' at revisited switch '{repeated_node_id}'."
                                        ),
                                        related_node_id=repeated_node_id,
                                        related_edge_id=return_edge.id,
                                        related_edge_ids=(return_edge.id, destination_edge.id),
                                    )
                                )
        return issues

    def _visual_circle_issue(
        self,
        repeated_node_id: str,
        first_occurrence: int,
        repeated_index: int,
        required_path: tuple[str, ...],
        edge_by_pair: dict[tuple[str, str], object],
        segments_by_edge_id: dict[str, list[_SegmentRef]],
        preset: DifficultyPreset | None,
    ) -> RoadGeometryIssue | None:
        polyline = self._route_polyline_points(
            required_path[first_occurrence:repeated_index + 1],
            edge_by_pair,
            segments_by_edge_id,
        )
        if len(polyline) < 5:
            return None

        area = abs(self._polygon_area(polyline))
        min_x, max_x, min_y, max_y = self._bounds(polyline)
        width = max_x - min_x
        height = max_y - min_y
        if width <= self.point_tolerance or height <= self.point_tolerance:
            return None

        fill_ratio = area / (width * height)
        aspect_ratio = max(width / height, height / width)
        min_area = self._loop_area_threshold(preset)
        min_aspect, max_aspect = self._circle_aspect_ratio_range
        if area < min_area or fill_ratio < self._minimum_loop_fill_ratio or not (min_aspect <= aspect_ratio <= max_aspect):
            return None

        return RoadGeometryIssue(
            severity="error",
            code="road_visually_circles_back_on_itself",
            message=(
                f"Required route revisits '{repeated_node_id}' with a compact enclosed road loop "
                f"(area {area:.2f}, aspect {aspect_ratio:.2f})."
            ),
            related_node_id=repeated_node_id,
        )

    def _return_path_too_close_to_destination_branch(
        self,
        return_segments: tuple[_SegmentRef, ...],
        destination_segments: tuple[_SegmentRef, ...],
        repeated_position: tuple[float, float],
        preset: DifficultyPreset | None,
    ) -> bool:
        if not return_segments or not destination_segments:
            return False
        minimum_spacing = self._return_loop_spacing(preset)
        if self._segment_sets_too_close(return_segments, destination_segments, minimum_spacing, (repeated_position,)):
            return True

        return_terminal = min(
            return_segments,
            key=lambda segment: self._point_distance(segment.end, repeated_position),
        )
        destination_initial = min(
            destination_segments,
            key=lambda segment: self._point_distance(segment.start, repeated_position),
        )
        return self._segments_leave_revisited_switch_in_parallel(
            (return_terminal.start, return_terminal.end),
            (destination_initial.start, destination_initial.end),
            repeated_position,
            minimum_spacing,
        )

    def _segments_leave_revisited_switch_in_parallel(
        self,
        return_segment: tuple[tuple[float, float], tuple[float, float]],
        destination_segment: tuple[tuple[float, float], tuple[float, float]],
        repeated_position: tuple[float, float],
        minimum_spacing: float,
    ) -> bool:
        if not self._segments_are_parallel(return_segment, destination_segment):
            return False
        if self._point_to_segment_distance(repeated_position, return_segment) > self.point_tolerance:
            return False
        if self._point_to_segment_distance(repeated_position, destination_segment) > self.point_tolerance:
            return False
        if self._segments_are_collinear(return_segment, destination_segment):
            return True
        return self._segments_distance(return_segment, destination_segment) < minimum_spacing

    def _segment_sets_too_close(
        self,
        first_segments: tuple[_SegmentRef, ...],
        second_segments: tuple[_SegmentRef, ...],
        minimum_spacing: float,
        ignored_node_positions: tuple[tuple[float, float], ...],
    ) -> bool:
        for first in first_segments:
            for second in second_segments:
                if first.edge_id == second.edge_id:
                    continue
                if self._segment_clearance_away_from_nodes(
                    (first.start, first.end),
                    (second.start, second.end),
                    ignored_node_positions,
                    minimum_spacing,
                ) < minimum_spacing:
                    return True
                if (
                    self._segments_are_parallel((first.start, first.end), (second.start, second.end))
                    and self._projection_overlap_length((first.start, first.end), (second.start, second.end)) > self._parallel_overlap_minimum
                    and self._segments_distance((first.start, first.end), (second.start, second.end)) < minimum_spacing
                ):
                    return True
        return False

    def _segment_clearance_away_from_nodes(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
        ignored_node_positions: tuple[tuple[float, float], ...],
        ignored_radius: float,
    ) -> float:
        distances: list[float] = []
        for fraction in (0.0, 0.10, 0.25, 0.50, 0.75, 0.90, 1.0):
            for point, segment in (
                (self._point_at_fraction(first, fraction), second),
                (self._point_at_fraction(second, fraction), first),
            ):
                nearest = self._nearest_point_on_segment(point, segment)
                if self._near_ignored_node(point, ignored_node_positions, ignored_radius) and self._near_ignored_node(nearest, ignored_node_positions, ignored_radius):
                    continue
                distances.append(self._point_distance(point, nearest))
        return min(distances) if distances else math.inf

    def _route_polyline_points(
        self,
        route_nodes: tuple[str, ...],
        edge_by_pair: dict[tuple[str, str], object],
        segments_by_edge_id: dict[str, list[_SegmentRef]],
    ) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for from_node_id, to_node_id in zip(route_nodes, route_nodes[1:]):
            edge = edge_by_pair.get((from_node_id, to_node_id))
            if edge is None:
                continue
            segments = segments_by_edge_id.get(edge.id, [])
            for segment in segments:
                if not points:
                    points.append(segment.start)
                elif not self._points_match(points[-1], segment.start):
                    points.append(segment.start)
                if not self._points_match(points[-1], segment.end):
                    points.append(segment.end)
        return points

    def _required_path_from_solution(self, solution) -> tuple[str, ...]:
        if solution is None:
            return ()
        metadata = getattr(solution, "_extra", {}).get("metadata", {})
        return tuple(metadata.get("solutionRoute", ()) or ())

    def _non_adjacent_spacing(self, preset: DifficultyPreset | None) -> float:
        spacing = self.MIN_NON_ADJACENT_SEGMENT_SPACING
        if preset is not None:
            spacing = max(spacing, preset.minimum_node_distance * 0.75)
            if preset.name in {"tutorial", "easy"}:
                spacing *= 1.10
            elif preset.name == "medium":
                spacing *= 1.05
            elif preset.name in {"hard", "expert"}:
                spacing *= 0.90
        return spacing

    def _return_loop_spacing(self, preset: DifficultyPreset | None) -> float:
        spacing = self.MIN_RETURN_LOOP_CORRIDOR_SPACING
        if preset is not None:
            spacing = max(spacing, preset.minimum_node_distance * 1.15)
            if preset.name in {"tutorial", "easy"}:
                spacing *= 1.10
            elif preset.name == "medium":
                spacing *= 1.05
            elif preset.name in {"hard", "expert"}:
                spacing *= 0.90
        return spacing

    def _loop_area_threshold(self, preset: DifficultyPreset | None) -> float:
        if preset is None or preset.name in {"tutorial", "easy", "medium"}:
            return self._minimum_loop_area
        return self._minimum_loop_area * 1.25

    def _segments_distance(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
    ) -> float:
        if self._segment_intersection_point(first, second) is not None:
            return 0.0
        return min(
            self._point_to_segment_distance(first[0], second),
            self._point_to_segment_distance(first[1], second),
            self._point_to_segment_distance(second[0], first),
            self._point_to_segment_distance(second[1], first),
        )

    def _segment_intersection_point(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
    ) -> tuple[float, float] | None:
        (x1, y1), (x2, y2) = first
        (x3, y3), (x4, y4) = second
        denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denominator) <= self.point_tolerance:
            return None
        px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denominator
        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denominator
        if self._point_on_segment((px, py), first) and self._point_on_segment((px, py), second):
            return (px, py)
        return None

    def _point_on_segment(
        self,
        point: tuple[float, float],
        segment: tuple[tuple[float, float], tuple[float, float]],
    ) -> bool:
        (x, y) = point
        (x1, y1), (x2, y2) = segment
        return (
            min(x1, x2) - self.point_tolerance <= x <= max(x1, x2) + self.point_tolerance
            and min(y1, y2) - self.point_tolerance <= y <= max(y1, y2) + self.point_tolerance
        )

    def _point_to_segment_distance(
        self,
        point: tuple[float, float],
        segment: tuple[tuple[float, float], tuple[float, float]],
    ) -> float:
        nearest = self._nearest_point_on_segment(point, segment)
        return self._point_distance(point, nearest)

    def _nearest_point_on_segment(
        self,
        point: tuple[float, float],
        segment: tuple[tuple[float, float], tuple[float, float]],
    ) -> tuple[float, float]:
        (px, py) = point
        (x1, y1), (x2, y2) = segment
        dx = x2 - x1
        dy = y2 - y1
        if abs(dx) <= self.point_tolerance and abs(dy) <= self.point_tolerance:
            return (x1, y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / ((dx * dx) + (dy * dy))))
        return (x1 + (t * dx), y1 + (t * dy))

    def _segments_are_parallel(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
    ) -> bool:
        first_dx = first[1][0] - first[0][0]
        first_dy = first[1][1] - first[0][1]
        second_dx = second[1][0] - second[0][0]
        second_dy = second[1][1] - second[0][1]
        return abs((first_dx * second_dy) - (first_dy * second_dx)) <= self.point_tolerance

    def _segments_are_collinear(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
    ) -> bool:
        (x1, y1), (x2, y2) = first
        (x3, y3), (x4, y4) = second
        return (
            abs((x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1)) <= self.point_tolerance
            and abs((x2 - x1) * (y4 - y1) - (y2 - y1) * (x4 - x1)) <= self.point_tolerance
        )

    def _projection_overlap_length(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
    ) -> float:
        first_horizontal = abs(first[0][1] - first[1][1]) <= abs(first[0][0] - first[1][0])
        if first_horizontal:
            first_range = sorted((first[0][0], first[1][0]))
            second_range = sorted((second[0][0], second[1][0]))
        else:
            first_range = sorted((first[0][1], first[1][1]))
            second_range = sorted((second[0][1], second[1][1]))
        return max(0.0, min(first_range[1], second_range[1]) - max(first_range[0], second_range[0]))

    def _polygon_area(self, points: list[tuple[float, float]]) -> float:
        if len(points) < 3:
            return 0.0
        area = 0.0
        for first, second in zip(points, [*points[1:], points[0]]):
            area += (first[0] * second[1]) - (second[0] * first[1])
        return area / 2.0

    def _bounds(self, points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        return min(xs), max(xs), min(ys), max(ys)

    def _point_at_fraction(
        self,
        segment: tuple[tuple[float, float], tuple[float, float]],
        fraction: float,
    ) -> tuple[float, float]:
        start, end = segment
        return (start[0] + ((end[0] - start[0]) * fraction), start[1] + ((end[1] - start[1]) * fraction))

    def _near_ignored_node(
        self,
        point: tuple[float, float],
        ignored_node_positions: tuple[tuple[float, float], ...],
        ignored_radius: float,
    ) -> bool:
        return any(self._point_distance(point, node_position) <= ignored_radius for node_position in ignored_node_positions)

    def _point_distance(self, first: tuple[float, float], second: tuple[float, float]) -> float:
        return math.hypot(first[0] - second[0], first[1] - second[1])

    def _points_match(self, first: tuple[float, float], second: tuple[float, float]) -> bool:
        return self._point_distance(first, second) <= self.point_tolerance
