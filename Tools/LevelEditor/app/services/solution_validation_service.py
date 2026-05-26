from __future__ import annotations

from pathlib import Path

from app.models import LevelDocument, SolutionModel
from app.services.level_identity_service import LevelIdentityService
from app.services.level_validation_service import (
    ValidationMessage,
    ValidationResult,
    ValidationSeverity,
)
from app.services.switch_classification_service import SwitchClassificationService, SwitchNodeKind


class SolutionValidationService:
    """Validate solution sidecar structure and level graph references.

    This service intentionally does not simulate gameplay or prove the level can
    be completed. True completion validation belongs to the Swift solvability
    harness; this Python pass catches malformed metadata and broken references
    before a level is saved or shipped.
    """

    def validate(
        self,
        level: LevelDocument,
        solution: SolutionModel | None,
        file_path: Path | None = None,
    ) -> ValidationResult:
        return validate(level, solution, file_path=file_path)


def validate(
    level: LevelDocument,
    solution: SolutionModel | None,
    file_path: Path | None = None,
) -> ValidationResult:
    """Validate a solution script's metadata, action timing, and node references."""

    messages: list[ValidationMessage] = []

    if solution is None:
        return ValidationResult(
            messages=[
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="missing_solution",
                    message="No solution is loaded for this level.",
                )
            ]
        )

    if solution.levelID != level.id:
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="solution_level_id_mismatch",
                message=(
                    f"Solution levelID '{solution.levelID}' does not match level ID '{level.id}'."
                ),
            )
        )

    if file_path is not None:
        identity_service = LevelIdentityService()
        level_number = identity_service.try_parse_number_from_level_filename(file_path)
        if level_number is not None:
            identity = identity_service.build_from_number(level_number)
            if solution.levelID != identity.level_id:
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        code="solution_level_id_filename_mismatch",
                        message=(
                            f"Solution levelID '{solution.levelID}' does not match "
                            f"corrected production ID '{identity.level_id}'."
                        ),
                    )
                )

    if solution.expectedOutcome != "completed":
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="invalid_expected_outcome",
                message="Solution expectedOutcome must be 'completed'.",
            )
        )

    has_valid_max_taps = (
        isinstance(solution.maxTaps, int)
        and not isinstance(solution.maxTaps, bool)
        and solution.maxTaps >= 0
    )
    if not has_valid_max_taps:
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="invalid_max_taps",
                message="Solution maxTaps must be a non-negative integer.",
            )
        )
    elif solution.maxTaps < len(solution.actions):
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="max_taps_less_than_action_count",
                message=(
                    f"Solution maxTaps is {solution.maxTaps}, but the script contains {len(solution.actions)} actions."
                ),
            )
        )
    elif solution.maxTaps > len(solution.actions):
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="max_taps_greater_than_action_count",
                message=(
                    f"Solution maxTaps is {solution.maxTaps}, but the script contains only {len(solution.actions)} actions."
                ),
            )
        )

    if solution.isPlaceholder is True:
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="solution_marked_placeholder",
                message="Solution is marked as a placeholder and should be replaced before shipping.",
            )
        )

    if solution.requiresWithinTimeLimit is False and solution.isPlaceholder is not True:
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="solution_requires_without_time_limit",
                message="Solution does not require completion within the level time limit.",
            )
        )

    node_by_id = {node.id: node for node in level.graph.nodes}
    edge_by_id = {edge.id: edge for edge in level.graph.edges}
    switch_classification_service = SwitchClassificationService()
    previous_time: int | float | None = None

    for index, action in enumerate(solution.actions):
        action_label = f"Solution action {index + 1}"

        if not action.tapNodeID or not action.tapNodeID.strip():
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="solution_action_missing_tap_node_id",
                    message=f"{action_label} is missing tapNodeID.",
                )
            )
        else:
            tapped_node = node_by_id.get(action.tapNodeID)
            if tapped_node is None:
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        code="solution_action_unknown_tap_node",
                        message=(
                            f"{action_label} taps unknown node '{action.tapNodeID}'."
                        ),
                        related_node_id=action.tapNodeID,
                    )
                )
            else:
                classification = switch_classification_service.classify_node(tapped_node, edge_by_id)
                if classification.valid_outgoing_edge_count < 2:
                    messages.append(
                        ValidationMessage(
                            severity=ValidationSeverity.WARNING,
                            code="tap_node_is_not_switchable",
                            message=(
                                f"{action_label} taps node '{action.tapNodeID}', but that node has "
                                f"{classification.valid_outgoing_edge_count} valid outgoing edge(s)."
                            ),
                            related_node_id=action.tapNodeID,
                        )
                    )
                elif classification.kind is SwitchNodeKind.INVALID_TOO_MANY_OUTGOING_EDGES:
                    messages.append(
                        ValidationMessage(
                            severity=ValidationSeverity.ERROR,
                            code="tap_node_has_too_many_outgoing_edges",
                            message=(
                                f"{action_label} taps node '{action.tapNodeID}', but that node has "
                                f"{classification.valid_outgoing_edge_count} valid outgoing edge(s), which is unsupported."
                            ),
                            related_node_id=action.tapNodeID,
                        )
                    )
                else:
                    messages.append(
                        ValidationMessage(
                            severity=ValidationSeverity.INFO,
                            code="tap_node_switch_context",
                            message=(
                                f"{action_label} taps {classification.display_name.lower()} "
                                f"'{action.tapNodeID}' with {classification.valid_outgoing_edge_count} option(s)."
                            ),
                            related_node_id=action.tapNodeID,
                        )
                    )

        if not (
            isinstance(action.timeSeconds, (int, float))
            and not isinstance(action.timeSeconds, bool)
        ):
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="solution_action_invalid_time",
                    message=f"{action_label} timeSeconds must be a number.",
                    related_node_id=action.tapNodeID or None,
                )
            )
            continue

        if action.timeSeconds < 0:
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="solution_action_negative_time",
                    message=f"{action_label} timeSeconds cannot be negative.",
                    related_node_id=action.tapNodeID or None,
                )
            )

        if (
            solution.requiresWithinTimeLimit is True
            and isinstance(level.timeLimitSeconds, (int, float))
            and not isinstance(level.timeLimitSeconds, bool)
            and action.timeSeconds > level.timeLimitSeconds
        ):
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="solution_action_after_time_limit",
                    message=(
                        f"{action_label} occurs at {action.timeSeconds}s, after the {level.timeLimitSeconds}s time limit."
                    ),
                    related_node_id=action.tapNodeID or None,
                )
            )

        if previous_time is not None:
            if action.timeSeconds < previous_time:
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        code="solution_actions_not_sorted",
                        message="Solution action times must be sorted in nondecreasing order.",
                        related_node_id=action.tapNodeID or None,
                    )
                )
            elif action.timeSeconds == previous_time:
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.WARNING,
                        code="duplicate_solution_action_time",
                        message=(
                            f"{action_label} has the same time as the previous solution action."
                        ),
                        related_node_id=action.tapNodeID or None,
                    )
                )

        previous_time = action.timeSeconds

    return ValidationResult(messages=messages)
