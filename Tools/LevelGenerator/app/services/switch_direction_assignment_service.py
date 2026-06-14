from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .route_timing_service import RouteTimingService


@dataclass(frozen=True)
class DirectionBucketAssignment:
    edge_id: str
    target_node_id: str
    road_shape: str | None
    bucket: str | None
    angle: float | None
    angle_degrees: float | None
    first_segment_length: float | None
    nearest_bucket_separation_degrees: float | None = None
    ambiguous_reason: str | None = None

    @property
    def is_ambiguous(self) -> bool:
        return self.ambiguous_reason is not None or self.bucket is None or self.angle is None


@dataclass(frozen=True)
class SwitchDirectionAssignmentReport:
    switch_id: str
    assignments: tuple[DirectionBucketAssignment, ...] = field(default_factory=tuple)
    issues: tuple[str, ...] = field(default_factory=tuple)
    minimum_exit_angle_separation_degrees: float | None = None
    quality: float = 1.0

    @property
    def ambiguous_switch_detected(self) -> bool:
        return bool(self.issues) or any(assignment.is_ambiguous for assignment in self.assignments)

    @property
    def direction_buckets(self) -> dict[str, str]:
        return {
            assignment.edge_id: assignment.bucket
            for assignment in self.assignments
            if assignment.bucket is not None
        }

    @property
    def duplicate_buckets(self) -> dict[str, list[str]]:
        bucket_counts = Counter(assignment.bucket for assignment in self.assignments if assignment.bucket is not None)
        return {
            bucket: [
                assignment.edge_id
                for assignment in self.assignments
                if assignment.bucket == bucket
            ]
            for bucket, count in bucket_counts.items()
            if count > 1
        }

    def to_metadata(self) -> dict[str, Any]:
        return {
            "switchID": self.switch_id,
            "quality": self.quality,
            "minimumExitAngleSeparationDegrees": self.minimum_exit_angle_separation_degrees,
            "ambiguousSwitchDetected": self.ambiguous_switch_detected,
            "issues": list(self.issues),
            "assignments": [
                {
                    "edgeID": assignment.edge_id,
                    "targetNodeID": assignment.target_node_id,
                    "roadShape": assignment.road_shape,
                    "bucket": assignment.bucket,
                    "angleDegrees": assignment.angle_degrees,
                    "firstSegmentLength": assignment.first_segment_length,
                    "nearestBucketSeparationDegrees": assignment.nearest_bucket_separation_degrees,
                    "ambiguousReason": assignment.ambiguous_reason,
                }
                for assignment in self.assignments
            ],
        }


class SwitchDirectionAssignmentService:
    minimum_bucket_separation_degrees = 80.0
    minimum_first_segment_length = 0.16
    point_tolerance = 1e-9

    def __init__(self) -> None:
        self.route_timing = RouteTimingService()

    def report_for_switch(
        self,
        switch_node,
        outgoing_edges: list[object],
        node_by_id: dict[str, object],
        *,
        road_shape_by_edge_id: dict[str, str | None] | None = None,
    ) -> SwitchDirectionAssignmentReport:
        positions = {
            node_id: self._point(node)
            for node_id, node in node_by_id.items()
        }
        edge_pairs = [
            (str(edge.id), str(edge.toNodeID), (road_shape_by_edge_id or {}).get(edge.id, edge.roadShape))
            for edge in outgoing_edges
        ]
        return self.report_for_switch_positions(str(switch_node.id), positions, edge_pairs)

    def report_for_switch_positions(
        self,
        switch_id: str,
        positions: dict[str, tuple[float, float]],
        outgoing_edges: list[tuple[str, str, str | None]],
    ) -> SwitchDirectionAssignmentReport:
        assignments = [
            self._assignment_for_edge(switch_id, positions, edge_id, target_node_id, road_shape)
            for edge_id, target_node_id, road_shape in outgoing_edges
        ]
        assignments = self._with_nearest_bucket_separation(assignments)
        issues = self._issues_for_assignments(switch_id, assignments)
        quality = self._quality(issues)
        separations = [
            assignment.nearest_bucket_separation_degrees
            for assignment in assignments
            if assignment.nearest_bucket_separation_degrees is not None
        ]
        return SwitchDirectionAssignmentReport(
            switch_id=switch_id,
            assignments=tuple(assignments),
            issues=tuple(dict.fromkeys(issues)),
            minimum_exit_angle_separation_degrees=round(min(separations), 4) if separations else None,
            quality=quality,
        )

    def _assignment_for_edge(
        self,
        switch_id: str,
        positions: dict[str, tuple[float, float]],
        edge_id: str,
        target_node_id: str,
        road_shape: str | None,
    ) -> DirectionBucketAssignment:
        source_position = positions.get(switch_id)
        target_position = positions.get(target_node_id)
        if source_position is None:
            return self._ambiguous(edge_id, target_node_id, road_shape, "missing switch node")
        if target_position is None:
            return self._ambiguous(edge_id, target_node_id, road_shape, "missing target node")
        if self._point_distance(source_position, target_position) <= self.point_tolerance:
            return self._ambiguous(edge_id, target_node_id, road_shape, "zero-length road path")

        try:
            angle = self.route_timing.direction_angle(source_position, target_position, road_shape)
        except ValueError as exc:
            return self._ambiguous(edge_id, target_node_id, road_shape, str(exc))

        first_segment_length = self._first_segment_length(source_position, target_position, road_shape)
        ambiguous_reason = None
        if first_segment_length <= self.minimum_first_segment_length:
            ambiguous_reason = "first road segment too short for readable switch arrow"

        return DirectionBucketAssignment(
            edge_id=edge_id,
            target_node_id=target_node_id,
            road_shape=road_shape,
            bucket=self.route_timing.direction_label(angle),
            angle=angle,
            angle_degrees=round(math.degrees(self._normalized_angle(angle)), 4),
            first_segment_length=round(first_segment_length, 4),
            ambiguous_reason=ambiguous_reason,
        )

    def _ambiguous(
        self,
        edge_id: str,
        target_node_id: str,
        road_shape: str | None,
        reason: str,
    ) -> DirectionBucketAssignment:
        return DirectionBucketAssignment(
            edge_id=edge_id,
            target_node_id=target_node_id,
            road_shape=road_shape,
            bucket=None,
            angle=None,
            angle_degrees=None,
            first_segment_length=None,
            ambiguous_reason=reason,
        )

    def _with_nearest_bucket_separation(
        self,
        assignments: list[DirectionBucketAssignment],
    ) -> list[DirectionBucketAssignment]:
        result: list[DirectionBucketAssignment] = []
        for assignment in assignments:
            if assignment.angle is None:
                result.append(assignment)
                continue
            separations = [
                abs(self._angle_difference_degrees(assignment.angle, other.angle))
                for other in assignments
                if other is not assignment and other.angle is not None
            ]
            result.append(
                DirectionBucketAssignment(
                    edge_id=assignment.edge_id,
                    target_node_id=assignment.target_node_id,
                    road_shape=assignment.road_shape,
                    bucket=assignment.bucket,
                    angle=assignment.angle,
                    angle_degrees=assignment.angle_degrees,
                    first_segment_length=assignment.first_segment_length,
                    nearest_bucket_separation_degrees=round(min(separations), 4) if separations else None,
                    ambiguous_reason=assignment.ambiguous_reason,
                )
            )
        return result

    def _issues_for_assignments(
        self,
        switch_id: str,
        assignments: list[DirectionBucketAssignment],
    ) -> list[str]:
        issues: list[str] = []
        for assignment in assignments:
            if assignment.is_ambiguous:
                issues.append(f"ambiguous_switch_exit:{switch_id}:{assignment.edge_id}")

        for bucket, count in Counter(assignment.bucket for assignment in assignments if assignment.bucket is not None).items():
            if count > 1:
                issues.append(f"conflicting_direction_bucket:{switch_id}:{bucket}")

        for assignment in assignments:
            separation = assignment.nearest_bucket_separation_degrees
            if separation is not None and separation < self.minimum_bucket_separation_degrees:
                issues.append(f"insufficient_exit_separation:{switch_id}:{assignment.edge_id}")
        return issues

    def _quality(self, issues: list[str]) -> float:
        score = 1.0
        for issue in issues:
            if issue.startswith("conflicting_direction_bucket"):
                score -= 0.38
            elif issue.startswith("ambiguous_switch_exit"):
                score -= 0.30
            elif issue.startswith("insufficient_exit_separation"):
                score -= 0.24
            else:
                score -= 0.08
        return round(max(0.0, min(1.0, score)), 4)

    def _first_segment_length(
        self,
        source_position: tuple[float, float],
        target_position: tuple[float, float],
        road_shape: str | None,
    ) -> float:
        source_x, source_y = source_position
        target_x, target_y = target_position
        if abs(source_x - target_x) <= self.point_tolerance or abs(source_y - target_y) <= self.point_tolerance:
            return self._point_distance(source_position, target_position)
        resolved_shape = road_shape or "horizontalFirst"
        if resolved_shape == "horizontalFirst":
            return abs(target_x - source_x)
        if resolved_shape == "verticalFirst":
            return abs(target_y - source_y)
        raise ValueError(f"Invalid roadShape: {road_shape}")

    def _point(self, node: Any) -> tuple[float, float]:
        if isinstance(node, tuple) and len(node) == 2:
            return float(node[0]), float(node[1])
        if isinstance(node, dict):
            return float(node["x"]), float(node["y"])
        return float(node.x), float(node.y)

    def _point_distance(self, first: tuple[float, float], second: tuple[float, float]) -> float:
        return math.hypot(first[0] - second[0], first[1] - second[1])

    def _angle_difference_degrees(self, first: float, second: float) -> float:
        return math.degrees(self._normalized_angle(first - second))

    def _normalized_angle(self, angle: float) -> float:
        normalized = angle
        while normalized <= -math.pi:
            normalized += 2 * math.pi
        while normalized > math.pi:
            normalized -= 2 * math.pi
        return normalized
