from __future__ import annotations

import json
from dataclasses import replace

import pytest

from app.models import (
    BlueprintStageResult,
    StaticPolicySearchResult,
    StrategyStageResult,
)
from app.services import (
    AlternateSuccessClassificationService,
    FailureRecoveryClassificationService,
    LocalObviousnessAnalysisService,
    PlanningHorizonClassificationService,
    PolicyEvaluationService,
    PuzzleBlueprintService,
    SearchLimitRejectionService,
    StaticPolicySolverService,
    StrategySearchService,
    UniqueOptimalProofService,
)
from test_support.policy_fixture import two_step_policy_level


def test_blueprint_stage_accepts_only_valid_target_matched_intent() -> None:
    blueprint = PuzzleBlueprintService().build_return_to_hub("medium", 95)

    result = BlueprintStageResult.accepted(
        candidate_id="level_095:95",
        level_id="level_095",
        seed=95,
        difficulty="medium",
        attempt_index=2,
        experience_target=blueprint.experience_target,
        blueprint=blueprint,
    )

    assert result.passed
    assert result["stage"] == "blueprint"
    assert result.validation_issues == ()
    assert result.to_report_dict()["blueprintID"] == blueprint.id
    assert result.to_report_dict()["dependencyDepth"] == (
        blueprint.decision_graph.dependency_depth
    )
    json.dumps(result.to_report_dict(), sort_keys=True)


def test_blueprint_stage_retains_rejected_intent_and_exact_validation_codes() -> None:
    blueprint = PuzzleBlueprintService().build_return_to_hub("medium", 96)
    invalid = replace(blueprint, id="")

    result = BlueprintStageResult.rejected(
        candidate_id="level_096:96",
        level_id="level_096",
        seed=96,
        difficulty="medium",
        attempt_index=0,
        experience_target=invalid.experience_target,
        blueprint=invalid,
    )

    assert not result.passed
    assert result.blueprint is invalid
    assert result.code == "blueprint_id_empty"
    assert result.validation_issues == invalid.validate()

    with pytest.raises(ValueError, match="passed must match blueprint validation"):
        BlueprintStageResult(
            passed=True,
            code="blueprint_accepted",
            candidate_id="level_096:96",
            level_id="level_096",
            seed=96,
            difficulty="medium",
            status="accepted",
            experience_target=invalid.experience_target,
            blueprint=invalid,
            validation_issues=invalid.validate(),
        )


def _strategy_evidence():
    level = two_step_policy_level()
    search = StrategySearchService().search(level)
    proof = UniqueOptimalProofService().prove(level, search)
    actual_static = StaticPolicySolverService().solve(level)
    policy = PolicyEvaluationService().evaluate(level, search_result=search)
    alternates = AlternateSuccessClassificationService().classify(level, search)
    failure_recovery = FailureRecoveryClassificationService().classify(level, search)
    planning_horizon = PlanningHorizonClassificationService().classify(
        level,
        search_result=search,
    )
    local_obviousness = LocalObviousnessAnalysisService().analyze(
        level,
        search_result=search,
    )
    production_static = StaticPolicySearchResult(
        successful_policies=(),
        tested_policy_count=actual_static.total_policy_count,
        total_policy_count=actual_static.total_policy_count,
        exhaustive=True,
    )
    limit_gate = SearchLimitRejectionService().assess(search, production_static)
    return (
        level,
        search,
        proof,
        actual_static,
        production_static,
        policy,
        alternates,
        failure_recovery,
        planning_horizon,
        local_obviousness,
        limit_gate,
    )


def test_strategy_stage_carries_complete_proof_evidence_to_report_boundary() -> None:
    (
        level,
        search,
        proof,
        _,
        production_static,
        policy,
        alternates,
        failure_recovery,
        planning_horizon,
        local_obviousness,
        limit_gate,
    ) = _strategy_evidence()

    result = StrategyStageResult.accepted(
        candidate_id="policy_evaluation_fixture:96",
        level_id=level.id,
        seed=96,
        difficulty="hard",
        strategy_search=search,
        unique_optimal_proof=proof,
        static_policy_search=production_static,
        policy_evaluation=policy,
        alternate_successes=alternates,
        failure_recovery=failure_recovery,
        planning_horizon=planning_horizon,
        local_obviousness=local_obviousness,
        search_limit_gate=limit_gate,
    )

    report = result.to_report_dict()
    assert result.passed
    assert result["stage"] == "strategy"
    assert report["strategySearch"]["exhaustive"] is True
    assert report["uniqueOptimalProof"]["accepted"] is True
    assert report["staticPolicySearch"]["acceptedForProduction"] is True
    assert report["planningHorizon"]["maximumHorizon"] == "twoTransitions"
    assert report["localObviousness"]["nonObviousDecisionCount"] == 1
    assert {item["name"] for item in report["policyEvaluation"]["policies"]} == {
        "random",
        "greedy_objective",
        "one_step_lookahead",
        "two_step_planning",
        "optimal",
    }
    json.dumps(report, sort_keys=True)


def test_strategy_stage_rejects_static_policy_witness_and_deduplicates_codes() -> None:
    (
        level,
        search,
        proof,
        actual_static,
        _,
        policy,
        alternates,
        failure_recovery,
        planning_horizon,
        local_obviousness,
        _,
    ) = _strategy_evidence()
    limit_gate = SearchLimitRejectionService().assess(search, actual_static)

    result = StrategyStageResult.rejected(
        candidate_id="policy_evaluation_fixture:97",
        level_id=level.id,
        seed=97,
        difficulty="hard",
        rejection_reasons=(
            "static_policy_solution_exists",
            "static_policy_solution_exists",
        ),
        strategy_search=search,
        unique_optimal_proof=proof,
        static_policy_search=actual_static,
        policy_evaluation=policy,
        alternate_successes=alternates,
        failure_recovery=failure_recovery,
        planning_horizon=planning_horizon,
        local_obviousness=local_obviousness,
        search_limit_gate=limit_gate,
    )

    assert not result.passed
    assert result.code == "static_policy_solution_exists"
    assert result.rejection_reasons == ("static_policy_solution_exists",)
    assert result.to_report_dict()["staticPolicySearch"]["successfulPolicyCount"] > 0

    with pytest.raises(ValueError, match="complete proof evidence"):
        StrategyStageResult.accepted(
            candidate_id="policy_evaluation_fixture:97",
            level_id=level.id,
            seed=97,
            difficulty="hard",
            strategy_search=search,
            unique_optimal_proof=proof,
            static_policy_search=actual_static,
            policy_evaluation=policy,
            alternate_successes=alternates,
            failure_recovery=failure_recovery,
            planning_horizon=planning_horizon,
            local_obviousness=local_obviousness,
            search_limit_gate=limit_gate,
        )
