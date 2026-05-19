from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.level_document import LevelDocument


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ValidationMessage:
    severity: ValidationSeverity
    code: str
    message: str
    related_node_id: str | None = None
    related_edge_id: str | None = None


@dataclass
class ValidationResult:
    messages: list[ValidationMessage] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(message.severity is ValidationSeverity.ERROR for message in self.messages)

    @property
    def has_warnings(self) -> bool:
        return any(message.severity is ValidationSeverity.WARNING for message in self.messages)


def _collect_reachable_node_ids(level: "LevelDocument", node_ids: set[str]) -> set[str]:
    if level.startNodeID not in node_ids:
        return set()

    adjacency: dict[str, set[str]] = {}
    for edge in level.graph.edges:
        if edge.fromNodeID in node_ids and edge.toNodeID in node_ids:
            adjacency.setdefault(edge.fromNodeID, set()).add(edge.toNodeID)

    reachable: set[str] = set()
    stack: list[str] = [level.startNodeID]
    while stack:
        node_id = stack.pop()
        if node_id in reachable:
            continue
        reachable.add(node_id)
        stack.extend(adjacency.get(node_id, ()))

    return reachable


def validate(level: "LevelDocument") -> ValidationResult:
    """Run all core structural validation rules against a LevelDocument.

    Returns a ValidationResult containing any errors, warnings, or info
    messages found.  No Qt modules are used here.
    """
    messages: list[ValidationMessage] = []

    # --- Level ID ---
    if not level.id or not level.id.strip():
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="missing_level_id",
                message="Level ID is missing or empty.",
            )
        )

    # --- Level name ---
    if not level.name or not level.name.strip():
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="missing_level_name",
                message="Level name is missing or empty.",
            )
        )

    # --- Time limit ---
    if not (
        isinstance(level.timeLimitSeconds, (int, float))
        and not isinstance(level.timeLimitSeconds, bool)
        and level.timeLimitSeconds > 0
    ):
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="invalid_time_limit",
                message="Time limit must be a positive number.",
            )
        )

    node_ids = {node.id for node in level.graph.nodes}

    # --- Exactly one start node ---
    if not level.startNodeID or not level.startNodeID.strip():
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="missing_start_node",
                message="Level must have a start node (startNodeID is missing or empty).",
            )
        )
    elif level.startNodeID not in node_ids:
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="start_node_not_found",
                message=f"Start node '{level.startNodeID}' is not present in the graph nodes.",
                related_node_id=level.startNodeID,
            )
        )

    # --- At least one destination node ---
    if not level.destinationNodeID or not level.destinationNodeID.strip():
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="missing_destination_node",
                message="Level must have a destination node (destinationNodeID is missing or empty).",
            )
        )
    elif level.destinationNodeID not in node_ids:
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="destination_node_not_found",
                message=f"Destination node '{level.destinationNodeID}' is not present in the graph nodes.",
                related_node_id=level.destinationNodeID,
            )
        )

    # --- Package node ---
    if not level.packageNodeID or not level.packageNodeID.strip():
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="missing_package_node",
                message="Level must have a package node (packageNodeID is missing or empty).",
            )
        )
    elif level.packageNodeID not in node_ids:
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="package_node_not_found",
                message=f"Package node '{level.packageNodeID}' is not present in the graph nodes.",
                related_node_id=level.packageNodeID,
            )
        )

    # --- Unique node IDs ---
    seen_node_ids: set[str] = set()
    for node in level.graph.nodes:
        if node.id in seen_node_ids:
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="duplicate_node_id",
                    message=f"Node ID '{node.id}' is used more than once.",
                    related_node_id=node.id,
                )
            )
        seen_node_ids.add(node.id)

    # --- Unique edge IDs ---
    seen_edge_ids: set[str] = set()
    for edge in level.graph.edges:
        if edge.id in seen_edge_ids:
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="duplicate_edge_id",
                    message=f"Edge ID '{edge.id}' is used more than once.",
                    related_edge_id=edge.id,
                )
            )
        seen_edge_ids.add(edge.id)

    # --- Every edge references existing nodes ---
    for edge in level.graph.edges:
        if edge.fromNodeID not in node_ids:
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="edge_references_missing_node",
                    message=(
                        f"Edge '{edge.id}' references missing fromNode '{edge.fromNodeID}'."
                    ),
                    related_edge_id=edge.id,
                    related_node_id=edge.fromNodeID,
                )
            )
        if edge.toNodeID not in node_ids:
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="edge_references_missing_node",
                    message=(
                        f"Edge '{edge.id}' references missing toNode '{edge.toNodeID}'."
                    ),
                    related_edge_id=edge.id,
                    related_node_id=edge.toNodeID,
                )
            )

    # --- Reachability from start node ---
    reachable_node_ids = _collect_reachable_node_ids(level, node_ids)
    if reachable_node_ids:
        if (
            level.packageNodeID in node_ids
            and level.packageNodeID not in reachable_node_ids
        ):
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="unreachable_package_node",
                    message=(
                        f"Package node '{level.packageNodeID}' is not reachable from start node '{level.startNodeID}'."
                    ),
                    related_node_id=level.packageNodeID,
                )
            )

        if (
            level.destinationNodeID in node_ids
            and level.destinationNodeID not in reachable_node_ids
        ):
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="unreachable_destination_node",
                    message=(
                        f"Destination node '{level.destinationNodeID}' is not reachable from start node '{level.startNodeID}'."
                    ),
                    related_node_id=level.destinationNodeID,
                )
            )

        critical_node_ids = {
            level.startNodeID,
            level.packageNodeID,
            level.destinationNodeID,
        }
        for node_id in sorted(node_ids):
            if node_id not in critical_node_ids and node_id not in reachable_node_ids:
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.WARNING,
                        code="unreachable_non_critical_node",
                        message=f"Node '{node_id}' is not reachable from start node '{level.startNodeID}'.",
                        related_node_id=node_id,
                    )
                )

    return ValidationResult(messages=messages)
