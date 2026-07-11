import pytest

from app.services.difficulty_service import DifficultyService
from app.services.motif_composer_service import MotifComposerService, MotifCompositionError


def test_same_seed_produces_same_composed_graph() -> None:
    preset = DifficultyService().get_preset("easy")
    service = MotifComposerService()
    first = service.compose("level-a", preset, 812)
    second = service.compose("level-a", preset, 812)
    assert first.motif_ids == second.motif_ids
    assert first.recipe.nodes == second.recipe.nodes
    assert first.recipe.edges == second.recipe.edges


def test_composed_ids_are_unique_and_route_visits_package_then_destination() -> None:
    preset = DifficultyService().get_preset("easy")
    result = MotifComposerService().compose(
        "level-a", preset, 4, ("single_binary_choice", "straight_segment")
    )
    ids = [node.id for node in result.recipe.nodes]
    assert len(ids) == len(set(ids))
    assert result.recipe.required_path[-2:] == ("package", "destination")
    assert result.topology_search.succeeded


def test_invalid_connector_combination_has_specific_reason() -> None:
    preset = DifficultyService().get_preset("easy")
    with pytest.raises(MotifCompositionError, match="motif_difficulty_not_allowed:four_way_hub:easy"):
        MotifComposerService().compose("level-a", preset, 1, ("four_way_hub",))


def test_unknown_motif_is_rejected_with_specific_reason() -> None:
    preset = DifficultyService().get_preset("easy")
    with pytest.raises(MotifCompositionError, match="unknown_motif_id:missing"):
        MotifComposerService().compose("level-a", preset, 1, ("missing",))
