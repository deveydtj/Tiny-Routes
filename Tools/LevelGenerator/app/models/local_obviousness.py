"""Typed evidence for locally obvious optimal route decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LocalObviousnessKind(str, Enum):
    """A simple visible rule that can select an optimal outgoing road."""

    EUCLIDEAN_OBJECTIVE_CLOSENESS = "euclideanObjectiveCloseness"
    ONLY_NON_DEAD_END_ROAD = "onlyNonDeadEndRoad"
    ONLY_NON_BACKWARD_ROAD = "onlyNonBackwardRoad"
    FIRST_OUTGOING_EDGE = "firstOutgoingEdge"
    FIXED_DIRECTION_RULE = "fixedDirectionRule"


@dataclass(frozen=True)
class LocalObviousnessDecision:
    """All trivial rules that explain one meaningful optimal decision."""

    decision_ordinal: int
    objective_index: int
    node_id: str
    optimal_edge_id: str
    matched_rules: tuple[LocalObviousnessKind, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("decision_ordinal", "objective_index"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        for field_name in ("node_id", "optimal_edge_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} cannot be empty")
            object.__setattr__(self, field_name, value.strip())
        rules = tuple(
            rule if isinstance(rule, LocalObviousnessKind) else LocalObviousnessKind(rule)
            for rule in self.matched_rules
        )
        if len(rules) != len(set(rules)):
            raise ValueError("matched_rules must be unique")
        object.__setattr__(self, "matched_rules", rules)

    @property
    def is_locally_obvious(self) -> bool:
        return bool(self.matched_rules)


@dataclass(frozen=True)
class LocalObviousnessReport:
    """Hard local-obviousness assessment over meaningful optimal choices."""

    level_id: str
    decisions: tuple[LocalObviousnessDecision, ...]
    successful_fixed_direction_rules: tuple[str, ...]
    strategy_proof_exhaustive: bool
    accepted: bool
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.level_id, str) or not self.level_id.strip():
            raise ValueError("level_id cannot be empty")
        object.__setattr__(self, "level_id", self.level_id.strip())
        decisions = tuple(self.decisions)
        keys = tuple((item.decision_ordinal, item.node_id) for item in decisions)
        if len(keys) != len(set(keys)):
            raise ValueError("local-obviousness decisions must be unique")
        object.__setattr__(self, "decisions", decisions)
        directions = tuple(self.successful_fixed_direction_rules)
        if any(direction not in {"north", "east", "south", "west"} for direction in directions):
            raise ValueError("fixed direction rules must be cardinal directions")
        if len(directions) != len(set(directions)):
            raise ValueError("fixed direction rules must be unique")
        object.__setattr__(self, "successful_fixed_direction_rules", directions)
        if not isinstance(self.strategy_proof_exhaustive, bool):
            raise ValueError("strategy_proof_exhaustive must be a Boolean")
        if not isinstance(self.accepted, bool):
            raise ValueError("accepted must be a Boolean")
        reasons = tuple(sorted(set(self.rejection_reasons)))
        should_reject = not decisions or all(item.is_locally_obvious for item in decisions)
        if self.accepted == should_reject:
            raise ValueError("accepted must match the local-obviousness decision evidence")
        if self.accepted and reasons:
            raise ValueError("an accepted local-obviousness report cannot have rejection reasons")
        if not self.accepted and not reasons:
            raise ValueError("a rejected local-obviousness report requires a rejection reason")
        object.__setattr__(self, "rejection_reasons", reasons)

    @property
    def all_optimal_decisions_locally_obvious(self) -> bool:
        return bool(self.decisions) and all(item.is_locally_obvious for item in self.decisions)

    @property
    def non_obvious_decision_count(self) -> int:
        return sum(not item.is_locally_obvious for item in self.decisions)
