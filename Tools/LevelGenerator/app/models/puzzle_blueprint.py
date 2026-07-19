"""Graph-independent building blocks for a V3 puzzle blueprint."""

from __future__ import annotations

from dataclasses import dataclass


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
