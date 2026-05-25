from __future__ import annotations

from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.templates.single_switch_template import SingleSwitchTemplate


def test_single_switch_default_route_is_wrong_and_one_tap_reaches_package() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(2))
    choice = next(node for node in generated.level_document.graph.nodes if node.id == "choice")
    edges = {edge.id: edge for edge in generated.level_document.graph.edges}

    assert edges[choice.outgoingEdgeIDs[0]].toNodeID == "dead_end_a"
    assert edges[choice.outgoingEdgeIDs[1]].toNodeID == "package"
    assert generated.level_document.parTaps == 1
    assert [action.tapNodeID for action in generated.solution.actions] == ["choice"]
    assert not GeneratedLevelValidationService().validate(generated, preset=preset, overwrite=True).has_errors
