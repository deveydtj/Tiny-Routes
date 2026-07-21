from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.models.layout_constraints import BoundingBox
from app.models.layout_graph import LayoutGraph
from app.models.recipe_topology_rules import RecipeTopologyRules
from app.services.pre_post_state_layout_validation_service import (
    PrePostStateLayoutValidationService,
)


def test_snapshots_model_initial_and_every_post_objective_state() -> None:
    graph = LayoutGraph.from_recipe(_stateful_recipe())
    snapshots = PrePostStateLayoutValidationService().snapshots_for(graph)
    edge_ids = {
        (edge.from_node_id, edge.to_node_id): edge.edge_id
        for edge in graph.edges
    }

    assert len(snapshots) == 3
    assert snapshots[0].active_objective_id == "package"
    assert snapshots[0].visible_objective_ids == ("package", "destination")
    assert edge_ids[("hub", "destination")] in snapshots[0].locked_edge_ids
    assert snapshots[1].completed_objective_ids == ("package",)
    assert snapshots[1].active_objective_id == "destination"
    assert edge_ids[("hub", "destination")] in snapshots[1].available_edge_ids
    assert edge_ids[("hub", "package")] in snapshots[1].locked_edge_ids
    assert snapshots[2].completed_objective_ids == ("package", "destination")
    assert snapshots[2].active_objective_id is None


def test_post_objective_crossing_rejects_layout_that_passes_initial_state() -> None:
    graph = LayoutGraph.from_recipe(_stateful_recipe())
    positions = {
        "start": (-1.0, -0.8),
        "hub": (-0.6, 0.0),
        "package": (0.0, 0.6),
        "return": (-0.6, 0.6),
        "destination": (0.6, 0.0),
        "dead": (0.0, -0.6),
    }

    result = PrePostStateLayoutValidationService().validate(
        graph,
        positions,
        bounds=BoundingBox(-1.2, 1.2, -1.2, 1.2),
    )
    codes_by_state = [
        {issue.code for issue in state.violations}
        for state in result.states
    ]

    assert "layout_state_route_crossing_failure" not in codes_by_state[0]
    assert "layout_state_route_crossing_failure" in codes_by_state[1]
    assert not result.is_valid


def test_all_pre_and_post_states_pass_for_readable_layout() -> None:
    graph = LayoutGraph.from_recipe(_stateful_recipe())
    positions = {
        "start": (-1.0, -0.8),
        "hub": (-0.6, 0.0),
        "package": (0.0, 0.6),
        "return": (-0.6, 0.6),
        "destination": (0.65, -0.45),
        "dead": (0.65, 0.65),
    }

    result = PrePostStateLayoutValidationService().validate(
        graph,
        positions,
        bounds=BoundingBox(-1.2, 1.2, -1.2, 1.2),
    )

    assert result.is_valid, result.violations
    assert all(state.is_valid for state in result.states)


def _stateful_recipe() -> GraphRecipe:
    return GraphRecipe(
        level_id="pre_post_layout_fixture",
        difficulty="hard",
        nodes=(
            GraphRecipeNode("start", "start"),
            GraphRecipeNode("hub", "switch"),
            GraphRecipeNode("package", "package"),
            GraphRecipeNode("return", "route"),
            GraphRecipeNode("destination", "destination"),
            GraphRecipeNode("dead", "route"),
        ),
        edges=(
            GraphRecipeEdge("start", "hub"),
            GraphRecipeEdge("hub", "package", "beforePackage"),
            GraphRecipeEdge("package", "return"),
            GraphRecipeEdge("return", "hub"),
            GraphRecipeEdge("hub", "destination", "afterPackage"),
            GraphRecipeEdge("package", "dead"),
        ),
        required_path=(
            "start", "hub", "package", "return", "hub", "destination"
        ),
        tap_node_ids=("hub", "hub"),
        topology_rules=RecipeTopologyRules(
            allows_cycles=True,
            allowed_cycle_count=1,
            allows_return_path=True,
            allows_rejoin=False,
            allows_revisit=True,
            allows_ring=False,
            requires_package_gate=True,
            requires_unique_solution=True,
            requires_swift_runtime_validation=False,
        ),
    )
