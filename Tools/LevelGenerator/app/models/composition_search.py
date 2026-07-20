"""Deterministic branch and evidence models for composition backtracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .composition_state import CompositionState


@dataclass(frozen=True)
class CompositionSearchChoice:
    """One lazily applied composition branch in a stable retry order.

    Sort order is blueprint realization, then port, then motif.  Consequently,
    the search retries compatible motifs before advancing to another port, and
    retries ports before moving to another blueprint realization.
    """

    choice_id: str
    apply: Callable[[CompositionState], CompositionState] = field(
        compare=False,
        repr=False,
    )
    motif_id: str = ""
    port_id: str = ""
    blueprint_realization_index: int = 0
    port_index: int = 0
    motif_index: int = 0

    def __post_init__(self) -> None:
        for field_name in ("choice_id", "motif_id", "port_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string")
            object.__setattr__(self, field_name, value.strip())
        if not self.choice_id:
            raise ValueError("choice_id must not be empty")
        if not callable(self.apply):
            raise TypeError("apply must be callable")
        for field_name in (
            "blueprint_realization_index",
            "port_index",
            "motif_index",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")

    @property
    def sort_key(self) -> tuple[int, int, int, str, str, str]:
        return (
            self.blueprint_realization_index,
            self.port_index,
            self.motif_index,
            self.port_id,
            self.motif_id,
            self.choice_id,
        )


@dataclass(frozen=True, order=True)
class CompositionRejectionCount:
    reason: str
    count: int

    def __post_init__(self) -> None:
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must not be empty")
        object.__setattr__(self, "reason", self.reason.strip())
        if (
            not isinstance(self.count, int)
            or isinstance(self.count, bool)
            or self.count <= 0
        ):
            raise ValueError("count must be a positive integer")

    def to_dict(self) -> dict[str, object]:
        return {"reason": self.reason, "count": self.count}


@dataclass(frozen=True)
class CompositionSearchTraceEntry:
    state_signature: str
    choice_id: str | None
    outcome: str
    reason: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "stateSignature": self.state_signature,
            "choiceId": self.choice_id,
            "outcome": self.outcome,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class CompositionSearchResult:
    status: str
    solution_state: CompositionState | None
    attempted_branch_count: int
    expanded_state_count: int
    visited_state_count: int
    rejection_counts: tuple[CompositionRejectionCount, ...] = ()
    trace: tuple[CompositionSearchTraceEntry, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {"completed", "failed", "budget_exhausted"}:
            raise ValueError(f"Unknown composition search status: {self.status}")
        if (self.status == "completed") != (self.solution_state is not None):
            raise ValueError("Only a completed search may contain a solution state")
        for field_name in (
            "attempted_branch_count",
            "expanded_state_count",
            "visited_state_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")

    @property
    def is_successful(self) -> bool:
        return self.status == "completed"

    @property
    def budget_exhausted(self) -> bool:
        return self.status == "budget_exhausted"

    @property
    def branch_count(self) -> int:
        """Compatibility name used by composition diagnostics."""

        return self.attempted_branch_count

    @property
    def failure_reasons(self) -> tuple[str, ...]:
        return tuple(item.reason for item in self.rejection_counts)

    @property
    def rejection_reasons(self) -> tuple[str, ...]:
        return self.failure_reasons

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "solutionStateSignature": (
                self.solution_state.signature if self.solution_state is not None else None
            ),
            "branchCount": self.branch_count,
            "attemptedBranchCount": self.attempted_branch_count,
            "expandedStateCount": self.expanded_state_count,
            "visitedStateCount": self.visited_state_count,
            "rejectionCounts": [item.to_dict() for item in self.rejection_counts],
            "trace": [item.to_dict() for item in self.trace],
        }
