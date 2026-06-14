from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Literal

from ..models.difficulty_preset import DifficultyPreset
from .graph_layout_service import BoundingBox
from .road_shape_service import RoadShapeService
from .switch_classification_service import SwitchClassificationService


LayoutReadabilitySeverity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class LayoutReadabilityThresholds:
    """Board-unit thresholds for final candidate layout acceptance."""

    minimum_node_spacing: float = 0.28
    important_node_spacing: float = 0.34
    switch_node_spacing: float = 0.36
    minimum_road_spacing: float = 0.18
    switch_exit_minimum_angle_degrees: float = 35.0
    overlapping_first_segment_minimum_length: float = 0.06
    important_node_road_clearance: float = 0.22
    start_goal_minimum_distance: float = 0.85
    portrait_edge_margin: float = 0.04
    portrait_max_aspect_ratio: float = 0.95
    portrait_min_vertical_separation: float = 0.75

    def to_dict(self) -> dict[str, float]:
        return {
            "minimumNodeSpacing": self.minimum_node_spacing,
            "importantNodeSpacing": self.important_node_spacing,
            "switchNodeSpacing": self.switch_node_spacing,
            "minimumRoadSpacing": self.minimum_road_spacing,
            "switchExitMinimumAngleDegrees": self.switch_exit_minimum_angle_degrees,
            "overlappingFirstSegmentMinimumLength": self.overlapping_first_segment_minimum_length,
            "importantNodeRoadClearance": self.important_node_road_clearance,
            "startGoalMinimumDistance": self.start_goal_minimum_distance,
            "portraitEdgeMargin": self.portrait_edge_margin,
            "portraitMaxAspectRatio": self.portrait_max_aspect_ratio,
            "portraitMinVerticalSeparation": self.portrait_min_vertical_separation,
        }


@dataclass(frozen=True)
class LayoutReadabilityIssue:
    severity: LayoutReadabilitySeverity
    code: str
    message: str
    related_node_id: str | None = None
    related_edge_id: str | None = None
    related_node_ids: tuple[str, ...] = field(default_factory=tuple)
    related_edge_ids: tuple[str, ...] = field(default_factory=tuple)
    measured_distance: float | None = None
    measured_angle_degrees: float | None = None
    threshold: float | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "relatedNodeID": self.related_node_id,
            "relatedEdgeID": self.related_edge_id,
            "relatedNodeIDs": list(self.related_node_ids),
            "relatedEdgeIDs": list(self.related_edge_ids),
            "measuredDistance": self.measured_distance,
            "measuredAngleDegrees": self.measured_angle_degrees,
            "threshold": self.threshold,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class LayoutReadabilityReport:
    issues: tuple[LayoutReadabilityIssue, ...]
    metadata: dict[str, Any]

    @property
    def errors(self) -> tuple[LayoutReadabilityIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


@dataclass(frozen=True)
class _SegmentRef:
    edge_id: str
    from_node_id: str
    to_node_id: str
    start_node_id: str | None
    end_node_id: str | None
    start: tuple[float, float]
    end: tuple[float, float]
    index: int


@dataclass(frozen=True)
class _ReadabilityContext:
    level: Any
    preset: DifficultyPreset | None
    layout_metadata: dict[str, Any]
    thresholds: LayoutReadabilityThresholds
    bounds: BoundingBox
    positions: dict[str, tuple[float, float]]
    edge_by_id: dict[str, Any]
    switch_node_ids: tuple[str, ...]
    important_node_ids: tuple[str, ...]
    segments: tuple[_SegmentRef, ...]


class LayoutReadabilityValidator:
    """Final visual acceptance gate for logically valid generated layouts."""

    point_tolerance = 1e-9

    def __init__(self, thresholds: LayoutReadabilityThresholds | None = None) -> None:
        self.base_thresholds = thresholds or LayoutReadabilityThresholds()
        self.road_shape_service = RoadShapeService()
        self.switch_classification_service = SwitchClassificationService()

    def report_for_generated_level(
        self,
        generated_level,
        preset: DifficultyPreset | None = None,
    ) -> LayoutReadabilityReport:
        return self.report_for_level(
            generated_level.level_document,
            preset=preset,
            layout_metadata=getattr(generated_level, "layout_metadata", None) or {},
        )

    def report_for_level(
        self,
        level,
        *,
        preset: DifficultyPreset | None = None,
        layout_metadata: dict[str, Any] | None = None,
    ) -> LayoutReadabilityReport:
        context = self._context_for_level(level, preset, layout_metadata or {})
        issues = self._dedupe_issues(
            [
                *self.validate_no_node_overlap(context),
                *self.validate_no_implicit_intersection_without_node(context),
                *self.validate_roads_not_too_close(context),
                *self.validate_switch_exit_separation(context),
                *self.validate_no_overlapping_first_segments(context),
                *self.validate_important_node_visibility(context),
                *self.validate_start_goal_separation(context),
                *self.validate_portrait_safety(context),
            ]
        )
        return LayoutReadabilityReport(
            issues=issues,
            metadata=self._metadata_for(context, issues),
        )

    def validateNoNodeOverlap(self, level, preset: DifficultyPreset | None = None, layout_metadata: dict[str, Any] | None = None):
        return self.validate_no_node_overlap(self._context_for_level(level, preset, layout_metadata or {}))

    def validateNoImplicitIntersectionWithoutNode(self, level, preset: DifficultyPreset | None = None, layout_metadata: dict[str, Any] | None = None):
        return self.validate_no_implicit_intersection_without_node(self._context_for_level(level, preset, layout_metadata or {}))

    def validateRoadsNotTooClose(self, level, preset: DifficultyPreset | None = None, layout_metadata: dict[str, Any] | None = None):
        return self.validate_roads_not_too_close(self._context_for_level(level, preset, layout_metadata or {}))

    def validateSwitchExitSeparation(self, level, preset: DifficultyPreset | None = None, layout_metadata: dict[str, Any] | None = None):
        return self.validate_switch_exit_separation(self._context_for_level(level, preset, layout_metadata or {}))

    def validateNoOverlappingFirstSegments(self, level, preset: DifficultyPreset | None = None, layout_metadata: dict[str, Any] | None = None):
        return self.validate_no_overlapping_first_segments(self._context_for_level(level, preset, layout_metadata or {}))

    def validateImportantNodeVisibility(self, level, preset: DifficultyPreset | None = None, layout_metadata: dict[str, Any] | None = None):
        return self.validate_important_node_visibility(self._context_for_level(level, preset, layout_metadata or {}))

    def validateStartGoalSeparation(self, level, preset: DifficultyPreset | None = None, layout_metadata: dict[str, Any] | None = None):
        return self.validate_start_goal_separation(self._context_for_level(level, preset, layout_metadata or {}))

    def validatePortraitSafety(self, level, preset: DifficultyPreset | None = None, layout_metadata: dict[str, Any] | None = None):
        return self.validate_portrait_safety(self._context_for_level(level, preset, layout_metadata or {}))

    def validate_no_node_overlap(self, context: _ReadabilityContext) -> tuple[LayoutReadabilityIssue, ...]:
        issues: list[LayoutReadabilityIssue] = []
        node_ids = tuple(context.positions)
        important_ids = set(context.important_node_ids)
        switch_ids = set(context.switch_node_ids)
        for first_index, first_id in enumerate(node_ids):
            for second_id in node_ids[first_index + 1:]:
                distance = self._point_distance(context.positions[first_id], context.positions[second_id])
                threshold = context.thresholds.minimum_node_spacing
                if first_id in important_ids or second_id in important_ids:
                    threshold = max(threshold, context.thresholds.important_node_spacing)
                if first_id in switch_ids or second_id in switch_ids:
                    threshold = max(threshold, context.thresholds.switch_node_spacing)
                if distance + self.point_tolerance >= threshold:
                    continue
                issues.append(
                    LayoutReadabilityIssue(
                        severity="error",
                        code="node_spacing_failure",
                        message=(
                            f"Nodes '{first_id}' and '{second_id}' are {distance:.2f} board units apart; "
                            f"minimum is {threshold:.2f}."
                        ),
                        related_node_id=first_id,
                        related_node_ids=(first_id, second_id),
                        measured_distance=round(distance, 4),
                        threshold=round(threshold, 4),
                        details={
                            "importantNodeInvolved": first_id in important_ids or second_id in important_ids,
                            "switchNodeInvolved": first_id in switch_ids or second_id in switch_ids,
                        },
                    )
                )
        return tuple(issues)

    def validate_no_implicit_intersection_without_node(self, context: _ReadabilityContext) -> tuple[LayoutReadabilityIssue, ...]:
        issues: list[LayoutReadabilityIssue] = []
        for first_index, first in enumerate(context.segments):
            for second in context.segments[first_index + 1:]:
                if first.edge_id == second.edge_id or self._segments_share_graph_node(first, second):
                    continue

                first_segment = (first.start, first.end)
                second_segment = (second.start, second.end)
                if self._segments_are_collinear(first_segment, second_segment):
                    overlap = self._projection_overlap_length(first_segment, second_segment)
                    if overlap > context.thresholds.overlapping_first_segment_minimum_length:
                        issues.append(
                            LayoutReadabilityIssue(
                                severity="error",
                                code="implicit_intersection_without_node",
                                message=(
                                    f"Edges '{first.edge_id}' and '{second.edge_id}' visually overlap "
                                    "without an explicit graph node."
                                ),
                                related_edge_id=first.edge_id,
                                related_edge_ids=(first.edge_id, second.edge_id),
                                measured_distance=0.0,
                                threshold=0.0,
                                details={"intersectionKind": "collinear_overlap", "overlapLength": round(overlap, 4)},
                            )
                        )
                    continue

                intersection = self._segment_intersection_point(first_segment, second_segment)
                if intersection is None or self._node_at_point(intersection, context.positions) is not None:
                    continue
                issues.append(
                    LayoutReadabilityIssue(
                        severity="error",
                        code="implicit_intersection_without_node",
                        message=(
                            f"Edges '{first.edge_id}' and '{second.edge_id}' visually cross "
                            "without an explicit graph node."
                        ),
                        related_edge_id=first.edge_id,
                        related_edge_ids=(first.edge_id, second.edge_id),
                        measured_distance=0.0,
                        threshold=0.0,
                        details={
                            "intersectionKind": "crossing",
                            "point": [round(intersection[0], 4), round(intersection[1], 4)],
                        },
                    )
                )
        return tuple(issues)

    def validate_roads_not_too_close(self, context: _ReadabilityContext) -> tuple[LayoutReadabilityIssue, ...]:
        issues: list[LayoutReadabilityIssue] = []
        emitted_pairs: set[tuple[str, str]] = set()
        for first_index, first in enumerate(context.segments):
            for second in context.segments[first_index + 1:]:
                if first.edge_id == second.edge_id or self._segments_share_graph_node(first, second):
                    continue
                pair_key = tuple(sorted((first.edge_id, second.edge_id)))
                if pair_key in emitted_pairs:
                    continue
                first_segment = (first.start, first.end)
                second_segment = (second.start, second.end)
                if self._segments_have_visual_intersection(first_segment, second_segment):
                    continue
                distance = self._segments_distance(first_segment, second_segment)
                if distance + self.point_tolerance >= context.thresholds.minimum_road_spacing:
                    continue
                emitted_pairs.add(pair_key)
                issues.append(
                    LayoutReadabilityIssue(
                        severity="error",
                        code="road_proximity_failure",
                        message=(
                            f"Edges '{first.edge_id}' and '{second.edge_id}' are {distance:.2f} board units apart; "
                            f"minimum unrelated-road spacing is {context.thresholds.minimum_road_spacing:.2f}."
                        ),
                        related_edge_id=first.edge_id,
                        related_edge_ids=(first.edge_id, second.edge_id),
                        measured_distance=round(distance, 4),
                        threshold=round(context.thresholds.minimum_road_spacing, 4),
                    )
                )
        return tuple(issues)

    def validate_switch_exit_separation(self, context: _ReadabilityContext) -> tuple[LayoutReadabilityIssue, ...]:
        issues: list[LayoutReadabilityIssue] = []
        first_segment_by_edge_id = self._first_segment_by_edge_id(context.segments)
        for switch_id in context.switch_node_ids:
            outgoing_edge_ids = self._valid_outgoing_edge_ids(context, switch_id)
            for first_index, first_edge_id in enumerate(outgoing_edge_ids):
                for second_edge_id in outgoing_edge_ids[first_index + 1:]:
                    first = first_segment_by_edge_id.get(first_edge_id)
                    second = first_segment_by_edge_id.get(second_edge_id)
                    if first is None or second is None:
                        continue
                    first_angle = self._segment_angle_degrees((first.start, first.end))
                    second_angle = self._segment_angle_degrees((second.start, second.end))
                    separation = self._angle_separation_degrees(first_angle, second_angle)
                    if separation + self.point_tolerance >= context.thresholds.switch_exit_minimum_angle_degrees:
                        continue
                    issues.append(
                        LayoutReadabilityIssue(
                            severity="error",
                            code="switch_exit_overlap",
                            message=(
                                f"Switch '{switch_id}' exits '{first_edge_id}' and '{second_edge_id}' leave "
                                f"only {separation:.1f} degrees apart."
                            ),
                            related_node_id=switch_id,
                            related_edge_id=first_edge_id,
                            related_node_ids=(switch_id,),
                            related_edge_ids=(first_edge_id, second_edge_id),
                            measured_angle_degrees=round(separation, 4),
                            threshold=round(context.thresholds.switch_exit_minimum_angle_degrees, 4),
                            details={
                                "firstAngleDegrees": round(first_angle, 4),
                                "secondAngleDegrees": round(second_angle, 4),
                                "rule": "exit_angle_separation",
                            },
                        )
                    )
        return tuple(issues)

    def validate_no_overlapping_first_segments(self, context: _ReadabilityContext) -> tuple[LayoutReadabilityIssue, ...]:
        issues: list[LayoutReadabilityIssue] = []
        first_segment_by_edge_id = self._first_segment_by_edge_id(context.segments)
        for switch_id in context.switch_node_ids:
            outgoing_edge_ids = self._valid_outgoing_edge_ids(context, switch_id)
            for first_index, first_edge_id in enumerate(outgoing_edge_ids):
                for second_edge_id in outgoing_edge_ids[first_index + 1:]:
                    first = first_segment_by_edge_id.get(first_edge_id)
                    second = first_segment_by_edge_id.get(second_edge_id)
                    if first is None or second is None:
                        continue
                    first_segment = (first.start, first.end)
                    second_segment = (second.start, second.end)
                    if not self._segments_are_collinear(first_segment, second_segment):
                        continue
                    overlap = self._projection_overlap_length(first_segment, second_segment)
                    if overlap + self.point_tolerance < context.thresholds.overlapping_first_segment_minimum_length:
                        continue
                    issues.append(
                        LayoutReadabilityIssue(
                            severity="error",
                            code="switch_exit_overlap",
                            message=(
                                f"Switch '{switch_id}' exits '{first_edge_id}' and '{second_edge_id}' have "
                                f"overlapping first visible road segments."
                            ),
                            related_node_id=switch_id,
                            related_edge_id=first_edge_id,
                            related_node_ids=(switch_id,),
                            related_edge_ids=(first_edge_id, second_edge_id),
                            measured_distance=round(overlap, 4),
                            threshold=round(context.thresholds.overlapping_first_segment_minimum_length, 4),
                            details={"rule": "overlapping_first_segments", "overlapLength": round(overlap, 4)},
                        )
                    )
        return tuple(issues)

    def validate_important_node_visibility(self, context: _ReadabilityContext) -> tuple[LayoutReadabilityIssue, ...]:
        issues: list[LayoutReadabilityIssue] = []
        for node_id in context.important_node_ids:
            node_position = context.positions.get(node_id)
            if node_position is None:
                continue
            for segment in context.segments:
                if node_id in {segment.from_node_id, segment.to_node_id}:
                    continue
                distance = self._point_to_segment_distance(node_position, (segment.start, segment.end))
                if distance + self.point_tolerance >= context.thresholds.important_node_road_clearance:
                    continue
                issues.append(
                    LayoutReadabilityIssue(
                        severity="error",
                        code="important_node_visibility_failure",
                        message=(
                            f"Important node '{node_id}' is {distance:.2f} board units from edge "
                            f"'{segment.edge_id}'; minimum clearance is "
                            f"{context.thresholds.important_node_road_clearance:.2f}."
                        ),
                        related_node_id=node_id,
                        related_edge_id=segment.edge_id,
                        related_node_ids=(node_id,),
                        related_edge_ids=(segment.edge_id,),
                        measured_distance=round(distance, 4),
                        threshold=round(context.thresholds.important_node_road_clearance, 4),
                    )
                )
        return tuple(issues)

    def validate_start_goal_separation(self, context: _ReadabilityContext) -> tuple[LayoutReadabilityIssue, ...]:
        start_id = context.level.startNodeID
        goal_id = context.level.destinationNodeID
        if start_id not in context.positions or goal_id not in context.positions:
            return ()
        distance = self._point_distance(context.positions[start_id], context.positions[goal_id])
        if distance + self.point_tolerance >= context.thresholds.start_goal_minimum_distance:
            return ()
        return (
            LayoutReadabilityIssue(
                severity="error",
                code="start_goal_separation_failure",
                message=(
                    f"Start '{start_id}' and goal '{goal_id}' are {distance:.2f} board units apart; "
                    f"minimum separation is {context.thresholds.start_goal_minimum_distance:.2f}."
                ),
                related_node_id=start_id,
                related_node_ids=(start_id, goal_id),
                measured_distance=round(distance, 4),
                threshold=round(context.thresholds.start_goal_minimum_distance, 4),
            ),
        )

    def validate_portrait_safety(self, context: _ReadabilityContext) -> tuple[LayoutReadabilityIssue, ...]:
        issues: list[LayoutReadabilityIssue] = []
        margin = context.thresholds.portrait_edge_margin
        for node_id, (x, y) in context.positions.items():
            if not (
                context.bounds.min_x + margin <= x <= context.bounds.max_x - margin
                and context.bounds.min_y + margin <= y <= context.bounds.max_y - margin
            ):
                issues.append(
                    LayoutReadabilityIssue(
                        severity="error",
                        code="portrait_safety_failure",
                        message=f"Node '{node_id}' is outside the readable portrait safe area.",
                        related_node_id=node_id,
                        related_node_ids=(node_id,),
                        threshold=round(margin, 4),
                        details={
                            "rule": "portrait_safe_area",
                            "position": [round(x, 4), round(y, 4)],
                            "bounds": [
                                context.bounds.min_x,
                                context.bounds.max_x,
                                context.bounds.min_y,
                                context.bounds.max_y,
                            ],
                        },
                    )
                )

        if self._layout_profile(context) != "portrait_vertical":
            return tuple(issues)

        metrics = self._portrait_metrics(context)
        if metrics["height"] <= self.point_tolerance:
            issues.append(
                LayoutReadabilityIssue(
                    severity="error",
                    code="portrait_safety_failure",
                    message="Portrait layout has no readable vertical span.",
                    details={"rule": "portrait_height", "metrics": metrics},
                )
            )
        if metrics["aspectRatio"] > context.thresholds.portrait_max_aspect_ratio:
            issues.append(
                LayoutReadabilityIssue(
                    severity="error",
                    code="portrait_safety_failure",
                    message=(
                        f"Portrait layout aspect ratio {metrics['aspectRatio']:.2f} exceeds "
                        f"{context.thresholds.portrait_max_aspect_ratio:.2f}."
                    ),
                    measured_distance=round(metrics["aspectRatio"], 4),
                    threshold=round(context.thresholds.portrait_max_aspect_ratio, 4),
                    details={"rule": "portrait_aspect_ratio", "metrics": metrics},
                )
            )
        minimum_vertical_separation = max(
            context.thresholds.portrait_min_vertical_separation,
            metrics["height"] * 0.40,
        )
        if metrics["verticalSeparation"] + self.point_tolerance < minimum_vertical_separation:
            issues.append(
                LayoutReadabilityIssue(
                    severity="error",
                    code="portrait_safety_failure",
                    message=(
                        f"Portrait start-goal vertical separation {metrics['verticalSeparation']:.2f} "
                        f"is below {minimum_vertical_separation:.2f}."
                    ),
                    related_node_id=context.level.startNodeID,
                    related_node_ids=(context.level.startNodeID, context.level.destinationNodeID),
                    measured_distance=round(metrics["verticalSeparation"], 4),
                    threshold=round(minimum_vertical_separation, 4),
                    details={"rule": "portrait_vertical_separation", "metrics": metrics},
                )
            )
        if not metrics["startInLowerPortion"]:
            issues.append(
                LayoutReadabilityIssue(
                    severity="error",
                    code="portrait_safety_failure",
                    message="Portrait layout start is not in the lower readable portion.",
                    related_node_id=context.level.startNodeID,
                    related_node_ids=(context.level.startNodeID,),
                    details={"rule": "portrait_start_lower_portion", "metrics": metrics},
                )
            )
        if not metrics["destinationInUpperPortion"]:
            issues.append(
                LayoutReadabilityIssue(
                    severity="error",
                    code="portrait_safety_failure",
                    message="Portrait layout goal is not in the upper readable portion.",
                    related_node_id=context.level.destinationNodeID,
                    related_node_ids=(context.level.destinationNodeID,),
                    details={"rule": "portrait_goal_upper_portion", "metrics": metrics},
                )
            )
        return tuple(issues)

    def _context_for_level(
        self,
        level,
        preset: DifficultyPreset | None,
        layout_metadata: dict[str, Any],
    ) -> _ReadabilityContext:
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        positions = {node.id: (float(node.x), float(node.y)) for node in level.graph.nodes}
        switch_node_ids = tuple(
            node.id
            for node in level.graph.nodes
            if self.switch_classification_service.classify_node(node, edge_by_id).is_switchable
        )
        important_node_ids = tuple(
            dict.fromkeys(
                node_id
                for node_id in (
                    level.startNodeID,
                    level.packageNodeID,
                    level.destinationNodeID,
                    *switch_node_ids,
                )
                if node_id in positions
            )
        )
        thresholds = self._thresholds_for(preset)
        bounds = BoundingBox(*(preset.coordinate_bounds if preset is not None else (-1.2, 1.2, -1.3, 1.0)))
        return _ReadabilityContext(
            level=level,
            preset=preset,
            layout_metadata=layout_metadata,
            thresholds=thresholds,
            bounds=bounds,
            positions=positions,
            edge_by_id=edge_by_id,
            switch_node_ids=switch_node_ids,
            important_node_ids=important_node_ids,
            segments=self._segments_for_level(level, positions),
        )

    def _thresholds_for(self, preset: DifficultyPreset | None) -> LayoutReadabilityThresholds:
        base = self.base_thresholds
        if preset is None:
            return base
        minimum_node_distance = float(preset.minimum_node_distance)
        return LayoutReadabilityThresholds(
            minimum_node_spacing=max(base.minimum_node_spacing, minimum_node_distance * 1.25),
            important_node_spacing=max(base.important_node_spacing, minimum_node_distance * 1.60),
            switch_node_spacing=max(base.switch_node_spacing, minimum_node_distance * 1.70),
            minimum_road_spacing=max(base.minimum_road_spacing, minimum_node_distance * 0.85),
            switch_exit_minimum_angle_degrees=base.switch_exit_minimum_angle_degrees,
            overlapping_first_segment_minimum_length=max(
                base.overlapping_first_segment_minimum_length,
                minimum_node_distance * 0.25,
            ),
            important_node_road_clearance=max(base.important_node_road_clearance, minimum_node_distance * 1.05),
            start_goal_minimum_distance=max(base.start_goal_minimum_distance, minimum_node_distance * 3.20),
            portrait_edge_margin=base.portrait_edge_margin,
            portrait_max_aspect_ratio=base.portrait_max_aspect_ratio,
            portrait_min_vertical_separation=base.portrait_min_vertical_separation,
        )

    def _segments_for_level(
        self,
        level,
        positions: dict[str, tuple[float, float]],
    ) -> tuple[_SegmentRef, ...]:
        segments: list[_SegmentRef] = []
        for edge in level.graph.edges:
            if edge.fromNodeID not in positions or edge.toNodeID not in positions:
                continue
            road_shape = edge.roadShape or "horizontalFirst"
            if not self.road_shape_service.is_allowed(road_shape):
                continue
            edge_segments = self.road_shape_service._segments_for_edge(
                positions[edge.fromNodeID],
                positions[edge.toNodeID],
                road_shape,
            )
            for index, (start, end) in enumerate(edge_segments):
                segments.append(
                    _SegmentRef(
                        edge_id=edge.id,
                        from_node_id=edge.fromNodeID,
                        to_node_id=edge.toNodeID,
                        start_node_id=edge.fromNodeID if index == 0 else None,
                        end_node_id=edge.toNodeID if index == len(edge_segments) - 1 else None,
                        start=start,
                        end=end,
                        index=index,
                    )
                )
        return tuple(segments)

    def _valid_outgoing_edge_ids(self, context: _ReadabilityContext, node_id: str) -> tuple[str, ...]:
        node = next((candidate for candidate in context.level.graph.nodes if candidate.id == node_id), None)
        if node is None:
            return ()
        return self.switch_classification_service.classify_node(node, context.edge_by_id).valid_outgoing_edge_ids

    def _first_segment_by_edge_id(self, segments: tuple[_SegmentRef, ...]) -> dict[str, _SegmentRef]:
        result: dict[str, _SegmentRef] = {}
        for segment in segments:
            if segment.index == 0 and segment.edge_id not in result:
                result[segment.edge_id] = segment
        return result

    def _layout_profile(self, context: _ReadabilityContext) -> str:
        return str(context.layout_metadata.get("layoutProfile", "") or "").strip().lower()

    def _portrait_metrics(self, context: _ReadabilityContext) -> dict[str, Any]:
        raw_metrics = context.layout_metadata.get("portraitMetrics")
        if isinstance(raw_metrics, dict):
            return {
                "width": float(raw_metrics.get("width", 0.0) or 0.0),
                "height": float(raw_metrics.get("height", 0.0) or 0.0),
                "aspectRatio": float(raw_metrics.get("aspectRatio", 999.0) or 999.0),
                "verticalSeparation": float(raw_metrics.get("verticalSeparation", 0.0) or 0.0),
                "startInLowerPortion": bool(raw_metrics.get("startInLowerPortion", False)),
                "destinationInUpperPortion": bool(raw_metrics.get("destinationInUpperPortion", False)),
            }

        if not context.positions:
            return {
                "width": 0.0,
                "height": 0.0,
                "aspectRatio": 999.0,
                "verticalSeparation": 0.0,
                "startInLowerPortion": False,
                "destinationInUpperPortion": False,
            }

        min_x = min(x for x, _ in context.positions.values())
        max_x = max(x for x, _ in context.positions.values())
        min_y = min(y for _, y in context.positions.values())
        max_y = max(y for _, y in context.positions.values())
        width = max_x - min_x
        height = max_y - min_y
        start_y = context.positions.get(context.level.startNodeID, (0.0, 0.0))[1]
        destination_y = context.positions.get(context.level.destinationNodeID, (0.0, 0.0))[1]
        lower_threshold = min_y + (height * 0.55)
        upper_threshold = min_y + (height * 0.45)
        return {
            "width": round(width, 4),
            "height": round(height, 4),
            "aspectRatio": round(width / height, 4) if height > self.point_tolerance else 999.0,
            "verticalSeparation": round(start_y - destination_y, 4),
            "startInLowerPortion": start_y >= lower_threshold,
            "destinationInUpperPortion": destination_y <= upper_threshold,
        }

    def _metadata_for(
        self,
        context: _ReadabilityContext,
        issues: tuple[LayoutReadabilityIssue, ...],
    ) -> dict[str, Any]:
        issue_codes = {issue.code for issue in issues}
        offending_nodes = sorted(
            {
                node_id
                for issue in issues
                for node_id in ((*issue.related_node_ids, issue.related_node_id) if issue.related_node_id else issue.related_node_ids)
                if node_id
            }
        )
        offending_roads = sorted(
            {
                edge_id
                for issue in issues
                for edge_id in ((*issue.related_edge_ids, issue.related_edge_id) if issue.related_edge_id else issue.related_edge_ids)
                if edge_id
            }
        )
        important_blocked = any(
            issue.code == "important_node_visibility_failure"
            or (issue.code == "node_spacing_failure" and bool(issue.details.get("importantNodeInvolved")))
            for issue in issues
        )
        measured_distances = [
            {
                "code": issue.code,
                "relatedNodeIDs": list(issue.related_node_ids),
                "relatedEdgeIDs": list(issue.related_edge_ids),
                "distance": issue.measured_distance,
                "threshold": issue.threshold,
            }
            for issue in issues
            if issue.measured_distance is not None
        ]
        measured_angles = [
            {
                "code": issue.code,
                "relatedNodeID": issue.related_node_id,
                "relatedEdgeIDs": list(issue.related_edge_ids),
                "angleDegrees": issue.measured_angle_degrees,
                "threshold": issue.threshold,
                "details": dict(issue.details),
            }
            for issue in issues
            if issue.measured_angle_degrees is not None
        ]
        return {
            "passed": not any(issue.severity == "error" for issue in issues),
            "nodeOverlapDetected": "node_spacing_failure" in issue_codes,
            "implicitIntersectionDetected": "implicit_intersection_without_node" in issue_codes,
            "roadsTooCloseDetected": "road_proximity_failure" in issue_codes,
            "switchExitOverlapDetected": "switch_exit_overlap" in issue_codes,
            "importantNodeBlocked": important_blocked,
            "startGoalTooClose": "start_goal_separation_failure" in issue_codes,
            "portraitSafetyFailure": "portrait_safety_failure" in issue_codes,
            "offendingNodes": offending_nodes,
            "offendingRoads": offending_roads,
            "measuredDistances": measured_distances,
            "measuredAngles": measured_angles,
            "thresholds": context.thresholds.to_dict(),
            "issueCounts": dict(Counter(issue.code for issue in issues)),
            "importantNodeIDs": list(context.important_node_ids),
            "switchNodeIDs": list(context.switch_node_ids),
            "segmentCount": len(context.segments),
            "layoutProfile": self._layout_profile(context) or None,
            "layoutSizeProfile": context.layout_metadata.get("layoutSizeProfile"),
        }

    def _dedupe_issues(self, issues: list[LayoutReadabilityIssue]) -> tuple[LayoutReadabilityIssue, ...]:
        deduped: list[LayoutReadabilityIssue] = []
        seen: set[tuple[Any, ...]] = set()
        for issue in issues:
            key = (
                issue.severity,
                issue.code,
                issue.related_node_id,
                issue.related_edge_id,
                issue.related_node_ids,
                issue.related_edge_ids,
                issue.details.get("rule"),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(issue)
        return tuple(deduped)

    def _segments_share_graph_node(self, first: _SegmentRef, second: _SegmentRef) -> bool:
        return bool({first.from_node_id, first.to_node_id} & {second.from_node_id, second.to_node_id})

    def _segments_have_visual_intersection(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
    ) -> bool:
        if self._segment_intersection_point(first, second) is not None:
            return True
        return self._segments_are_collinear(first, second) and self._projection_overlap_length(first, second) > self.point_tolerance

    def _segments_distance(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
    ) -> float:
        if self._segments_have_visual_intersection(first, second):
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
            and self._point_to_line_distance(point, segment) <= self.point_tolerance
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

    def _point_to_line_distance(
        self,
        point: tuple[float, float],
        segment: tuple[tuple[float, float], tuple[float, float]],
    ) -> float:
        (px, py) = point
        (x1, y1), (x2, y2) = segment
        denominator = self._point_distance((x1, y1), (x2, y2))
        if denominator <= self.point_tolerance:
            return self._point_distance(point, (x1, y1))
        return abs(((x2 - x1) * (y1 - py)) - ((x1 - px) * (y2 - y1))) / denominator

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

    def _node_at_point(
        self,
        point: tuple[float, float],
        positions: dict[str, tuple[float, float]],
    ) -> str | None:
        return next(
            (
                node_id
                for node_id, position in positions.items()
                if self._point_distance(point, position) <= self.point_tolerance
            ),
            None,
        )

    def _segment_angle_degrees(
        self,
        segment: tuple[tuple[float, float], tuple[float, float]],
    ) -> float:
        start, end = segment
        return math.degrees(math.atan2(end[1] - start[1], end[0] - start[0])) % 360.0

    def _angle_separation_degrees(self, first: float, second: float) -> float:
        raw = abs((first - second) % 360.0)
        return min(raw, 360.0 - raw)

    def _point_distance(self, first: tuple[float, float], second: tuple[float, float]) -> float:
        return math.hypot(first[0] - second[0], first[1] - second[1])
