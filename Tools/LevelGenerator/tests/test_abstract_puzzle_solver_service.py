from __future__ import annotations

import pytest

from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.random_source import RandomSource
from app.recipes import RecipeFamilyRegistry
from app.services.abstract_puzzle_solver_service import (
    AbstractPuzzleSolverError,
    AbstractPuzzleSolverService,
)
from app.services.difficulty_service import DifficultyService
from app.services.topology_solver_service import TopologySolverService


def _preset(name: str):
    return DifficultyService().get_preset(name)


def _solve_family(difficulty: str, family_name: str, seed: int = 1):
    preset = _preset(difficulty)
    family = RecipeFamilyRegistry().get_family(family_name)
    recipe = family.generate_recipe("level_012", preset, RandomSource(seed))
    return AbstractPuzzleSolverService().solve(recipe, preset)


def test_abstract_solver_solves_no_switch_tutorial_route() -> None:
    solved = _solve_family("tutorial", "straight_delivery")

    assert solved.tap_node_ids == ()
    assert solved.solved_metadata is not None
    assert solved.solved_metadata.required_path[0] == "start"
    assert solved.solved_metadata.required_path[-1] == "destination"
    assert solved.solved_metadata.minimum_required_taps == 0
    assert solved.solved_metadata.package_before_destination is True


def test_abstract_solver_solves_single_switch_with_wrong_branch() -> None:
    solved = _solve_family("easy", "single_switch", seed=2)

    assert solved.solved_metadata is not None
    assert solved.solved_metadata.minimum_required_taps == 1
    assert solved.solved_metadata.dead_end_count == 1
    assert solved.tap_node_ids == solved.solved_metadata.solution_tap_node_ids


def test_topology_solver_exposes_decision_terms_and_legacy_aliases() -> None:
    solved = _solve_family("easy", "single_switch", seed=2)
    metadata = solved.solved_metadata
    assert metadata is not None
    assert metadata.decision_node_ids == metadata.solution_tap_node_ids
    assert metadata.minimum_required_decisions == metadata.minimum_required_taps
    assert "minimumRequiredDecisions" in metadata.to_dict()


def test_topology_search_returns_structured_limit_result() -> None:
    preset = _preset("tutorial")
    family = RecipeFamilyRegistry().get_family("straight_delivery")
    recipe = family.generate_recipe("level_001", preset, RandomSource(1))
    result = TopologySolverService().search(recipe, preset, solution_cap=0)
    assert not result.succeeded
    assert result.limit_reached
    assert result.failure_reasons == ("topology_solution_cap_reached",)


@pytest.mark.parametrize(
    ("difficulty", "family_name"),
    [
        ("easy", "package_gate"),
        ("medium", "return_loop"),
        ("hard", "ring_route"),
        ("expert", "four_way_intersection"),
    ],
)
def test_abstract_solver_covers_supported_mechanic_families(difficulty: str, family_name: str) -> None:
    solved = _solve_family(difficulty, family_name, seed=4)

    assert solved.solved_metadata is not None
    assert solved.solved_metadata.minimum_required_taps == len(solved.tap_node_ids)
    assert "package" in solved.solved_metadata.required_path
    assert solved.solved_metadata.required_path[-1] == "destination"


def test_abstract_solver_rejects_unsolvable_graph() -> None:
    recipe = GraphRecipe(
        level_id="level_099",
        difficulty="easy",
        nodes=(
            GraphRecipeNode("start", "start"),
            GraphRecipeNode("package", "package"),
            GraphRecipeNode("destination", "destination"),
        ),
        edges=(GraphRecipeEdge("start", "package"),),
        required_path=("start", "package", "destination"),
        tap_node_ids=(),
    )

    with pytest.raises(AbstractPuzzleSolverError) as error:
        AbstractPuzzleSolverService().solve(recipe, _preset("easy"))

    assert error.value.code == "abstract_recipe_invalid"
    assert "required_path_missing_edge:package:destination" in error.value.details


def test_abstract_solver_rejects_destination_before_package_when_not_tutorialized() -> None:
    recipe = GraphRecipe(
        level_id="level_099",
        difficulty="easy",
        nodes=(
            GraphRecipeNode("start", "start"),
            GraphRecipeNode("destination", "destination"),
            GraphRecipeNode("package", "package"),
        ),
        edges=(
            GraphRecipeEdge("start", "destination"),
            GraphRecipeEdge("start", "package"),
            GraphRecipeEdge("package", "destination"),
        ),
        required_path=("start", "package", "destination"),
        tap_node_ids=("start",),
    )

    with pytest.raises(AbstractPuzzleSolverError) as error:
        AbstractPuzzleSolverService().solve(recipe, _preset("easy"))

    assert error.value.code == "abstract_destination_before_package"
