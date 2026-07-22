"""Behavior-first duplicate comparison against the shipped level corpus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..models.candidate_signature import CandidateSignature


@dataclass(frozen=True)
class BehaviorComparisonDimension:
    name: str
    similarity: float
    weight: float


@dataclass(frozen=True)
class ExistingCorpusBehaviorComparisonResult:
    too_similar: bool
    score: float
    threshold: float
    matched_level_id: str | None = None
    reason_code: str | None = None
    message: str = "No comparable behavior evidence."
    dimensions: tuple[BehaviorComparisonDimension, ...] = ()


class ExistingCorpusBehaviorComparisonService:
    """Compare puzzle behavior while ignoring names and visual layout.

    Exact role-normalized route behavior is always rejected. Rich V3 proof
    evidence is otherwise compared dimension by dimension; sparse legacy
    evidence cannot accidentally become a duplicate merely because default or
    empty fields happen to match.
    """

    DEFAULT_REJECTION_THRESHOLD = 0.90
    MINIMUM_COMPARABLE_WEIGHT = 0.30

    def check_candidate(
        self,
        candidate: CandidateSignature,
        existing_signatures: Iterable[CandidateSignature],
        *,
        threshold: float | None = None,
    ) -> ExistingCorpusBehaviorComparisonResult:
        resolved_threshold = self._threshold(threshold)
        best = ExistingCorpusBehaviorComparisonResult(
            too_similar=False,
            score=0.0,
            threshold=resolved_threshold,
        )
        for existing in existing_signatures:
            result = self.compare(candidate, existing, threshold=resolved_threshold)
            if result.too_similar:
                return result
            if result.score > best.score:
                best = result
        return best

    def maximum_similarity(
        self,
        candidate: CandidateSignature,
        existing_signatures: Iterable[CandidateSignature],
    ) -> float:
        return max(
            (self.compare(candidate, existing).score for existing in existing_signatures),
            default=0.0,
        )

    def compare(
        self,
        candidate: CandidateSignature,
        existing: CandidateSignature,
        *,
        threshold: float | None = None,
    ) -> ExistingCorpusBehaviorComparisonResult:
        resolved_threshold = self._threshold(threshold)
        if (
            candidate.structural_behavior_signature
            and candidate.structural_behavior_signature
            == existing.structural_behavior_signature
        ):
            return ExistingCorpusBehaviorComparisonResult(
                too_similar=True,
                score=1.0,
                threshold=resolved_threshold,
                matched_level_id=existing.level_id,
                reason_code="same_structural_behavior",
                message=(
                    f"matches {existing.level_id}: the role-normalized route graph, "
                    "road-state rules, objectives, and tap pattern are identical"
                ),
                dimensions=(
                    BehaviorComparisonDimension("structuralBehavior", 1.0, 0.30),
                ),
            )

        dimensions: list[BehaviorComparisonDimension] = []
        self._exact_dimension(
            dimensions,
            "structuralBehavior",
            candidate.structural_behavior_signature,
            existing.structural_behavior_signature,
            0.30,
        )
        self._exact_dimension(
            dimensions,
            "dependencyDAG",
            candidate.dependency_dag_signature,
            existing.dependency_dag_signature,
            0.16,
        )
        self._collection_dimension(
            dimensions,
            "adaptiveDecisions",
            candidate.adaptive_decision_pattern,
            existing.adaptive_decision_pattern,
            0.10,
        )
        self._collection_dimension(
            dimensions,
            "stateTransitions",
            candidate.state_transition_pattern,
            existing.state_transition_pattern,
            0.10,
        )
        self._exact_dimension(
            dimensions,
            "staticPolicyProof",
            candidate.static_policy_proof_signature,
            existing.static_policy_proof_signature,
            0.06,
        )
        self._collection_dimension(
            dimensions,
            "agentPerformance",
            candidate.agent_performance_profile,
            existing.agent_performance_profile,
            0.05,
        )
        self._collection_dimension(
            dimensions,
            "revisitPattern",
            candidate.revisit_pattern,
            existing.revisit_pattern,
            0.06,
        )
        self._collection_dimension(
            dimensions,
            "outcomeDistribution",
            candidate.success_failure_distribution,
            existing.success_failure_distribution,
            0.06,
        )
        self._exact_dimension(
            dimensions,
            "optimalStrategy",
            candidate.optimal_strategy_signature,
            existing.optimal_strategy_signature,
            0.06,
        )
        self._sequence_dimension(
            dimensions,
            "objectiveKinds",
            candidate.objective_kinds,
            existing.objective_kinds,
            0.03,
        )
        self._sequence_dimension(
            dimensions,
            "switchDegrees",
            candidate.switch_degree_sequence,
            existing.switch_degree_sequence,
            0.02,
        )

        comparable_weight = sum(item.weight for item in dimensions)
        score = (
            sum(item.similarity * item.weight for item in dimensions)
            / comparable_weight
            if comparable_weight >= self.MINIMUM_COMPARABLE_WEIGHT
            else 0.0
        )
        score = round(score, 4)
        too_similar = comparable_weight >= self.MINIMUM_COMPARABLE_WEIGHT and score >= resolved_threshold
        reason_code = "behavior_similarity_threshold" if too_similar else None
        detail = ", ".join(
            f"{item.name}={item.similarity:.2f}" for item in dimensions
        ) or "no shared non-empty behavior dimensions"
        message = (
            f"matches {existing.level_id}: behavior similarity {score:.2f} "
            f"{'exceeds' if too_similar else 'is below'} {resolved_threshold:.2f}; "
            f"{detail}"
        )
        return ExistingCorpusBehaviorComparisonResult(
            too_similar=too_similar,
            score=score,
            threshold=resolved_threshold,
            matched_level_id=existing.level_id,
            reason_code=reason_code,
            message=message,
            dimensions=tuple(dimensions),
        )

    @classmethod
    def _threshold(cls, value: float | None) -> float:
        resolved = cls.DEFAULT_REJECTION_THRESHOLD if value is None else float(value)
        if not 0.0 < resolved <= 1.0:
            raise ValueError("behavior comparison threshold must be in (0, 1]")
        return resolved

    @staticmethod
    def _exact_dimension(dimensions, name, first, second, weight) -> None:
        if first and second:
            dimensions.append(
                BehaviorComparisonDimension(name, 1.0 if first == second else 0.0, weight)
            )

    @staticmethod
    def _collection_dimension(dimensions, name, first, second, weight) -> None:
        if not first or not second:
            return
        left = {repr(value) for value in first}
        right = {repr(value) for value in second}
        similarity = len(left & right) / len(left | right)
        dimensions.append(BehaviorComparisonDimension(name, similarity, weight))

    @staticmethod
    def _sequence_dimension(dimensions, name, first, second, weight) -> None:
        if not first or not second:
            return
        length = max(len(first), len(second))
        matches = sum(left == right for left, right in zip(first, second))
        dimensions.append(BehaviorComparisonDimension(name, matches / length, weight))
