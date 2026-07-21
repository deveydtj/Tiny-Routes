from __future__ import annotations

from dataclasses import replace

from app.models import (
    PuzzleAnalysis,
    PuzzleOutcomeCount,
    StaticPolicySearchResult,
    StrategyCost,
)
from app.services import (
    DifficultyService,
    DifficultyTargetResolver,
    ParTapDerivationService,
    PolicyEvaluationConfig,
    PolicyEvaluationService,
    StrategySearchService,
    TimeLimitDerivationService,
    UniqueOptimalProofService,
)
from test_support.policy_fixture import two_step_policy_level


def _proof_evidence():
    level = two_step_policy_level()
    search = StrategySearchService().search(level)
    proof = UniqueOptimalProofService().prove(level, search)
    policy_report = PolicyEvaluationService().evaluate(
        level,
        config=PolicyEvaluationConfig(random_run_count=2),
    )
    analysis = PuzzleAnalysis(
        meaningful_decisions=2,
        planning_decisions=1,
        adaptive_decisions=0,
        dependency_depth=2,
        independent_decision_ratio=0.5,
        static_policy_result=StaticPolicySearchResult((), 0, 0, True),
        agent_results=policy_report.evaluations,
        objective_phases=1,
        state_changes=0,
        revisits=0,
        successful_strategy_classes=1,
        optimal_uniqueness=True,
        recovery_failure_distribution=(PuzzleOutcomeCount("success", 1),),
        equivalent_choices=0,
        no_op_choices=0,
        optimal_accepted_taps=search.optimal_cost.accepted_taps,
        optimal_route_distance=search.optimal_cost.route_distance,
        optimal_travel_time_seconds=search.optimal_cost.travel_time_seconds,
        visual_complexity=0.4,
    )
    return search, proof, analysis


def test_par_taps_come_only_from_the_accepted_optimal_cost() -> None:
    search, proof, _ = _proof_evidence()

    result = ParTapDerivationService().derive(proof)

    assert result.accepted
    assert result.par_taps == search.optimal_cost.accepted_taps == 1
    assert result.optimal_cost == search.optimal_cost
    assert result.rejection_reasons == ()


def test_par_derivation_rejects_missing_or_non_unique_proof() -> None:
    service = ParTapDerivationService()
    _, proof, _ = _proof_evidence()

    missing = service.derive(None)
    non_unique = service.derive(
        replace(
            proof,
            accepted=False,
            is_unique=False,
            optimal_strategy_class=None,
            equal_cost_strategy_classes=(),
            rejection_reasons=("unique_optimal_multiple_strategy_classes",),
        )
    )

    assert not missing.accepted
    assert missing.rejection_reasons == ("par_optimal_proof_missing",)
    assert not non_unique.accepted
    assert "par_optimal_strategy_not_unique" in non_unique.rejection_reasons


def test_time_limit_uses_exact_runtime_distribution_and_difficulty_allowances() -> None:
    search, proof, analysis = _proof_evidence()
    preset = DifficultyService().get_preset("medium")
    target = DifficultyTargetResolver().resolve("medium")

    result = TimeLimitDerivationService().derive(
        search,
        proof,
        analysis,
        preset,
        target,
    )

    assert result.accepted
    assert result.par_taps == search.optimal_cost.accepted_taps
    assert result.runtime_distribution.samples_seconds == (
        search.optimal_cost.travel_time_seconds,
    )
    assert result.distribution_reference_seconds == search.optimal_cost.travel_time_seconds
    assert result.planning_allowance_seconds == preset.time_limit_padding_seconds
    assert result.input_allowance_seconds == (
        search.optimal_cost.accepted_taps * preset.min_tap_spacing_seconds
    )
    assert result.time_limit_seconds == 29
    assert result.available_planning_margin_seconds >= result.planning_allowance_seconds
    assert result.star_time_thresholds_seconds == (21, 25, 29)


def test_near_optimal_runtime_changes_the_distribution_reference() -> None:
    search, proof, analysis = _proof_evidence()
    canonical = search.canonical_optimal_strategy
    slower = replace(
        canonical,
        cost=StrategyCost(
            accepted_taps=canonical.cost.accepted_taps + 1,
            travel_time_seconds=canonical.cost.travel_time_seconds + 8.0,
            route_distance=canonical.cost.route_distance + 8.0,
        ),
    )
    search_with_alternate = replace(search, near_optimal_strategies=(slower,))

    result = TimeLimitDerivationService().derive(
        search_with_alternate,
        proof,
        analysis,
        DifficultyService().get_preset("medium"),
        DifficultyTargetResolver().resolve("medium"),
    )

    assert result.accepted
    assert result.runtime_distribution.sample_count == 2
    assert result.runtime_distribution.upper_quartile_seconds == (
        search.optimal_cost.travel_time_seconds + 6.0
    )
    assert result.distribution_reference_seconds == (
        search.optimal_cost.travel_time_seconds + 6.0
    )
    assert result.time_limit_seconds == 35


def test_time_limit_rejects_when_difficulty_cap_removes_safe_planning_margin() -> None:
    search, proof, analysis = _proof_evidence()
    target = replace(
        DifficultyTargetResolver().resolve("medium"),
        desired_solve_time_range=(10.0, 20.0),
    )

    result = TimeLimitDerivationService().derive(
        search,
        proof,
        analysis,
        DifficultyService().get_preset("medium"),
        target,
    )

    assert not result.accepted
    assert result.time_limit_seconds == 20
    assert result.available_planning_margin_seconds < result.planning_allowance_seconds
    assert result.rejection_reasons == ("insufficient_time_limit_planning_margin",)


def test_time_limit_rejects_incomplete_runtime_distribution() -> None:
    search, proof, analysis = _proof_evidence()

    result = TimeLimitDerivationService().derive(
        replace(search, exhaustive=False, limit_reasons=("strategy_search_incomplete",)),
        proof,
        analysis,
        DifficultyService().get_preset("medium"),
        DifficultyTargetResolver().resolve("medium"),
    )

    assert not result.accepted
    assert "time_limit_runtime_distribution_incomplete" in result.rejection_reasons
