from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.models.recipe_topology_rules import RecipeTopologyRules
from app.services.layout_layer_service import LayoutLayerService


def test_simple_path_is_monotonic_from_lower_start_to_upper_destination() -> None:
    result = LayoutLayerService().assign_layers(_recipe(
        nodes=("start", "a", "package", "destination"),
        edges=(("start", "a"), ("a", "package"), ("package", "destination")),
        route=("start", "a", "package", "destination"),
    ))

    assignments = result.by_node_id
    assert [assignments[node_id].logical_layer for node_id in ("start", "a", "package", "destination")] == [0, 1, 2, 3]
    assert all(assignments[node_id].lane.index == 0 for node_id in assignments)


def test_split_and_rejoin_uses_an_adjacent_lane() -> None:
    result = LayoutLayerService().assign_layers(_recipe(
        nodes=("start", "split", "package", "branch", "rejoin", "destination"),
        edges=(("start", "split"), ("split", "package"), ("package", "rejoin"), ("split", "branch"), ("branch", "rejoin"), ("rejoin", "destination")),
        route=("start", "split", "package", "rejoin", "destination"),
    ))

    assignments = result.by_node_id
    assert assignments["package"].lane.index == 0
    assert abs(assignments["branch"].lane.index) == 1
    assert assignments["branch"].logical_layer > assignments["split"].logical_layer


def test_return_loop_uses_nonoverlapping_outer_lane() -> None:
    result = LayoutLayerService().assign_layers(_recipe(
        nodes=("start", "switch", "package", "return_node", "destination"),
        edges=(("start", "switch"), ("switch", "package"), ("package", "return_node"), ("return_node", "switch"), ("return_node", "destination")),
        route=("start", "switch", "package", "return_node", "destination"),
    ))

    assignments = result.by_node_id
    assert result.return_edge_ids
    assert abs(assignments["return_node"].lane.index) >= 2
    assert assignments["return_node"].lane.kind == "return"


def test_multiway_switch_reserves_expanded_icon_clearance() -> None:
    result = LayoutLayerService().assign_layers(_recipe(
        nodes=("start", "hub", "package", "a", "b", "destination"),
        edges=(("start", "hub"), ("hub", "package"), ("hub", "a"), ("hub", "b"), ("package", "destination")),
        route=("start", "hub", "package", "destination"),
    ))

    assert [
        (item.node_id, item.horizontal_cells, item.vertical_cells)
        for item in result.reserved_icon_clearances
    ] == [
        ("hub", 2, 2),
        ("package", 2, 2),
        ("destination", 2, 2),
    ]


def _recipe(*, nodes, edges, route) -> GraphRecipe:
    roles = {"start": "start", "package": "package", "destination": "destination", "split": "switch", "switch": "switch", "hub": "switch"}
    return GraphRecipe(
        level_id="layer_test",
        difficulty="medium",
        nodes=tuple(GraphRecipeNode(node_id, roles.get(node_id, "route")) for node_id in nodes),
        edges=tuple(GraphRecipeEdge(*edge) for edge in edges),
        required_path=tuple(route),
        tap_node_ids=(),
        topology_rules=RecipeTopologyRules(
            allows_cycles=True,
            allowed_cycle_count=1,
            allows_return_path=True,
            allows_rejoin=True,
            allows_revisit=True,
            allows_ring=False,
            requires_package_gate=False,
            requires_unique_solution=False,
            requires_swift_runtime_validation=False,
        ),
    )
