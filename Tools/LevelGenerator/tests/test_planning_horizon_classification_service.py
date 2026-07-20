from __future__ import annotations

from dataclasses import replace

import pytest

from app.models import PlanningHorizon
from app.services import (
    PlanningHorizonClassificationService,
    StrategySearchService,
)
from test_support.policy_fixture import deep_policy_level, two_step_policy_level


def test_classifier_finds_the_minimum_horizon_for_every_optimal_decision() -> None:
    level = two_step_policy_level()

    report = PlanningHorizonClassificationService().classify(level)

    assert report.strategy_proof_exhaustive
    assert [item.optimal_edge_id for item in report.decisions] == ["planned", "finish"]
    assert report.decisions[0].horizon is PlanningHorizon.TWO_TRANSITIONS
    assert report.decisions[0].matched_policy_names == ("two_step_planning",)
    assert report.decisions[1].horizon is PlanningHorizon.IMMEDIATE_EDGE_ONLY
    assert report.maximum_horizon is PlanningHorizon.TWO_TRANSITIONS
    assert dict(report.counts) == {
        PlanningHorizon.IMMEDIATE_EDGE_ONLY: 1,
        PlanningHorizon.TWO_TRANSITIONS: 1,
    }


def test_classifier_rejects_uncertain_or_missing_strategy_proofs() -> None:
    level = two_step_policy_level()
    proof = StrategySearchService().search(level)
    service = PlanningHorizonClassificationService()

    with pytest.raises(ValueError, match="exhaustive"):
        service.classify(level, replace(proof, exhaustive=False))
    with pytest.raises(ValueError, match="successful"):
        service.classify(
            level,
            replace(
                proof,
                optimal_cost=None,
                canonical_optimal_strategy=None,
                equal_cost_optimal_strategies=(),
            ),
        )


def test_planning_horizon_report_is_deterministic() -> None:
    level = two_step_policy_level()
    service = PlanningHorizonClassificationService()

    assert service.classify(level) == service.classify(level)


def test_deep_decisions_distinguish_objective_state_from_cross_phase_knowledge() -> None:
    service = PlanningHorizonClassificationService()

    objective_state = service.classify(deep_policy_level(multi_stop=False))
    cross_phase = service.classify(deep_policy_level(multi_stop=True))

    assert objective_state.decisions[0].horizon is PlanningHorizon.OBJECTIVE_STATE_KNOWLEDGE
    assert cross_phase.decisions[0].horizon is PlanningHorizon.CROSS_PHASE_KNOWLEDGE
