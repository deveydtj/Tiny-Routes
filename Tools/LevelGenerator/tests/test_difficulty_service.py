from __future__ import annotations

import pytest

from app.models.decision_profile import DecisionProfile
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


def test_medium_thresholds_reject_an_all_independent_decision_chain() -> None:
    service = DifficultyService()
    preset = service.get_preset("medium")
    generated = MultiSwitchChainTemplate().generate("level_020", 20, preset, RandomSource(7))
    profile = DecisionProfile(
        required_decision_count=3,
        unique_switch_count=3,
        independent_decision_ratio=1.0,
        minimum_window_seconds=1.4,
    )

    issues = service.check_candidate_matches_difficulty(
        generated.level_document,
        generated.solution,
        preset,
        allow_range_exceptions=True,
        decision_profile=profile,
    )

    assert "insufficient_strategic_decision_evidence" in issues
    assert "independent_decision_ratio_above_preset_maximum" in issues


def test_tutorial_thresholds_allow_zero_decisions_without_strategic_evidence() -> None:
    service = DifficultyService()
    preset = service.get_preset("tutorial")
    generated = StraightDeliveryTemplate().generate("level_001", 1, preset, RandomSource(1))

    issues = service.check_candidate_matches_difficulty(
        generated.level_document,
        generated.solution,
        preset,
        decision_profile=DecisionProfile(required_decision_count=0),
    )

    assert "insufficient_strategic_decision_evidence" not in issues
    assert not any(issue.startswith("decision_count_out_of_range") for issue in issues)


def test_tutorial_thresholds_allow_a_later_second_teaching_decision() -> None:
    preset = DifficultyService().get_preset("tutorial")

    assert preset.switch_count_range == (0, 2)
    assert preset.required_tap_range == (0, 2)
    assert preset.required_decision_count_range == (0, 2)
