from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from app.models.runtime_solution_search import RuntimeDecisionTimingDiagnostic
from app.services.difficulty_target_resolver import DifficultyTargetResolver
from app.services.runtime_solution_search_service import RuntimeSolutionSearchService
from app.services.runtime_timing_accessibility_service import (
    RuntimeTimingAccessibilityService,
)
from app.services.strategy_search_service import StrategySearchService


def _diagnostic(rotation_count: int) -> RuntimeDecisionTimingDiagnostic:
    tap_times = tuple(1.5 + index * 0.25 for index in range(rotation_count))
    return RuntimeDecisionTimingDiagnostic(
        node_id="hub",
        visit_index=1,
        rotation_count=rotation_count,
        window_open_seconds=1.0,
        window_close_seconds=3.0,
        chosen_tap_seconds=tap_times,
        safety_margin_seconds=0.12,
    )


def _stateful_level(*, return_distance: float) -> LevelDocument:
    checkpoint_x = 2.0 + return_distance
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "state_visibility_fixture",
            "name": "State Visibility Fixture",
            "startNodeID": "start",
            "packageNodeID": "checkpoint",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 30,
            "parTaps": 1,
            "rules": {
                "switchInteractionMode": "liveLookahead",
                "switchLookaheadSeconds": 1.35,
                "switchTapCooldownSeconds": 0.12,
            },
            "objectives": [
                {
                    "id": "inspect",
                    "nodeID": "checkpoint",
                    "kind": "checkpoint",
                    "sequenceIndex": 0,
                    "revealPolicy": "always",
                },
                {
                    "id": "finish",
                    "nodeID": "destination",
                    "kind": "destination",
                    "sequenceIndex": 1,
                    "revealPolicy": "whenActive",
                },
            ],
            "graph": {
                "nodes": [
                    {"id": "start", "x": 0, "y": 0, "outgoingEdgeIDs": ["to_hub"]},
                    {
                        "id": "hub",
                        "x": 2,
                        "y": 0,
                        "outgoingEdgeIDs": ["to_checkpoint", "to_dead", "to_destination"],
                    },
                    {"id": "dead", "x": 2, "y": -1, "outgoingEdgeIDs": []},
                    {
                        "id": "checkpoint",
                        "x": checkpoint_x,
                        "y": 0,
                        "outgoingEdgeIDs": ["return_hub"],
                    },
                    {"id": "destination", "x": 4, "y": 0, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "to_hub", "fromNodeID": "start", "toNodeID": "hub"},
                    {"id": "to_dead", "fromNodeID": "hub", "toNodeID": "dead"},
                    {
                        "id": "to_checkpoint",
                        "fromNodeID": "hub",
                        "toNodeID": "checkpoint",
                        "availabilityRule": {"maximumObjectiveIndex": 0, "usageLimit": 1},
                    },
                    {
                        "id": "to_destination",
                        "fromNodeID": "hub",
                        "toNodeID": "destination",
                        "availabilityRule": {
                            "requiredCompletedObjectiveIDs": ["inspect"],
                            "minimumObjectiveIndex": 1,
                        },
                    },
                    {"id": "return_hub", "fromNodeID": "checkpoint", "toNodeID": "hub"},
                ],
            },
        }
    )


def test_easy_rejects_any_rapid_multi_tap_encounter_while_medium_allows_one() -> None:
    service = RuntimeTimingAccessibilityService()
    resolver = DifficultyTargetResolver()
    level = _stateful_level(return_distance=3.0)

    easy = service.evaluate(level, (_diagnostic(2),), None, resolver.resolve("easy"))
    medium = service.evaluate(level, (_diagnostic(2),), None, resolver.resolve("medium"))

    assert not easy.passed
    assert easy.failure_reason == "required_tap_burst_exceeds_target"
    assert easy.rapid_multi_tap_encounters[0].preserves_safety_margin
    assert medium.passed


def test_three_tap_burst_is_rejected_even_when_encounter_count_is_below_cap() -> None:
    report = RuntimeTimingAccessibilityService().evaluate(
        _stateful_level(return_distance=3.0),
        (_diagnostic(3),),
        None,
        DifficultyTargetResolver().resolve("expert"),
    )

    assert not report.passed
    assert report.failure_reason == "required_tap_burst_exceeds_target"
    assert not report.rapid_multi_tap_encounters[0].within_per_encounter_limit


def test_runtime_search_rejects_state_change_that_occurs_too_near_next_window() -> None:
    level = _stateful_level(return_distance=1.4)
    strategy = StrategySearchService().search(level).canonical_optimal_strategy

    result = RuntimeSolutionSearchService().search(
        level,
        strategy,
        experience_target=DifficultyTargetResolver().resolve("easy"),
    )

    assert not result.passed
    assert result.failure_reason == "state_change_not_visible_before_decision"
    report = result.timing_accessibility_report
    assert report is not None
    objective_change = next(
        item for item in report.state_change_visibility if item.completed_objective_ids
    )
    assert objective_change.completed_objective_ids == ("inspect",)
    assert objective_change.opened_edge_ids == ("to_destination",)
    assert objective_change.closed_edge_ids == ("to_checkpoint",)
    assert objective_change.visibility_seconds < 1.0


def test_runtime_search_accepts_state_change_with_full_readability_lead_time() -> None:
    level = _stateful_level(return_distance=3.0)
    strategy = StrategySearchService().search(level).canonical_optimal_strategy

    result = RuntimeSolutionSearchService().search(
        level,
        strategy,
        experience_target=DifficultyTargetResolver().resolve("easy"),
    )

    assert result.passed
    report = result.timing_accessibility_report
    assert report is not None and report.passed
    objective_change = next(
        item for item in report.state_change_visibility if item.completed_objective_ids
    )
    assert objective_change.visibility_seconds >= 1.0
    assert objective_change.active_objective_id == "finish"
