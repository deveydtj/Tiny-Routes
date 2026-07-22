from __future__ import annotations

import json
from types import SimpleNamespace

from app.services.generator_health_metrics_service import GeneratorHealthMetricsService


def _accepted_diagnostic() -> dict:
    return {
        "candidateID": "candidate-1",
        "levelID": "level_031",
        "difficulty": "hard",
        "seed": 101,
        "attemptIndex": 0,
        "passed": True,
        "terminalStage": "quality",
        "code": "quality_accepted",
        "stages": [
            {
                "stage": "blueprint",
                "blueprint": {"archetype": "return_to_hub"},
            },
            {
                "stage": "strategy",
                "policy_evaluation": {
                    "evaluations": [
                        {
                            "policy_name": "greedy_objective",
                            "runs": [
                                {"succeeded": True},
                                {"succeeded": False},
                            ],
                        }
                    ]
                },
            },
            {"stage": "layout", "passed": True, "metrics": {"repairCount": 2}},
            {"stage": "runtime", "passed": True, "metrics": {"jitterPassed": True}},
            {
                "stage": "quality",
                "puzzle_analysis": {
                    "meaningful_decisions": 4,
                    "planning_decisions": 2,
                    "adaptive_decisions": 1,
                    "dependency_depth": 3,
                    "objective_phases": 3,
                    "state_changes": 2,
                    "revisits": 1,
                    "successful_strategy_classes": 2,
                },
            },
        ],
    }


def _rejected_diagnostic() -> dict:
    return {
        "candidateID": "candidate-2",
        "levelID": "level_031",
        "difficulty": "hard",
        "seed": 202,
        "attemptIndex": 1,
        "passed": False,
        "terminalStage": "strategy",
        "code": "static_policy_solution_exists",
        "stages": [
            {
                "stage": "blueprint",
                "blueprint": {"archetype": "return_to_hub"},
            },
            {"stage": "strategy", "passed": False},
        ],
    }


def _candidate(topology: str, behavior: str, archetype: str, mechanic: str):
    signature = SimpleNamespace(
        topology_hash=topology,
        structural_behavior_signature=behavior,
        blueprint_archetype=archetype,
        mechanic_tags=(mechanic,),
    )
    return SimpleNamespace(candidate_signature=signature)


def test_health_report_aggregates_required_difficulty_and_archetype_metrics(tmp_path) -> None:
    pool = SimpleNamespace(
        attempt_diagnostics=(_accepted_diagnostic(), _rejected_diagnostic())
    )
    service = GeneratorHealthMetricsService()

    report = service.build(
        pool,
        root_seed=9001,
        selected_candidates=(
            _candidate("topology-a", "behavior-a", "return_to_hub", "revisit"),
            _candidate("topology-b", "behavior-b", "return_to_hub", "unlock"),
        ),
        run_completed=True,
    )

    assert report.overall.completion_rate == 0.5
    assert report.overall.candidate_yield == 0.5
    assert report.overall.static_policy_rejection_rate == 0.5
    assert report.overall.dominant_rejections == (("static_policy_solution_exists", 1),)
    assert dict(report.overall.agent_performance)["greedy_objective"] == 0.5
    assert dict(report.overall.mean_decision_metrics)["dependency_depth"] == 3.0
    assert report.overall.layout_repair_rate == 1.0
    assert report.overall.runtime_robustness_rate == 1.0
    assert report.overall.static_policy_solvable_output_count == 0
    assert tuple(item.key for item in report.by_difficulty) == ("hard",)
    assert tuple(item.key for item in report.by_archetype) == ("return_to_hub",)
    assert report.portfolio_diversity.topology_ratio == 1.0
    assert report.portfolio_diversity.behavior_ratio == 1.0
    assert report.portfolio_diversity.archetype_ratio == 0.5
    assert report.portfolio_diversity.mechanic_ratio == 1.0

    output = service.write(report, tmp_path / "health.json")
    payload = json.loads(output.read_text())
    assert payload["rootSeed"] == 9001
    assert payload["byDifficulty"][0]["candidateYield"] == 0.5
    assert payload["portfolioDiversity"]["aggregateScore"] == 0.875


def test_health_report_counts_any_accepted_static_policy_witness() -> None:
    diagnostic = _accepted_diagnostic()
    diagnostic["stages"][1]["staticPolicySearch"] = {
        "successfulPolicyCount": 1,
        "acceptedForProduction": False,
    }

    report = GeneratorHealthMetricsService().build(
        SimpleNamespace(attempt_diagnostics=(diagnostic,)),
        root_seed=55,
        run_completed=True,
    )

    assert report.overall.static_policy_solvable_output_count == 1
    assert report.by_difficulty[0].static_policy_solvable_output_count == 1
