from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..level_editor_imports import LevelValidationService, SolutionValidationService, ValidationSeverity
from ..models.difficulty_preset import DifficultyPreset
from .difficulty_service import DifficultyService
from .graph_layout_service import BoundingBox, GraphLayoutService
from .python_solution_simulator_service import PythonSolutionSimulatorService
from .road_shape_service import RoadShapeService
from .switch_classification_service import (
    MAX_SUPPORTED_OUTGOING_EDGES,
    SwitchClassificationService,
    SwitchNodeKind,
)
from .visual_clarity_validation_service import VisualClarityValidationService


@dataclass(frozen=True)
class GeneratorValidationMessage:
    severity: str
    code: str
    message: str
    related_node_id: str | None = None
    related_edge_id: str | None = None


@dataclass
class GeneratorValidationResult:
    messages: list[GeneratorValidationMessage] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(message.severity == "error" for message in self.messages)

    @property
    def error_codes(self) -> list[str]:
        return [message.code for message in self.messages if message.severity == "error"]


class GeneratedLevelValidationService:
    minimum_pre_arrival_tap_buffer_seconds = 0.15

    def __init__(self) -> None:
        self.level_validation_service = LevelValidationService()
        self.solution_validation_service = SolutionValidationService()
        self.difficulty_service = DifficultyService()
        self.road_shape_service = RoadShapeService()
        self.solution_simulator = PythonSolutionSimulatorService()
        self.switch_classification_service = SwitchClassificationService()
        self.visual_clarity_validation_service = VisualClarityValidationService()

    def validate(
        self,
        generated_level,
        preset: DifficultyPreset | None = None,
        level_output_path: Path | None = None,
        solution_output_path: Path | None = None,
        overwrite: bool = False,
        enforce_difficulty: bool = True,
    ) -> GeneratorValidationResult:
        level = generated_level.level_document
        solution = generated_level.solution
        messages: list[GeneratorValidationMessage] = []

        for message in self.level_validation_service.validate(level).messages:
            messages.append(_convert_editor_message(message))
        for message in self.solution_validation_service.validate(level, solution).messages:
            converted = _convert_editor_message(message)
            if converted.code in {
                "tap_node_is_not_switchable",
                "solution_marked_placeholder",
                "solution_requires_without_time_limit",
            }:
                converted = GeneratorValidationMessage(
                    severity="error",
                    code=converted.code,
                    message=converted.message,
                    related_node_id=converted.related_node_id,
                    related_edge_id=converted.related_edge_id,
                )
            messages.append(converted)

        messages.extend(self._generator_specific_messages(generated_level, preset, enforce_difficulty))

        if not overwrite:
            if level_output_path is not None and level_output_path.exists():
                messages.append(
                    GeneratorValidationMessage(
                        severity="error",
                        code="level_output_file_exists",
                        message=f"Level output file already exists: {level_output_path}",
                    )
                )
            if solution_output_path is not None and solution_output_path.exists():
                messages.append(
                    GeneratorValidationMessage(
                        severity="error",
                        code="solution_output_file_exists",
                        message=f"Solution output file already exists: {solution_output_path}",
                    )
                )

        return GeneratorValidationResult(messages=messages)

    def _generator_specific_messages(
        self,
        generated_level,
        preset: DifficultyPreset | None,
        enforce_difficulty: bool,
    ) -> list[GeneratorValidationMessage]:
        level = generated_level.level_document
        solution = generated_level.solution
        messages: list[GeneratorValidationMessage] = []
        node_by_id = {node.id: node for node in level.graph.nodes}
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        classifications_by_node_id = {
            node.id: self.switch_classification_service.classify_node(node, edge_by_id)
            for node in level.graph.nodes
        }

        for edge in level.graph.edges:
            if not self.road_shape_service.is_allowed(edge.roadShape):
                messages.append(
                    GeneratorValidationMessage(
                        severity="error",
                        code="invalid_road_shape",
                        message=f"Edge '{edge.id}' has invalid roadShape '{edge.roadShape}'.",
                        related_edge_id=edge.id,
                    )
                )
            from_node = node_by_id.get(edge.fromNodeID)
            to_node = node_by_id.get(edge.toNodeID)
            if from_node is not None and to_node is not None and from_node.x == to_node.x and from_node.y == to_node.y:
                messages.append(
                    GeneratorValidationMessage(
                        severity="error",
                        code="zero_length_edge",
                        message=f"Edge '{edge.id}' has identical from/to coordinates.",
                        related_edge_id=edge.id,
                    )
                )
        messages.extend(self._road_shape_plan_messages(generated_level))

        for node in level.graph.nodes:
            classification = classifications_by_node_id[node.id]
            if classification.kind is SwitchNodeKind.INVALID_TOO_MANY_OUTGOING_EDGES:
                messages.append(
                    GeneratorValidationMessage(
                        severity="error",
                        code="switch_has_too_many_outgoing_edges",
                        message=(
                            f"Node '{node.id}' has {classification.valid_outgoing_edge_count} valid outgoing edges; "
                            f"at most {MAX_SUPPORTED_OUTGOING_EDGES} are supported."
                        ),
                        related_node_id=node.id,
                    )
                )
        messages.extend(self._visual_clarity_messages(generated_level))

        if preset is not None:
            bounds = BoundingBox(*preset.coordinate_bounds)
            layout = GraphLayoutService(bounds=bounds, minimum_node_distance=preset.minimum_node_distance)
            positions = {node.id: (node.x, node.y) for node in level.graph.nodes}
            for issue in layout.validate_positions(positions):
                raw_code, *detail = issue.split(":")
                code = {
                    "node_out_of_bounds": "layout_node_out_of_bounds",
                    "overlapping_nodes": "layout_node_cluster",
                }.get(raw_code, raw_code)
                messages.append(
                    GeneratorValidationMessage(
                        severity="error",
                        code=code,
                        message=f"Layout issue: {issue}",
                        related_node_id=detail[0] if detail else None,
                    )
                )

            if enforce_difficulty:
                for issue in self.difficulty_service.check_candidate_matches_difficulty(level, solution, preset):
                    code, *detail = issue.split(":")
                    messages.append(
                        GeneratorValidationMessage(
                            severity="error",
                            code=code,
                            message=f"Difficulty issue: {issue}",
                            related_node_id=detail[0] if detail else None,
                        )
                    )
                messages.extend(self._readability_messages(level, layout, preset))

            previous_time: float | None = None
            tolerance = 1e-9
            for action in sorted(solution.actions, key=lambda value: value.timeSeconds):
                if previous_time is not None and action.timeSeconds - previous_time < preset.min_tap_spacing_seconds - tolerance:
                    messages.append(
                        GeneratorValidationMessage(
                            severity="error",
                            code="solution_action_spacing_too_small",
                            message=(
                                f"Solution action at {action.timeSeconds}s is less than "
                                f"{preset.min_tap_spacing_seconds}s after the previous action."
                            ),
                            related_node_id=action.tapNodeID,
                        )
                    )
                previous_time = action.timeSeconds

        if solution.isPlaceholder is True:
            messages.append(
                GeneratorValidationMessage(
                    severity="error",
                    code="solution_marked_placeholder",
                    message="Generated production solutions must not be placeholders.",
                )
            )

        for action in solution.actions:
            node = node_by_id.get(action.tapNodeID)
            if node is not None and classifications_by_node_id[node.id].valid_outgoing_edge_count < 2:
                messages.append(
                    GeneratorValidationMessage(
                        severity="error",
                        code="tap_node_is_not_switchable",
                        message=f"Tap node '{action.tapNodeID}' is not switchable.",
                        related_node_id=action.tapNodeID,
                    )
                )

        messages.extend(self._timed_tap_arrival_messages(generated_level))
        messages.extend(self._four_way_solution_complexity_messages(level, solution, classifications_by_node_id, preset))

        try:
            simulation = self.solution_simulator.simulate(generated_level)
        except Exception as exc:
            simulation = None
            messages.append(
                GeneratorValidationMessage(
                    severity="error",
                    code="solution_simulation_failed",
                    message=f"Python solution simulation failed: {exc}",
                )
            )
        else:
            generated_level.simulation_result = simulation
            if not simulation.passed:
                messages.append(
                    GeneratorValidationMessage(
                        severity="error",
                        code="solution_simulation_failed",
                        message=f"Python solution simulation failed: {self._simulation_failure_detail(simulation)}",
                    )
                )
            elif preset is not None and enforce_difficulty:
                messages.extend(self._simulation_difficulty_messages(simulation, preset))

        return messages

    def _road_shape_plan_messages(self, generated_level) -> list[GeneratorValidationMessage]:
        metadata = getattr(generated_level, "road_shape_metadata", None) or {}
        messages: list[GeneratorValidationMessage] = []
        for issue in metadata.get("issues", []):
            code, *detail = str(issue).split(":")
            severity = "error" if code in {
                "same_switch_first_segments_overlap",
                "required_and_wrong_route_first_segments_overlap",
                "road_crossing_near_important_node",
                "implicit_intersection_without_graph_node",
                "road_crosses_through_unconnected_node",
                "unconnected_road_endpoint_touches_segment",
                "unconnected_parallel_road_overlap",
            } else "warning"
            messages.append(
                GeneratorValidationMessage(
                    severity=severity,
                    code=code,
                    message=f"Road-shape issue: {issue}",
                    related_node_id=detail[0] if detail else None,
                )
            )
        return messages

    def _four_way_solution_complexity_messages(
        self,
        level,
        solution,
        classifications_by_node_id,
        preset: DifficultyPreset | None,
    ) -> list[GeneratorValidationMessage]:
        messages: list[GeneratorValidationMessage] = []
        four_way_node_ids = {
            node_id
            for node_id, classification in classifications_by_node_id.items()
            if classification.kind is SwitchNodeKind.FOUR_WAY_INTERSECTION_SWITCH
        }
        if not four_way_node_ids:
            return messages

        actions_by_node_id: dict[str, list[float]] = {}
        for action in solution.actions:
            if action.tapNodeID in four_way_node_ids:
                actions_by_node_id.setdefault(action.tapNodeID, []).append(float(action.timeSeconds))

        max_four_way_taps = 3 if preset is None or preset.name != "expert" else 4
        minimum_spacing = (preset.min_tap_spacing_seconds if preset is not None else 0.4) * 1.5
        for node_id, times in actions_by_node_id.items():
            if len(times) > max_four_way_taps:
                messages.append(
                    GeneratorValidationMessage(
                        severity="error",
                        code="four_way_switch_requires_too_many_taps",
                        message=f"4-way switch '{node_id}' requires {len(times)} taps in the solution.",
                        related_node_id=node_id,
                    )
                )
            sorted_times = sorted(times)
            for previous, current in zip(sorted_times, sorted_times[1:]):
                if current - previous < minimum_spacing:
                    messages.append(
                        GeneratorValidationMessage(
                            severity="error",
                            code="four_way_switch_taps_too_close",
                            message=(
                                f"4-way switch '{node_id}' has taps only "
                                f"{current - previous:.2f}s apart."
                            ),
                            related_node_id=node_id,
                        )
                    )

        return messages

    def _simulation_difficulty_messages(self, simulation, preset: DifficultyPreset) -> list[GeneratorValidationMessage]:
        ranges = {
            "tutorial": (0.2, 8.0),
            "easy": (0.8, 12.0),
            "medium": (1.2, 16.0),
            "hard": (1.8, 22.0),
            "expert": (2.0, 26.0),
        }
        minimum, maximum = ranges.get(preset.name, (0.0, 999.0))
        if minimum <= simulation.elapsed_time_seconds <= maximum:
            return []
        return [
            GeneratorValidationMessage(
                severity="error",
                code="route_length_outside_difficulty_range",
                message=(
                    f"Simulated route time {simulation.elapsed_time_seconds}s is outside "
                    f"{preset.name} range {minimum}-{maximum}s."
                ),
            )
        ]

    def _readability_messages(self, level, layout: GraphLayoutService, preset: DifficultyPreset) -> list[GeneratorValidationMessage]:
        positions = {node.id: (node.x, node.y) for node in level.graph.nodes}
        edges = [(edge.fromNodeID, edge.toNodeID, edge.id) for edge in level.graph.edges]
        summary = layout.readability_summary(positions, edges)
        messages: list[GeneratorValidationMessage] = []
        if summary["crossings"] > 3:
            messages.append(
                GeneratorValidationMessage(
                    severity="error",
                    code="layout_too_many_edge_crossings",
                    message=f"Layout has too many crossing edges: {summary['crossings']}.",
                )
            )
        if summary["edgeSpacingIssues"] > 3:
            messages.append(
                GeneratorValidationMessage(
                    severity="error",
                    code="layout_too_many_tight_edge_spacing_issues",
                    message=f"Layout has too many tight edge spacing issues: {summary['edgeSpacingIssues']}.",
                )
            )
        important_node_ids = [level.startNodeID, level.packageNodeID, level.destinationNodeID]
        for index, first_id in enumerate(important_node_ids):
            for second_id in important_node_ids[index + 1:]:
                if first_id in positions and second_id in positions:
                    distance = layout.point_distance(positions[first_id], positions[second_id])
                    if distance < preset.minimum_node_distance * 1.5:
                        messages.append(
                            GeneratorValidationMessage(
                                severity="error",
                                code="layout_important_nodes_too_close",
                                message=f"Important nodes are too close: {first_id} and {second_id}.",
                                related_node_id=first_id,
                            )
                        )
        if level.packageNodeID in positions and level.destinationNodeID in positions:
            distance = layout.point_distance(positions[level.packageNodeID], positions[level.destinationNodeID])
            if distance < preset.minimum_node_distance * 2.0:
                messages.append(
                    GeneratorValidationMessage(
                        severity="error",
                        code="layout_package_destination_confusing",
                        message="Package and destination are too close to read as separate goals.",
                        related_node_id=level.packageNodeID,
                    )
                )
        margin = max(0.2, preset.minimum_node_distance * 0.9)
        for node in level.graph.nodes:
            valid_outgoing = [
                edge
                for edge in level.graph.edges
                if edge.fromNodeID == node.id and edge.id in node.outgoingEdgeIDs
            ]
            if len(valid_outgoing) < 2:
                continue
            x, y = positions[node.id]
            distance_to_edge = min(
                x - layout.bounds.min_x,
                layout.bounds.max_x - x,
                y - layout.bounds.min_y,
                layout.bounds.max_y - y,
            )
            if distance_to_edge < margin:
                messages.append(
                    GeneratorValidationMessage(
                        severity="error",
                        code="layout_switch_too_close_to_edge",
                        message=f"Switch '{node.id}' is too close to the board edge.",
                        related_node_id=node.id,
                    )
                )
        return messages

    def _timed_tap_arrival_messages(self, generated_level) -> list[GeneratorValidationMessage]:
        solution = generated_level.solution
        messages: list[GeneratorValidationMessage] = []
        tolerance = 1e-9
        sorted_actions = sorted(solution.actions, key=lambda action: float(action.timeSeconds))
        for index, action in enumerate(sorted_actions):
            try:
                arrival_time = self.solution_simulator.arrival_time_for_action(generated_level, index)
            except Exception:
                continue
            if arrival_time is None:
                continue
            arrival_buffer = arrival_time - float(action.timeSeconds)
            if arrival_buffer + tolerance >= self.minimum_pre_arrival_tap_buffer_seconds:
                continue
            messages.append(
                GeneratorValidationMessage(
                    severity="error",
                    code="solution_tap_not_before_switch_arrival",
                    message=(
                        f"Solution action at {float(action.timeSeconds):.2f}s for '{action.tapNodeID}' leaves only "
                        f"{arrival_buffer:.2f}s before arrival at {arrival_time:.2f}s; minimum buffer is "
                        f"{self.minimum_pre_arrival_tap_buffer_seconds:.2f}s."
                    ),
                    related_node_id=action.tapNodeID,
                )
            )
        return messages

    def _visual_clarity_messages(self, generated_level) -> list[GeneratorValidationMessage]:
        report = self.visual_clarity_validation_service.report_for_generated_level(generated_level)
        return [
            GeneratorValidationMessage(
                severity=issue.severity,
                code=issue.code,
                message=issue.message,
                related_node_id=issue.related_node_id,
                related_edge_id=issue.related_edge_id,
            )
            for issue in report.issues
        ]

    def _simulation_failure_detail(self, simulation) -> str:
        detail = simulation.failure_reason or "unknown_failure"
        last_tap_step = next((step for step in reversed(simulation.steps) if step.event == "tap_switch"), None)
        if last_tap_step is None:
            return detail
        return (
            f"{detail} at {last_tap_step.time_seconds:.3f}s "
            f"node={last_tap_step.node_id or '(none)'} {last_tap_step.detail}"
        )


def _convert_editor_message(message) -> GeneratorValidationMessage:
    severity = "error" if message.severity is ValidationSeverity.ERROR else message.severity.value
    return GeneratorValidationMessage(
        severity=severity,
        code=message.code,
        message=message.message,
        related_node_id=message.related_node_id,
        related_edge_id=message.related_edge_id,
    )
