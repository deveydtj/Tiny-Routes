from __future__ import annotations

from dataclasses import replace

import pytest

from app.models.planning_horizon import PlanningHorizon
from app.models.static_policy import StaticPolicySearchResult, StaticPolicySolution
from app.services.production_pipeline_policy_service import (
    ProductionPipelinePolicyError,
    ProductionPipelinePolicyService,
)
from app.services.v3_candidate_pipeline_coordinator import (
    V3CandidatePipelineRequest,
    V3CandidatePipelineResult,
)
from test_support.production_v3_smoke import _SmokeCandidatePipeline


@pytest.fixture(scope="module")
def accepted_pipeline_result():
    return _SmokeCandidatePipeline().run(
        V3CandidatePipelineRequest(
            candidate_id="level_901:candidate:0000",
            level_id="level_901",
            seed=731_005,
            difficulty="easy",
        )
    )


@pytest.fixture(scope="module")
def accepted_medium_pipeline_result():
    return _SmokeCandidatePipeline().run(
        V3CandidatePipelineRequest(
            candidate_id="level_902:candidate:0000",
            level_id="level_902",
            seed=731_006,
            difficulty="medium",
        )
    )


def test_accepts_only_the_locked_unrelaxed_v3_path(accepted_pipeline_result) -> None:
    ProductionPipelinePolicyService().require((accepted_pipeline_result,))


@pytest.mark.parametrize(
    ("stage_index", "field", "value", "code"),
    [
        (0, "generatorArchitecture", "v2_legacy", "non_v3_stage_architecture"),
        (1, "fallbackUsed", True, "production_fallback_used"),
        (1, "sourceKind", "direct_motif_fixture", "weak_composition_source"),
        (3, "manualRepairRequired", True, "manual_repair_path"),
        (5, "antiTrivialityStatus", "failed", "anti_triviality_evidence_missing"),
        (5, "generationProfile", "playtest_portfolio", "non_production_quality_profile"),
        (5, "qualityThresholdsRelaxed", True, "relaxed_quality_thresholds"),
        (5, "manualApprovalRequired", True, "manual_approval_path"),
    ],
)
def test_rejects_every_weak_production_fallback(
    accepted_pipeline_result,
    stage_index: int,
    field: str,
    value,
    code: str,
) -> None:
    stages = list(accepted_pipeline_result.stage_results)
    fields = dict(stages[stage_index].report_fields)
    fields[field] = value
    stages[stage_index] = replace(stages[stage_index], report_fields=fields)
    weakened = V3CandidatePipelineResult(
        accepted_pipeline_result.request,
        tuple(stages),
    )

    with pytest.raises(ProductionPipelinePolicyError, match=code):
        ProductionPipelinePolicyService().require((weakened,))


def test_rejects_untyped_or_missing_selected_evidence() -> None:
    service = ProductionPipelinePolicyService()

    with pytest.raises(ProductionPipelinePolicyError, match="evidence_missing"):
        service.require(())
    with pytest.raises(ProductionPipelinePolicyError, match="evidence_invalid"):
        service.require((object(),))


@pytest.mark.parametrize("accepted_taps", (0, 1))
def test_rejects_stale_selected_evidence_for_zero_or_one_tap_output(
    accepted_pipeline_result,
    accepted_taps: int,
) -> None:
    stages = list(accepted_pipeline_result.stage_results)
    quality = stages[5]
    stages[5] = replace(
        quality,
        puzzle_analysis=replace(
            quality.puzzle_analysis,
            optimal_accepted_taps=accepted_taps,
        ),
    )
    stale = V3CandidatePipelineResult(
        accepted_pipeline_result.request,
        tuple(stages),
    )

    with pytest.raises(ProductionPipelinePolicyError, match="production_one_tap_level"):
        ProductionPipelinePolicyService().require((stale,))


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("meaningful_decisions", 1, "insufficient_meaningful_decisions"),
        ("adaptive_decisions", 0, "insufficient_adaptive_decisions"),
    ],
)
def test_rejects_stale_final_decision_counters(
    accepted_pipeline_result,
    field: str,
    value: int,
    code: str,
) -> None:
    stages = list(accepted_pipeline_result.stage_results)
    quality = stages[5]
    stages[5] = replace(
        quality,
        puzzle_analysis=replace(quality.puzzle_analysis, **{field: value}),
    )
    stale = V3CandidatePipelineResult(
        accepted_pipeline_result.request,
        tuple(stages),
    )

    with pytest.raises(ProductionPipelinePolicyError, match=code):
        ProductionPipelinePolicyService().require((stale,))


def test_rejects_optimal_trace_with_fewer_than_two_meaningful_decisions(
    accepted_pipeline_result,
) -> None:
    stages = list(accepted_pipeline_result.stage_results)
    strategy = stages[2]
    search = strategy.strategy_search
    trace = search.canonical_optimal_strategy
    first_meaningful_index = next(
        index
        for index, action in enumerate(trace.actions)
        if action.meaningful_decision is True
    )
    actions = list(trace.actions)
    actions[first_meaningful_index] = replace(
        actions[first_meaningful_index],
        meaningful_decision=False,
    )
    stages[2] = replace(
        strategy,
        strategy_search=replace(
            search,
            canonical_optimal_strategy=replace(trace, actions=tuple(actions)),
        ),
    )
    stale = V3CandidatePipelineResult(
        accepted_pipeline_result.request,
        tuple(stages),
    )

    with pytest.raises(
        ProductionPipelinePolicyError,
        match="insufficient_meaningful_decisions",
    ):
        ProductionPipelinePolicyService().require((stale,))


def test_rejects_meaningful_trace_action_without_consequence_evidence(
    accepted_pipeline_result,
) -> None:
    stages = list(accepted_pipeline_result.stage_results)
    strategy = stages[2]
    search = strategy.strategy_search
    trace = search.canonical_optimal_strategy
    actions = list(trace.actions)
    meaningful_index = next(
        index
        for index, action in enumerate(actions)
        if action.meaningful_decision is True
    )
    actions[meaningful_index] = replace(
        actions[meaningful_index],
        consequence_evidence=None,
    )
    stages[2] = replace(
        strategy,
        strategy_search=replace(
            search,
            canonical_optimal_strategy=replace(trace, actions=tuple(actions)),
        ),
    )
    stale = V3CandidatePipelineResult(
        accepted_pipeline_result.request,
        tuple(stages),
    )

    with pytest.raises(
        ProductionPipelinePolicyError,
        match="decision_consequence_evidence_missing",
    ):
        ProductionPipelinePolicyService().require((stale,))


def test_rejects_trace_with_an_equivalent_choice_class(
    accepted_pipeline_result,
) -> None:
    stages = list(accepted_pipeline_result.stage_results)
    strategy = stages[2]
    search = strategy.strategy_search
    trace = search.canonical_optimal_strategy
    actions = list(trace.actions)
    meaningful_index = next(
        index
        for index, action in enumerate(actions)
        if action.meaningful_decision is True
    )
    action = actions[meaningful_index]
    evidence = action.consequence_evidence
    assert evidence is not None
    actions[meaningful_index] = replace(
        action,
        consequence_evidence=replace(
            evidence,
            choice_count=evidence.choice_count + 1,
            equivalent_choice_count=1,
            equivalent_selected_edge_ids=("decorative_duplicate",),
        ),
    )
    stages[2] = replace(
        strategy,
        strategy_search=replace(
            search,
            canonical_optimal_strategy=replace(trace, actions=tuple(actions)),
        ),
    )
    stale = V3CandidatePipelineResult(
        accepted_pipeline_result.request,
        tuple(stages),
    )

    with pytest.raises(
        ProductionPipelinePolicyError,
        match="equivalent_choice_present",
    ):
        ProductionPipelinePolicyService().require((stale,))


def test_rejects_optimal_trace_without_a_decision_after_state_change(
    accepted_pipeline_result,
) -> None:
    stages = list(accepted_pipeline_result.stage_results)
    strategy = stages[2]
    search = strategy.strategy_search
    trace = search.canonical_optimal_strategy
    actions = tuple(
        replace(action, state_transition=None)
        for action in trace.actions
    )
    stages[2] = replace(
        strategy,
        strategy_search=replace(
            search,
            canonical_optimal_strategy=replace(trace, actions=actions),
        ),
    )
    stale = V3CandidatePipelineResult(
        accepted_pipeline_result.request,
        tuple(stages),
    )

    with pytest.raises(
        ProductionPipelinePolicyError,
        match="insufficient_adaptive_decisions",
    ):
        ProductionPipelinePolicyService().require((stale,))


def test_rejects_planning_horizon_that_does_not_match_the_optimal_trace(
    accepted_pipeline_result,
) -> None:
    stages = list(accepted_pipeline_result.stage_results)
    strategy = stages[2]
    report = strategy.planning_horizon
    decisions = list(report.decisions)
    decisions[0] = replace(decisions[0], optimal_edge_id="stale_edge")
    stages[2] = replace(
        strategy,
        planning_horizon=replace(report, decisions=tuple(decisions)),
    )
    stale = V3CandidatePipelineResult(
        accepted_pipeline_result.request,
        tuple(stages),
    )

    with pytest.raises(
        ProductionPipelinePolicyError,
        match="planning_horizon_evidence_mismatch",
    ):
        ProductionPipelinePolicyService().require((stale,))


def test_rejects_level_without_trace_backed_downstream_planning(
    accepted_pipeline_result,
) -> None:
    stages = list(accepted_pipeline_result.stage_results)
    strategy = stages[2]
    report = strategy.planning_horizon
    stages[2] = replace(
        strategy,
        planning_horizon=replace(
            report,
            decisions=tuple(
                replace(
                    decision,
                    horizon=PlanningHorizon.IMMEDIATE_EDGE_ONLY,
                )
                for decision in report.decisions
            ),
        ),
    )
    stale = V3CandidatePipelineResult(
        accepted_pipeline_result.request,
        tuple(stages),
    )

    with pytest.raises(
        ProductionPipelinePolicyError,
        match="insufficient_downstream_planning_decisions",
    ):
        ProductionPipelinePolicyService().require((stale,))


def test_rejects_medium_plus_without_multi_decision_or_cross_phase_reasoning(
    accepted_medium_pipeline_result,
) -> None:
    stages = list(accepted_medium_pipeline_result.stage_results)
    strategy = stages[2]
    report = strategy.planning_horizon
    trace = strategy.strategy_search.canonical_optimal_strategy
    assert trace is not None
    stages[2] = replace(
        strategy,
        planning_horizon=replace(
            report,
            decisions=tuple(
                replace(
                    decision,
                    horizon=(
                        PlanningHorizon.ONE_TRANSITION
                        if action.meaningful_decision
                        else PlanningHorizon.IMMEDIATE_EDGE_ONLY
                    ),
                )
                for action, decision in zip(trace.actions, report.decisions)
            ),
        ),
    )
    stale = V3CandidatePipelineResult(
        accepted_medium_pipeline_result.request,
        tuple(stages),
    )

    with pytest.raises(
        ProductionPipelinePolicyError,
        match="insufficient_deep_planning_horizon",
    ):
        ProductionPipelinePolicyService().require((stale,))


def test_rejects_stale_final_analysis_with_a_static_policy_witness(
    accepted_pipeline_result,
) -> None:
    stages = list(accepted_pipeline_result.stage_results)
    quality = stages[5]
    strategy = stages[2]
    static = strategy.static_policy_search
    trace = strategy.strategy_search.canonical_optimal_strategy
    stale_static = StaticPolicySearchResult(
        successful_policies=(StaticPolicySolution((), trace),),
        tested_policy_count=static.tested_policy_count,
        total_policy_count=static.total_policy_count,
        exhaustive=True,
    )
    stages[5] = replace(
        quality,
        puzzle_analysis=replace(
            quality.puzzle_analysis,
            static_policy_result=stale_static,
        ),
    )
    stale = V3CandidatePipelineResult(
        accepted_pipeline_result.request,
        tuple(stages),
    )

    with pytest.raises(
        ProductionPipelinePolicyError,
        match="static_policy_evidence_mismatch",
    ):
        ProductionPipelinePolicyService().require((stale,))


def test_rejects_medium_plus_when_final_greedy_evidence_claims_success(
    accepted_medium_pipeline_result,
) -> None:
    stages = list(accepted_medium_pipeline_result.stage_results)
    quality = stages[5]
    analysis = quality.puzzle_analysis
    greedy = analysis.agent_result_for("greedy_objective")
    successful_greedy = replace(
        greedy,
        runs=(replace(greedy.runs[0], succeeded=True, outcome_code="success"),),
    )
    stages[5] = replace(
        quality,
        puzzle_analysis=replace(
            analysis,
            agent_results=tuple(
                successful_greedy if item.policy_name == "greedy_objective" else item
                for item in analysis.agent_results
            ),
        ),
    )
    stale = V3CandidatePipelineResult(
        accepted_medium_pipeline_result.request,
        tuple(stages),
    )

    with pytest.raises(
        ProductionPipelinePolicyError,
        match="greedy_policy_(evidence_mismatch|too_successful)",
    ):
        ProductionPipelinePolicyService().require((stale,))
