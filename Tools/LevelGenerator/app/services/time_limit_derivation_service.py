"""Derive production time limits from proven runtime distributions."""

from __future__ import annotations

from math import ceil, floor

from ..models.difficulty_preset import DifficultyPreset
from ..models.puzzle_analysis import PuzzleAnalysis
from ..models.puzzle_experience_target import PuzzleExperienceTarget
from ..models.solution_limits import (
    RuntimeDistributionSummary,
    TimeLimitDerivationResult,
)
from ..models.strategy_search import StrategySearchResult, UniqueOptimalProof
from .par_tap_derivation_service import ParTapDerivationService


class TimeLimitDerivationService:
    """Calculate a fair limit without trusting authored level metadata.

    The runtime reference is the upper quartile of exact optimal and near-optimal
    successful strategy classes. Planning allowance comes from the larger of the
    legacy difficulty padding and the minimum visible decision windows required
    by the V3 target. Input allowance reserves one difficulty-specific minimum tap
    spacing interval for every proven optimal tap.
    """

    def __init__(self, par_service: ParTapDerivationService | None = None) -> None:
        self.par_service = par_service or ParTapDerivationService()

    def derive(
        self,
        strategy_search: StrategySearchResult,
        proof: UniqueOptimalProof | None,
        analysis: PuzzleAnalysis,
        preset: DifficultyPreset,
        target: PuzzleExperienceTarget,
    ) -> TimeLimitDerivationResult:
        reasons: list[str] = []
        par = self.par_service.derive(proof)
        reasons.extend(par.rejection_reasons)
        if not strategy_search.exhaustive:
            reasons.append("time_limit_runtime_distribution_incomplete")
        if (
            strategy_search.canonical_optimal_strategy is None
            or strategy_search.optimal_cost is None
        ):
            reasons.append("time_limit_optimal_strategy_missing")
        elif par.optimal_cost is not None and strategy_search.optimal_cost != par.optimal_cost:
            reasons.append("time_limit_proof_search_cost_mismatch")
        if preset.name.strip().lower() != target.difficulty:
            reasons.append("time_limit_difficulty_target_mismatch")

        distribution = self._runtime_distribution(strategy_search)
        if distribution is None:
            reasons.append("time_limit_runtime_distribution_empty")

        if strategy_search.optimal_cost is not None and (
            strategy_search.optimal_cost.accepted_taps != analysis.optimal_accepted_taps
            or strategy_search.optimal_cost.travel_time_seconds
            != analysis.optimal_travel_time_seconds
            or strategy_search.optimal_cost.route_distance != analysis.optimal_route_distance
        ):
            reasons.append("time_limit_analysis_cost_mismatch")

        if (
            par.par_taps is None
            or strategy_search.optimal_cost is None
            or distribution is None
        ):
            return self._rejected(reasons)

        planning_allowance = max(
            float(preset.time_limit_padding_seconds),
            analysis.meaningful_decisions * float(target.decision_window_targets[0]),
        )
        input_allowance = par.par_taps * float(preset.min_tap_spacing_seconds)
        runtime_reference = max(
            strategy_search.optimal_cost.travel_time_seconds,
            distribution.upper_quartile_seconds,
        )
        uncapped_limit = ceil(runtime_reference + planning_allowance + input_allowance)
        desired_minimum, desired_maximum = target.desired_solve_time_range
        nominal_limit = max(uncapped_limit, ceil(desired_minimum))
        nominal_limit = min(nominal_limit, floor(desired_maximum))
        nominal_limit = max(1, nominal_limit)
        available_planning_margin = max(
            0.0,
            nominal_limit - runtime_reference - input_allowance,
        )
        if available_planning_margin + 1e-9 < planning_allowance:
            reasons.append("insufficient_time_limit_planning_margin")

        thresholds = self._star_thresholds(
            optimal_runtime=strategy_search.optimal_cost.travel_time_seconds,
            runtime_reference=runtime_reference,
            planning_allowance=planning_allowance,
            input_allowance=input_allowance,
            time_limit=nominal_limit,
        )
        return TimeLimitDerivationResult(
            accepted=not reasons,
            time_limit_seconds=nominal_limit,
            par_taps=par.par_taps,
            optimal_travel_time_seconds=strategy_search.optimal_cost.travel_time_seconds,
            runtime_distribution=distribution,
            distribution_reference_seconds=runtime_reference,
            planning_allowance_seconds=planning_allowance,
            input_allowance_seconds=input_allowance,
            available_planning_margin_seconds=available_planning_margin,
            star_time_thresholds_seconds=thresholds,
            rejection_reasons=tuple(reasons),
        )

    derive_time_limit = derive

    @staticmethod
    def _runtime_distribution(
        strategy_search: StrategySearchResult,
    ) -> RuntimeDistributionSummary | None:
        traces = (
            *strategy_search.equal_cost_optimal_strategies,
            *strategy_search.near_optimal_strategies,
        )
        samples = tuple(
            sorted(trace.cost.travel_time_seconds for trace in traces if trace.succeeded)
        )
        if not samples:
            return None
        return RuntimeDistributionSummary(
            samples_seconds=samples,
            median_seconds=TimeLimitDerivationService._percentile(samples, 0.50),
            upper_quartile_seconds=TimeLimitDerivationService._percentile(samples, 0.75),
            maximum_seconds=samples[-1],
        )

    @staticmethod
    def _percentile(samples: tuple[float, ...], fraction: float) -> float:
        """Return a deterministic linearly interpolated percentile."""

        if len(samples) == 1:
            return samples[0]
        index = (len(samples) - 1) * fraction
        lower_index = floor(index)
        upper_index = ceil(index)
        if lower_index == upper_index:
            return samples[lower_index]
        weight = index - lower_index
        return round(
            samples[lower_index] * (1.0 - weight) + samples[upper_index] * weight,
            9,
        )

    @staticmethod
    def _star_thresholds(
        *,
        optimal_runtime: float,
        runtime_reference: float,
        planning_allowance: float,
        input_allowance: float,
        time_limit: int,
    ) -> tuple[int, int, int]:
        fastest = min(
            time_limit,
            max(1, ceil(optimal_runtime + input_allowance + planning_allowance * 0.50)),
        )
        middle = min(
            time_limit,
            max(fastest, ceil(runtime_reference + input_allowance + planning_allowance * 0.75)),
        )
        return fastest, middle, time_limit

    @staticmethod
    def _rejected(reasons: list[str]) -> TimeLimitDerivationResult:
        return TimeLimitDerivationResult(
            accepted=False,
            time_limit_seconds=None,
            par_taps=None,
            optimal_travel_time_seconds=None,
            runtime_distribution=None,
            distribution_reference_seconds=None,
            planning_allowance_seconds=0.0,
            input_allowance_seconds=0.0,
            available_planning_margin_seconds=0.0,
            rejection_reasons=tuple(reasons or ("time_limit_derivation_evidence_missing",)),
        )
