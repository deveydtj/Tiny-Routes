from __future__ import annotations

from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.templates.single_switch_template import SingleSwitchTemplate


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
