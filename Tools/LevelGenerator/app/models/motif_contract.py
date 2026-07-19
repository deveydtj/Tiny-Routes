"""Machine-readable precondition and effect contracts for puzzle motifs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MotifIncomingObjectiveState(str, Enum):
    """Objective state required when a motif is entered."""

    ANY = "any"
    BEFORE_ACTIVE_OBJECTIVE = "beforeActiveObjective"
    AFTER_ACTIVE_OBJECTIVE = "afterActiveObjective"


class MotifEdgeStateChangeKind(str, Enum):
    """A route-state change produced when the local objective is completed."""

    OPEN = "open"
    CLOSE = "close"
    CONSUME = "consume"


class MotifDependencyEffect(str, Enum):
    """The strategic dependency that the motif is intended to realize."""

    NONE = "none"
    OBJECTIVE_STATE = "objectiveState"
    EARLIER_CHOICE = "earlierChoice"
    REVISIT = "revisit"


@dataclass(frozen=True)
class MotifEdgeStateChange:
    """A verifiable state change on one motif-local directed edge."""

    from_node_id: str
    to_node_id: str
    kind: MotifEdgeStateChangeKind
    trigger_objective_node_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, MotifEdgeStateChangeKind):
            object.__setattr__(self, "kind", MotifEdgeStateChangeKind(self.kind))


@dataclass(frozen=True)
class MotifPreconditionContract:
    """Conditions that must hold before a motif can be composed."""

    minimum_objective_phase_index: int = 0
    maximum_objective_phase_index: int | None = None
    required_incoming_objective_state: MotifIncomingObjectiveState = (
        MotifIncomingObjectiveState.ANY
    )
    required_completed_objective_roles: tuple[str, ...] = ()
    forbidden_completed_objective_roles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.required_incoming_objective_state, MotifIncomingObjectiveState):
            object.__setattr__(
                self,
                "required_incoming_objective_state",
                MotifIncomingObjectiveState(self.required_incoming_objective_state),
            )
        object.__setattr__(
            self,
            "required_completed_objective_roles",
            tuple(self.required_completed_objective_roles),
        )
        object.__setattr__(
            self,
            "forbidden_completed_objective_roles",
            tuple(self.forbidden_completed_objective_roles),
        )

    def validate(self) -> tuple[str, ...]:
        issues: list[str] = []
        if (
            not isinstance(self.minimum_objective_phase_index, int)
            or isinstance(self.minimum_objective_phase_index, bool)
            or self.minimum_objective_phase_index < 0
        ):
            issues.append("motif_precondition_minimum_phase_invalid")
        if self.maximum_objective_phase_index is not None and (
            not isinstance(self.maximum_objective_phase_index, int)
            or isinstance(self.maximum_objective_phase_index, bool)
            or self.maximum_objective_phase_index < self.minimum_objective_phase_index
        ):
            issues.append("motif_precondition_maximum_phase_invalid")
        completed = self.required_completed_objective_roles
        forbidden = self.forbidden_completed_objective_roles
        if len(completed) != len(set(completed)):
            issues.append("motif_precondition_completed_roles_not_unique")
        if len(forbidden) != len(set(forbidden)):
            issues.append("motif_precondition_forbidden_roles_not_unique")
        overlap = sorted(set(completed).intersection(forbidden))
        if overlap:
            issues.append(f"motif_precondition_objective_role_conflict:{overlap[0]}")
        if any(not isinstance(role, str) or not role.strip() for role in completed + forbidden):
            issues.append("motif_precondition_objective_role_empty")
        return tuple(issues)


@dataclass(frozen=True)
class MotifEffectContract:
    """Structural and gameplay effects a motif promises to create."""

    completed_objective_node_ids: tuple[str, ...] = ()
    edge_state_changes: tuple[MotifEdgeStateChange, ...] = ()
    decision_node_ids: tuple[str, ...] = ()
    expected_downstream_dependency: MotifDependencyEffect = MotifDependencyEffect.NONE
    introduces_cycle: bool = False
    introduces_revisit: bool = False
    introduces_rejoin: bool = False
    introduces_failure_exit: bool = False
    introduces_recovery_exit: bool = False
    minimum_layout_footprint: tuple[int, int] = (1, 1)
    incompatible_effects: tuple[str, ...] = ()
    maximum_instances_per_composition: int | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "completed_objective_node_ids",
            "edge_state_changes",
            "decision_node_ids",
            "minimum_layout_footprint",
            "incompatible_effects",
        ):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))
        if not isinstance(self.expected_downstream_dependency, MotifDependencyEffect):
            object.__setattr__(
                self,
                "expected_downstream_dependency",
                MotifDependencyEffect(self.expected_downstream_dependency),
            )

    def validate(self) -> tuple[str, ...]:
        issues: list[str] = []
        for field_name, values in (
            ("completed_objective_nodes", self.completed_objective_node_ids),
            ("decision_nodes", self.decision_node_ids),
            ("incompatible_effects", self.incompatible_effects),
        ):
            if len(values) != len(set(values)):
                issues.append(f"motif_effect_{field_name}_not_unique")
            if any(not isinstance(value, str) or not value.strip() for value in values):
                issues.append(f"motif_effect_{field_name}_empty")
        if (
            len(self.minimum_layout_footprint) != 2
            or any(
                not isinstance(value, int) or isinstance(value, bool) or value <= 0
                for value in self.minimum_layout_footprint
            )
        ):
            issues.append("motif_effect_layout_footprint_invalid")
        if self.maximum_instances_per_composition is not None and (
            not isinstance(self.maximum_instances_per_composition, int)
            or isinstance(self.maximum_instances_per_composition, bool)
            or self.maximum_instances_per_composition <= 0
        ):
            issues.append("motif_effect_composition_limit_invalid")
        if len(self.edge_state_changes) != len(set(self.edge_state_changes)):
            issues.append("motif_effect_edge_state_changes_not_unique")
        return tuple(issues)
