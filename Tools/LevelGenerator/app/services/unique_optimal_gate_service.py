"""Production gate for exact unique-optimal strategy evidence."""

from __future__ import annotations

from ..models.production_puzzle_gate import UniqueOptimalGateResult
from ..models.puzzle_analysis import PuzzleAnalysis
from ..models.strategy_search import UniqueOptimalProof


class UniqueOptimalGateService:
    """Reject missing, uncertain, stale, or non-unique optimal proof evidence."""

    rejection_code = "unique_optimal_not_proven"

    def assess(
        self,
        analysis: PuzzleAnalysis,
        proof: UniqueOptimalProof | None,
    ) -> UniqueOptimalGateResult:
        proof_reasons: list[str] = []
        if proof is None:
            proof_reasons.append("unique_optimal_proof_missing")
        else:
            proof_reasons.extend(proof.rejection_reasons)
            if not proof.accepted:
                proof_reasons.append("unique_optimal_proof_rejected")
            if not proof.exhaustive:
                proof_reasons.append("unique_optimal_proof_incomplete")
            if not proof.is_unique or len(proof.equal_cost_strategy_classes) != 1:
                proof_reasons.append("unique_optimal_strategy_class_not_unique")
            if proof.optimal_strategy_class is None or proof.optimal_cost is None:
                proof_reasons.append("unique_optimal_strategy_evidence_missing")
            elif proof.optimal_strategy_class.canonical_trace.cost != proof.optimal_cost:
                proof_reasons.append("unique_optimal_proof_cost_inconsistent")
            if proof.optimal_cost is not None and (
                proof.optimal_cost.accepted_taps != analysis.optimal_accepted_taps
                or proof.optimal_cost.route_distance != analysis.optimal_route_distance
                or proof.optimal_cost.travel_time_seconds
                != analysis.optimal_travel_time_seconds
            ):
                proof_reasons.append("unique_optimal_analysis_cost_mismatch")
        if not analysis.optimal_uniqueness:
            proof_reasons.append("puzzle_analysis_optimal_uniqueness_false")

        accepted = not proof_reasons
        return UniqueOptimalGateResult(
            accepted=accepted,
            proof_rejection_reasons=tuple(proof_reasons),
            rejection_reasons=() if accepted else (self.rejection_code,),
        )

    gate = assess
