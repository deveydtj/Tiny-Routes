"""Derive production par taps only from accepted exact proof evidence."""

from __future__ import annotations

from ..models.solution_limits import ParTapDerivationResult
from ..models.strategy_search import UniqueOptimalProof


class ParTapDerivationService:
    """Fail closed unless one exhaustive, cost-consistent optimum is proven."""

    def derive(self, proof: UniqueOptimalProof | None) -> ParTapDerivationResult:
        reasons: list[str] = []
        if proof is None:
            reasons.append("par_optimal_proof_missing")
            return ParTapDerivationResult(False, None, None, tuple(reasons))

        if not proof.accepted:
            reasons.append("par_optimal_proof_rejected")
        if not proof.exhaustive:
            reasons.append("par_optimal_search_incomplete")
        if not proof.is_unique or len(proof.equal_cost_strategy_classes) != 1:
            reasons.append("par_optimal_strategy_not_unique")
        if proof.optimal_cost is None:
            reasons.append("par_optimal_cost_missing")
        if proof.optimal_strategy_class is None:
            reasons.append("par_optimal_strategy_class_missing")
        elif (
            proof.optimal_cost is not None
            and proof.optimal_strategy_class.canonical_trace.cost != proof.optimal_cost
        ):
            reasons.append("par_optimal_cost_inconsistent")

        if reasons:
            return ParTapDerivationResult(
                accepted=False,
                par_taps=None,
                optimal_cost=proof.optimal_cost,
                rejection_reasons=tuple(reasons),
            )
        assert proof.optimal_cost is not None
        return ParTapDerivationResult(
            accepted=True,
            par_taps=proof.optimal_cost.accepted_taps,
            optimal_cost=proof.optimal_cost,
        )

    derive_par_taps = derive
