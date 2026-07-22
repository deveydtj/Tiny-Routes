from __future__ import annotations

from dataclasses import replace

import pytest

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
