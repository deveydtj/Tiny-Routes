from __future__ import annotations

from app.random_source import RandomSource
from app.level_editor_imports import LevelDocument, RouteEdgeModel, RouteGraphModel, RouteNodeModel, SolutionModel
from app.models.generated_level import GeneratedLevel
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.templates.single_switch_template import SingleSwitchTemplate
from .late_tap_chain_fixture import build_late_tap_chain_generated_level, late_tap_chain_new_times, late_tap_chain_old_times


def test_generated_level_validation_rejects_invalid_road_shape() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(8))
    generated.level_document.graph.edges[0].roadShape = "diagonal"

    result = GeneratedLevelValidationService().validate(generated, preset=preset, overwrite=True)

    assert "invalid_road_shape" in result.error_codes


def test_generated_level_validation_rejects_placeholder_solution() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(9))
    generated.solution.isPlaceholder = True

    result = GeneratedLevelValidationService().validate(generated, preset=preset, overwrite=True)

    assert "solution_marked_placeholder" in result.error_codes


def test_generated_level_validation_rejects_important_nodes_too_close() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(9))
    node_by_id = {node.id: node for node in generated.level_document.graph.nodes}
    node_by_id[generated.level_document.packageNodeID].x = node_by_id[generated.level_document.startNodeID].x
    node_by_id[generated.level_document.packageNodeID].y = node_by_id[generated.level_document.startNodeID].y + 0.01

    result = GeneratedLevelValidationService().validate(generated, preset=preset, overwrite=True)

    assert "important_nodes_too_close" in result.error_codes


def test_generated_level_validation_rejects_five_way_switch_for_all_presets() -> None:
    generated = _generated_switch_with_outgoing_count(5)
    service = GeneratedLevelValidationService()

    for difficulty in ["tutorial", "easy", "medium", "hard", "expert"]:
        result = service.validate(
            generated,
            preset=DifficultyService().get_preset(difficulty),
            overwrite=True,
            enforce_difficulty=False,
        )

        assert "switch_has_too_many_outgoing_edges" in result.error_codes


def test_generated_level_validation_rejects_tap_that_is_not_before_switch_arrival_buffer() -> None:
    preset = DifficultyService().get_preset("hard")

    result = GeneratedLevelValidationService().validate(
        build_late_tap_chain_generated_level(late_tap_chain_old_times()),
        preset=preset,
        overwrite=True,
    )

    assert "solution_tap_not_before_switch_arrival" in result.error_codes


def test_generated_level_validation_accepts_regenerated_earlier_tap_times() -> None:
    preset = DifficultyService().get_preset("hard")

    result = GeneratedLevelValidationService().validate(
        build_late_tap_chain_generated_level(late_tap_chain_new_times()),
        preset=preset,
        overwrite=True,
    )

    assert "solution_tap_not_before_switch_arrival" not in result.error_codes


def _generated_switch_with_outgoing_count(outgoing_count: int) -> GeneratedLevel:
    level = LevelDocument(
        id="level_999",
        name="Switch Count",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(
                    id="switch",
                    x=0.0,
                    y=0.0,
                    outgoingEdgeIDs=[f"e{index}" for index in range(outgoing_count)],
                ),
                *[
                    RouteNodeModel(id=f"target_{index}", x=float(index + 1), y=0.0, outgoingEdgeIDs=[])
                    for index in range(outgoing_count)
                ],
            ],
            edges=[
                RouteEdgeModel(id=f"e{index}", fromNodeID="switch", toNodeID=f"target_{index}")
                for index in range(outgoing_count)
            ],
        ),
        startNodeID="switch",
        packageNodeID="target_0",
        destinationNodeID="target_1",
        timeLimitSeconds=30,
        parTaps=0,
    )
    return GeneratedLevel(
        level_document=level,
        solution=SolutionModel(
            levelID=level.id,
            description="No-op",
            expectedOutcome="completed",
            maxTaps=0,
            requiresWithinTimeLimit=True,
            actions=[],
        ),
        template_name="test",
        difficulty="test",
        seed=1,
    )
