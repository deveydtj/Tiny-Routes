from app.models.layout_constraints import BoundingBox
from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.models.layout_graph import LayoutGraph
from app.models.recipe_topology_rules import RecipeTopologyRules
from app.services.layout_layer_service import LayoutLayerService
from app.services.stateful_hub_spacing_service import StatefulHubSpacingService


def test_stateful_hub_reserves_larger_clearance_and_identifies_return_lane() -> None:
    graph = LayoutGraph.from_recipe(_revisited_hub_recipe())
    rule = StatefulHubSpacingService().rules_for(graph)[0]
    layers = LayoutLayerService().assign_layers(_revisited_hub_recipe())

    assert rule.hub_node_id == "hub"
    assert rule.objective_phase_indices == (0, 1)
    assert rule.return_approach_node_ids == ("return",)
    assert rule.reserved_clearance.horizontal_cells == 3
    assert rule.reserved_clearance.vertical_cells == 3
    clearances = {
        item.node_id: (item.horizontal_cells, item.vertical_cells)
        for item in layers.reserved_icon_clearances
    }
    assert clearances == {
        "hub": (3, 3),
        "package": (2, 2),
        "destination": (2, 2),
    }


def test_well_spaced_stateful_hub_passes_all_rules() -> None:
    graph = LayoutGraph.from_recipe(_revisited_hub_recipe())
    positions = {
        "start": (0.0, -0.8),
        "hub": (0.0, 0.0),
        "package": (-0.65, 0.45),
        "return": (0.0, -0.6),
        "dead": (0.7, -0.2),
        "destination": (0.65, 0.45),
    }

    assert not StatefulHubSpacingService().validate(
        graph,
        positions,
        bounds=BoundingBox(-1.2, 1.2, -1.2, 1.2),
    )


def test_cramped_stateful_hub_reports_exit_angle_return_and_camera_failures() -> None:
    graph = LayoutGraph.from_recipe(_revisited_hub_recipe())
    positions = {
        "start": (0.0, -0.8),
        "hub": (1.1, 0.0),
        "package": (1.18, 0.01),
        "return": (1.11, 0.0),
        "dead": (1.17, 0.02),
        "destination": (1.19, 0.02),
    }

    codes = {
        issue.code
        for issue in StatefulHubSpacingService().validate(
            graph,
            positions,
            bounds=BoundingBox(-1.2, 1.2, -1.2, 1.2),
        )
    }
    assert "stateful_hub_exit_clearance_failure" in codes
    assert "stateful_hub_outgoing_separation_failure" in codes
    assert "stateful_hub_return_approach_clearance_failure" in codes
    assert "stateful_hub_return_exit_overlap" in codes
    assert "stateful_hub_camera_frame_failure" in codes


def _revisited_hub_recipe() -> GraphRecipe:
    return GraphRecipe(
        level_id="stateful_hub_spacing_fixture",
        difficulty="hard",
        nodes=tuple(
            GraphRecipeNode(node_id, "switch" if node_id == "hub" else "route")
            for node_id in (
                "start", "hub", "package", "return", "dead", "destination"
            )
        ),
        edges=(
            GraphRecipeEdge("start", "hub"),
            GraphRecipeEdge("hub", "package", "beforePackage"),
            GraphRecipeEdge("package", "return"),
            GraphRecipeEdge("return", "hub"),
            GraphRecipeEdge("hub", "destination", "afterPackage"),
            GraphRecipeEdge("hub", "dead"),
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
