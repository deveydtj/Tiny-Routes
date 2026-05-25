from __future__ import annotations

from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.templates.straight_delivery_template import StraightDeliveryTemplate


def test_straight_delivery_has_no_switches_and_default_package_before_destination() -> None:
    preset = DifficultyService().get_preset("tutorial")
    generated = StraightDeliveryTemplate().generate("level_012", 12, preset, RandomSource(1))

    assert generated.switch_count == 0
    assert generated.solution.actions == []
    path = []
    current = generated.level_document.startNodeID
    edge_by_id = {edge.id: edge for edge in generated.level_document.graph.edges}
    while current:
        path.append(current)
        node = next(node for node in generated.level_document.graph.nodes if node.id == current)
        if not node.outgoingEdgeIDs:
            break
        current = edge_by_id[node.outgoingEdgeIDs[0]].toNodeID
    assert path.index("package") < path.index("destination")
    assert not GeneratedLevelValidationService().validate(generated, preset=preset, overwrite=True).has_errors
