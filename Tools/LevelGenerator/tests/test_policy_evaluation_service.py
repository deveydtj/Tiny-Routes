from __future__ import annotations

from dataclasses import replace

import pytest

from app.agents import GreedyObjectiveAgent
from app.services import (
    PolicyEvaluationConfig,
    PolicyEvaluationService,
    StrategySearchService,
)
from test_support.policy_fixture import two_step_policy_level


def test_standard_policy_report_measures_separation_costs_and_divergence() -> None:
    level = two_step_policy_level()
    report = PolicyEvaluationService().evaluate(
        level,
        config=PolicyEvaluationConfig(random_run_count=8),
    )

    greedy = report.evaluation_for("greedy_objective")
    one_step = report.evaluation_for("one_step_lookahead")
    two_step = report.evaluation_for("two_step_planning")
    optimal = report.evaluation_for("optimal")

    assert report.strategy_proof_exhaustive
    assert greedy.success_rate == 0
    assert one_step.success_rate == 0
    assert two_step.success_rate == 1
    assert optimal.success_rate == 1
    assert greedy.failure_types[0].code == "structural_dead_end"
    assert greedy.divergences[0].selected_edge_id == "tempting"
    assert greedy.divergences[0].optimal_edge_id == "planned"
    assert optimal.average_taps == report.optimal_cost.accepted_taps
    assert optimal.average_completion_time_seconds == report.optimal_cost.travel_time_seconds
    assert optimal.regret_relative_to_optimum is not None
    assert optimal.regret_relative_to_optimum.accepted_taps == 0
    assert optimal.divergences == ()


def test_custom_agent_evaluation_and_proof_requirements_are_explicit() -> None:
    level = two_step_policy_level()
    service = PolicyEvaluationService()
    proof = StrategySearchService().search(level)

    result = service.evaluate_agent(
        level,
        GreedyObjectiveAgent(level),
        policy_name="custom_greedy",
        search_result=proof,
    )

    assert result.policy_name == "custom_greedy"
    assert result.run_count == 1
    assert result.average_taps is None
    assert result.regret_relative_to_optimum is None

    with pytest.raises(ValueError, match="exhaustive"):
        service.evaluate(level, search_result=replace(proof, exhaustive=False))


def test_policy_evaluation_is_byte_stable_for_the_same_configuration() -> None:
    level = two_step_policy_level()
    config = PolicyEvaluationConfig(random_run_count=12, random_seed=314)
    service = PolicyEvaluationService()

    assert service.evaluate(level, config=config) == service.evaluate(level, config=config)
