"""Typed proof evidence for state-oblivious permanent switch policies."""

from __future__ import annotations

from dataclasses import dataclass

from .strategy_search import StrategyTrace


def _identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


@dataclass(frozen=True, order=True)
class StaticPolicyAssignment:
    """One permanent outgoing-road selection for an authored switch."""

    node_id: str
    selected_edge_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _identifier(self.node_id, "node_id"))
        object.__setattr__(
            self,
            "selected_edge_id",
            _identifier(self.selected_edge_id, "selected_edge_id"),
        )


@dataclass(frozen=True)
class StaticPolicySolution:
    """A permanent assignment that completes every ordered objective."""

    assignments: tuple[StaticPolicyAssignment, ...]
    trace: StrategyTrace

    def __post_init__(self) -> None:
        assignments = tuple(self.assignments)
        node_ids = tuple(item.node_id for item in assignments)
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("static policy assignments must contain unique node IDs")
        if not self.trace.succeeded:
            raise ValueError("a static policy solution must contain a successful trace")
        object.__setattr__(self, "assignments", assignments)


@dataclass(frozen=True)
class StaticPolicySearchResult:
    """Conclusive witness or bounded exhaustive rejection evidence."""

    successful_policies: tuple[StaticPolicySolution, ...]
    tested_policy_count: int
    total_policy_count: int
    exhaustive: bool
    limit_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("tested_policy_count", "total_policy_count"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.tested_policy_count > self.total_policy_count:
            raise ValueError("tested_policy_count cannot exceed total_policy_count")
        policies = tuple(self.successful_policies)
        signatures = tuple(
            tuple((item.node_id, item.selected_edge_id) for item in policy.assignments)
            for policy in policies
        )
        if len(signatures) != len(set(signatures)):
            raise ValueError("successful static policies must be unique")
        reasons = tuple(sorted(set(self.limit_reasons)))
        if self.exhaustive and reasons:
            raise ValueError("an exhaustive static policy search cannot have limit reasons")
        if self.exhaustive and self.tested_policy_count != self.total_policy_count:
            raise ValueError("an exhaustive search must test every policy")
        if not self.exhaustive and not reasons:
            raise ValueError("a non-exhaustive search requires a limit reason")
        object.__setattr__(self, "successful_policies", policies)
        object.__setattr__(self, "limit_reasons", reasons)

    @property
    def static_policy_solvable(self) -> bool:
        return bool(self.successful_policies)

    @property
    def proof_complete(self) -> bool:
        """An existential witness is conclusive even if enumeration was bounded."""

        return self.static_policy_solvable or self.exhaustive

    @property
    def accepted_for_production(self) -> bool:
        return self.exhaustive and not self.static_policy_solvable

    @property
    def rejection_reasons(self) -> tuple[str, ...]:
        if self.static_policy_solvable:
            return ("static_policy_solution_exists",)
        if self.exhaustive:
            return ()
        return (
            "static_policy_search_incomplete",
            *(f"static_policy_limit:{reason}" for reason in self.limit_reasons),
        )


@dataclass(frozen=True)
class SearchLimitRejectionResult:
    """Hard-gate result for uncertainty in exact strategy proofs."""

    accepted: bool
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        reasons = tuple(sorted(set(self.rejection_reasons)))
        if self.accepted and reasons:
            raise ValueError("an accepted search-limit gate cannot have rejection reasons")
        if not self.accepted and not reasons:
            raise ValueError("a rejected search-limit gate requires a rejection reason")
        object.__setattr__(self, "rejection_reasons", reasons)
