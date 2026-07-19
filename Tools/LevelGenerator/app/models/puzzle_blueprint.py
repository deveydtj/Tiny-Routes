"""Graph-independent building blocks for a V3 puzzle blueprint."""

from __future__ import annotations

from dataclasses import dataclass

from .decision_dependency_graph import (
    DecisionDependencyGraph,
    DecisionDependencyKind,
)
from .puzzle_experience_target import PuzzleExperienceTarget


_OBJECTIVE_KINDS = {"pickup", "checkpoint", "delivery", "destination"}
_REVEAL_POLICIES = {"always", "whenActive", "afterPrevious"}


def _require_identifier(field_name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value.strip()


def _require_non_negative_integer(field_name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")


def _normalize_unique_identifiers(field_name: str, values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(_require_identifier(field_name, value) for value in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must be unique")
    return normalized


@dataclass(frozen=True)
class ObjectiveSpec:
    """An ordered objective phase before concrete graph nodes are allocated."""

    id: str
    kind: str
    sequence_index: int
    phase_entry_role: str
    phase_exit_role: str
    reveal_policy: str = "whenActive"

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_identifier("id", self.id))

        kind = _require_identifier("kind", self.kind).lower()
        if kind not in _OBJECTIVE_KINDS:
            raise ValueError(f"kind must be one of {sorted(_OBJECTIVE_KINDS)}")
        object.__setattr__(self, "kind", kind)

        _require_non_negative_integer("sequence_index", self.sequence_index)
        object.__setattr__(
            self,
            "phase_entry_role",
            _require_identifier("phase_entry_role", self.phase_entry_role),
        )
        object.__setattr__(
            self,
            "phase_exit_role",
            _require_identifier("phase_exit_role", self.phase_exit_role),
        )

        reveal_policy = _require_identifier("reveal_policy", self.reveal_policy)
        if reveal_policy not in _REVEAL_POLICIES:
            raise ValueError(
                f"reveal_policy must be one of {sorted(_REVEAL_POLICIES)}"
            )
        object.__setattr__(self, "reveal_policy", reveal_policy)

    @property
    def is_terminal(self) -> bool:
        return self.kind == "destination"


@dataclass(frozen=True)
class StateTransitionSpec:
    """A visible phase or route-state change required by a blueprint.

    A transition is triggered by exactly one objective completion or decision
    choice. Role identifiers deliberately refer to blueprint roles rather than
    final edge IDs, keeping this model independent from topology composition.
    """

    id: str
    from_phase_index: int
    to_phase_index: int
    trigger_objective_id: str | None = None
    trigger_decision_id: str | None = None
    required_completed_objective_ids: tuple[str, ...] = ()
    revealed_objective_ids: tuple[str, ...] = ()
    opened_edge_roles: tuple[str, ...] = ()
    closed_edge_roles: tuple[str, ...] = ()
    consumed_edge_roles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_identifier("id", self.id))
        _require_non_negative_integer("from_phase_index", self.from_phase_index)
        _require_non_negative_integer("to_phase_index", self.to_phase_index)
        if self.to_phase_index <= self.from_phase_index:
            raise ValueError("to_phase_index must be greater than from_phase_index")

        triggers = (
            self.trigger_objective_id is not None,
            self.trigger_decision_id is not None,
        )
        if sum(triggers) != 1:
            raise ValueError(
                "exactly one of trigger_objective_id or trigger_decision_id is required"
            )
        if self.trigger_objective_id is not None:
            object.__setattr__(
                self,
                "trigger_objective_id",
                _require_identifier("trigger_objective_id", self.trigger_objective_id),
            )
        if self.trigger_decision_id is not None:
            object.__setattr__(
                self,
                "trigger_decision_id",
                _require_identifier("trigger_decision_id", self.trigger_decision_id),
            )

        for field_name in (
            "required_completed_objective_ids",
            "revealed_objective_ids",
            "opened_edge_roles",
            "closed_edge_roles",
            "consumed_edge_roles",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalize_unique_identifiers(field_name, getattr(self, field_name)),
            )

        opened = set(self.opened_edge_roles)
        closed = set(self.closed_edge_roles)
        consumed = set(self.consumed_edge_roles)
        if opened.intersection(closed | consumed):
            raise ValueError("an edge role cannot be both opened and closed or consumed")
        if closed.intersection(consumed):
            raise ValueError("an edge role cannot be both closed and consumed")

    @property
    def changes_route_state(self) -> bool:
        return bool(
            self.opened_edge_roles
            or self.closed_edge_roles
            or self.consumed_edge_roles
        )


@dataclass(frozen=True)
class PuzzleBlueprint:
    """Validated strategic intent for a V3 puzzle before topology is built.

    The blueprint deliberately refers to objective, switch, and edge *roles*.
    Concrete node IDs, coordinates, and road geometry are assigned by later
    composition stages. ``validate()`` returns stable issue codes so blueprint
    search can reject intent deterministically without relying on exceptions.
    """

    id: str
    archetype: str
    experience_target: PuzzleExperienceTarget
    objectives: tuple[ObjectiveSpec, ...]
    decision_graph: DecisionDependencyGraph
    state_transitions: tuple[StateTransitionSpec, ...]
    planning_decision_ids: tuple[str, ...]
    adaptive_decision_ids: tuple[str, ...]
    required_revisit_decision_ids: tuple[str, ...]
    successful_strategy_count_range: tuple[int, int]
    requires_unique_optimal_strategy: bool
    requires_static_policy_rejection: bool
    recoverable_mistake_target: int
    fatal_mistake_cap: int
    required_mechanic_categories: tuple[str, ...]
    forbidden_mechanic_combinations: tuple[tuple[str, ...], ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.id, str):
            object.__setattr__(self, "id", self.id.strip())
        if isinstance(self.archetype, str):
            object.__setattr__(self, "archetype", self.archetype.strip().lower())
        for field_name in (
            "objectives",
            "state_transitions",
            "planning_decision_ids",
            "adaptive_decision_ids",
            "required_revisit_decision_ids",
            "required_mechanic_categories",
        ):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))
        object.__setattr__(
            self,
            "successful_strategy_count_range",
            tuple(self.successful_strategy_count_range),
        )
        object.__setattr__(
            self,
            "forbidden_mechanic_combinations",
            tuple(tuple(combination) for combination in self.forbidden_mechanic_combinations),
        )

    @property
    def decision_ids(self) -> tuple[str, ...]:
        return tuple(decision.id for decision in self.decision_graph.decisions)

    @property
    def objective_phases(self) -> tuple[ObjectiveSpec, ...]:
        """Alias that makes the phase-oriented blueprint API explicit."""

        return self.objectives

    @property
    def is_valid(self) -> bool:
        return not self.validate()

    def validate(self) -> tuple[str, ...]:
        """Return deterministic issue codes for malformed or weak intent."""

        issues: list[str] = []
        if not isinstance(self.id, str) or not self.id.strip():
            issues.append("blueprint_id_empty")
        if not isinstance(self.archetype, str) or not self.archetype.strip():
            issues.append("blueprint_archetype_empty")
        if not isinstance(self.experience_target, PuzzleExperienceTarget):
            issues.append("blueprint_experience_target_invalid")
            return tuple(issues)
        if not isinstance(self.decision_graph, DecisionDependencyGraph):
            issues.append("blueprint_decision_graph_invalid")
            return tuple(issues)

        objective_by_id: dict[str, ObjectiveSpec] = {}
        objective_indices: list[int] = []
        terminal_ids: list[str] = []
        for objective in self.objectives:
            if not isinstance(objective, ObjectiveSpec):
                issues.append("blueprint_objective_invalid")
                continue
            if objective.id in objective_by_id:
                issues.append(f"blueprint_objective_duplicate:{objective.id}")
            else:
                objective_by_id[objective.id] = objective
            objective_indices.append(objective.sequence_index)
            if objective.is_terminal:
                terminal_ids.append(objective.id)

        expected_indices = list(range(len(self.objectives)))
        if objective_indices != expected_indices:
            issues.append("blueprint_objective_sequence_not_contiguous")
        if len(terminal_ids) != 1:
            issues.append("blueprint_terminal_objective_count_invalid")
        elif self.objectives and self.objectives[-1].id != terminal_ids[0]:
            issues.append("blueprint_terminal_objective_not_final")

        objective_count = len(self.objectives)
        self._check_count_range(
            "objective_count",
            objective_count,
            self.experience_target.objective_count_range,
            issues,
        )

        issues.extend(
            f"blueprint_{issue}" for issue in self.decision_graph.validate()
        )
        decision_by_id = {
            decision.id: decision for decision in self.decision_graph.decisions
        }
        self._check_count_range(
            "meaningful_decision_count",
            len(decision_by_id),
            self.experience_target.meaningful_decision_range,
            issues,
        )
        self._check_count_range(
            "dependency_depth",
            self.decision_graph.dependency_depth,
            self.experience_target.dependency_depth_range,
            issues,
        )

        for decision in self.decision_graph.decisions:
            if decision.phase_index >= objective_count:
                issues.append(f"blueprint_decision_phase_unknown:{decision.id}")
        for objective_id, phase_index in self.decision_graph.objective_phase_indices:
            objective = objective_by_id.get(objective_id)
            if objective is None:
                issues.append(f"blueprint_dependency_objective_unknown:{objective_id}")
            elif objective.sequence_index != phase_index:
                issues.append(
                    f"blueprint_dependency_objective_phase_mismatch:{objective_id}"
                )

        self._validate_decision_subset(
            "planning",
            self.planning_decision_ids,
            decision_by_id,
            self.experience_target.planning_decision_minimum,
            issues,
        )

        dependency_decision_ids = {
            decision_id
            for dependency in self.decision_graph.dependencies
            for decision_id in (dependency.source_id, dependency.target_id)
            if decision_id in decision_by_id
        }
        for decision_id in self.planning_decision_ids:
            if (
                decision_id in decision_by_id
                and decision_id not in dependency_decision_ids
            ):
                issues.append(
                    f"blueprint_planning_decision_has_no_dependency:{decision_id}"
                )
        self._validate_decision_subset(
            "adaptive",
            self.adaptive_decision_ids,
            decision_by_id,
            self.experience_target.adaptive_decision_minimum,
            issues,
        )

        adaptive_dependency_targets = {
            dependency.target_id
            for dependency in self.decision_graph.dependencies
            if dependency.kind
            in {DecisionDependencyKind.OBJECTIVE_STATE, DecisionDependencyKind.REVISIT}
        }
        for decision_id in self.adaptive_decision_ids:
            if decision_id not in adaptive_dependency_targets:
                issues.append(
                    f"blueprint_adaptive_decision_has_no_state_dependency:{decision_id}"
                )

        revisit_targets = {
            dependency.target_id
            for dependency in self.decision_graph.dependencies
            if dependency.kind is DecisionDependencyKind.REVISIT
        }
        revisit_ids = self.required_revisit_decision_ids
        self._validate_unique_ids("required_revisit", revisit_ids, issues)
        for decision_id in revisit_ids:
            if decision_id not in decision_by_id:
                issues.append(f"blueprint_required_revisit_unknown:{decision_id}")
            elif decision_id not in revisit_targets:
                issues.append(f"blueprint_required_revisit_not_realized:{decision_id}")
        missing_required_revisits = revisit_targets.difference(revisit_ids)
        for decision_id in sorted(missing_required_revisits):
            issues.append(f"blueprint_revisit_not_declared:{decision_id}")
        self._check_count_range(
            "revisit_count",
            len(set(revisit_ids)),
            self.experience_target.revisit_range,
            issues,
        )

        transition_ids: set[str] = set()
        route_state_change_count = 0
        for transition in self.state_transitions:
            if not isinstance(transition, StateTransitionSpec):
                issues.append("blueprint_state_transition_invalid")
                continue
            if transition.id in transition_ids:
                issues.append(f"blueprint_state_transition_duplicate:{transition.id}")
            transition_ids.add(transition.id)
            if (
                transition.from_phase_index >= objective_count
                or transition.to_phase_index >= objective_count
            ):
                issues.append(f"blueprint_state_transition_phase_unknown:{transition.id}")
            if (
                transition.trigger_objective_id is not None
                and transition.trigger_objective_id not in objective_by_id
            ):
                issues.append(
                    f"blueprint_state_transition_objective_unknown:{transition.id}:"
                    f"{transition.trigger_objective_id}"
                )
            elif transition.trigger_objective_id is not None:
                trigger_objective = objective_by_id[transition.trigger_objective_id]
                if trigger_objective.sequence_index != transition.from_phase_index:
                    issues.append(
                        f"blueprint_state_transition_objective_phase_mismatch:"
                        f"{transition.id}"
                    )
            if (
                transition.trigger_decision_id is not None
                and transition.trigger_decision_id not in decision_by_id
            ):
                issues.append(
                    f"blueprint_state_transition_decision_unknown:{transition.id}:"
                    f"{transition.trigger_decision_id}"
                )
            elif transition.trigger_decision_id is not None:
                trigger_decision = decision_by_id[transition.trigger_decision_id]
                if trigger_decision.phase_index != transition.from_phase_index:
                    issues.append(
                        f"blueprint_state_transition_decision_phase_mismatch:"
                        f"{transition.id}"
                    )
            for referenced_id in (
                *transition.required_completed_objective_ids,
                *transition.revealed_objective_ids,
            ):
                if referenced_id not in objective_by_id:
                    issues.append(
                        f"blueprint_state_transition_reference_unknown:"
                        f"{transition.id}:{referenced_id}"
                    )
            if transition.changes_route_state:
                route_state_change_count += 1
        self._check_count_range(
            "state_change_count",
            route_state_change_count,
            self.experience_target.state_change_range,
            issues,
        )

        strategy_range = self.successful_strategy_count_range
        if not self._is_non_negative_int_range(strategy_range) or strategy_range[0] < 1:
            issues.append("blueprint_successful_strategy_range_invalid")
        else:
            target_strategy_range = self.experience_target.successful_route_class_range
            if (
                strategy_range[0] < target_strategy_range[0]
                or strategy_range[1] > target_strategy_range[1]
            ):
                issues.append("blueprint_successful_strategy_range_outside_target")

        if self.requires_unique_optimal_strategy is not True:
            issues.append("blueprint_unique_optimal_strategy_not_required")
        if self.requires_static_policy_rejection is not True:
            issues.append("blueprint_static_policy_rejection_not_required")

        if not self._is_non_negative_int(self.recoverable_mistake_target):
            issues.append("blueprint_recoverable_mistake_target_invalid")
        else:
            self._check_count_range(
                "recoverable_mistake_target",
                self.recoverable_mistake_target,
                self.experience_target.recoverable_mistake_range,
                issues,
            )
        if not self._is_non_negative_int(self.fatal_mistake_cap):
            issues.append("blueprint_fatal_mistake_cap_invalid")
        elif self.fatal_mistake_cap > self.experience_target.fatal_mistake_cap:
            issues.append("blueprint_fatal_mistake_cap_above_target")

        required_mechanics = self.required_mechanic_categories
        self._validate_unique_ids("required_mechanic", required_mechanics, issues)
        allowed_mechanics = set(self.experience_target.allowed_mechanic_categories)
        for mechanic in required_mechanics:
            if mechanic not in allowed_mechanics:
                issues.append(f"blueprint_required_mechanic_not_allowed:{mechanic}")

        seen_combinations: set[tuple[str, ...]] = set()
        required_mechanic_set = set(required_mechanics)
        for index, combination in enumerate(self.forbidden_mechanic_combinations):
            if len(combination) < 2 or any(
                not isinstance(mechanic, str) or not mechanic.strip()
                for mechanic in combination
            ):
                issues.append(f"blueprint_forbidden_combination_invalid:{index}")
                continue
            if len(combination) != len(set(combination)):
                issues.append(f"blueprint_forbidden_combination_duplicate_item:{index}")
            for mechanic in combination:
                if mechanic not in allowed_mechanics:
                    issues.append(
                        f"blueprint_forbidden_mechanic_not_allowed:{index}:{mechanic}"
                    )
            canonical = tuple(sorted(combination))
            if canonical in seen_combinations:
                issues.append(f"blueprint_forbidden_combination_duplicate:{index}")
            seen_combinations.add(canonical)
            if set(combination).issubset(required_mechanic_set):
                issues.append(f"blueprint_forbidden_combination_required:{index}")

        return tuple(issues)

    @classmethod
    def _validate_decision_subset(
        cls,
        label: str,
        decision_ids: tuple[str, ...],
        decision_by_id: dict[str, object],
        minimum: int,
        issues: list[str],
    ) -> None:
        cls._validate_unique_ids(f"{label}_decision", decision_ids, issues)
        for decision_id in decision_ids:
            if decision_id not in decision_by_id:
                issues.append(f"blueprint_{label}_decision_unknown:{decision_id}")
        if len(set(decision_ids)) < minimum:
            issues.append(f"blueprint_{label}_decision_count_below_target")

    @staticmethod
    def _validate_unique_ids(
        label: str,
        values: tuple[str, ...],
        issues: list[str],
    ) -> None:
        seen: set[str] = set()
        for value in values:
            if not isinstance(value, str) or not value.strip():
                issues.append(f"blueprint_{label}_id_empty")
                continue
            if value in seen:
                issues.append(f"blueprint_{label}_id_duplicate:{value}")
            seen.add(value)

    @classmethod
    def _check_count_range(
        cls,
        label: str,
        value: int,
        expected_range: tuple[int, int],
        issues: list[str],
    ) -> None:
        if value < expected_range[0]:
            issues.append(f"blueprint_{label}_below_target")
        elif value > expected_range[1]:
            issues.append(f"blueprint_{label}_above_target")

    @staticmethod
    def _is_non_negative_int(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0

    @classmethod
    def _is_non_negative_int_range(cls, value: object) -> bool:
        return (
            isinstance(value, tuple)
            and len(value) == 2
            and all(cls._is_non_negative_int(item) for item in value)
            and value[0] <= value[1]
        )
