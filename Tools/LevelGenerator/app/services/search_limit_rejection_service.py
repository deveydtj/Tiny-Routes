"""Hard rejection gate for incomplete exact-strategy proof searches."""

from __future__ import annotations

from ..models.static_policy import (
    SearchLimitRejectionResult,
    StaticPolicySearchResult,
)
from ..models.strategy_search import StrategySearchResult


class SearchLimitRejectionService:
    """Reject uncertainty; proof requirements may never relax after a limit."""

    def assess(
        self,
        strategy_search: StrategySearchResult,
        static_policy_search: StaticPolicySearchResult,
    ) -> SearchLimitRejectionResult:
        reasons: list[str] = []
        if not strategy_search.exhaustive:
            reasons.append("strategy_proof_search_incomplete")
            reasons.extend(
                f"strategy_proof_limit:{reason}"
                for reason in strategy_search.limit_reasons
            )
        if not static_policy_search.proof_complete:
            reasons.append("static_policy_proof_search_incomplete")
            reasons.extend(
                f"static_policy_proof_limit:{reason}"
                for reason in static_policy_search.limit_reasons
            )
        return SearchLimitRejectionResult(
            accepted=not reasons,
            rejection_reasons=tuple(reasons),
        )

    # Gate is a convenient verb for production-pipeline callers.
    gate = assess
