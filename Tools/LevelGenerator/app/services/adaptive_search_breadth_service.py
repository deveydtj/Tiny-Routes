"""Deterministically broaden V3 candidate search when yield is too low."""

from __future__ import annotations

from dataclasses import dataclass

from ..models.search_planning import (
    AdaptiveSearchBreadthResult,
    SearchBreadth,
    SearchBreadthAdjustment,
    SearchYieldEvidence,
)
from .v3_candidate_pipeline_coordinator import V3CandidatePipelineResult


@dataclass(frozen=True)
class AdaptiveSearchBreadthConfig:
    low_yield_ratio: float = 0.25
    minimum_sample_size: int = 3
    maximum_breadth: SearchBreadth = SearchBreadth(32, 16, 12, 12, 24, 256)

    def __post_init__(self) -> None:
        if not 0.0 <= self.low_yield_ratio <= 1.0:
            raise ValueError("low_yield_ratio must be between zero and one")
        if (
            not isinstance(self.minimum_sample_size, int)
            or isinstance(self.minimum_sample_size, bool)
            or self.minimum_sample_size <= 0
        ):
            raise ValueError("minimum_sample_size must be a positive integer")
        if not isinstance(self.maximum_breadth, SearchBreadth):
            raise TypeError("maximum_breadth must be SearchBreadth")


class AdaptiveSearchBreadthService:
    """Increase every production search dimension, never a quality threshold."""

    _FIELDS = (
        "blueprint_count",
        "composition_alternatives_per_blueprint",
        "layout_variants",
        "road_shape_variants",
        "candidate_pool_size",
        "attempt_budget",
    )

    def __init__(self, config: AdaptiveSearchBreadthConfig | None = None) -> None:
        self.config = config or AdaptiveSearchBreadthConfig()

    def evaluate(
        self,
        breadth: SearchBreadth,
        *,
        attempted_candidates: int,
        accepted_candidates: int,
        difficulty: str,
        archetype: str,
        required_candidates: int | None = None,
        previous_adjustments: tuple[SearchBreadthAdjustment, ...] = (),
    ) -> AdaptiveSearchBreadthResult:
        if not isinstance(breadth, SearchBreadth):
            raise TypeError("breadth must be SearchBreadth")
        evidence = SearchYieldEvidence(
            difficulty=difficulty,
            archetype=archetype,
            attempted_candidates=attempted_candidates,
            accepted_candidates=accepted_candidates,
            required_candidates=(
                breadth.candidate_pool_size
                if required_candidates is None
                else required_candidates
            ),
        )
        prior = tuple(previous_adjustments)
        if any(not isinstance(item, SearchBreadthAdjustment) for item in prior):
            raise TypeError("previous_adjustments contains an invalid value")
        if not self._is_low_yield(evidence):
            return AdaptiveSearchBreadthResult(breadth, evidence, ())

        expanded = self._expanded(breadth)
        changed = tuple(
            field_name
            for field_name in self._FIELDS
            if getattr(expanded, field_name) != getattr(breadth, field_name)
        )
        if not changed:
            return AdaptiveSearchBreadthResult(breadth, evidence, ())
        adjustment = SearchBreadthAdjustment(
            sequence=len(prior) + 1,
            reason="low_candidate_yield",
            evidence=evidence,
            before=breadth,
            after=expanded,
            changed_dimensions=changed,
        )
        return AdaptiveSearchBreadthResult(expanded, evidence, (adjustment,))

    def evaluate_pipeline_results(
        self,
        breadth: SearchBreadth,
        results: tuple[V3CandidatePipelineResult, ...],
        *,
        difficulty: str,
        archetype: str,
        required_candidates: int | None = None,
        previous_adjustments: tuple[SearchBreadthAdjustment, ...] = (),
    ) -> AdaptiveSearchBreadthResult:
        attempts = tuple(results)
        if any(not isinstance(item, V3CandidatePipelineResult) for item in attempts):
            raise TypeError("results must contain V3CandidatePipelineResult values")
        return self.evaluate(
            breadth,
            attempted_candidates=len(attempts),
            accepted_candidates=sum(item.passed for item in attempts),
            difficulty=difficulty,
            archetype=archetype,
            required_candidates=required_candidates,
            previous_adjustments=previous_adjustments,
        )

    # Concise aliases for orchestration callers.
    adapt = evaluate
    plan = evaluate

    def _is_low_yield(self, evidence: SearchYieldEvidence) -> bool:
        if evidence.pool_shortfall == 0:
            return False
        if evidence.attempted_candidates < self.config.minimum_sample_size:
            return False
        return evidence.yield_ratio <= self.config.low_yield_ratio

    def _expanded(self, breadth: SearchBreadth) -> SearchBreadth:
        maximum = self.config.maximum_breadth
        values = {
            "blueprint_count": self._grow(
                breadth.blueprint_count, maximum.blueprint_count, 1
            ),
            "composition_alternatives_per_blueprint": self._grow(
                breadth.composition_alternatives_per_blueprint,
                maximum.composition_alternatives_per_blueprint,
                1,
            ),
            "layout_variants": self._grow(
                breadth.layout_variants, maximum.layout_variants, 1
            ),
            "road_shape_variants": self._grow(
                breadth.road_shape_variants, maximum.road_shape_variants, 1
            ),
            "candidate_pool_size": self._grow(
                breadth.candidate_pool_size, maximum.candidate_pool_size, 1
            ),
            "attempt_budget": self._grow(
                breadth.attempt_budget, maximum.attempt_budget, 4
            ),
        }
        return SearchBreadth(**values)

    @staticmethod
    def _grow(value: int, maximum: int, minimum_increment: int) -> int:
        increment = max(minimum_increment, (value + 1) // 2)
        # A caller may resume a run whose persisted breadth predates the
        # current configured cap. Adaptive planning is monotonic even then.
        return max(value, min(maximum, value + increment))
