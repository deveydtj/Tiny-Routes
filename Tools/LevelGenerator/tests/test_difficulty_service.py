from __future__ import annotations

import pytest

from app.services.difficulty_service import DifficultyService
from app.random_source import RandomSource
from app.templates.straight_delivery_template import StraightDeliveryTemplate
from app.templates.multi_switch_chain_template import MultiSwitchChainTemplate


def test_all_difficulty_presets_are_available() -> None:
    service = DifficultyService()

    for name in ["tutorial", "easy", "medium", "hard", "expert"]:
        assert service.get_preset(name).name == name


def test_invalid_difficulty_is_rejected() -> None:
    with pytest.raises(ValueError):
        DifficultyService().get_preset("extreme")


def test_only_expert_allows_four_outgoing_edges() -> None:
    from app.level_editor_imports import LevelDocument, RouteEdgeModel, RouteGraphModel, RouteNodeModel, SolutionModel

    service = DifficultyService()
    level = LevelDocument(
        id="level_999",
        name="Four Way",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id="switch", x=0.0, y=0.0, outgoingEdgeIDs=["e0", "e1", "e2", "e3"]),
                RouteNodeModel(id="package", x=0.0, y=1.0, outgoingEdgeIDs=[]),
                RouteNodeModel(id="destination", x=1.0, y=0.0, outgoingEdgeIDs=[]),
                RouteNodeModel(id="dead", x=-1.0, y=0.0, outgoingEdgeIDs=[]),
                RouteNodeModel(id="side", x=0.0, y=-1.0, outgoingEdgeIDs=[]),
            ],
            edges=[
                RouteEdgeModel(id="e0", fromNodeID="switch", toNodeID="dead"),
                RouteEdgeModel(id="e1", fromNodeID="switch", toNodeID="package"),
                RouteEdgeModel(id="e2", fromNodeID="switch", toNodeID="destination"),
                RouteEdgeModel(id="e3", fromNodeID="switch", toNodeID="side"),
            ],
        ),
        startNodeID="switch",
        packageNodeID="package",
        destinationNodeID="destination",
        timeLimitSeconds=30,
        parTaps=2,
    )
    solution = SolutionModel(
        levelID="level_999",
        description="Test",
        expectedOutcome="completed",
        maxTaps=2,
        requiresWithinTimeLimit=True,
        actions=[],
    )

    assert "switch_too_many_outgoing_edges:switch" in service.check_candidate_matches_difficulty(
        level,
        solution,
        service.get_preset("hard"),
        allow_range_exceptions=True,
    )
    assert "switch_too_many_outgoing_edges:switch" not in service.check_candidate_matches_difficulty(
        level,
        solution,
        service.get_preset("expert"),
        allow_range_exceptions=True,
    )


def test_difficulty_metrics_keep_tutorial_levels_simple() -> None:
    service = DifficultyService()
    preset = service.get_preset("tutorial")
    generated = StraightDeliveryTemplate().generate("level_001", 1, preset, RandomSource(1))

    metrics = service.metrics_for_generated_level(generated)

    assert metrics.estimated_band == "tutorial"
    assert metrics.required_tap_count == 0
    assert metrics.switch_count == 0
    assert metrics.visual_complexity_score < 0.4
    assert "no_required_taps" in metrics.explanations


def test_hard_level_metrics_have_meaningful_complexity() -> None:
    service = DifficultyService()
    preset = service.get_preset("hard")
    generated = MultiSwitchChainTemplate().generate("level_032", 32, preset, RandomSource(6))

    metrics = service.metrics_for_generated_level(generated)

    assert metrics.required_tap_count >= 3
    assert metrics.switch_count >= 3
    assert metrics.mechanical_score >= 0.5
    assert metrics.estimated_band in {"medium", "hard", "expert"}
