from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.models.layout_constraints import BoundingBox
from app.models.layout_graph import LayoutGraph
from app.models.recipe_topology_rules import RecipeTopologyRules
from app.services.objective_marker_clearance_service import (
    ObjectiveMarkerClearanceService,
)


def test_objective_markers_reserve_ordered_clearance_and_fit_when_separated() -> None:
    graph = LayoutGraph.from_recipe(_simple_recipe())
    positions = {
        "start": (-0.8, -0.6),
        "package": (0.0, 0.0),
        "destination": (0.8, 0.6),
    }
    service = ObjectiveMarkerClearanceService()

    rules = service.rules_for(graph)
    assert [
        (rule.objective_id, rule.phase_index, rule.reserved_clearance.node_id)
        for rule in rules
    ] == [
        ("package", 0, "package"),
        ("destination", 1, "destination"),
    ]
    assert service.validate(
        graph,
        positions,
        bounds=BoundingBox(-1.2, 1.2, -1.2, 1.2),
    ) == ()


def test_objective_markers_reject_overlap_with_each_other_and_stateful_hub() -> None:
    graph = LayoutGraph.from_recipe(_revisited_hub_recipe())
    positions = {
        "start": (-0.8, -0.8),
        "hub": (0.0, 0.0),
        "package": (0.12, 0.0),
        "return": (-0.6, 0.5),
        "dead": (0.7, -0.3),
        "destination": (0.2, 0.02),
    }

    codes = {
        issue.code
        for issue in ObjectiveMarkerClearanceService().validate(graph, positions)
    }
    assert "objective_marker_overlap" in codes
    assert "objective_marker_stateful_hub_overlap" in codes


def test_objective_markers_validate_road_and_camera_clearance() -> None:
    graph = LayoutGraph.from_recipe(_simple_recipe(extra_crossing=True))
    positions = {
        "start": (-0.8, 0.0),
        "route": (0.8, 0.0),
        "package": (0.0, 0.04),
        "destination": (1.15, 0.7),
    }

    codes = {
        issue.code
        for issue in ObjectiveMarkerClearanceService().validate(graph, positions)
    }
    assert "objective_marker_road_clearance_failure" in codes
    assert "objective_marker_camera_frame_failure" in codes


def _simple_recipe(*, extra_crossing: bool = False) -> GraphRecipe:
    nodes = [
        GraphRecipeNode("start", "start"),
        GraphRecipeNode("package", "package"),
        GraphRecipeNode("destination", "destination"),
    ]
    edges = [
        GraphRecipeEdge("start", "package"),
        GraphRecipeEdge("package", "destination"),
    ]
    if extra_crossing:
        nodes.append(GraphRecipeNode("route", "route"))
        edges.append(GraphRecipeEdge("start", "route"))
    return GraphRecipe(
        level_id="objective_marker_fixture",
        difficulty="medium",
        nodes=tuple(nodes),
        edges=tuple(edges),
        required_path=("start", "package", "destination"),
        tap_node_ids=(),
        topology_rules=RecipeTopologyRules(
            allows_cycles=False,
            allowed_cycle_count=0,
            allows_return_path=False,
            allows_rejoin=False,
            allows_revisit=False,
            allows_ring=False,
            requires_package_gate=False,
            requires_unique_solution=True,
            requires_swift_runtime_validation=False,
        ),
    )

def _revisited_hub_recipe() -> GraphRecipe:
    return GraphRecipe(
        level_id="objective_hub_fixture",
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
