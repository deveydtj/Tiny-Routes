from __future__ import annotations

import pytest

from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.models.recipe_topology_rules import RecipeTopologyRules
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
    assert solved.solved_metadata.minimum_required_decisions == 0
    assert solved.solved_metadata.package_before_destination is True


def test_abstract_solver_solves_single_switch_with_wrong_branch() -> None:
    solved = _solve_family("easy", "single_switch", seed=2)

    assert solved.solved_metadata is not None
    assert solved.solved_metadata.minimum_required_decisions == 1
    assert solved.solved_metadata.dead_end_count == 1
    assert solved.tap_node_ids == solved.solved_metadata.decision_node_ids


def test_topology_solver_exposes_only_decision_terms() -> None:
    solved = _solve_family("easy", "single_switch", seed=2)
    metadata = solved.solved_metadata
    assert metadata is not None
    serialized = metadata.to_dict()
    assert "decisionNodeIDs" in serialized
    assert "minimumRequiredDecisions" in serialized
    assert "solutionTapNodeIDs" not in serialized
    assert "minimumRequiredTaps" not in serialized


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
    assert solved.solved_metadata.minimum_required_decisions == len(solved.tap_node_ids)
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


def test_topology_solver_filters_and_normalizes_edges_across_package_state() -> None:
    rules = RecipeTopologyRules(
        allows_cycles=False,
        allows_rejoin=False,
        allows_revisit=False,
        allows_return_path=False,
        allows_ring=False,
        allowed_cycle_count=0,
        requires_package_gate=True,
        requires_unique_solution=False,
        requires_swift_runtime_validation=True,
    )
    recipe = GraphRecipe(
        level_id="package_state_solver",
        difficulty="medium",
        nodes=tuple(
            GraphRecipeNode(node_id, role)
            for node_id, role in (
                ("start", "start"),
                ("switch", "route"),
                ("dead_before", "route"),
                ("package", "package"),
                ("post_gate", "route"),
                ("trap_before", "route"),
                ("destination", "destination"),
            )
        ),
        edges=(
            GraphRecipeEdge("start", "switch"),
            GraphRecipeEdge("switch", "dead_before", "beforePackage"),
            GraphRecipeEdge("switch", "package"),
            GraphRecipeEdge("package", "post_gate"),
            GraphRecipeEdge("post_gate", "trap_before", "beforePackage"),
            GraphRecipeEdge("post_gate", "destination", "afterPackage"),
        ),
        required_path=("start", "switch", "package", "post_gate", "destination"),
        tap_node_ids=("switch",),
        topology_rules=rules,
        mechanic_tags=("package_gate",),
        primary_mechanic_tag="package_gate",
        topology_class="package_gate",
        mechanic_metadata={"topologyRules": rules.to_metadata()},
    )

    solved = AbstractPuzzleSolverService().solve(recipe, _preset("medium"))

    assert solved.tap_node_ids == ("switch",)
    assert solved.required_path == (
        "start", "switch", "package", "post_gate", "destination",
    )
