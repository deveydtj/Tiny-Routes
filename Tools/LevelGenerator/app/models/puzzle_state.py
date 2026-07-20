"""Compact immutable state shared by V3 structural and runtime searches."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class PuzzleTerminalOutcome(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    FAILURE = "failure"


def _identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value.strip()


def _optional_identifier(value: str | None, field_name: str) -> str | None:
    return None if value is None else _identifier(value, field_name)


def _non_negative_integer(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _identifier_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_identifier(value, field_name) for value in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must be unique")
    return tuple(sorted(normalized))


def _mapping_tuple(
    values: tuple[tuple[str, str], ...],
    field_name: str,
) -> tuple[tuple[str, str], ...]:
    normalized = tuple(
        (_identifier(key, f"{field_name}_key"), _identifier(value, f"{field_name}_value"))
        for key, value in values
    )
    if len({key for key, _ in normalized}) != len(normalized):
        raise ValueError(f"{field_name} keys must be unique")
    return tuple(sorted(normalized))


def _count_tuple(
    values: tuple[tuple[str, int], ...],
) -> tuple[tuple[str, int], ...]:
    normalized = tuple(
        (
            _identifier(node_id, "visit_node_id"),
            _non_negative_integer(count, "visit_count"),
        )
        for node_id, count in values
    )
    if len({node_id for node_id, _ in normalized}) != len(normalized):
        raise ValueError("visit_counts node IDs must be unique")
    if any(count == 0 for _, count in normalized):
        raise ValueError("visit_counts must omit zero counts")
    return tuple(sorted(normalized))


@dataclass(frozen=True)
class PuzzleState:
    """A finite, canonical search key for all player-observable route state.

    Exactly one of ``current_node_id`` and ``current_edge_id`` is populated.
    Tuple-backed sets and maps are normalized on construction, making equal
    logical states equal and hash-identical regardless of input ordering.
    """

    current_node_id: str | None
    current_edge_id: str | None
    objective_index: int
    completed_objective_ids: tuple[str, ...] = ()
    available_edge_ids: tuple[str, ...] = ()
    consumed_edge_ids: tuple[str, ...] = ()
    active_switch_edge_ids: tuple[tuple[str, str], ...] = ()
    visit_counts: tuple[tuple[str, int], ...] = ()
    accepted_tap_count: int = 0
    elapsed_time_seconds: float = 0.0
    terminal_outcome: PuzzleTerminalOutcome = PuzzleTerminalOutcome.ACTIVE

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "current_node_id",
            _optional_identifier(self.current_node_id, "current_node_id"),
        )
        object.__setattr__(
            self,
            "current_edge_id",
            _optional_identifier(self.current_edge_id, "current_edge_id"),
        )
        if (self.current_node_id is None) == (self.current_edge_id is None):
            raise ValueError("exactly one current node or edge position is required")
        _non_negative_integer(self.objective_index, "objective_index")
        _non_negative_integer(self.accepted_tap_count, "accepted_tap_count")
        if (
            not isinstance(self.elapsed_time_seconds, (int, float))
            or isinstance(self.elapsed_time_seconds, bool)
            or self.elapsed_time_seconds < 0
        ):
            raise ValueError("elapsed_time_seconds must be a non-negative number")
        object.__setattr__(self, "elapsed_time_seconds", float(self.elapsed_time_seconds))
        if not isinstance(self.terminal_outcome, PuzzleTerminalOutcome):
            object.__setattr__(
                self,
                "terminal_outcome",
                PuzzleTerminalOutcome(self.terminal_outcome),
            )
        for field_name in (
            "completed_objective_ids",
            "available_edge_ids",
            "consumed_edge_ids",
        ):
            object.__setattr__(
                self,
                field_name,
                _identifier_tuple(tuple(getattr(self, field_name)), field_name),
            )
        object.__setattr__(
            self,
            "active_switch_edge_ids",
            _mapping_tuple(tuple(self.active_switch_edge_ids), "active_switch_edge_ids"),
        )
        object.__setattr__(self, "visit_counts", _count_tuple(tuple(self.visit_counts)))
        if set(self.available_edge_ids).intersection(self.consumed_edge_ids):
            raise ValueError("an edge cannot be both available and consumed")
        if any(
            edge_id not in self.available_edge_ids
            for _, edge_id in self.active_switch_edge_ids
        ):
            raise ValueError("active switch edges must be available")
        if self.objective_index != len(self.completed_objective_ids):
            raise ValueError("objective_index must equal completed objective count")

    @classmethod
    def initial(
        cls,
        *,
        start_node_id: str,
        available_edge_ids: tuple[str, ...],
        active_switch_edge_ids: tuple[tuple[str, str], ...] = (),
    ) -> "PuzzleState":
        return cls(
            current_node_id=start_node_id,
            current_edge_id=None,
            objective_index=0,
            available_edge_ids=available_edge_ids,
            active_switch_edge_ids=active_switch_edge_ids,
            visit_counts=((start_node_id, 1),),
        )

    @property
    def is_terminal(self) -> bool:
        return self.terminal_outcome is not PuzzleTerminalOutcome.ACTIVE

    @property
    def active_switch_map(self) -> dict[str, str]:
        return dict(self.active_switch_edge_ids)

    @property
    def visit_count_map(self) -> dict[str, int]:
        return dict(self.visit_counts)

    def evolve(self, **changes: object) -> "PuzzleState":
        return replace(self, **changes)
