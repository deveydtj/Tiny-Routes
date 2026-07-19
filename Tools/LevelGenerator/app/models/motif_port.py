"""Typed connection points exposed by composable puzzle motifs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MotifPortType(str, Enum):
    """The structural role a motif port can play during composition."""

    MAIN_ROUTE_ENTRY = "mainRouteEntry"
    MAIN_ROUTE_EXIT = "mainRouteExit"
    BRANCH_INSERTION_POINT = "branchInsertionPoint"
    REJOIN_INPUT = "rejoinInput"
    RETURN_PATH_INPUT = "returnPathInput"
    RETURN_PATH_OUTPUT = "returnPathOutput"
    OBJECTIVE_ATTACHMENT = "objectiveAttachment"
    STATE_CHANGE_ATTACHMENT = "stateChangeAttachment"
    FAILURE_EXIT = "failureExit"
    RECOVERY_EXIT = "recoveryExit"


@dataclass(frozen=True)
class MotifPort:
    """One named, typed connection point on a motif-local graph node."""

    id: str
    node_id: str
    port_type: MotifPortType

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", self.id.strip() if isinstance(self.id, str) else self.id)
        object.__setattr__(
            self,
            "node_id",
            self.node_id.strip() if isinstance(self.node_id, str) else self.node_id,
        )
        if not isinstance(self.port_type, MotifPortType):
            object.__setattr__(self, "port_type", MotifPortType(self.port_type))

    def validate(self) -> tuple[str, ...]:
        issues: list[str] = []
        if not isinstance(self.id, str) or not self.id:
            issues.append("motif_port_id_empty")
        if not isinstance(self.node_id, str) or not self.node_id:
            issues.append(f"motif_port_node_id_empty:{self.id or 'unknown'}")
        return tuple(issues)
