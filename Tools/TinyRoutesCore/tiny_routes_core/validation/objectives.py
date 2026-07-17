"""Schema-3 ordered-objective validation."""

from __future__ import annotations

from dataclasses import dataclass

from tiny_routes_core.models import LevelDocument, RouteObjectiveKind


@dataclass(frozen=True)
class ObjectiveValidationIssue:
    code: str
    message: str
    objective_id: str | None = None
    node_id: str | None = None


def validate_level_objectives(level: LevelDocument) -> tuple[ObjectiveValidationIssue, ...]:
    """Validate objective ownership, ordering, references, and terminal semantics."""

    schema_version = level.schema_version
    objectives = level.objectives
    if schema_version < 3:
        if objectives is None:
            return ()
        return (
            ObjectiveValidationIssue(
                "objectives_require_schema_3",
                "The objectives field requires schemaVersion 3 or newer.",
            ),
        )

    if not objectives:
        return (
            ObjectiveValidationIssue(
                "schema_3_objectives_required",
                "Schema 3 levels must define at least one objective.",
            ),
        )

    issues: list[ObjectiveValidationIssue] = []
    node_ids = {node.id for node in level.graph.nodes}

    objective_id_counts: dict[str, int] = {}
    for objective in objectives:
        objective_id_counts[objective.id] = objective_id_counts.get(objective.id, 0) + 1
        if not objective.id.strip():
            issues.append(ObjectiveValidationIssue(
                "empty_objective_id",
                "Objective IDs must not be empty.",
                objective_id=objective.id,
            ))
        if objective.nodeID not in node_ids:
            issues.append(ObjectiveValidationIssue(
                "objective_node_not_found",
                f"Objective '{objective.id}' references missing node '{objective.nodeID}'.",
                objective_id=objective.id,
                node_id=objective.nodeID,
            ))

    for objective_id in sorted(
        objective_id for objective_id, count in objective_id_counts.items() if count > 1
    ):
        issues.append(ObjectiveValidationIssue(
            "duplicate_objective_id",
            f"Objective ID '{objective_id}' is used more than once.",
            objective_id=objective_id,
        ))

    actual_indices = sorted(objective.sequenceIndex for objective in objectives)
    expected_indices = list(range(len(objectives)))
    if actual_indices != expected_indices:
        issues.append(ObjectiveValidationIssue(
            "noncontiguous_objective_sequence_indices",
            "Objective sequenceIndex values must be contiguous and start at 0.",
        ))

    for expected_index, objective in enumerate(objectives):
        if objective.sequenceIndex != expected_index:
            issues.append(ObjectiveValidationIssue(
                "objective_array_order_mismatch",
                f"Objective '{objective.id}' must appear at sequence index {objective.sequenceIndex}.",
                objective_id=objective.id,
            ))

    terminal_objectives = [
        objective for objective in objectives
        if objective.kind is RouteObjectiveKind.DESTINATION
    ]
    if len(terminal_objectives) != 1:
        issues.append(ObjectiveValidationIssue(
            "invalid_terminal_objective_count",
            "Schema 3 levels must define exactly one destination objective.",
        ))
    else:
        terminal = terminal_objectives[0]
        if terminal.sequenceIndex != len(objectives) - 1:
            issues.append(ObjectiveValidationIssue(
                "terminal_objective_not_final",
                f"Destination objective '{terminal.id}' must be the final objective.",
                objective_id=terminal.id,
                node_id=terminal.nodeID,
            ))
        if terminal.nodeID != level.destinationNodeID:
            issues.append(ObjectiveValidationIssue(
                "legacy_destination_objective_conflict",
                "destinationNodeID must match the schema 3 destination objective nodeID.",
                objective_id=terminal.id,
                node_id=terminal.nodeID,
            ))

    pickup_objectives = sorted(
        (objective for objective in objectives if objective.kind is RouteObjectiveKind.PICKUP),
        key=lambda objective: objective.sequenceIndex,
    )
    if pickup_objectives and pickup_objectives[0].nodeID != level.packageNodeID:
        pickup = pickup_objectives[0]
        issues.append(ObjectiveValidationIssue(
            "legacy_package_objective_conflict",
            "packageNodeID must match the first schema 3 pickup objective nodeID.",
            objective_id=pickup.id,
            node_id=pickup.nodeID,
        ))

    return tuple(issues)
