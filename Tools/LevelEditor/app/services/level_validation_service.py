from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from pathlib import Path

from app.models import LevelDocument, RouteGraphModel, RouteNodeModel
from app.services.level_identity_service import LevelIdentityService
from app.services.switch_classification_service import (
    MAX_SUPPORTED_OUTGOING_EDGES,
    SwitchClassificationService,
    SwitchNodeKind,
)


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


class LevelValidationService:
    def validate(
        self,
        level: "LevelDocument",
        file_path: Path | None = None,
    ) -> ValidationResult:
        return validate(level, file_path=file_path)


def create_default_level_document() -> LevelDocument:
    return LevelDocument(
        id="new_level",
        name="New Level",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(
                    id="start",
                    x=0.0,
                    y=0.0,
                    outgoingEdgeIDs=[],
                )
            ],
            edges=[],
        ),
        startNodeID="start",
        packageNodeID="start",
        destinationNodeID="start",
        timeLimitSeconds=30,
        parTaps=0,
    )


def _collect_reachable_node_ids(
    level: "LevelDocument",
    node_ids: set[str],
    start_node_id: str,
) -> set[str]:
    if start_node_id not in node_ids:
        return set()

    adjacency: dict[str, set[str]] = {}
    for edge in level.graph.edges:
        if edge.fromNodeID in node_ids and edge.toNodeID in node_ids:
            adjacency.setdefault(edge.fromNodeID, set()).add(edge.toNodeID)

    reachable: set[str] = set()
    stack: list[str] = [start_node_id]
    while stack:
        node_id = stack.pop()
        if node_id in reachable:
            continue
        reachable.add(node_id)
        stack.extend(adjacency.get(node_id, ()))

    return reachable


def _is_production_levels_path(file_path: Path) -> bool:
    parent_parts = file_path.parent.parts
    return len(parent_parts) >= 3 and parent_parts[-3:] == (
        "TinyRoutes",
        "Resources",
        "Levels",
    )


def _add_metadata_validation_messages(
    messages: list[ValidationMessage],
    level: "LevelDocument",
    file_path: Path | None,
) -> None:
    identity_service = LevelIdentityService()
    level_number = identity_service.try_parse_number_from_level_id(level.id)
    if level_number is not None and not identity_service.is_padded_production_level_id(level.id):
        normalized_identity = identity_service.build_from_number(level_number)
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="non_padded_level_id",
                message=(
                    f"Level ID '{level.id}' should be normalized to "
                    f"'{normalized_identity.level_id}'."
                ),
            )
        )

    if (
        identity_service.is_padded_production_level_id(level.id)
        and level.name == "New Level"
    ):
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="default_level_name_in_production_level",
                message=(
                    f"Production level '{level.id}' still has the default name 'New Level'."
                ),
            )
        )

    if file_path is None:
        return

    level_file_number = identity_service.try_parse_number_from_level_filename(file_path)
    if level_file_number is not None:
        normalized_identity = identity_service.build_from_number(level_file_number)
        if file_path.name != normalized_identity.level_filename:
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    code="non_padded_level_filename",
                    message=(
                        f"Level filename '{file_path.name}' should be normalized to "
                        f"'{normalized_identity.level_filename}'."
                    ),
                )
            )

        if file_path.stem != level.id:
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="level_id_filename_mismatch",
                    message=f"File is named '{file_path.name}' but level ID is '{level.id}'.",
                )
            )

    if _is_production_levels_path(file_path) and identity_service.is_draft_level_id(level.id):
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="draft_level_id_in_production_path",
                message=(
                    "Draft level ID 'new_level' should not be saved in the production "
                    "Levels directory."
                ),
            )
        )


def validate(
    level: "LevelDocument",
    file_path: Path | None = None,
) -> ValidationResult:
    """Run all core structural validation rules against a LevelDocument.

    Returns a ValidationResult containing any errors, warnings, or info
    messages found.  No Qt modules are used here.
    """
    messages: list[ValidationMessage] = []
    _add_metadata_validation_messages(messages, level, file_path)

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

    # --- Par taps ---
    if not (
        isinstance(level.parTaps, int)
        and not isinstance(level.parTaps, bool)
        and level.parTaps >= 0
    ):
        messages.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="invalid_par_taps",
                message="Par taps must be a non-negative integer.",
            )
        )

    node_ids = {node.id for node in level.graph.nodes}
    node_by_id = {node.id: node for node in level.graph.nodes}

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
    edge_by_id = {}
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
        else:
            edge_by_id[edge.id] = edge
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

    # --- Node outgoing edge lists match graph edges ---
    for node in level.graph.nodes:
        seen_outgoing_edge_ids: set[str] = set()
        for outgoing_edge_id in node.outgoingEdgeIDs:
            if outgoing_edge_id in seen_outgoing_edge_ids:
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        code="duplicate_outgoing_edge_id",
                        message=(
                            f"Node '{node.id}' lists outgoing edge '{outgoing_edge_id}' more than once."
                        ),
                        related_node_id=node.id,
                        related_edge_id=outgoing_edge_id,
                    )
                )
            seen_outgoing_edge_ids.add(outgoing_edge_id)

            edge = edge_by_id.get(outgoing_edge_id)
            if edge is None:
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        code="outgoing_edge_id_not_found",
                        message=(
                            f"Node '{node.id}' lists outgoing edge '{outgoing_edge_id}', but no edge with that ID exists."
                        ),
                        related_node_id=node.id,
                        related_edge_id=outgoing_edge_id,
                    )
                )
                continue

            if edge.fromNodeID != node.id:
                messages.append(
                    ValidationMessage(
                        severity=ValidationSeverity.ERROR,
                        code="outgoing_edge_wrong_source_node",
                        message=(
                            f"Node '{node.id}' lists edge '{edge.id}', but that edge starts at '{edge.fromNodeID}'."
                        ),
                        related_node_id=node.id,
                        related_edge_id=edge.id,
                    )
                )

    for edge in level.graph.edges:
        source_node = node_by_id.get(edge.fromNodeID)
        if source_node is None:
            continue
        if edge.id not in source_node.outgoingEdgeIDs:
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="edge_missing_from_source_outgoing_ids",
                    message=(
                        f"Edge '{edge.id}' starts at node '{edge.fromNodeID}', but the node does not list it in outgoingEdgeIDs."
                    ),
                    related_node_id=edge.fromNodeID,
                    related_edge_id=edge.id,
                )
            )

    switch_classification_service = SwitchClassificationService()
    for node in level.graph.nodes:
        classification = switch_classification_service.classify_node(node, edge_by_id)
        if classification.kind is SwitchNodeKind.INVALID_TOO_MANY_OUTGOING_EDGES:
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="switch_has_too_many_outgoing_edges",
                    message=(
                        f"Node '{node.id}' has {classification.valid_outgoing_edge_count} valid outgoing edges; "
                        f"at most {MAX_SUPPORTED_OUTGOING_EDGES} are supported."
                    ),
                    related_node_id=node.id,
                )
            )
            continue

        if classification.kind is SwitchNodeKind.FOUR_WAY_INTERSECTION_SWITCH:
            messages.extend(
                _four_way_readability_messages(
                    node,
                    classification.valid_outgoing_edge_ids,
                    node_by_id,
                    edge_by_id,
                )
            )

    # --- Reachability from start node ---
    reachable_node_ids = _collect_reachable_node_ids(level, node_ids, level.startNodeID)
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

    # --- Required route order reachability ---
    if level.packageNodeID in node_ids and level.destinationNodeID in node_ids:
        package_reachable_node_ids = _collect_reachable_node_ids(
            level,
            node_ids,
            level.packageNodeID,
        )
        if level.destinationNodeID not in package_reachable_node_ids:
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.ERROR,
                    code="destination_unreachable_from_package_node",
                    message=(
                        f"Destination node '{level.destinationNodeID}' is not reachable from package node '{level.packageNodeID}'."
                    ),
                    related_node_id=level.destinationNodeID,
                )
            )

    return ValidationResult(messages=messages)


def _four_way_readability_messages(
    node: RouteNodeModel,
    valid_outgoing_edge_ids: tuple[str, ...],
    node_by_id: dict[str, RouteNodeModel],
    edge_by_id: dict[str, object],
) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    angles: list[tuple[str, float]] = []
    minimum_edge_length = 0.35

    for edge_id in valid_outgoing_edge_ids:
        edge = edge_by_id[edge_id]
        target_node = node_by_id.get(edge.toNodeID)
        if target_node is None:
            continue

        dx = float(target_node.x) - float(node.x)
        dy = float(target_node.y) - float(node.y)
        distance = math.hypot(dx, dy)
        if distance < minimum_edge_length:
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    code="four_way_switch_short_outgoing_edge",
                    message=(
                        f"4-way switch '{node.id}' has a very short outgoing edge '{edge_id}' "
                        f"to '{target_node.id}'."
                    ),
                    related_node_id=node.id,
                    related_edge_id=edge_id,
                )
            )
        if distance > 0:
            angles.append((edge_id, math.atan2(dy, dx)))

    if len(angles) < 2:
        return messages

    sorted_angles = sorted(angles, key=lambda item: item[1])
    min_separation = math.radians(20)
    for index, (edge_id, angle) in enumerate(sorted_angles):
        next_edge_id, next_angle = sorted_angles[(index + 1) % len(sorted_angles)]
        separation = (next_angle - angle) % (math.pi * 2)
        if separation < min_separation:
            messages.append(
                ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    code="four_way_switch_ambiguous_angles",
                    message=(
                        f"4-way switch '{node.id}' has near-overlapping outgoing directions "
                        f"for '{edge_id}' and '{next_edge_id}'."
                    ),
                    related_node_id=node.id,
                    related_edge_id=edge_id,
                )
            )

    return messages
