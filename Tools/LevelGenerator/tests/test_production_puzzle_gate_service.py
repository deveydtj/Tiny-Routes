from __future__ import annotations

from dataclasses import replace

import pytest
from tiny_routes_core.models import LevelDocument

from app.models import (
    PuzzleAnalysis,
    PuzzleOutcomeCount,
    StaticPolicySearchResult,
)
from app.services import (
    DifficultyTargetResolver,
    LocalObviousnessAnalysisService,
    PolicyEvaluationConfig,
    PolicyEvaluationService,
    ProductionPuzzleGateService,
    StrategySearchService,
    UniqueOptimalGateService,
    UniqueOptimalProofService,
)
from test_support.policy_fixture import two_step_policy_level


def _two_tap_level() -> LevelDocument:
    payload = two_step_policy_level().to_dict()
    payload["graph"]["nodes"][0]["outgoingEdgeIDs"] = [
        "start_decoy",
        "tempting",
        "planned",
    ]
    payload["graph"]["nodes"].append(
        {"id": "start_dead", "x": -1, "y": -1, "outgoingEdgeIDs": []}
    )
    payload["graph"]["edges"].append(
        {
            "id": "start_decoy",
            "fromNodeID": "start",
            "toNodeID": "start_dead",
        }
    )
    return LevelDocument.from_dict(payload)


def _evidence():
    level = _two_tap_level()
    search = StrategySearchService().search(level)
    proof = UniqueOptimalProofService().prove(level, search)
    policies = PolicyEvaluationService().evaluate(
        level,
        search_result=search,
        config=PolicyEvaluationConfig(random_run_count=2),
    )
    analysis = PuzzleAnalysis(
        meaningful_decisions=2,
        planning_decisions=1,
        adaptive_decisions=1,
        dependency_depth=1,
        independent_decision_ratio=0.5,
        static_policy_result=StaticPolicySearchResult((), 0, 0, True),
        agent_results=policies.evaluations,
        objective_phases=2,
        state_changes=1,
        revisits=0,
        successful_strategy_classes=1,
        optimal_uniqueness=True,
        recovery_failure_distribution=(
            PuzzleOutcomeCount("immediateDeadEnd", 1),
            PuzzleOutcomeCount("recoverableDetour", 1),
        ),
        equivalent_choices=0,
        no_op_choices=0,
        optimal_accepted_taps=search.optimal_cost.accepted_taps,
        optimal_route_distance=search.optimal_cost.route_distance,
        optimal_travel_time_seconds=search.optimal_cost.travel_time_seconds,
        visual_complexity=0.4,
    )
    obviousness = LocalObviousnessAnalysisService().assess(level, search)
    return analysis, proof, obviousness


def test_all_hard_gates_pass_before_candidate_ranking_is_allowed() -> None:
    analysis, proof, obviousness = _evidence()

    result = ProductionPuzzleGateService().assess(
        analysis,
        DifficultyTargetResolver().resolve("easy"),
        unique_optimal_proof=proof,
        local_obviousness=obviousness,
        state_change_readable=True,
        runtime_solution_robust=True,
    )

    assert result.accepted
    assert result.ranking_eligible
    assert result.rejection_reasons == ()
    assert all(check.passed for check in result.checks)


@pytest.mark.parametrize(
    ("changes", "expected_code"),
    (
        ({"optimal_accepted_taps": 1}, "production_one_tap_level"),
        ({"meaningful_decisions": 1}, "insufficient_meaningful_decisions"),
        ({"planning_decisions": 0}, "insufficient_planning_decisions"),
        ({"adaptive_decisions": 0}, "insufficient_adaptive_decisions"),
        ({"equivalent_choices": 1}, "equivalent_choice_present"),
        ({"objective_phases": 1}, "objective_sequence_trivial"),
        ({"state_changes": 0}, "state_change_without_player_consequence"),
        (
            {
                "recovery_failure_distribution": (
                    PuzzleOutcomeCount("immediateDeadEnd", 1),
                )
            },
            "all_failures_are_instant_dead_ends",
        ),
    ),
)
def test_strategic_failures_cannot_be_compensated_by_other_evidence(
    changes: dict[str, object],
    expected_code: str,
) -> None:
    analysis, proof, obviousness = _evidence()

    result = ProductionPuzzleGateService().assess(
        replace(analysis, **changes),
        DifficultyTargetResolver().resolve("easy"),
        unique_optimal_proof=proof,
        local_obviousness=obviousness,
        state_change_readable=True,
        runtime_solution_robust=True,
    )

    assert not result.ranking_eligible
    assert expected_code in result.rejection_reasons


def test_policy_layout_and_runtime_evidence_fail_closed() -> None:
    analysis, proof, _ = _evidence()
    greedy = analysis.agent_result_for("greedy_objective")
    successful_greedy = replace(
        greedy,
        runs=(replace(greedy.runs[0], succeeded=True, outcome_code="success"),),
    )
    agent_results = tuple(
        successful_greedy if item.policy_name == "greedy_objective" else item
        for item in analysis.agent_results
    )

    result = ProductionPuzzleGateService().assess(
        replace(
            analysis,
            agent_results=agent_results,
            meaningful_decisions=3,
            planning_decisions=2,
            dependency_depth=2,
            objective_phases=3,
            revisits=1,
        ),
        DifficultyTargetResolver().resolve("medium"),
        unique_optimal_proof=proof,
        local_obviousness=None,
        state_change_readable=None,
        runtime_solution_robust=False,
    )

    assert {
        "greedy_policy_too_successful",
        "all_optimal_decisions_locally_obvious",
        "unreadable_state_change",
        "runtime_solution_not_robust",
    } <= set(result.rejection_reasons)


def test_static_policy_witness_is_a_hard_rejection() -> None:
    analysis, proof, obviousness = _evidence()
    from app.services import StaticPolicySolverService

    static_result = StaticPolicySolverService().search(_two_tap_level())
    assert static_result.static_policy_solvable

    result = ProductionPuzzleGateService().assess(
        replace(analysis, static_policy_result=static_result),
        DifficultyTargetResolver().resolve("easy"),
        unique_optimal_proof=proof,
        local_obviousness=obviousness,
        state_change_readable=True,
        runtime_solution_robust=True,
    )

    assert "static_policy_solution_exists" in result.rejection_reasons


def test_unique_optimal_gate_rejects_missing_incomplete_and_stale_proofs() -> None:
    analysis, proof, _ = _evidence()
    service = UniqueOptimalGateService()

    assert service.assess(analysis, proof).accepted
    missing = service.assess(analysis, None)
    stale = service.assess(replace(analysis, optimal_accepted_taps=3), proof)
    incomplete = service.assess(
        analysis,
        replace(proof, accepted=False, exhaustive=False, rejection_reasons=("limit",)),
    )

    for result in (missing, stale, incomplete):
        assert not result.accepted
        assert result.rejection_reasons == ("unique_optimal_not_proven",)
        assert result.proof_rejection_reasons
