from __future__ import annotations

from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.templates.package_gate_template import PackageGateTemplate


def test_package_gate_has_two_required_switches_and_ordered_actions() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = PackageGateTemplate().generate("level_012", 12, preset, RandomSource(3))

    assert generated.switch_count == 2
    assert generated.level_document.parTaps == 2
    switch_node_ids = {
        node.id for node in generated.level_document.graph.nodes if len(node.outgoingEdgeIDs) > 1
    }
    assert [action.tapNodeID for action in generated.solution.actions] == [
        action.tapNodeID for action in sorted(generated.solution.actions, key=lambda action: action.timeSeconds)
    ]
    assert all(action.tapNodeID in switch_node_ids for action in generated.solution.actions)
    assert [action.timeSeconds for action in generated.solution.actions] == sorted(
        action.timeSeconds for action in generated.solution.actions
    )
    assert not GeneratedLevelValidationService().validate(generated, preset=preset, overwrite=True).has_errors
