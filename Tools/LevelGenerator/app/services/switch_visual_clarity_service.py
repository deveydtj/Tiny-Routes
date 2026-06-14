from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .switch_direction_assignment_service import SwitchDirectionAssignmentService
from .route_timing_service import RouteTimingService
from .switch_classification_service import SwitchClassificationService


@dataclass(frozen=True)
class SwitchVisualDirection:
    edge_id: str
    target_node_id: str
    bucket: str | None
    angle: float | None
    angle_degrees: float | None = None
    first_segment_length: float | None = None
    nearest_bucket_separation_degrees: float | None = None
    ambiguous_reason: str | None = None

    @property
    def is_ambiguous(self) -> bool:
        return self.ambiguous_reason is not None or self.bucket is None or self.angle is None


@dataclass(frozen=True)
class SwitchVisualClarityIssue:
    code: str
    message: str
    node_id: str
    edge_id: str | None = None


@dataclass(frozen=True)
class SwitchVisualClarityReport:
    switch_id: str
    directions: list[SwitchVisualDirection] = field(default_factory=list)
    issues: tuple[str, ...] = field(default_factory=tuple)
    minimum_exit_angle_separation_degrees: float | None = None
    quality: float = 1.0

    @property
    def duplicate_buckets(self) -> dict[str, list[str]]:
        bucket_counts = Counter(direction.bucket for direction in self.directions if direction.bucket is not None)
        return {
            bucket: [
                direction.edge_id
                for direction in self.directions
                if direction.bucket == bucket
            ]
            for bucket, count in bucket_counts.items()
            if count > 1
        }


class SwitchVisualClarityService:
    vector_magnitude_tolerance = 1e-9

    def __init__(self) -> None:
        self.route_timing = RouteTimingService()
        self.switch_classification = SwitchClassificationService()
        self.switch_direction_assignment = SwitchDirectionAssignmentService()

    def report_for_level(self, level) -> list[SwitchVisualClarityReport]:
        node_by_id = {node.id: node for node in level.graph.nodes}
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        reports: list[SwitchVisualClarityReport] = []

        for node in level.graph.nodes:
            classification = self.switch_classification.classify_node(node, edge_by_id)
            if not classification.is_switchable:
                continue

            assignment_report = self.switch_direction_assignment.report_for_switch(
                node,
                [
                    edge_by_id[edge_id]
                    for edge_id in classification.valid_outgoing_edge_ids
                    if edge_id in edge_by_id
                ],
                node_by_id,
            )
            directions = [
                SwitchVisualDirection(
                    edge_id=assignment.edge_id,
                    target_node_id=assignment.target_node_id,
                    bucket=assignment.bucket,
                    angle=assignment.angle,
                    angle_degrees=assignment.angle_degrees,
                    first_segment_length=assignment.first_segment_length,
                    nearest_bucket_separation_degrees=assignment.nearest_bucket_separation_degrees,
                    ambiguous_reason=assignment.ambiguous_reason,
                )
                for assignment in assignment_report.assignments
            ]
            reports.append(
                SwitchVisualClarityReport(
                    switch_id=node.id,
                    directions=directions,
                    issues=assignment_report.issues,
                    minimum_exit_angle_separation_degrees=assignment_report.minimum_exit_angle_separation_degrees,
                    quality=assignment_report.quality,
                )
            )

        return reports

    def issues_for_level(self, level, solution=None) -> list[SwitchVisualClarityIssue]:
        reports = self.report_for_level(level)
        reports_by_switch_id = {report.switch_id: report for report in reports}
        issues: list[SwitchVisualClarityIssue] = []

        for report in reports:
            for direction in report.directions:
                if not direction.is_ambiguous:
                    continue
                issues.append(
                    SwitchVisualClarityIssue(
                        code="ambiguous_switch_exit",
                        message=(
                            f"Switch '{report.switch_id}' edge '{direction.edge_id}' has no clearly readable exit: "
                            f"{direction.ambiguous_reason or 'unknown'}."
                        ),
                        node_id=report.switch_id,
                        edge_id=direction.edge_id,
                    )
                )
                issues.append(
                    SwitchVisualClarityIssue(
                        code="switch_choice_visual_direction_ambiguous",
                        message=(
                            f"Switch '{report.switch_id}' edge '{direction.edge_id}' has ambiguous "
                            f"visual direction: {direction.ambiguous_reason or 'unknown'}."
                        ),
                        node_id=report.switch_id,
                        edge_id=direction.edge_id,
                    )
                )

            for bucket, edge_ids in sorted(report.duplicate_buckets.items()):
                issues.append(
                    SwitchVisualClarityIssue(
                        code="conflicting_direction_bucket",
                        message=(
                            f"Switch '{report.switch_id}' has multiple outgoing choices in the "
                            f"{bucket} visual bucket: {', '.join(edge_ids)}."
                        ),
                        node_id=report.switch_id,
                        edge_id=edge_ids[0] if edge_ids else None,
                    )
                )
                issues.append(
                    SwitchVisualClarityIssue(
                        code="switch_choices_same_visual_direction",
                        message=(
                            f"Switch '{report.switch_id}' has multiple outgoing choices in the "
                            f"{bucket} visual bucket: {', '.join(edge_ids)}."
                        ),
                        node_id=report.switch_id,
                        edge_id=edge_ids[0] if edge_ids else None,
                    )
                )
            for issue in report.issues:
                if not issue.startswith("insufficient_exit_separation"):
                    continue
                _, _, edge_id = issue.split(":", 2)
                issues.append(
                    SwitchVisualClarityIssue(
                        code="insufficient_exit_separation",
                        message=f"Switch '{report.switch_id}' edge '{edge_id}' is too close to another exit direction.",
                        node_id=report.switch_id,
                        edge_id=edge_id,
                    )
                )

        if solution is not None:
            issues.extend(self._solution_tap_issues(solution, reports_by_switch_id))

        return issues

    def _solution_tap_issues(self, solution, reports_by_switch_id) -> list[SwitchVisualClarityIssue]:
        issues: list[SwitchVisualClarityIssue] = []
        active_indices_by_switch_id = {
            switch_id: 0
            for switch_id in reports_by_switch_id
        }
        duplicate_buckets_by_switch_id = {
            switch_id: set(report.duplicate_buckets)
            for switch_id, report in reports_by_switch_id.items()
        }

        for action in sorted(solution.actions, key=lambda action: float(action.timeSeconds)):
            report = reports_by_switch_id.get(action.tapNodeID)
            if report is None or not report.directions:
                continue

            active_indices_by_switch_id[report.switch_id] = (
                active_indices_by_switch_id[report.switch_id] + 1
            ) % len(report.directions)
            direction = report.directions[active_indices_by_switch_id[report.switch_id]]
            if (
                direction.is_ambiguous
                or direction.bucket in duplicate_buckets_by_switch_id[report.switch_id]
            ):
                issues.append(
                    SwitchVisualClarityIssue(
                        code="solution_tap_cycles_to_visually_confusing_edge",
                        message=(
                            f"Solution tap on switch '{report.switch_id}' cycles to edge "
                            f"'{direction.edge_id}', whose visual direction is not uniquely readable."
                        ),
                        node_id=report.switch_id,
                        edge_id=direction.edge_id,
                    )
                )

        return issues

    def _direction_for_edge(self, source_node, edge, node_by_id) -> SwitchVisualDirection:
        target_node = node_by_id.get(edge.toNodeID)
        if target_node is None:
            return SwitchVisualDirection(
                edge_id=edge.id,
                target_node_id=edge.toNodeID,
                bucket=None,
                angle=None,
                ambiguous_reason="missing target node",
            )

        dx = float(target_node.x) - float(source_node.x)
        dy = float(target_node.y) - float(source_node.y)
        if abs(dx) <= self.vector_magnitude_tolerance and abs(dy) <= self.vector_magnitude_tolerance:
            return SwitchVisualDirection(
                edge_id=edge.id,
                target_node_id=edge.toNodeID,
                bucket=None,
                angle=None,
                ambiguous_reason="zero-length road path",
            )

        try:
            angle = self.route_timing.direction_angle(source_node, target_node, edge.roadShape)
        except ValueError as exc:
            return SwitchVisualDirection(
                edge_id=edge.id,
                target_node_id=edge.toNodeID,
                bucket=None,
                angle=None,
                ambiguous_reason=str(exc),
            )

        return SwitchVisualDirection(
            edge_id=edge.id,
            target_node_id=edge.toNodeID,
            bucket=self.route_timing.direction_label(angle),
            angle=angle,
        )
