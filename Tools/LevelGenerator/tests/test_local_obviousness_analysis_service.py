from __future__ import annotations

from dataclasses import replace

import pytest

from app.models import LocalObviousnessKind
from app.services import LocalObviousnessAnalysisService, StrategySearchService
from test_support.policy_fixture import (
    locally_obvious_policy_level,
    two_step_policy_level,
)


def test_all_locally_obvious_optimal_decisions_are_rejected_with_evidence() -> None:
    report = LocalObviousnessAnalysisService().assess(locally_obvious_policy_level())

    assert not report.accepted
    assert report.rejection_reasons == ("all_optimal_decisions_locally_obvious",)
    assert report.all_optimal_decisions_locally_obvious
    assert report.non_obvious_decision_count == 0
    assert "east" in report.successful_fixed_direction_rules
    assert {
        LocalObviousnessKind.EUCLIDEAN_OBJECTIVE_CLOSENESS,
        LocalObviousnessKind.ONLY_NON_DEAD_END_ROAD,
        LocalObviousnessKind.FIRST_OUTGOING_EDGE,
        LocalObviousnessKind.FIXED_DIRECTION_RULE,
    }.issubset(report.decisions[0].matched_rules)
    assert LocalObviousnessKind.ONLY_NON_BACKWARD_ROAD in report.decisions[1].matched_rules


def test_one_genuinely_non_obvious_optimal_choice_passes_the_local_gate() -> None:
    report = LocalObviousnessAnalysisService().gate(two_step_policy_level())

    assert report.accepted
    assert report.rejection_reasons == ()
    assert report.non_obvious_decision_count == 1
    assert report.decisions[0].optimal_edge_id == "planned"
    assert report.decisions[0].matched_rules == ()


def test_local_obviousness_requires_complete_successful_proof_evidence() -> None:
    level = two_step_policy_level()
    proof = StrategySearchService().search(level)
    service = LocalObviousnessAnalysisService()

    with pytest.raises(ValueError, match="exhaustive"):
        service.assess(level, replace(proof, exhaustive=False))
    with pytest.raises(ValueError, match="successful"):
        service.assess(
            level,
            replace(
                proof,
                optimal_cost=None,
                canonical_optimal_strategy=None,
                equal_cost_optimal_strategies=(),
            ),
        )


def test_local_obviousness_analysis_is_deterministic() -> None:
    level = locally_obvious_policy_level()
    service = LocalObviousnessAnalysisService()

    assert service.assess(level) == service.assess(level)
