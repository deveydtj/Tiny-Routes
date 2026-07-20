"""Typed minimum-information horizon classifications for optimal decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PlanningHorizon(str, Enum):
    """Increasing information required to prefer a proven optimal action."""

    IMMEDIATE_EDGE_ONLY = "immediateEdgeOnly"
    ONE_TRANSITION = "oneTransition"
    TWO_TRANSITIONS = "twoTransitions"
    OBJECTIVE_STATE_KNOWLEDGE = "objectiveStateKnowledge"
    CROSS_PHASE_KNOWLEDGE = "crossPhaseKnowledge"

    @property
    def rank(self) -> int:
        return tuple(PlanningHorizon).index(self)


@dataclass(frozen=True)
class PlanningHorizonDecision:
    """Minimum visible reasoning horizon for one action on the optimal trace."""

    decision_ordinal: int
    objective_index: int
    node_id: str
    optimal_edge_id: str
    horizon: PlanningHorizon
    matched_policy_names: tuple[str, ...]
    rationale: str

    def __post_init__(self) -> None:
        for field_name in ("decision_ordinal", "objective_index"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        for field_name in ("node_id", "optimal_edge_id", "rationale"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} cannot be empty")
            object.__setattr__(self, field_name, value.strip())
        if not isinstance(self.horizon, PlanningHorizon):
            object.__setattr__(self, "horizon", PlanningHorizon(self.horizon))
        names = tuple(self.matched_policy_names)
        if any(not isinstance(name, str) or not name.strip() for name in names):
            raise ValueError("matched_policy_names cannot contain empty names")
        if len(names) != len(set(names)):
            raise ValueError("matched_policy_names must be unique")
        object.__setattr__(self, "matched_policy_names", names)


@dataclass(frozen=True)
class PlanningHorizonReport:
    """Deterministic planning-depth evidence over a complete optimal trace."""

    level_id: str
    decisions: tuple[PlanningHorizonDecision, ...]
    strategy_proof_exhaustive: bool

    def __post_init__(self) -> None:
        if not isinstance(self.level_id, str) or not self.level_id.strip():
            raise ValueError("level_id cannot be empty")
        object.__setattr__(self, "level_id", self.level_id.strip())
        if not isinstance(self.strategy_proof_exhaustive, bool):
            raise ValueError("strategy_proof_exhaustive must be a Boolean")
        decisions = tuple(self.decisions)
        if tuple(item.decision_ordinal for item in decisions) != tuple(range(len(decisions))):
            raise ValueError("decision ordinals must be contiguous from zero")
        object.__setattr__(self, "decisions", decisions)

    @property
    def maximum_horizon(self) -> PlanningHorizon | None:
        if not self.decisions:
            return None
        return max((item.horizon for item in self.decisions), key=lambda value: value.rank)

    @property
    def counts(self) -> tuple[tuple[PlanningHorizon, int], ...]:
        return tuple(
            (horizon, sum(item.horizon is horizon for item in self.decisions))
            for horizon in PlanningHorizon
            if any(item.horizon is horizon for item in self.decisions)
        )
