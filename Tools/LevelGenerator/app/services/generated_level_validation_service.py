from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..level_editor_imports import LevelValidationService, SolutionValidationService, ValidationSeverity
from ..models.difficulty_preset import DifficultyPreset
from .difficulty_service import DifficultyService
from .graph_layout_service import BoundingBox, GraphLayoutService
from .road_shape_service import RoadShapeService


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
    def __init__(self) -> None:
        self.level_validation_service = LevelValidationService()
        self.solution_validation_service = SolutionValidationService()
        self.difficulty_service = DifficultyService()
        self.road_shape_service = RoadShapeService()

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

        if preset is not None:
            bounds = BoundingBox(*preset.coordinate_bounds)
            layout = GraphLayoutService(bounds=bounds, minimum_node_distance=preset.minimum_node_distance)
            positions = {node.id: (node.x, node.y) for node in level.graph.nodes}
            for issue in layout.validate_positions(positions):
                code, *detail = issue.split(":")
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
            if node is not None and len(node.outgoingEdgeIDs) < 2:
                messages.append(
                    GeneratorValidationMessage(
                        severity="error",
                        code="tap_node_is_not_switchable",
                        message=f"Tap node '{action.tapNodeID}' is not switchable.",
                        related_node_id=action.tapNodeID,
                    )
                )

        return messages


def _convert_editor_message(message) -> GeneratorValidationMessage:
    severity = "error" if message.severity is ValidationSeverity.ERROR else message.severity.value
    return GeneratorValidationMessage(
        severity=severity,
        code=message.code,
        message=message.message,
        related_node_id=message.related_node_id,
        related_edge_id=message.related_edge_id,
    )
