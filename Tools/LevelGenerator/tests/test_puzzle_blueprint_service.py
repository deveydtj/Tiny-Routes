from __future__ import annotations

import pytest

from app.models import DecisionDependencyKind
from app.services import PuzzleBlueprintGeneratorService, PuzzleBlueprintService


@pytest.mark.parametrize("difficulty", ("easy", "medium", "hard", "expert"))
@pytest.mark.parametrize("seed", (0, 1, 23, 9_001))
def test_return_to_hub_blueprints_are_deterministic_and_valid(
    difficulty: str,
    seed: int,
) -> None:
    service = PuzzleBlueprintService()

    first = service.build_return_to_hub(difficulty, seed)
    second = service.build_return_to_hub(difficulty, seed)

    assert first == second
    assert first.archetype == "return_to_hub"
    assert first.validate() == ()
    assert "hub_revisit" in first.required_mechanic_categories
    assert first.required_revisit_decision_ids

    decisions = {decision.id: decision for decision in first.decision_graph.decisions}
    revisit_dependencies = tuple(
        dependency
        for dependency in first.decision_graph.dependencies
        if dependency.kind is DecisionDependencyKind.REVISIT
    )
    assert tuple(
        dependency.target_id for dependency in revisit_dependencies
    ) == first.required_revisit_decision_ids
    for dependency in revisit_dependencies:
        source = decisions[dependency.source_id]
        target = decisions[dependency.target_id]
        assert source.switch_role == target.switch_role == "central_route_hub"
        assert source.required_outgoing_edge_role != target.required_outgoing_edge_role

    first_transition = first.state_transitions[0]
    first_visit = decisions[revisit_dependencies[0].source_id]
    second_visit = decisions[revisit_dependencies[0].target_id]
    assert first_transition.closed_edge_roles == (
        first_visit.required_outgoing_edge_role,
    )
    assert first_transition.opened_edge_roles == (
        second_visit.required_outgoing_edge_role,
    )


@pytest.mark.parametrize("difficulty", ("easy", "medium", "hard", "expert"))
@pytest.mark.parametrize("seed", (0, 2, 71, 44_000))
def test_unlock_shortcut_blueprints_are_deterministic_and_valid(
    difficulty: str,
    seed: int,
) -> None:
    service = PuzzleBlueprintService()

    first = service.build_unlock_shortcut(difficulty, seed)
    second = service.build_unlock_shortcut(difficulty, seed)

    assert first == second
    assert first.archetype == "unlock_shortcut"
    assert first.validate() == ()
    assert "unlock_shortcut" in first.required_mechanic_categories
    assert first.objectives[0].id == "shortcut_key"

    unlock = first.state_transitions[0]
    assert unlock.trigger_objective_id == "shortcut_key"
    assert unlock.opened_edge_roles == ("unlocked_shortcut",)
    assert unlock.closed_edge_roles == ("long_outbound_route",)

    hub_visits = tuple(
        decision
        for decision in first.decision_graph.decisions
        if decision.switch_role == "shortcut_junction"
    )
    assert hub_visits[0].required_outgoing_edge_role == "long_outbound_route"
    assert hub_visits[1].required_outgoing_edge_role == "unlocked_shortcut"
    assert hub_visits[0].phase_index < hub_visits[1].phase_index


def test_generate_selects_only_completed_archetypes_and_supports_explicit_choice() -> None:
    service = PuzzleBlueprintService()

    assert service.generate("easy", 0).archetype == "return_to_hub"
    assert service.generate("easy", 1).archetype == "unlock_shortcut"
    assert (
        service.generate("medium", 9, archetype=" RETURN_TO_HUB ").archetype
        == "return_to_hub"
    )


def test_blueprint_service_rejects_invalid_seed_and_unfinished_archetype() -> None:
    service = PuzzleBlueprintService()

    with pytest.raises(ValueError, match="seed must be an integer"):
        service.generate("easy", True)
    with pytest.raises(ValueError, match="Unknown production V3 blueprint archetype"):
        service.generate("easy", 0, archetype="closed_return")


def test_generator_service_alias_preserves_existing_service_naming_convention() -> None:
    assert PuzzleBlueprintGeneratorService is PuzzleBlueprintService
