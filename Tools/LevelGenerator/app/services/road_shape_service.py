from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from itertools import product
from typing import Any

from .route_timing_service import RouteTimingService
from .switch_direction_assignment_service import SwitchDirectionAssignmentService


@dataclass(frozen=True)
class RoadShapeEdgePlan:
    from_node_id: str
    to_node_id: str
    road_shape: str
    start_direction: str
    end_direction: str
    required_path_edge: bool


@dataclass(frozen=True)
class RoadShapePlan:
    strategy: str
    edge_shapes: dict[tuple[str, str], str]
    edge_plans: tuple[RoadShapeEdgePlan, ...]
    score: float
    issues: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateRoadGeometryPlan:
    edge_shapes: dict[tuple[str, str], str]
    accepted_edge_order: tuple[tuple[str, str], ...]
    violations: tuple[str, ...]
    intentional_intersections: tuple[tuple[float, float], ...]
    reserved_corridors: tuple[tuple[tuple[float, float], tuple[float, float]], ...]


class RoadShapeService:
    ALLOWED_VALUES = {"horizontalFirst", "verticalFirst"}
    _shape_order = ("horizontalFirst", "verticalFirst")
    _point_tolerance = 1e-9
    _merge_distance = 0.16
    _important_node_clearance = 0.18
    _return_loop_false_shortcut_clearance = 0.14

    def __init__(self) -> None:
        self.switch_direction_assignment = SwitchDirectionAssignmentService()

    def pick_for_positions(
        self,
        from_x: float,
        from_y: float,
        to_x: float,
        to_y: float,
        override: str | None = None,
    ) -> str:
        if override is not None:
            if override not in self.ALLOWED_VALUES:
                raise ValueError(f"Invalid roadShape: {override}")
            return override
        horizontal_delta = abs(to_x - from_x)
        vertical_delta = abs(to_y - from_y)
        return "horizontalFirst" if horizontal_delta >= vertical_delta else "verticalFirst"

    def is_allowed(self, road_shape: str | None) -> bool:
        return road_shape in self.ALLOWED_VALUES

    def plan_for_graph(
        self,
        positions: dict[str, tuple[float, float]],
        edges: list[tuple[str, str]],
        *,
        required_path: tuple[str, ...] = (),
        strategy: str = "auto",
        important_node_ids: tuple[str, ...] = (),
    ) -> RoadShapePlan:
        normalized_strategy = self._normalized_strategy(strategy)
        if not edges:
            return RoadShapePlan(
                strategy=normalized_strategy,
                edge_shapes={},
                edge_plans=(),
                score=1.0,
                metadata={"strategy": normalized_strategy},
            )

        for from_node_id, to_node_id in edges:
            if from_node_id not in positions:
                raise ValueError(f"Unknown from node for road-shape planning: {from_node_id}")
            if to_node_id not in positions:
                raise ValueError(f"Unknown to node for road-shape planning: {to_node_id}")

        candidate_assignments = self._candidate_assignments(positions, edges, normalized_strategy)
        scored_plans = [
            self._score_assignment(
                positions,
                edges,
                assignment,
                normalized_strategy,
                required_path,
                important_node_ids,
            )
            for assignment in candidate_assignments
        ]
        return max(scored_plans, key=lambda plan: (plan.score, -len(plan.issues)))

    def build_candidate_geometry(
        self,
        positions: dict[str, tuple[float, float]],
        edges: list[tuple[str, str]],
        *,
        reserved_lanes: dict[tuple[str, str], str] | None = None,
        important_node_ids: tuple[str, ...] = (),
        minimum_clearance: float = 0.18,
    ) -> CandidateRoadGeometryPlan:
        """Choose each bend incrementally while reserving accepted road corridors."""
        shapes: dict[tuple[str, str], str] = {}
        reserved: list[tuple[tuple[float, float], tuple[float, float]]] = []
        reserved_edges: list[tuple[str, str]] = []
        violations: list[str] = []
        intentional: list[tuple[float, float]] = []
        nodes_at = {point: node_id for node_id, point in positions.items()}

        for edge in edges:
            if edge[0] not in positions or edge[1] not in positions:
                raise ValueError(f"Unknown node for candidate road geometry: {edge[0]}->{edge[1]}")
            preferred = (reserved_lanes or {}).get(edge)
            options = [preferred] if preferred in self.ALLOWED_VALUES else []
            options.extend(shape for shape in self._shape_order if shape not in options)
            ranked = []
            for option in options:
                segments = self._segments_for_edge(positions[edge[0]], positions[edge[1]], option)
                conflicts, intersections, node_conflicts = self._incremental_conflicts(
                    edge, segments, reserved_edges, reserved, positions, important_node_ids, minimum_clearance
                )
                ranked.append((conflicts + node_conflicts, len(intersections), option, segments, intersections, node_conflicts))
            _, _, selected, segments, intersections, node_conflicts = min(
                ranked, key=lambda item: (item[0], item[1], options.index(item[2]))
            )
            shapes[edge] = selected
            for point in intersections:
                if point in nodes_at:
                    intentional.append(point)
                else:
                    violations.append(f"implicit_intersection_requires_node:{edge[0]}:{edge[1]}")
            if node_conflicts:
                violations.append(f"road_clearance_from_node:{edge[0]}:{edge[1]}")
            reserved.extend(segments)
            reserved_edges.extend([edge] * len(segments))

        return CandidateRoadGeometryPlan(
            edge_shapes=shapes,
            accepted_edge_order=tuple(edges),
            violations=tuple(dict.fromkeys(violations)),
            intentional_intersections=tuple(dict.fromkeys(intentional)),
            reserved_corridors=tuple(reserved),
        )

    def _incremental_conflicts(
        self, edge, segments, reserved_edges, reserved, positions, important_node_ids, minimum_clearance
    ) -> tuple[int, list[tuple[float, float]], int]:
        conflicts = 0
        intersections: list[tuple[float, float]] = []
        node_conflicts = 0
        for segment in segments:
            for other_edge, other in zip(reserved_edges, reserved):
                if set(edge) & set(other_edge):
                    continue
                point = self._segment_intersection_point(segment, other)
                if point is not None:
                    intersections.append(point)
                    conflicts += 1
                elif self._segments_distance(segment, other) < minimum_clearance:
                    conflicts += 1
            for node_id, point in positions.items():
                if node_id in edge:
                    continue
                clearance = self._important_node_clearance if node_id in important_node_ids else minimum_clearance
                if self._point_to_segment_distance(point, segment) < clearance:
                    node_conflicts += 1
        return conflicts, intersections, node_conflicts

    def plan_for_assignment(
        self,
        positions: dict[str, tuple[float, float]],
        edges: list[tuple[str, str]],
        edge_shapes: dict[tuple[str, str], str],
        *,
        required_path: tuple[str, ...] = (),
        strategy: str = "assigned",
        important_node_ids: tuple[str, ...] = (),
    ) -> RoadShapePlan:
        for edge in edges:
            if edge not in edge_shapes:
                raise ValueError(f"Missing roadShape assignment for edge: {edge[0]}->{edge[1]}")
            if not self.is_allowed(edge_shapes[edge]):
                raise ValueError(f"Invalid roadShape assignment for edge {edge[0]}->{edge[1]}: {edge_shapes[edge]}")
        return self._score_assignment(
            positions,
            edges,
            dict(edge_shapes),
            strategy,
            required_path,
            important_node_ids,
        )

    def _normalized_strategy(self, strategy: str) -> str:
        normalized = strategy.strip().lower().replace("-", "_")
        if normalized in {"", "auto"}:
            return "auto"
        if normalized in {
            "all_straight",
            "horizontal_first",
            "vertical_first",
            "alternating",
            "switch_clarity_optimized",
            "crossing_minimized",
            "main_route_smoothed",
        }:
            return normalized
        raise ValueError(f"Unknown road-shape strategy: {strategy}")

    def _candidate_assignments(
        self,
        positions: dict[str, tuple[float, float]],
        edges: list[tuple[str, str]],
        strategy: str,
    ) -> list[dict[tuple[str, str], str]]:
        if strategy == "horizontal_first":
            return [{edge: "horizontalFirst" for edge in edges}]
        if strategy == "vertical_first":
            return [{edge: "verticalFirst" for edge in edges}]
        if strategy == "alternating":
            return [
                {
                    edge: "horizontalFirst" if index % 2 == 0 else "verticalFirst"
                    for index, edge in enumerate(edges)
                }
            ]

        base = {
            edge: self.pick_for_positions(*positions[edge[0]], *positions[edge[1]])
            for edge in edges
        }
        assignments = [base]
        if strategy == "all_straight":
            return assignments

        if len(edges) <= 9:
            assignments.extend(
                {
                    edge: shape
                    for edge, shape in zip(edges, shape_options)
                }
                for shape_options in product(self._shape_order, repeat=len(edges))
            )
        else:
            switch_edges = self._switch_outgoing_edges(edges)
            flexible_edges = [edge for edge in edges if edge in switch_edges]
            fixed_edges = [edge for edge in edges if edge not in switch_edges]
            if len(flexible_edges) > 8:
                flexible_edges = flexible_edges[:8]
                fixed_edges = [edge for edge in edges if edge not in flexible_edges]
            for shape_options in product(self._shape_order, repeat=len(flexible_edges)):
                assignment = {edge: base[edge] for edge in fixed_edges}
                assignment.update(
                    {
                        edge: shape
                        for edge, shape in zip(flexible_edges, shape_options)
                    }
                )
                assignments.append(assignment)
            for edge in edges:
                assignment = dict(base)
                assignment[edge] = "verticalFirst" if base[edge] == "horizontalFirst" else "horizontalFirst"
                assignments.append(assignment)

        deduped: dict[tuple[tuple[tuple[str, str], str], ...], dict[tuple[str, str], str]] = {}
        for assignment in assignments:
            key = tuple((edge, assignment[edge]) for edge in edges)
            deduped[key] = assignment
        return list(deduped.values())

    def _score_assignment(
        self,
        positions: dict[str, tuple[float, float]],
        edges: list[tuple[str, str]],
        assignment: dict[tuple[str, str], str],
        strategy: str,
        required_path: tuple[str, ...],
        important_node_ids: tuple[str, ...],
    ) -> RoadShapePlan:
        route_timing = RouteTimingService()
        required_edges = set(zip(required_path, required_path[1:]))
        important_nodes = set(important_node_ids)
        outgoing_edges_by_node = self._outgoing_edges_by_node(edges)
        segment_sets = {
            edge: self._segments_for_edge(positions[edge[0]], positions[edge[1]], assignment[edge])
            for edge in edges
        }

        issues: list[str] = []
        edge_plans: list[RoadShapeEdgePlan] = []
        switch_direction_buckets: dict[str, dict[str, str]] = {}
        switch_exit_angle_separation: dict[str, float | None] = {}
        switch_direction_quality_by_switch: dict[str, float] = {}
        direction_bucket_assignments: dict[str, list[dict[str, Any]]] = {}
        endpoint_mismatch_count = 0
        for edge in edges:
            from_node_id, to_node_id = edge
            start_direction = route_timing.direction_label(
                route_timing.direction_angle(positions[from_node_id], positions[to_node_id], assignment[edge])
            )
            end_direction = self._end_direction_label(route_timing, positions[from_node_id], positions[to_node_id], assignment[edge])
            direct_direction = route_timing.direction_label(
                route_timing.direction_angle(positions[from_node_id], positions[to_node_id], None)
            )
            if direct_direction != start_direction and self._is_bent_edge(positions[from_node_id], positions[to_node_id]):
                endpoint_mismatch_count += 1
            edge_plans.append(
                RoadShapeEdgePlan(
                    from_node_id=from_node_id,
                    to_node_id=to_node_id,
                    road_shape=assignment[edge],
                    start_direction=start_direction,
                    end_direction=end_direction,
                    required_path_edge=edge in required_edges,
                )
            )

        edge_plan_by_edge = {
            (plan.from_node_id, plan.to_node_id): plan
            for plan in edge_plans
        }
        for node_id, outgoing_edges in outgoing_edges_by_node.items():
            if len(outgoing_edges) < 2 or len(outgoing_edges) > 4:
                continue
            switch_direction_report = self.switch_direction_assignment.report_for_switch_positions(
                node_id,
                positions,
                [
                    (f"{edge[0]}->{edge[1]}", edge[1], assignment[edge])
                    for edge in outgoing_edges
                ],
            )
            buckets = switch_direction_report.direction_buckets
            switch_direction_buckets[node_id] = buckets
            switch_exit_angle_separation[node_id] = switch_direction_report.minimum_exit_angle_separation_degrees
            switch_direction_quality_by_switch[node_id] = switch_direction_report.quality
            direction_bucket_assignments[node_id] = switch_direction_report.to_metadata()["assignments"]
            issues.extend(switch_direction_report.issues)
            duplicated = [
                bucket
                for bucket, count in Counter(buckets.values()).items()
                if count > 1
            ]
            for bucket in duplicated:
                issues.append(f"switch_choices_same_visual_direction:{node_id}:{bucket}")
            if len(outgoing_edges) == 4 and set(buckets.values()) != {"north", "east", "south", "west"}:
                issues.append(f"four_way_switch_missing_cardinal_exits:{node_id}")
            issues.extend(
                self._same_switch_first_segment_issues(
                    node_id,
                    outgoing_edges,
                    required_edges,
                    segment_sets,
                    edge_plan_by_edge,
                )
            )

        crossing_count, confusing_crossing_count, required_crossing_count = self._crossing_counts(
            positions,
            edges,
            required_edges,
            important_nodes,
            segment_sets,
        )
        long_parallel_count = self._long_parallel_segment_count(edges, segment_sets)
        visual_topology_counts = self._visual_topology_counts(positions, edges, segment_sets)
        important_node_proximity_count = self._important_node_proximity_count(
            positions,
            important_nodes,
            edges,
            segment_sets,
        )
        smooth_break_count = self._main_route_smooth_break_count(required_path, edge_plan_by_edge)
        return_loop_false_shortcut_count = self._return_loop_false_shortcut_count(
            positions,
            required_path,
            segment_sets,
        )

        if confusing_crossing_count:
            issues.append(f"road_crossing_near_important_node:{confusing_crossing_count}")
        if required_crossing_count:
            issues.append(f"required_path_crossing:{required_crossing_count}")
        if long_parallel_count:
            issues.append(f"long_parallel_road_segments:{long_parallel_count}")
        for code, count in visual_topology_counts.items():
            if count:
                issues.append(f"{code}:{count}")
        if important_node_proximity_count:
            issues.append(f"road_segment_too_close_to_important_node:{important_node_proximity_count}")
        if return_loop_false_shortcut_count:
            issues.append(f"return_loop_false_shortcut:{return_loop_false_shortcut_count}")

        switch_direction_quality = min(switch_direction_quality_by_switch.values()) if switch_direction_quality_by_switch else 1.0
        ambiguous_switch_detected = any(
            issue.startswith("ambiguous_switch_exit")
            or issue.startswith("conflicting_direction_bucket")
            or issue.startswith("insufficient_exit_separation")
            or issue.startswith("switch_choices_same_visual_direction")
            or issue.startswith("same_switch_first_segments_overlap")
            for issue in issues
        )
        duplicate_switch_penalty = sum(
            1
            for issue in issues
            if issue.startswith("switch_choices_same_visual_direction")
            or issue.startswith("same_switch_first_segments_overlap")
            or issue.startswith("required_and_wrong_route_first_segments_overlap")
            or issue.startswith("conflicting_direction_bucket")
            or issue.startswith("ambiguous_switch_exit")
            or issue.startswith("insufficient_exit_separation")
        )
        readability_adjustments = self._readability_adjustments(positions, edges, assignment)
        road_shape_warnings = [
            issue
            for issue in issues
            if issue.startswith("long_parallel_road_segments")
            or issue.startswith("return_loop_false_shortcut")
            or issue.startswith("road_segment_too_close_to_important_node")
            or issue.startswith("required_path_crossing")
            or issue.startswith("road_crossing_near_important_node")
        ]
        score = 1.0
        score -= duplicate_switch_penalty * 0.35
        score -= crossing_count * 0.04
        score -= confusing_crossing_count * 0.18
        score -= required_crossing_count * 0.12
        score -= long_parallel_count * 0.10
        score -= visual_topology_counts["implicit_intersection_without_graph_node"] * 0.30
        score -= visual_topology_counts["unconnected_road_endpoint_touches_segment"] * 0.22
        score -= visual_topology_counts["unconnected_parallel_road_overlap"] * 0.18
        score -= visual_topology_counts["road_crosses_through_unconnected_node"] * 0.35
        score -= return_loop_false_shortcut_count * 0.35
        score -= important_node_proximity_count * 0.08
        if strategy == "crossing_minimized":
            score -= crossing_count * 0.05
        if strategy == "main_route_smoothed":
            score -= smooth_break_count * 0.08
        else:
            score -= smooth_break_count * 0.03
        if strategy in {"switch_clarity_optimized", "auto"}:
            score -= endpoint_mismatch_count * 0.01
        score -= (1.0 - switch_direction_quality) * 0.25
        score -= min(len(readability_adjustments), 6) * 0.01
        score = max(0.0, min(1.0, score))

        return RoadShapePlan(
            strategy=strategy,
            edge_shapes=dict(assignment),
            edge_plans=tuple(edge_plans),
            score=round(score, 4),
            issues=tuple(dict.fromkeys(issues)),
            metadata={
                "strategy": strategy,
                "score": round(score, 4),
                "crossingCount": crossing_count,
                "confusingCrossingCount": confusing_crossing_count,
                "requiredPathCrossingCount": required_crossing_count,
                "longParallelSegmentCount": long_parallel_count,
                "visualTopologyIssueCounts": visual_topology_counts,
                "returnLoopFalseShortcutCount": return_loop_false_shortcut_count,
                "importantNodeProximityCount": important_node_proximity_count,
                "mainRouteSmoothBreakCount": smooth_break_count,
                "endpointVectorMismatchCount": endpoint_mismatch_count,
                "switchDirectionBuckets": switch_direction_buckets,
                "switchClarityScore": round(switch_direction_quality, 4),
                "switchDirectionQuality": {
                    "overall": round(switch_direction_quality, 4),
                    "bySwitch": switch_direction_quality_by_switch,
                },
                "switchExitAngleSeparation": switch_exit_angle_separation,
                "ambiguousSwitchDetected": ambiguous_switch_detected,
                "roadShapeWarnings": road_shape_warnings,
                "readabilityAdjustments": readability_adjustments,
                "directionBucketAssignments": direction_bucket_assignments,
                "edgePlans": [
                    {
                        "fromNodeID": plan.from_node_id,
                        "toNodeID": plan.to_node_id,
                        "roadShape": plan.road_shape,
                        "startDirection": plan.start_direction,
                        "endDirection": plan.end_direction,
                        "requiredPathEdge": plan.required_path_edge,
                    }
                    for plan in edge_plans
                ],
                "issues": list(dict.fromkeys(issues)),
            },
        )

    def _switch_outgoing_edges(self, edges: list[tuple[str, str]]) -> set[tuple[str, str]]:
        return {
            edge
            for outgoing_edges in self._outgoing_edges_by_node(edges).values()
            if 2 <= len(outgoing_edges) <= 4
            for edge in outgoing_edges
        }

    def _readability_adjustments(
        self,
        positions: dict[str, tuple[float, float]],
        edges: list[tuple[str, str]],
        assignment: dict[tuple[str, str], str],
    ) -> list[dict[str, str]]:
        adjustments: list[dict[str, str]] = []
        for edge in edges:
            preferred_shape = self.pick_for_positions(*positions[edge[0]], *positions[edge[1]])
            assigned_shape = assignment[edge]
            if assigned_shape == preferred_shape:
                continue
            adjustments.append(
                {
                    "fromNodeID": edge[0],
                    "toNodeID": edge[1],
                    "fromRoadShape": preferred_shape,
                    "toRoadShape": assigned_shape,
                    "reason": "switch_exit_or_route_readability",
                }
            )
        return adjustments

    def _outgoing_edges_by_node(self, edges: list[tuple[str, str]]) -> dict[str, list[tuple[str, str]]]:
        outgoing: dict[str, list[tuple[str, str]]] = {}
        for edge in edges:
            outgoing.setdefault(edge[0], []).append(edge)
        return outgoing

    def _segments_for_edge(
        self,
        from_position: tuple[float, float],
        to_position: tuple[float, float],
        road_shape: str,
    ) -> list[tuple[tuple[float, float], tuple[float, float]]]:
        from_x, from_y = from_position
        to_x, to_y = to_position
        if abs(from_x - to_x) <= self._point_tolerance or abs(from_y - to_y) <= self._point_tolerance:
            return [(from_position, to_position)]
        middle = (to_x, from_y) if road_shape == "horizontalFirst" else (from_x, to_y)
        return [
            segment
            for segment in [(from_position, middle), (middle, to_position)]
            if self._segment_length(segment) > self._point_tolerance
        ]

    def _end_direction_label(
        self,
        route_timing: RouteTimingService,
        from_position: tuple[float, float],
        to_position: tuple[float, float],
        road_shape: str,
    ) -> str:
        segments = self._segments_for_edge(from_position, to_position, road_shape)
        if not segments:
            return route_timing.direction_label(0.0)
        start, end = segments[-1]
        return route_timing.direction_label(route_timing._snapped_axis_angle(end[0] - start[0], end[1] - start[1]))

    def _is_bent_edge(self, from_position: tuple[float, float], to_position: tuple[float, float]) -> bool:
        return (
            abs(from_position[0] - to_position[0]) > self._point_tolerance
            and abs(from_position[1] - to_position[1]) > self._point_tolerance
        )

    def _same_switch_first_segment_issues(
        self,
        node_id: str,
        outgoing_edges: list[tuple[str, str]],
        required_edges: set[tuple[str, str]],
        segment_sets: dict[tuple[str, str], list[tuple[tuple[float, float], tuple[float, float]]]],
        edge_plan_by_edge: dict[tuple[str, str], RoadShapeEdgePlan],
    ) -> list[str]:
        issues: list[str] = []
        for first_index, first_edge in enumerate(outgoing_edges):
            for second_edge in outgoing_edges[first_index + 1:]:
                if edge_plan_by_edge[first_edge].start_direction != edge_plan_by_edge[second_edge].start_direction:
                    continue
                if not self._segments_overlap(segment_sets[first_edge][0], segment_sets[second_edge][0]):
                    continue
                issues.append(f"same_switch_first_segments_overlap:{node_id}:{first_edge[1]}:{second_edge[1]}")
                if (first_edge in required_edges) != (second_edge in required_edges):
                    issues.append(f"required_and_wrong_route_first_segments_overlap:{node_id}:{first_edge[1]}:{second_edge[1]}")
        return issues

    def _crossing_counts(
        self,
        positions: dict[str, tuple[float, float]],
        edges: list[tuple[str, str]],
        required_edges: set[tuple[str, str]],
        important_nodes: set[str],
        segment_sets: dict[tuple[str, str], list[tuple[tuple[float, float], tuple[float, float]]]],
    ) -> tuple[int, int, int]:
        crossing_count = 0
        confusing_count = 0
        required_count = 0
        for first_index, first_edge in enumerate(edges):
            for second_edge in edges[first_index + 1:]:
                if set(first_edge) & set(second_edge):
                    continue
                for first_segment in segment_sets[first_edge]:
                    for second_segment in segment_sets[second_edge]:
                        intersection = self._segment_intersection_point(first_segment, second_segment)
                        if intersection is None:
                            continue
                        crossing_count += 1
                        if first_edge in required_edges or second_edge in required_edges:
                            required_count += 1
                        if any(
                            node_id in positions
                            and self._point_distance(intersection, positions[node_id]) < self._important_node_clearance
                            for node_id in important_nodes
                            if node_id not in first_edge and node_id not in second_edge
                        ):
                            confusing_count += 1
        return crossing_count, confusing_count, required_count

    def _long_parallel_segment_count(
        self,
        edges: list[tuple[str, str]],
        segment_sets: dict[tuple[str, str], list[tuple[tuple[float, float], tuple[float, float]]]],
    ) -> int:
        count = 0
        for first_index, first_edge in enumerate(edges):
            for second_edge in edges[first_index + 1:]:
                if set(first_edge) & set(second_edge):
                    continue
                for first_segment in segment_sets[first_edge]:
                    for second_segment in segment_sets[second_edge]:
                        if self._segments_are_tight_parallel(first_segment, second_segment):
                            count += 1
        return count

    def _visual_topology_counts(
        self,
        positions: dict[str, tuple[float, float]],
        edges: list[tuple[str, str]],
        segment_sets: dict[tuple[str, str], list[tuple[tuple[float, float], tuple[float, float]]]],
    ) -> dict[str, int]:
        counts = {
            "implicit_intersection_without_graph_node": 0,
            "road_crosses_through_unconnected_node": 0,
            "unconnected_road_endpoint_touches_segment": 0,
            "unconnected_parallel_road_overlap": 0,
        }

        for edge in edges:
            for segment in segment_sets[edge]:
                for node_id, position in positions.items():
                    if node_id in edge:
                        continue
                    if self._point_lies_on_segment(position, segment):
                        counts["road_crosses_through_unconnected_node"] += 1

        for first_index, first_edge in enumerate(edges):
            for second_edge in edges[first_index + 1:]:
                if set(first_edge) & set(second_edge):
                    continue
                for first_segment in segment_sets[first_edge]:
                    for second_segment in segment_sets[second_edge]:
                        if self._segments_are_collinear(first_segment, second_segment):
                            if self._projection_overlap_length(first_segment, second_segment) > self._point_tolerance:
                                counts["unconnected_parallel_road_overlap"] += 1
                            continue

                        intersection = self._segment_intersection_point(first_segment, second_segment)
                        if intersection is None:
                            continue
                        if self._edge_endpoint_at_intersection(positions, first_edge, intersection) or self._edge_endpoint_at_intersection(
                            positions,
                            second_edge,
                            intersection,
                        ):
                            counts["unconnected_road_endpoint_touches_segment"] += 1
                        elif self._node_at_point(intersection, positions) is None:
                            counts["implicit_intersection_without_graph_node"] += 1
        return counts

    def _important_node_proximity_count(
        self,
        positions: dict[str, tuple[float, float]],
        important_node_ids: set[str],
        edges: list[tuple[str, str]],
        segment_sets: dict[tuple[str, str], list[tuple[tuple[float, float], tuple[float, float]]]],
    ) -> int:
        count = 0
        for node_id in important_node_ids:
            if node_id not in positions:
                continue
            for edge in edges:
                if node_id in edge:
                    continue
                if any(
                    self._point_to_segment_distance(positions[node_id], segment) < self._important_node_clearance
                    for segment in segment_sets[edge]
                ):
                    count += 1
        return count

    def _main_route_smooth_break_count(
        self,
        required_path: tuple[str, ...],
        edge_plan_by_edge: dict[tuple[str, str], RoadShapeEdgePlan],
    ) -> int:
        if len(required_path) < 3:
            return 0
        count = 0
        for previous_node, current_node, next_node in zip(required_path, required_path[1:], required_path[2:]):
            incoming = edge_plan_by_edge.get((previous_node, current_node))
            outgoing = edge_plan_by_edge.get((current_node, next_node))
            if incoming is None or outgoing is None:
                continue
            if incoming.end_direction != outgoing.start_direction:
                count += 1
        return count

    def _return_loop_false_shortcut_count(
        self,
        positions: dict[str, tuple[float, float]],
        required_path: tuple[str, ...],
        segment_sets: dict[tuple[str, str], list[tuple[tuple[float, float], tuple[float, float]]]],
    ) -> int:
        if len(required_path) < 4 or len(set(required_path)) == len(required_path):
            return 0

        count = 0
        emitted_pairs: set[tuple[tuple[str, str], tuple[str, str]]] = set()
        repeated_nodes = {
            node_id
            for node_id, node_count in Counter(required_path).items()
            if node_count > 1 and node_id in positions
        }
        for repeated_node_id in repeated_nodes:
            repeated_position = positions[repeated_node_id]
            repeated_indexes = [
                index
                for index, node_id in enumerate(required_path)
                if node_id == repeated_node_id
            ]
            for repeated_index in repeated_indexes[1:]:
                if repeated_index == 0 or repeated_index + 1 >= len(required_path):
                    continue
                return_edge = (required_path[repeated_index - 1], repeated_node_id)
                destination_edge = (repeated_node_id, required_path[repeated_index + 1])
                if return_edge not in segment_sets or destination_edge not in segment_sets:
                    continue
                pair_key = (return_edge, destination_edge)
                if pair_key in emitted_pairs:
                    continue
                if self._return_loop_edge_pair_creates_false_shortcut(
                    segment_sets[return_edge],
                    segment_sets[destination_edge],
                    repeated_position,
                ):
                    emitted_pairs.add(pair_key)
                    count += 1
        return count

    def _return_loop_edge_pair_creates_false_shortcut(
        self,
        return_segments: list[tuple[tuple[float, float], tuple[float, float]]],
        destination_segments: list[tuple[tuple[float, float], tuple[float, float]]],
        repeated_position: tuple[float, float],
    ) -> bool:
        for return_segment in return_segments:
            for destination_segment in destination_segments:
                if self._return_loop_segments_create_false_shortcut(
                    return_segment,
                    destination_segment,
                    repeated_position,
                ):
                    return True
        return False

    def _return_loop_segments_create_false_shortcut(
        self,
        return_segment: tuple[tuple[float, float], tuple[float, float]],
        destination_segment: tuple[tuple[float, float], tuple[float, float]],
        repeated_position: tuple[float, float],
    ) -> bool:
        if self._segments_are_collinear(return_segment, destination_segment):
            return self._projection_overlap_length(return_segment, destination_segment) > self._point_tolerance

        intersection = self._segment_intersection_point(return_segment, destination_segment)
        if intersection is not None:
            return self._point_distance(intersection, repeated_position) > self._point_tolerance

        return (
            self._segment_clearance_away_from_node(return_segment, destination_segment, repeated_position)
            < self._return_loop_false_shortcut_clearance
        )

    def _segment_length(self, segment: tuple[tuple[float, float], tuple[float, float]]) -> float:
        return math.hypot(segment[1][0] - segment[0][0], segment[1][1] - segment[0][1])

    def _segment_intersection_point(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
    ) -> tuple[float, float] | None:
        (x1, y1), (x2, y2) = first
        (x3, y3), (x4, y4) = second
        denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denominator) <= self._point_tolerance:
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
            min(x1, x2) - self._point_tolerance <= x <= max(x1, x2) + self._point_tolerance
            and min(y1, y2) - self._point_tolerance <= y <= max(y1, y2) + self._point_tolerance
        )

    def _point_lies_on_segment(
        self,
        point: tuple[float, float],
        segment: tuple[tuple[float, float], tuple[float, float]],
    ) -> bool:
        return (
            self._point_on_segment(point, segment)
            and self._point_to_segment_distance(point, segment) <= self._point_tolerance
        )

    def _node_at_point(
        self,
        point: tuple[float, float],
        positions: dict[str, tuple[float, float]],
    ) -> str | None:
        return next(
            (
                node_id
                for node_id, position in positions.items()
                if self._point_distance(point, position) <= self._point_tolerance
            ),
            None,
        )

    def _edge_endpoint_at_intersection(
        self,
        positions: dict[str, tuple[float, float]],
        edge: tuple[str, str],
        intersection: tuple[float, float],
    ) -> bool:
        return (
            self._point_distance(positions[edge[0]], intersection) <= self._point_tolerance
            or self._point_distance(positions[edge[1]], intersection) <= self._point_tolerance
        )

    def _segments_overlap(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
    ) -> bool:
        if self._segment_intersection_point(first, second) is not None:
            return True
        return self._segments_are_collinear(first, second) and self._projection_overlap_length(first, second) > self._point_tolerance

    def _segments_are_collinear(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
    ) -> bool:
        (x1, y1), (x2, y2) = first
        (x3, y3), (x4, y4) = second
        return (
            abs((x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1)) <= self._point_tolerance
            and abs((x2 - x1) * (y4 - y1) - (y2 - y1) * (x4 - x1)) <= self._point_tolerance
        )

    def _segments_are_tight_parallel(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
    ) -> bool:
        if self._segments_are_collinear(first, second):
            return self._projection_overlap_length(first, second) > 0.35
        first_horizontal = abs(first[0][1] - first[1][1]) <= self._point_tolerance
        second_horizontal = abs(second[0][1] - second[1][1]) <= self._point_tolerance
        first_vertical = abs(first[0][0] - first[1][0]) <= self._point_tolerance
        second_vertical = abs(second[0][0] - second[1][0]) <= self._point_tolerance
        if first_horizontal and second_horizontal:
            return abs(first[0][1] - second[0][1]) < self._merge_distance and self._projection_overlap_length(first, second) > 0.35
        if first_vertical and second_vertical:
            return abs(first[0][0] - second[0][0]) < self._merge_distance and self._projection_overlap_length(first, second) > 0.35
        return False

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

    def _point_to_segment_distance(
        self,
        point: tuple[float, float],
        segment: tuple[tuple[float, float], tuple[float, float]],
    ) -> float:
        nearest = self._nearest_point_on_segment(point, segment)
        return math.hypot(point[0] - nearest[0], point[1] - nearest[1])

    def _segments_distance(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
    ) -> float:
        if self._segments_overlap(first, second):
            return 0.0
        return min(
            self._point_to_segment_distance(first[0], second),
            self._point_to_segment_distance(first[1], second),
            self._point_to_segment_distance(second[0], first),
            self._point_to_segment_distance(second[1], first),
        )

    def _segment_clearance_away_from_node(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
        ignored_node_position: tuple[float, float],
    ) -> float:
        distances: list[float] = []
        for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
            for point, segment in (
                (self._point_at_fraction(first, fraction), second),
                (self._point_at_fraction(second, fraction), first),
            ):
                nearest = self._nearest_point_on_segment(point, segment)
                if (
                    self._point_distance(point, ignored_node_position) <= self._return_loop_false_shortcut_clearance
                    and self._point_distance(nearest, ignored_node_position) <= self._return_loop_false_shortcut_clearance
                ):
                    continue
                distances.append(self._point_distance(point, nearest))
        return min(distances) if distances else math.inf

    def _nearest_point_on_segment(
        self,
        point: tuple[float, float],
        segment: tuple[tuple[float, float], tuple[float, float]],
    ) -> tuple[float, float]:
        (px, py) = point
        (x1, y1), (x2, y2) = segment
        dx = x2 - x1
        dy = y2 - y1
        if abs(dx) <= self._point_tolerance and abs(dy) <= self._point_tolerance:
            return (x1, y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / ((dx * dx) + (dy * dy))))
        return (x1 + (t * dx), y1 + (t * dy))

    def _point_distance(self, first: tuple[float, float], second: tuple[float, float]) -> float:
        return math.hypot(first[0] - second[0], first[1] - second[1])

    def _point_at_fraction(
        self,
        segment: tuple[tuple[float, float], tuple[float, float]],
        fraction: float,
    ) -> tuple[float, float]:
        start, end = segment
        return (start[0] + ((end[0] - start[0]) * fraction), start[1] + ((end[1] - start[1]) * fraction))
