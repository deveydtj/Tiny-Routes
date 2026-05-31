from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

from .road_shape_service import RoadShapeService
from .route_timing_service import RouteTimingService
from .switch_classification_service import SwitchClassificationService
from .switch_visual_clarity_service import SwitchVisualClarityService

VisualClaritySeverity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class VisualClarityIssue:
    severity: VisualClaritySeverity
    code: str
    message: str
    related_node_id: str | None = None
    related_edge_id: str | None = None
    related_edge_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class VisualClarityReport:
    issues: tuple[VisualClarityIssue, ...]
    score: float
    metadata: dict

    @property
    def errors(self) -> tuple[VisualClarityIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[VisualClarityIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

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
    required_path_edge: bool


class VisualClarityValidationService:
    node_spacing_distance = 0.28
    switch_spacing_distance = 0.25
    tap_target_spacing_distance = 0.38
    important_node_spacing_distance = 0.25
    important_node_clearance = 0.22
    switch_crossing_clearance = 0.26
    arrow_collision_clearance = 0.18
    parallel_merge_distance = 0.16
    long_parallel_overlap = 0.35
    main_route_dead_end_ratio = 0.80
    small_device_spacing_distance = 0.32
    point_tolerance = 1e-9

    def __init__(self) -> None:
        self.road_shape = RoadShapeService()
        self.route_timing = RouteTimingService()
        self.switch_classification = SwitchClassificationService()
        self.switch_visual_clarity = SwitchVisualClarityService()

    def report_for_generated_level(self, generated_level) -> VisualClarityReport:
        required_path = tuple(getattr(getattr(generated_level, "abstract_solution_metadata", None), "required_path", ()) or ())
        return self.report_for_level(generated_level.level_document, generated_level.solution, required_path=required_path)

    def report_for_level(self, level, solution=None, required_path: tuple[str, ...] = ()) -> VisualClarityReport:
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        positions = {node.id: (float(node.x), float(node.y)) for node in level.graph.nodes}
        resolved_required_path = required_path or self._required_path_from_solution_metadata(solution) or ()
        required_edge_pairs = set(zip(resolved_required_path, resolved_required_path[1:]))
        required_edge_ids = {
            edge.id
            for edge in level.graph.edges
            if (edge.fromNodeID, edge.toNodeID) in required_edge_pairs
        }
        important_node_ids = tuple(
            node_id
            for node_id in (level.startNodeID, level.packageNodeID, level.destinationNodeID)
            if node_id in positions
        )
        switch_node_ids = tuple(
            node.id
            for node in level.graph.nodes
            if self.switch_classification.classify_node(node, edge_by_id).is_switchable
        )
        segments = self._segments_for_level(level, positions, required_edge_ids)

        issues: list[VisualClarityIssue] = []
        issues.extend(self._switch_issues(level, switch_node_ids, positions, segments))
        issues.extend(self._visual_topology_issues(segments, positions))
        issues.extend(self._route_crossing_issues(segments, positions, important_node_ids, switch_node_ids, required_edge_ids))
        issues.extend(self._route_overlap_issues(segments, switch_node_ids, edge_by_id))
        issues.extend(self._node_spacing_issues(positions, important_node_ids))
        issues.extend(self._tap_target_spacing_issues(positions, switch_node_ids))
        issues.extend(self._important_node_readability_issues(positions, important_node_ids, segments))
        issues.extend(self._mobile_ui_issues(level, positions, switch_node_ids, important_node_ids, segments))
        issues.extend(self._route_flow_issues(level, positions, edge_by_id, resolved_required_path, required_edge_ids, switch_node_ids))

        deduped_issues = tuple(dict.fromkeys(issues))
        score = self._score(deduped_issues)
        metadata = {
            "issueCounts": dict(Counter(issue.severity for issue in deduped_issues)),
            "requiredPath": list(resolved_required_path),
            "importantNodeIDs": list(important_node_ids),
            "switchNodeIDs": list(switch_node_ids),
            "segmentCount": len(segments),
        }
        return VisualClarityReport(issues=deduped_issues, score=score, metadata=metadata)

    def _switch_issues(
        self,
        level,
        switch_node_ids: tuple[str, ...],
        positions: dict[str, tuple[float, float]],
        segments: tuple[_SegmentRef, ...],
    ) -> list[VisualClarityIssue]:
        issues: list[VisualClarityIssue] = []
        switch_reports = self.switch_visual_clarity.report_for_level(level)
        for report in switch_reports:
            for direction in report.directions:
                if direction.is_ambiguous:
                    issues.append(
                        VisualClarityIssue(
                            severity="error",
                            code="switch_choice_visual_direction_ambiguous",
                            message=(
                                f"Switch '{report.switch_id}' edge '{direction.edge_id}' has ambiguous "
                                f"visual direction: {direction.ambiguous_reason or 'unknown'}."
                            ),
                            related_node_id=report.switch_id,
                            related_edge_id=direction.edge_id,
                        )
                    )
            for bucket, edge_ids in sorted(report.duplicate_buckets.items()):
                issues.append(
                    VisualClarityIssue(
                        severity="error",
                        code="switch_choices_same_visual_direction",
                        message=(
                            f"Switch '{report.switch_id}' has multiple outgoing choices in the "
                            f"{bucket} visual bucket: {', '.join(edge_ids)}."
                        ),
                        related_node_id=report.switch_id,
                        related_edge_id=edge_ids[0] if edge_ids else None,
                        related_edge_ids=tuple(edge_ids),
                    )
                )
            if report.directions:
                active_direction = report.directions[0]
                if active_direction.is_ambiguous or active_direction.bucket in report.duplicate_buckets:
                    issues.append(
                        VisualClarityIssue(
                            severity="error",
                            code="ambiguous_active_edge_arrow",
                            message=f"Switch '{report.switch_id}' starts on an active edge whose arrow is not uniquely readable.",
                            related_node_id=report.switch_id,
                            related_edge_id=active_direction.edge_id,
                        )
                    )
                hidden_by = self._edge_visually_hidden_by_another_road(active_direction.edge_id, segments)
                if hidden_by is not None:
                    issues.append(
                        VisualClarityIssue(
                            severity="warning",
                            code="active_edge_visually_hidden_under_another_road",
                            message=(
                                f"Switch '{report.switch_id}' active edge '{active_direction.edge_id}' visually merges "
                                f"with edge '{hidden_by}'."
                            ),
                            related_node_id=report.switch_id,
                            related_edge_id=active_direction.edge_id,
                            related_edge_ids=(active_direction.edge_id, hidden_by),
                        )
                    )
            buckets = {direction.bucket for direction in report.directions if direction.bucket is not None}
            if len(report.directions) == 4 and buckets != {"north", "east", "south", "west"}:
                issues.append(
                    VisualClarityIssue(
                        severity="error",
                        code="four_way_switch_missing_clear_cardinal_options",
                        message=f"4-way switch '{report.switch_id}' does not expose one clear north/east/south/west choice.",
                        related_node_id=report.switch_id,
                    )
                )

        for first_index, first_id in enumerate(switch_node_ids):
            for second_id in switch_node_ids[first_index + 1:]:
                if self._point_distance(positions[first_id], positions[second_id]) < self.switch_spacing_distance:
                    issues.append(
                        VisualClarityIssue(
                            severity="error",
                            code="switch_too_close_to_another_switch",
                            message=f"Switches '{first_id}' and '{second_id}' are too close to read independently.",
                            related_node_id=first_id,
                        )
                    )
        return issues

    def _visual_topology_issues(
        self,
        segments: tuple[_SegmentRef, ...],
        positions: dict[str, tuple[float, float]],
    ) -> list[VisualClarityIssue]:
        issues: list[VisualClarityIssue] = []

        for segment in segments:
            for node_id, position in positions.items():
                if node_id in {segment.from_node_id, segment.to_node_id}:
                    continue
                if self._point_lies_on_segment(position, (segment.start, segment.end)):
                    issues.append(
                        VisualClarityIssue(
                            severity="error",
                            code="road_crosses_through_unconnected_node",
                            message=f"Edge '{segment.edge_id}' visually crosses node '{node_id}' without a graph connection.",
                            related_node_id=node_id,
                            related_edge_id=segment.edge_id,
                        )
                    )

        for first_index, first in enumerate(segments):
            for second in segments[first_index + 1:]:
                if first.edge_id == second.edge_id or {first.from_node_id, first.to_node_id} & {second.from_node_id, second.to_node_id}:
                    continue

                first_segment = (first.start, first.end)
                second_segment = (second.start, second.end)
                if self._segments_are_collinear(first_segment, second_segment):
                    if self._projection_overlap_length(first_segment, second_segment) > self.point_tolerance:
                        issues.append(
                            VisualClarityIssue(
                                severity="error",
                                code="unconnected_parallel_road_overlap",
                                message=f"Edges '{first.edge_id}' and '{second.edge_id}' overlap without a graph connection.",
                                related_edge_id=first.edge_id,
                                related_edge_ids=(first.edge_id, second.edge_id),
                            )
                        )
                    continue

                intersection = self._segment_intersection_point(first_segment, second_segment)
                if intersection is None:
                    continue

                endpoint_touch = self._unconnected_endpoint_touch(first, second, intersection)
                if endpoint_touch is not None:
                    touched_node_id, touched_edge_id = endpoint_touch
                    issues.append(
                        VisualClarityIssue(
                            severity="error",
                            code="unconnected_road_endpoint_touches_segment",
                            message=f"Endpoint node '{touched_node_id}' touches edge '{touched_edge_id}' without a graph connection.",
                            related_node_id=touched_node_id,
                            related_edge_id=touched_edge_id,
                            related_edge_ids=(first.edge_id, second.edge_id),
                        )
                    )
                    continue

                graph_node_id = self._node_at_point(intersection, positions)
                if graph_node_id is None:
                    issues.append(
                        VisualClarityIssue(
                            severity="error",
                            code="implicit_intersection_without_graph_node",
                            message=(
                                f"Edges '{first.edge_id}' and '{second.edge_id}' visually intersect "
                                "without an intersection node."
                            ),
                            related_edge_id=first.edge_id,
                            related_edge_ids=(first.edge_id, second.edge_id),
                        )
                    )
        return issues

    def _route_crossing_issues(
        self,
        segments: tuple[_SegmentRef, ...],
        positions: dict[str, tuple[float, float]],
        important_node_ids: tuple[str, ...],
        switch_node_ids: tuple[str, ...],
        required_edge_ids: set[str],
    ) -> list[VisualClarityIssue]:
        issues: list[VisualClarityIssue] = []
        crossing_count = 0
        required_crossing_count = 0
        required_self_crossing_count = 0
        for first_index, first in enumerate(segments):
            for second in segments[first_index + 1:]:
                if first.edge_id == second.edge_id or {first.from_node_id, first.to_node_id} & {second.from_node_id, second.to_node_id}:
                    continue
                intersection = self._segment_intersection_point((first.start, first.end), (second.start, second.end))
                if intersection is None:
                    continue
                crossing_count += 1
                first_required = first.edge_id in required_edge_ids
                second_required = second.edge_id in required_edge_ids
                if first_required or second_required:
                    required_crossing_count += 1
                if first_required and second_required:
                    required_self_crossing_count += 1
                nearby_switch = self._nearby_node(intersection, positions, switch_node_ids, self.switch_crossing_clearance)
                if nearby_switch is not None:
                    issues.append(
                        VisualClarityIssue(
                            severity="warning",
                            code="wrong_route_crosses_required_route_near_switch" if first_required != second_required else "route_crossing_near_switch",
                            message=f"Road crossing near switch '{nearby_switch}' is visually confusing.",
                            related_node_id=nearby_switch,
                            related_edge_id=first.edge_id,
                            related_edge_ids=(first.edge_id, second.edge_id),
                        )
                    )
                nearby_important = self._nearby_node(intersection, positions, important_node_ids, self.important_node_clearance)
                if nearby_important is not None:
                    issues.append(
                        VisualClarityIssue(
                            severity="error",
                            code="route_crossing_near_important_node",
                            message=f"Road crossing near important node '{nearby_important}' competes with the goal flow.",
                            related_node_id=nearby_important,
                            related_edge_id=first.edge_id,
                            related_edge_ids=(first.edge_id, second.edge_id),
                        )
                    )

        if required_self_crossing_count > 2:
            issues.append(
                VisualClarityIssue(
                    severity="error",
                    code="required_path_crosses_itself_too_much",
                    message=f"Required path has {required_self_crossing_count} self-crossings.",
                )
            )
        elif required_self_crossing_count > 0:
            issues.append(
                VisualClarityIssue(
                    severity="warning",
                    code="required_path_self_crossing",
                    message=f"Required path has {required_self_crossing_count} self-crossing.",
                )
            )
        decorative_crossings = max(0, crossing_count - required_crossing_count)
        if decorative_crossings > 2:
            issues.append(
                VisualClarityIssue(
                    severity="warning",
                    code="route_has_many_decorative_crossings",
                    message=f"Layout has {decorative_crossings} non-required road crossings.",
                )
            )
        elif decorative_crossings > 0:
            issues.append(
                VisualClarityIssue(
                    severity="info",
                    code="route_has_decorative_crossings",
                    message=f"Layout has {decorative_crossings} non-required road crossing.",
                )
            )
        return issues

    def _route_overlap_issues(
        self,
        segments: tuple[_SegmentRef, ...],
        switch_node_ids: tuple[str, ...],
        edge_by_id: dict[str, object],
    ) -> list[VisualClarityIssue]:
        issues: list[VisualClarityIssue] = []
        first_segment_by_edge = {
            segment.edge_id: segment
            for segment in segments
            if segment.index == 0
        }
        outgoing_by_switch: dict[str, list[str]] = {}
        for edge_id, edge in edge_by_id.items():
            if edge.fromNodeID in switch_node_ids:
                outgoing_by_switch.setdefault(edge.fromNodeID, []).append(edge_id)
        for switch_id, edge_ids in outgoing_by_switch.items():
            for first_index, first_edge_id in enumerate(edge_ids):
                for second_edge_id in edge_ids[first_index + 1:]:
                    first = first_segment_by_edge.get(first_edge_id)
                    second = first_segment_by_edge.get(second_edge_id)
                    if first is None or second is None:
                        continue
                    if self._same_origin_segments_visually_overlap(first, second):
                        issues.append(
                            VisualClarityIssue(
                                severity="error",
                                code="overlapping_first_segments_from_same_switch",
                                message=f"Switch '{switch_id}' has outgoing roads that initially overlap.",
                                related_node_id=switch_id,
                                related_edge_id=first_edge_id,
                                related_edge_ids=(first_edge_id, second_edge_id),
                            )
                        )

        for first_index, first in enumerate(segments):
            for second in segments[first_index + 1:]:
                if first.edge_id == second.edge_id or {first.from_node_id, first.to_node_id} & {second.from_node_id, second.to_node_id}:
                    continue
                if self._segments_are_tight_parallel((first.start, first.end), (second.start, second.end)):
                    issues.append(
                        VisualClarityIssue(
                            severity="warning",
                            code="long_parallel_road_segments_visually_merge",
                            message=f"Edges '{first.edge_id}' and '{second.edge_id}' have parallel segments that can read as one road.",
                            related_edge_id=first.edge_id,
                            related_edge_ids=(first.edge_id, second.edge_id),
                        )
                    )
        return issues

    def _node_spacing_issues(
        self,
        positions: dict[str, tuple[float, float]],
        important_node_ids: tuple[str, ...],
    ) -> list[VisualClarityIssue]:
        issues: list[VisualClarityIssue] = []
        node_ids = tuple(positions)
        important_set = set(important_node_ids)
        for first_index, first_id in enumerate(node_ids):
            for second_id in node_ids[first_index + 1:]:
                distance = self._point_distance(positions[first_id], positions[second_id])
                minimum = self.important_node_spacing_distance if first_id in important_set or second_id in important_set else self.node_spacing_distance
                if distance >= minimum:
                    continue
                issues.append(
                    VisualClarityIssue(
                        severity="error" if first_id in important_set or second_id in important_set else "warning",
                        code="important_nodes_too_close" if first_id in important_set or second_id in important_set else "nodes_too_close",
                        message=f"Nodes '{first_id}' and '{second_id}' are only {distance:.2f} board units apart.",
                        related_node_id=first_id,
                    )
                )
        return issues

    def _tap_target_spacing_issues(
        self,
        positions: dict[str, tuple[float, float]],
        switch_node_ids: tuple[str, ...],
    ) -> list[VisualClarityIssue]:
        issues: list[VisualClarityIssue] = []
        for first_index, first_id in enumerate(switch_node_ids):
            for second_id in switch_node_ids[first_index + 1:]:
                distance = self._point_distance(positions[first_id], positions[second_id])
                if distance < self.tap_target_spacing_distance:
                    issues.append(
                        VisualClarityIssue(
                            severity="error",
                            code="switch_tap_targets_too_close",
                            message=f"Switch tap targets '{first_id}' and '{second_id}' are too close on mobile screens.",
                            related_node_id=first_id,
                        )
                    )
        return issues

    def _important_node_readability_issues(
        self,
        positions: dict[str, tuple[float, float]],
        important_node_ids: tuple[str, ...],
        segments: tuple[_SegmentRef, ...],
    ) -> list[VisualClarityIssue]:
        issues: list[VisualClarityIssue] = []
        for node_id in important_node_ids:
            for segment in segments:
                if node_id in {segment.from_node_id, segment.to_node_id}:
                    continue
                if self._point_to_segment_distance(positions[node_id], (segment.start, segment.end)) < self.important_node_clearance:
                    issues.append(
                        VisualClarityIssue(
                            severity="error",
                            code="important_node_readability_blocked_by_road",
                            message=f"Important node '{node_id}' is too close to edge '{segment.edge_id}'.",
                            related_node_id=node_id,
                            related_edge_id=segment.edge_id,
                        )
                    )
        return issues

    def _mobile_ui_issues(
        self,
        level,
        positions: dict[str, tuple[float, float]],
        switch_node_ids: tuple[str, ...],
        important_node_ids: tuple[str, ...],
        segments: tuple[_SegmentRef, ...],
    ) -> list[VisualClarityIssue]:
        issues: list[VisualClarityIssue] = []
        for switch_id in switch_node_ids:
            for node_id in important_node_ids:
                if switch_id == node_id:
                    continue
                if self._point_distance(positions[switch_id], positions[node_id]) < self.small_device_spacing_distance:
                    issues.append(
                        VisualClarityIssue(
                            severity="warning",
                            code="important_nodes_tight_on_small_device",
                            message=f"Switch '{switch_id}' is tight against important node '{node_id}' at small-device scale.",
                            related_node_id=switch_id,
                        )
                    )

        for edge in level.graph.edges:
            if edge.fromNodeID not in switch_node_ids or edge.fromNodeID not in positions:
                continue
            first_segment = next((segment for segment in segments if segment.edge_id == edge.id and segment.index == 0), None)
            if first_segment is None:
                continue
            arrow_anchor = self._point_along_segment((first_segment.start, first_segment.end), 0.16)
            for node_id in important_node_ids:
                if node_id == edge.fromNodeID or node_id not in positions:
                    continue
                if self._point_distance(arrow_anchor, positions[node_id]) < self.arrow_collision_clearance:
                    issues.append(
                        VisualClarityIssue(
                            severity="warning",
                            code="arrow_icon_may_collide_with_node_label_or_package",
                            message=f"Arrow for edge '{edge.id}' may collide with node '{node_id}' artwork or label.",
                            related_node_id=edge.fromNodeID,
                            related_edge_id=edge.id,
                        )
                    )
        return issues

    def _route_flow_issues(
        self,
        level,
        positions: dict[str, tuple[float, float]],
        edge_by_id: dict[str, object],
        required_path: tuple[str, ...],
        required_edge_ids: set[str],
        switch_node_ids: tuple[str, ...],
    ) -> list[VisualClarityIssue]:
        if not required_path:
            return []
        issues: list[VisualClarityIssue] = []
        required_pairs = set(zip(required_path, required_path[1:]))
        required_successor_by_node = {
            from_node_id: to_node_id
            for from_node_id, to_node_id in required_pairs
        }
        edge_by_pair = {
            (edge.fromNodeID, edge.toNodeID): edge
            for edge in edge_by_id.values()
        }

        for edge in edge_by_id.values():
            if edge.id in required_edge_ids or edge.fromNodeID not in required_successor_by_node:
                continue
            required_edge = edge_by_pair.get((edge.fromNodeID, required_successor_by_node[edge.fromNodeID]))
            if required_edge is None:
                continue
            try:
                wrong_angle = self.route_timing.direction_angle(positions[edge.fromNodeID], positions[edge.toNodeID], edge.roadShape)
                required_angle = self.route_timing.direction_angle(
                    positions[required_edge.fromNodeID],
                    positions[required_edge.toNodeID],
                    required_edge.roadShape,
                )
            except ValueError:
                continue
            wrong_length = self._route_edge_length(positions, edge)
            required_length = self._route_edge_length(positions, required_edge)
            if self.route_timing.angles_match(wrong_angle, required_angle) and wrong_length >= required_length * self.main_route_dead_end_ratio:
                issues.append(
                    VisualClarityIssue(
                        severity="warning",
                        code="dead_end_looks_like_main_route",
                        message=f"Dead-end edge '{edge.id}' leaves '{edge.fromNodeID}' like the required route.",
                        related_node_id=edge.fromNodeID,
                        related_edge_id=edge.id,
                    )
                )

        if len(set(required_path)) < len(required_path):
            repeated_nodes = [node_id for node_id, count in Counter(required_path).items() if count > 1]
            for node_id in repeated_nodes:
                if node_id in switch_node_ids:
                    issues.append(
                        VisualClarityIssue(
                            severity="warning",
                            code="return_loop_visually_unclear",
                            message=f"Return loop revisits switch '{node_id}', which can obscure the intended route flow.",
                            related_node_id=node_id,
                        )
                    )

        if level.packageNodeID in positions:
            package_index = required_path.index(level.packageNodeID) if level.packageNodeID in required_path else -1
            if package_index > 0:
                previous_node_id = required_path[package_index - 1]
                next_node_id = required_path[package_index + 1] if package_index + 1 < len(required_path) else None
                nearby_route_nodes = [node_id for node_id in (previous_node_id, next_node_id) if node_id in positions]
                if nearby_route_nodes:
                    nearest_flow_distance = min(
                        self._point_distance(positions[level.packageNodeID], positions[node_id])
                        for node_id in nearby_route_nodes
                    )
                    if nearest_flow_distance > 1.35:
                        issues.append(
                            VisualClarityIssue(
                                severity="warning",
                                code="package_off_visual_flow_without_intent",
                                message=f"Package node '{level.packageNodeID}' sits far from adjacent required-route nodes.",
                                related_node_id=level.packageNodeID,
                            )
                        )
        return issues

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
            try:
                edge_segments = self.road_shape._segments_for_edge(
                    positions[edge.fromNodeID],
                    positions[edge.toNodeID],
                    edge.roadShape,
                )
            except ValueError:
                continue
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
                        required_path_edge=edge.id in required_edge_ids,
                    )
                )
        return tuple(segments)

    def _required_path_from_solution_metadata(self, solution) -> tuple[str, ...]:
        metadata = getattr(solution, "abstract_solution_metadata", None)
        required_path = getattr(metadata, "required_path", None)
        return tuple(required_path or ())

    def _edge_visually_hidden_by_another_road(self, edge_id: str, segments: tuple[_SegmentRef, ...]) -> str | None:
        edge_segments = [segment for segment in segments if segment.edge_id == edge_id]
        if not edge_segments:
            return None
        first_segment = edge_segments[0]
        for other in segments:
            if other.edge_id == edge_id or {first_segment.from_node_id, first_segment.to_node_id} & {other.from_node_id, other.to_node_id}:
                continue
            first = (first_segment.start, first_segment.end)
            second = (other.start, other.end)
            if self._segments_are_collinear(first, second) and self._projection_overlap_length(first, second) > self.point_tolerance:
                return other.edge_id
        return None

    def _same_origin_segments_visually_overlap(self, first: _SegmentRef, second: _SegmentRef) -> bool:
        first_segment = (first.start, first.end)
        second_segment = (second.start, second.end)
        return (
            self._segments_are_collinear(first_segment, second_segment)
            and self._projection_overlap_length(first_segment, second_segment) > self.point_tolerance
        )

    def _route_edge_length(self, positions: dict[str, tuple[float, float]], edge) -> float:
        return self.route_timing.edge_length(positions[edge.fromNodeID], positions[edge.toNodeID], edge.roadShape)

    def _nearby_node(
        self,
        point: tuple[float, float],
        positions: dict[str, tuple[float, float]],
        node_ids: tuple[str, ...],
        distance: float,
    ) -> str | None:
        return next(
            (
                node_id
                for node_id in node_ids
                if node_id in positions and self._point_distance(point, positions[node_id]) < distance
            ),
            None,
        )

    def _score(self, issues: tuple[VisualClarityIssue, ...]) -> float:
        score = 1.0
        for issue in issues:
            if issue.severity == "error":
                score -= 0.22
            elif issue.severity == "warning":
                score -= 0.08
            else:
                score -= 0.02
        return round(max(0.0, min(1.0, score)), 4)

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

    def _point_lies_on_segment(
        self,
        point: tuple[float, float],
        segment: tuple[tuple[float, float], tuple[float, float]],
    ) -> bool:
        return (
            self._point_on_segment(point, segment)
            and self._point_to_segment_distance(point, segment) <= self.point_tolerance
        )

    def _point_matches(self, first: tuple[float, float], second: tuple[float, float]) -> bool:
        return self._point_distance(first, second) <= self.point_tolerance

    def _node_at_point(
        self,
        point: tuple[float, float],
        positions: dict[str, tuple[float, float]],
    ) -> str | None:
        return next(
            (
                node_id
                for node_id, position in positions.items()
                if self._point_matches(point, position)
            ),
            None,
        )

    def _unconnected_endpoint_touch(
        self,
        first: _SegmentRef,
        second: _SegmentRef,
        intersection: tuple[float, float],
    ) -> tuple[str, str] | None:
        for node_id, endpoint in ((first.start_node_id, first.start), (first.end_node_id, first.end)):
            if node_id is not None and self._point_matches(endpoint, intersection):
                return (node_id, second.edge_id)
        for node_id, endpoint in ((second.start_node_id, second.start), (second.end_node_id, second.end)):
            if node_id is not None and self._point_matches(endpoint, intersection):
                return (node_id, first.edge_id)
        return None

    def _segments_overlap(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
    ) -> bool:
        if self._segment_intersection_point(first, second) is not None:
            return True
        return self._segments_are_collinear(first, second) and self._projection_overlap_length(first, second) > self.point_tolerance

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

    def _segments_are_tight_parallel(
        self,
        first: tuple[tuple[float, float], tuple[float, float]],
        second: tuple[tuple[float, float], tuple[float, float]],
    ) -> bool:
        if self._segments_are_collinear(first, second):
            return self._projection_overlap_length(first, second) > self.long_parallel_overlap
        first_horizontal = abs(first[0][1] - first[1][1]) <= self.point_tolerance
        second_horizontal = abs(second[0][1] - second[1][1]) <= self.point_tolerance
        first_vertical = abs(first[0][0] - first[1][0]) <= self.point_tolerance
        second_vertical = abs(second[0][0] - second[1][0]) <= self.point_tolerance
        if first_horizontal and second_horizontal:
            return abs(first[0][1] - second[0][1]) < self.parallel_merge_distance and self._projection_overlap_length(first, second) > self.long_parallel_overlap
        if first_vertical and second_vertical:
            return abs(first[0][0] - second[0][0]) < self.parallel_merge_distance and self._projection_overlap_length(first, second) > self.long_parallel_overlap
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
        (px, py) = point
        (x1, y1), (x2, y2) = segment
        dx = x2 - x1
        dy = y2 - y1
        if abs(dx) <= self.point_tolerance and abs(dy) <= self.point_tolerance:
            return math.hypot(px - x1, py - y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / ((dx * dx) + (dy * dy))))
        nearest = (x1 + (t * dx), y1 + (t * dy))
        return math.hypot(px - nearest[0], py - nearest[1])

    def _point_distance(self, first: tuple[float, float], second: tuple[float, float]) -> float:
        return math.hypot(first[0] - second[0], first[1] - second[1])

    def _point_along_segment(
        self,
        segment: tuple[tuple[float, float], tuple[float, float]],
        distance: float,
    ) -> tuple[float, float]:
        start, end = segment
        length = self._point_distance(start, end)
        if length <= self.point_tolerance:
            return start
        scale = min(1.0, distance / length)
        return (start[0] + ((end[0] - start[0]) * scale), start[1] + ((end[1] - start[1]) * scale))
