import pytest

from app.models.decision_profile import DecisionProfile
from app.services.difficulty_service import DifficultyService
from app.services.motif_composer_service import MotifComposerService, MotifCompositionError


@pytest.mark.parametrize(
    ("motif_id", "expected_metric"),
    (
        ("road_opens_after_package", "roads_opened_after_package_count"),
        ("shortcut_closes_after_package", "roads_closed_after_package_count"),
        ("return_route_changes_after_package", "state_dependent_route_change_count"),
        ("package_state_revisited_switch", "switch_state_change_on_revisit_count"),
    ),
)
def test_package_state_motifs_have_measured_effects(motif_id, expected_metric) -> None:
    preset = DifficultyService().get_preset("hard")
    result = MotifComposerService().compose("level-stateful", preset, 41, (motif_id,))

    profile = result.decision_profile
    assert profile.package_phase_transition_count == 1
    assert profile.state_dependent_route_change_count >= 1
    assert getattr(profile, expected_metric) >= 1
    assert profile.impossible_availability_condition_count == 0
    assert profile.irrelevant_availability_condition_count == 0
    assert "package_state_transition" in result.recipe.mechanic_metadata["detectedMechanics"]


def test_composition_rejects_multiple_embedded_package_motifs() -> None:
    preset = DifficultyService().get_preset("hard")
    with pytest.raises(MotifCompositionError, match="multiple_embedded_package_motifs"):
        MotifComposerService().compose(
            "level-stateful",
            preset,
            41,
            ("road_opens_after_package", "shortcut_closes_after_package"),
        )


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


def test_medium_rejects_an_independent_binary_switch_chain() -> None:
    preset = DifficultyService().get_preset("medium")
    with pytest.raises(MotifCompositionError, match="dead_end_punishment_cap_exceeded"):
        MotifComposerService().compose(
            "level-a", preset, 1, ("single_binary_choice", "single_binary_choice")
        )


def test_medium_composition_has_measured_dependency_and_descriptive_metadata() -> None:
    preset = DifficultyService().get_preset("medium")
    result = MotifComposerService().compose(
        "level-a", preset, 14, ("split_and_rejoin", "package_branch")
    )
    assert result.decision_profile.ordered_dependency_count >= 1
    assert result.decision_profile.independent_decision_ratio <= preset.maximum_independent_decision_ratio
    assert result.recipe.mechanic_tags == ("split_and_rejoin", "package_branch")
    assert "ordered_dependency" in result.recipe.mechanic_metadata["detectedMechanics"]
    assert result.recipe.mechanic_metadata["mechanicDiscrepancies"] == []


def test_lost_required_motif_effect_is_reported_and_rejected() -> None:
    class EmptyDecisionProfiler:
        def analyze(self, recipe, solutions):
            return DecisionProfile(required_decision_count=2, independent_decision_ratio=1.0)

    preset = DifficultyService().get_preset("medium")
    with pytest.raises(MotifCompositionError, match="required_motif_effect_lost"):
        MotifComposerService(decision_profiler=EmptyDecisionProfiler()).compose(
            "level-a", preset, 2, ("split_and_rejoin", "package_branch")
        )
