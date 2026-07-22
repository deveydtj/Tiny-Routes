from __future__ import annotations

import json
from dataclasses import replace

import pytest

from app.models import (
    GeneratorHealthReport,
    GeneratorHealthSlice,
    GeneratorHealthThresholds,
    PortfolioDiversityMetrics,
)
from app.services import (
    GeneratorHealthAnomalyError,
    GeneratorHealthAnomalyService,
)


def _slice(
    key: str,
    *,
    attempt_count: int = 100,
    accepted_count: int = 30,
    dominant_rejections: tuple[tuple[str, int], ...] = (("composition_failed", 20),),
    dependency_depth: float = 3.0,
    static_outputs: int = 0,
) -> GeneratorHealthSlice:
    return GeneratorHealthSlice(
        key=key,
        attempt_count=attempt_count,
        completed_pipeline_count=accepted_count,
        accepted_candidate_count=accepted_count,
        completion_rate=accepted_count / attempt_count,
        candidate_yield=accepted_count / attempt_count,
        dominant_rejections=dominant_rejections,
        static_policy_rejection_rate=0.1,
        agent_performance=(("greedy_objective", 0.1),),
        mean_decision_metrics=(("dependency_depth", dependency_depth),),
        layout_repair_rate=0.2,
        runtime_robustness_rate=1.0,
        static_policy_solvable_output_count=static_outputs,
    )


def _report(
    *,
    seed: int,
    run_completed: bool = True,
    overall: GeneratorHealthSlice | None = None,
    hard: GeneratorHealthSlice | None = None,
    behavior_ratio: float = 1.0,
) -> GeneratorHealthReport:
    overall = overall or _slice("all")
    hard = hard or replace(overall, key="hard")
    diversity = PortfolioDiversityMetrics(
        selected_count=10,
        topology_ratio=1.0,
        behavior_ratio=behavior_ratio,
        archetype_ratio=0.8,
        mechanic_ratio=0.8,
        aggregate_score=(2.6 + behavior_ratio) / 4.0,
    )
    return GeneratorHealthReport(
        root_seed=seed,
        run_completed=run_completed,
        overall=overall,
        by_difficulty=(hard,),
        by_archetype=(),
        portfolio_diversity=diversity,
    )


def test_health_within_locked_absolute_and_baseline_thresholds_passes() -> None:
    baseline = _report(seed=10)
    current = _report(
        seed=11,
        overall=_slice(
            "all",
            accepted_count=25,
            dominant_rejections=(("composition_failed", 25),),
        ),
        hard=_slice("hard", accepted_count=25, dependency_depth=2.5),
        behavior_ratio=0.9,
    )

    result = GeneratorHealthAnomalyService().assess(current, baseline=baseline)

    assert result.passed
    assert result.rejection_codes == ()


def test_health_anomalies_cover_every_required_systemic_regression() -> None:
    thresholds = GeneratorHealthThresholds(
        minimum_attempt_count=10,
        maximum_dominant_rejection_share=0.60,
        maximum_dominant_rejection_share_increase=0.10,
        minimum_candidate_yield=0.10,
        maximum_candidate_yield_drop=0.10,
        maximum_decision_metric_drift=0.20,
        maximum_behavior_duplicate_rate=0.20,
        maximum_behavior_duplicate_rate_increase=0.10,
    )
    baseline = _report(seed=20)
    current_overall = _slice(
        "all",
        accepted_count=5,
        dominant_rejections=(("composition_failed", 90), ("layout_failed", 5)),
        static_outputs=1,
    )
    current = _report(
        seed=21,
        run_completed=False,
        overall=current_overall,
        hard=replace(
            current_overall,
            key="hard",
            mean_decision_metrics=(("dependency_depth", 1.0),),
        ),
        behavior_ratio=0.5,
    )

    result = GeneratorHealthAnomalyService(thresholds).assess(
        current,
        baseline=baseline,
    )

    assert not result.passed
    assert {
        "rejection_code_dominance",
        "candidate_yield_below_baseline",
        "difficulty_metric_drift",
        "behavior_duplicate_rate_rise",
        "static_policy_solvable_output",
        "full_run_completion_dropped",
    } <= set(result.rejection_codes)


def test_small_samples_skip_statistical_drift_but_never_safety_failures() -> None:
    small = _slice(
        "all",
        attempt_count=2,
        accepted_count=1,
        dominant_rejections=(("composition_failed", 1),),
        static_outputs=1,
    )
    report = _report(seed=31, overall=small, hard=replace(small, key="hard"))

    result = GeneratorHealthAnomalyService().assess(report)

    assert set(result.rejection_codes) == {"static_policy_solvable_output"}


def test_ci_gate_raises_typed_error_and_writes_reproducible_report(tmp_path) -> None:
    service = GeneratorHealthAnomalyService()
    current = _report(seed=41, run_completed=False)

    with pytest.raises(GeneratorHealthAnomalyError) as error:
        service.require_healthy(current)

    output = service.write(error.value.report, tmp_path / "health_anomalies.json")
    payload = json.loads(output.read_text())
    assert payload["passed"] is False
    assert payload["currentRootSeed"] == 41
    assert payload["anomalies"][0]["code"] == "full_run_incomplete"
