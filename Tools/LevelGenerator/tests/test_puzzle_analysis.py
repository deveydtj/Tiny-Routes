from __future__ import annotations

from dataclasses import replace

import pytest

from app.models import PuzzleAnalysis, PuzzleOutcomeCount, StaticPolicySearchResult
from app.services import PolicyEvaluationConfig, PolicyEvaluationService
from test_support.policy_fixture import two_step_policy_level


def _analysis() -> PuzzleAnalysis:
    policy_report = PolicyEvaluationService().evaluate(
        two_step_policy_level(),
        config=PolicyEvaluationConfig(random_run_count=2),
    )
    return PuzzleAnalysis(
        meaningful_decisions=2,
        planning_decisions=1,
        adaptive_decisions=0,
        dependency_depth=2,
        independent_decision_ratio=0.5,
        static_policy_result=StaticPolicySearchResult((), 0, 0, True),
        agent_results=policy_report.evaluations,
        objective_phases=1,
        state_changes=1,
        revisits=0,
        successful_strategy_classes=1,
        optimal_uniqueness=True,
        recovery_failure_distribution=(
            PuzzleOutcomeCount("immediateDeadEnd", 2),
            PuzzleOutcomeCount("success", 1),
        ),
        equivalent_choices=0,
        no_op_choices=0,
        optimal_accepted_taps=policy_report.optimal_cost.accepted_taps,
        optimal_route_distance=policy_report.optimal_cost.route_distance,
        optimal_travel_time_seconds=policy_report.optimal_cost.travel_time_seconds,
        visual_complexity=0.4,
    )


def test_puzzle_analysis_retains_every_raw_gate_and_ranking_value() -> None:
    analysis = _analysis()

    assert analysis.meaningful_decision_count == 2
    assert analysis.planning_decision_count == 1
    assert analysis.adaptive_decision_count == 0
    assert analysis.objective_phase_count == 1
    assert analysis.state_change_count == 1
    assert analysis.revisit_count == 0
    assert analysis.successful_strategy_class_count == 1
    assert analysis.optimal_unique
    assert analysis.route_distance_cost == analysis.optimal_route_distance
    assert analysis.timing_cost_seconds == analysis.optimal_travel_time_seconds
    assert analysis.agent_result_for("optimal").success_rate == 1


def test_puzzle_analysis_rejects_invalid_raw_values_and_duplicate_evidence() -> None:
    analysis = _analysis()

    with pytest.raises(ValueError, match="between zero and one"):
        replace(analysis, independent_decision_ratio=1.1)
    with pytest.raises(ValueError, match="unique policy names"):
        replace(analysis, agent_results=(analysis.agent_results[0],) * 2)
    with pytest.raises(ValueError, match="codes must be unique"):
        replace(
            analysis,
            recovery_failure_distribution=(
                PuzzleOutcomeCount("deadEnd", 1),
                PuzzleOutcomeCount("deadEnd", 2),
            ),
        )
    with pytest.raises(ValueError, match="non-negative integer"):
        replace(analysis, meaningful_decisions=-1)
