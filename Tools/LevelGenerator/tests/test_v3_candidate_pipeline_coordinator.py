from __future__ import annotations

import json

from app.models import (
    BlueprintStageResult,
    CandidateStageResult,
    GeneratedLevel,
    GenerationQualityScore,
    ProductionPuzzleGateCheck,
    ProductionPuzzleGateResult,
    PuzzleAnalysis,
    QualityStageResult,
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
    V3CandidatePipelineCoordinator,
    V3CandidatePipelineHandlers,
    V3CandidatePipelineRequest,
)
from test_support.policy_fixture import two_step_policy_level


def _request() -> V3CandidatePipelineRequest:
    return V3CandidatePipelineRequest(
        candidate_id="policy_evaluation_fixture:101",
        level_id="policy_evaluation_fixture",
        seed=101,
        difficulty="easy",
        attempt_index=3,
    )


def _blueprint(request: V3CandidatePipelineRequest) -> BlueprintStageResult:
    blueprint = PuzzleBlueprintService().generate(request.difficulty, request.seed)
    return BlueprintStageResult.accepted(
        candidate_id=request.candidate_id,
        level_id=request.level_id,
        seed=request.seed,
        difficulty=request.difficulty,
        attempt_index=request.attempt_index,
        experience_target=blueprint.experience_target,
        blueprint=blueprint,
    )


def _stage(request: V3CandidatePipelineRequest, name: str) -> CandidateStageResult:
    return CandidateStageResult(
        passed=True,
        stage=name,
        code=f"{name}_accepted",
        candidate_id=request.candidate_id,
        level_id=request.level_id,
        seed=request.seed,
        difficulty=request.difficulty,
        status="accepted",
    )


def _strategy(request: V3CandidatePipelineRequest) -> StrategyStageResult:
    level = two_step_policy_level()
    search = StrategySearchService().search(level)
    proof = UniqueOptimalProofService().prove(level, search)
    actual_static = StaticPolicySolverService().solve(level)
    production_static = StaticPolicySearchResult(
        successful_policies=(),
        tested_policy_count=actual_static.total_policy_count,
        total_policy_count=actual_static.total_policy_count,
        exhaustive=True,
    )
    policy = PolicyEvaluationService().evaluate(level, search_result=search)
    alternates = AlternateSuccessClassificationService().classify(level, search)
    recovery = FailureRecoveryClassificationService().classify(level, search)
    planning = PlanningHorizonClassificationService().classify(
        level, search_result=search
    )
    obviousness = LocalObviousnessAnalysisService().analyze(
        level, search_result=search
    )
    limits = SearchLimitRejectionService().assess(search, production_static)
    return StrategyStageResult.accepted(
        candidate_id=request.candidate_id,
        level_id=request.level_id,
        seed=request.seed,
        difficulty=request.difficulty,
        strategy_search=search,
        unique_optimal_proof=proof,
        static_policy_search=production_static,
        policy_evaluation=policy,
        alternate_successes=alternates,
        failure_recovery=recovery,
        planning_horizon=planning,
        local_obviousness=obviousness,
        search_limit_gate=limits,
    )


def _quality(request: V3CandidatePipelineRequest) -> QualityStageResult:
    level = two_step_policy_level()
    generated = GeneratedLevel(
        level_document=level,
        solution=object(),
        template_name="production_v3",
        difficulty=request.difficulty,
        seed=request.seed,
    )
    analysis = PuzzleAnalysis(
        meaningful_decisions=2,
        planning_decisions=1,
        adaptive_decisions=1,
        dependency_depth=1,
        independent_decision_ratio=0.5,
        static_policy_result=StaticPolicySearchResult((), 0, 0, True),
        agent_results=(),
        objective_phases=2,
        state_changes=1,
        revisits=0,
        successful_strategy_classes=1,
        optimal_uniqueness=True,
        recovery_failure_distribution=(),
        equivalent_choices=0,
        no_op_choices=0,
        optimal_accepted_taps=2,
        optimal_route_distance=4,
        optimal_travel_time_seconds=4,
        visual_complexity=0.4,
    )
    gate = ProductionPuzzleGateResult(
        (ProductionPuzzleGateCheck("all_final_gates", True, "true", "true"),),
        (),
    )
    score = GenerationQualityScore(
        total_score=82,
        category_scores={"logic": 90},
        total=0.82,
        readability=0.8,
        uniqueness=0.8,
        difficulty_fit=0.8,
        route_interest=0.8,
    )
    return QualityStageResult.accepted(
        candidate_id=request.candidate_id,
        level_id=request.level_id,
        seed=request.seed,
        difficulty=request.difficulty,
        generated_level=generated,
        puzzle_analysis=analysis,
        hard_gate=gate,
        quality_score=score,
    )


def test_coordinator_runs_the_locked_candidate_order_and_returns_the_candidate() -> None:
    request = _request()
    calls: list[str] = []

    def blueprint(value):
        calls.append("blueprint")
        return _blueprint(value)

    def composition(value, _blueprint_result):
        calls.append("composition")
        return _stage(value, "composition")

    def strategy(value, _composition_result):
        calls.append("strategy")
        return _strategy(value)

    def layout(value, _composition_result, _strategy_result):
        calls.append("layout")
        return _stage(value, "layout")

    def runtime(value, _layout_result, _strategy_result):
        calls.append("runtime")
        return _stage(value, "runtime")

    def quality(value, *_evidence):
        calls.append("quality")
        return _quality(value)

    result = V3CandidatePipelineCoordinator(
        V3CandidatePipelineHandlers(
            blueprint=blueprint,
            composition=composition,
            strategy=strategy,
            layout=layout,
            runtime=runtime,
            quality=quality,
        )
    ).run(request)

    assert calls == [
        "blueprint",
        "composition",
        "strategy",
        "layout",
        "runtime",
        "quality",
    ]
    assert result.passed
    assert result.candidate is not None
    assert result.terminal_stage == "quality"
    json.dumps(result.to_report_dict(), sort_keys=True)


def test_strategy_rejection_prevents_layout_and_runtime_work() -> None:
    request = _request()
    calls: list[str] = []

    def rejected_strategy(value, _composition_result):
        calls.append("strategy")
        return StrategyStageResult.rejected(
            candidate_id=value.candidate_id,
            level_id=value.level_id,
            seed=value.seed,
            difficulty=value.difficulty,
            rejection_reasons=("static_policy_solution_exists",),
        )

    def forbidden(*_args):
        raise AssertionError("expensive downstream stage must not run")

    result = V3CandidatePipelineCoordinator(
        V3CandidatePipelineHandlers(
            blueprint=lambda value: (calls.append("blueprint"), _blueprint(value))[1],
            composition=lambda value, _prior: (
                calls.append("composition"),
                _stage(value, "composition"),
            )[1],
            strategy=rejected_strategy,
            layout=forbidden,
            runtime=forbidden,
            quality=forbidden,
        )
    ).run(request)

    assert calls == ["blueprint", "composition", "strategy"]
    assert not result.passed
    assert result.terminal_stage == "strategy"
    assert result.code == "static_policy_solution_exists"
    assert [stage.stage for stage in result.stage_results] == [
        "blueprint",
        "composition",
        "strategy",
    ]


def test_stage_exception_becomes_a_stable_fail_closed_result() -> None:
    request = _request()

    def broken_composition(_request, _blueprint_result):
        raise RuntimeError("composition fixture exploded")

    result = V3CandidatePipelineCoordinator(
        V3CandidatePipelineHandlers(
            blueprint=_blueprint,
            composition=broken_composition,
            strategy=lambda *_args: _strategy(request),
            layout=lambda *_args: _stage(request, "layout"),
            runtime=lambda *_args: _stage(request, "runtime"),
            quality=lambda *_args: _quality(request),
        )
    ).run(request)

    assert not result.passed
    assert result.terminal_stage == "composition"
    assert result.code == "composition_stage_error"
    assert result.stage_results[-1].report_fields["exceptionType"] == "RuntimeError"
