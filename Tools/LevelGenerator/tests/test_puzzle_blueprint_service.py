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


@pytest.mark.parametrize("difficulty", ("easy", "medium", "hard", "expert"))
@pytest.mark.parametrize("seed", (0, 3, 41, 62_000))
def test_closed_return_blueprints_are_deterministic_and_close_outbound_route(
    difficulty: str,
    seed: int,
) -> None:
    service = PuzzleBlueprintService()

    first = service.build_closed_return(difficulty, seed)
    second = service.build_closed_return(difficulty, seed)

    assert first == second
    assert first.archetype == "closed_return"
    assert first.validate() == ()
    assert first.required_mechanic_categories == ("close_behind",)
    assert first.objectives[0].id == "return_pickup"

    closure = first.state_transitions[0]
    assert closure.trigger_objective_id == "return_pickup"
    assert closure.opened_edge_roles == ("alternate_return_route",)
    assert closure.closed_edge_roles == ("outbound_route",)

    junction_visits = tuple(
        decision
        for decision in first.decision_graph.decisions
        if decision.switch_role == "return_junction"
    )
    assert junction_visits[0].required_outgoing_edge_role == "outbound_route"
    assert junction_visits[1].required_outgoing_edge_role == "alternate_return_route"
    assert junction_visits[0].phase_index < junction_visits[1].phase_index


@pytest.mark.parametrize("difficulty", ("easy", "medium", "hard", "expert"))
@pytest.mark.parametrize("seed", (0, 4, 53, 73_000))
def test_ordered_checkpoint_blueprints_keep_ordered_points_visible_and_stateful(
    difficulty: str,
    seed: int,
) -> None:
    service = PuzzleBlueprintService()

    first = service.build_ordered_checkpoint(difficulty, seed)
    second = service.build_ordered_checkpoint(difficulty, seed)

    assert first == second
    assert first.archetype == "ordered_checkpoint"
    assert first.validate() == ()
    assert first.required_mechanic_categories == ("ordered_checkpoint",)
    assert all(objective.reveal_policy == "always" for objective in first.objectives)
    assert [objective.id for objective in first.objectives[:-1]] == [
        f"checkpoint_{index}"
        for index in range(1, len(first.objectives))
    ]
    assert first.objectives[-1].id == "destination"

    for transition in first.state_transitions:
        expected_completed = tuple(
            objective.id
            for objective in first.objectives[: transition.to_phase_index]
        )
        assert transition.required_completed_objective_ids == expected_completed
        assert transition.revealed_objective_ids == ()


@pytest.mark.parametrize("difficulty", ("easy", "medium", "hard", "expert"))
@pytest.mark.parametrize("seed", (0, 5, 67, 84_000))
def test_recoverable_loop_blueprints_return_wrong_choices_to_the_junction(
    difficulty: str,
    seed: int,
) -> None:
    service = PuzzleBlueprintService()

    first = service.build_recoverable_loop(difficulty, seed)
    second = service.build_recoverable_loop(difficulty, seed)

    assert first == second
    assert first.archetype == "recoverable_loop"
    assert first.validate() == ()
    assert first.required_mechanic_categories == ("recoverable_detour",)
    assert first.recoverable_mistake_target >= 1

    junction_visits = tuple(
        decision
        for decision in first.decision_graph.decisions
        if decision.switch_role == "recoverable_loop_junction"
    )
    assert junction_visits
    assert all(
        "recoverable_wrong_loop" in decision.outgoing_edge_roles
        for decision in junction_visits
    )
    assert all(
        decision.required_outgoing_edge_role != "recoverable_wrong_loop"
        for decision in junction_visits
    )
    assert first.state_transitions[0].opened_edge_roles == (
        "loop_route_after_objective",
    )
    assert first.state_transitions[0].closed_edge_roles == (
        "loop_route_before_objective",
    )


@pytest.mark.parametrize("difficulty", ("hard", "expert"))
@pytest.mark.parametrize("seed", (0, 6, 79, 95_000))
def test_competing_success_route_blueprints_require_multiple_routes_and_one_optimum(
    difficulty: str,
    seed: int,
) -> None:
    service = PuzzleBlueprintService()

    first = service.build_competing_success_routes(difficulty, seed)
    second = service.build_competing_success_routes(difficulty, seed)

    assert first == second
    assert first.archetype == "competing_success_routes"
    assert first.validate() == ()
    assert first.required_mechanic_categories == ("competing_routes",)
    assert first.successful_strategy_count_range[0] >= 2
    assert first.requires_unique_optimal_strategy is True

    route_choices = tuple(
        decision
        for decision in first.decision_graph.decisions
        if decision.switch_role == "competing_route_junction"
    )
    assert route_choices
    assert all(
        "slower_success_route" in decision.outgoing_edge_roles
        for decision in route_choices
    )
    assert all(
        decision.required_outgoing_edge_role != "slower_success_route"
        for decision in route_choices
    )


@pytest.mark.parametrize("difficulty", ("easy", "medium"))
def test_competing_success_routes_respect_difficulty_mechanic_allowlist(
    difficulty: str,
) -> None:
    service = PuzzleBlueprintService()

    with pytest.raises(ValueError, match="requires a difficulty"):
        service.build_competing_success_routes(difficulty, seed=0)


def test_generate_selects_only_completed_archetypes_and_supports_explicit_choice() -> None:
    service = PuzzleBlueprintService()

    assert service.generate("easy", 0).archetype == "return_to_hub"
    assert service.generate("easy", 1).archetype == "unlock_shortcut"
    assert service.generate("easy", 2).archetype == "closed_return"
    assert service.generate("easy", 3).archetype == "ordered_checkpoint"
    assert service.generate("easy", 4).archetype == "recoverable_loop"
    assert service.generate("hard", 5).archetype == "competing_success_routes"
    assert (
        service.generate("medium", 9, archetype=" RETURN_TO_HUB ").archetype
        == "return_to_hub"
    )


def test_blueprint_service_rejects_invalid_seed_and_unknown_archetype() -> None:
    service = PuzzleBlueprintService()

    with pytest.raises(ValueError, match="seed must be an integer"):
        service.generate("easy", True)
    with pytest.raises(ValueError, match="Unknown production V3 blueprint archetype"):
        service.generate("easy", 0, archetype="split_commitment")


def test_generator_service_alias_preserves_existing_service_naming_convention() -> None:
    assert PuzzleBlueprintGeneratorService is PuzzleBlueprintService
