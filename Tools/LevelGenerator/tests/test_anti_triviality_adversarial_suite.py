from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from tiny_routes_core.models import LevelDocument

from app.models import (
    LocalObviousnessKind,
    LocalObviousnessReport,
    PuzzleAnalysis,
    PuzzleOutcomeCount,
    StaticPolicySearchResult,
    UniqueOptimalProof,
)
from app.services import (
    DifficultyTargetResolver,
    LocalObviousnessAnalysisService,
    PolicyEvaluationConfig,
    PolicyEvaluationService,
    ProductionPuzzleGateService,
    StaticPolicySolverService,
    StrategySearchService,
    UniqueOptimalProofService,
)
from test_support.policy_fixture import two_step_policy_level


_MANIFEST = (
    Path(__file__).parent / "fixtures" / "anti_triviality" / "manifest.json"
)
_ANALYSIS_FIELDS = {
    "optimalAcceptedTaps": "optimal_accepted_taps",
    "meaningfulDecisions": "meaningful_decisions",
    "planningDecisions": "planning_decisions",
    "adaptiveDecisions": "adaptive_decisions",
    "dependencyDepth": "dependency_depth",
    "equivalentChoices": "equivalent_choices",
    "noOpChoices": "no_op_choices",
    "objectivePhases": "objective_phases",
    "stateChanges": "state_changes",
    "revisits": "revisits",
}


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


def _accepted_evidence():
    level = _two_tap_level()
    strategy = StrategySearchService().search(level)
    proof = UniqueOptimalProofService().prove(level, strategy)
    policies = PolicyEvaluationService().evaluate(
        level,
        search_result=strategy,
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
        optimal_accepted_taps=strategy.optimal_cost.accepted_taps,
        optimal_route_distance=strategy.optimal_cost.route_distance,
        optimal_travel_time_seconds=strategy.optimal_cost.travel_time_seconds,
        visual_complexity=0.4,
    )
    obviousness = LocalObviousnessAnalysisService().assess(level, strategy)
    return level, analysis, proof, obviousness


def _all_obvious(report: LocalObviousnessReport) -> LocalObviousnessReport:
    decisions = tuple(
        replace(
            decision,
            matched_rules=(LocalObviousnessKind.EUCLIDEAN_OBJECTIVE_CLOSENESS,),
        )
        for decision in report.decisions
    )
    return LocalObviousnessReport(
        level_id=report.level_id,
        decisions=decisions,
        successful_fixed_direction_rules=(),
        strategy_proof_exhaustive=True,
        accepted=False,
        rejection_reasons=("all_optimal_decisions_locally_obvious",),
    )


def _successful_greedy(analysis: PuzzleAnalysis) -> PuzzleAnalysis:
    greedy = analysis.agent_result_for("greedy_objective")
    successful_runs = tuple(
        replace(run, succeeded=True, outcome_code="success") for run in greedy.runs
    )
    successful = replace(greedy, runs=successful_runs)
    return replace(
        analysis,
        agent_results=tuple(
            successful if item.policy_name == "greedy_objective" else item
            for item in analysis.agent_results
        ),
    )


def _non_unique(proof: UniqueOptimalProof) -> UniqueOptimalProof:
    strategy_class = proof.optimal_strategy_class
    assert strategy_class is not None
    return replace(
        proof,
        accepted=False,
        is_unique=False,
        equal_cost_strategy_classes=(strategy_class, strategy_class),
        rejection_reasons=("multiple_equal_optimal_strategy_classes",),
    )


def _fixture_cases() -> tuple[dict, ...]:
    payload = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == 1
    fixtures = tuple(payload["fixtures"])
    assert len(fixtures) == 14
    assert len({item["id"] for item in fixtures}) == len(fixtures)
    return fixtures


@pytest.mark.parametrize(
    "fixture",
    _fixture_cases(),
    ids=lambda fixture: fixture["id"],
)
def test_named_adversarial_fixture_fails_for_its_intended_hard_gate(
    fixture: dict,
) -> None:
    level, analysis, proof, obviousness = _accepted_evidence()
    analysis_changes = {
        _ANALYSIS_FIELDS[key]: value
        for key, value in fixture.get("analysis", {}).items()
    }
    if analysis_changes:
        analysis = replace(analysis, **analysis_changes)

    evidence = fixture.get("evidence", {})
    if evidence.get("staticPolicy") == "solvable":
        analysis = replace(
            analysis,
            static_policy_result=StaticPolicySolverService().solve(level),
        )
    if evidence.get("greedySuccessRate") == 1.0:
        analysis = _successful_greedy(analysis)
    if evidence.get("localObviousness") == "all_obvious":
        obviousness = _all_obvious(obviousness)
    if evidence.get("uniqueOptimal") == "multiple_equal_classes":
        proof = _non_unique(proof)
        analysis = replace(analysis, optimal_uniqueness=False)

    result = ProductionPuzzleGateService().assess(
        analysis,
        DifficultyTargetResolver().resolve(fixture["difficulty"]),
        unique_optimal_proof=proof,
        local_obviousness=obviousness,
        state_change_readable=evidence.get("stateChangeReadable", True),
        runtime_solution_robust=evidence.get("runtimeSolutionRobust", True),
    )

    assert not result.accepted
    assert fixture["expectedRejectionCode"] in result.rejection_reasons
