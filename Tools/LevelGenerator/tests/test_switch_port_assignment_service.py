from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.models.layout_graph import LayoutGraph, SwitchPortDirection
from app.models.recipe_topology_rules import RecipeTopologyRules
from app.services.switch_port_assignment_service import SwitchPortAssignmentService


def test_two_outgoing_roads_receive_distinct_nonoverlapping_ports() -> None:
    result = SwitchPortAssignmentService().assign_ports(
        _graph(("upper", "lower")),
        {"start": (0, -1), "switch": (0, 0), "upper": (1, 1), "lower": (-1, 1), "destination": (0, 2)},
    )

    assignments = result.assignments_by_switch["switch"]
    assert len({item.direction for item in assignments}) == 2
    assert {item.direction for item in assignments} == {
        SwitchPortDirection.NORTH_EAST,
        SwitchPortDirection.NORTH_WEST,
    }


def test_four_way_switch_uses_cardinal_ports() -> None:
    targets = ("north", "east", "south", "west")
    result = SwitchPortAssignmentService().assign_ports(
        _graph(targets),
        {
            "start": (0, -2), "switch": (0, 0), "north": (0, 1), "east": (1, 0),
            "south": (0, -1), "west": (-1, 0), "destination": (0, 2),
        },
    )

    assert {item.direction for item in result.assignments_by_switch["switch"]} == {
        SwitchPortDirection.NORTH, SwitchPortDirection.EAST,
        SwitchPortDirection.SOUTH, SwitchPortDirection.WEST,
    }


def test_port_order_is_stable_clockwise_and_initial_route_gets_readable_port() -> None:
    service = SwitchPortAssignmentService()
    graph = _graph(("upper", "lower"))
    positions = {"start": (0, -1), "switch": (0, 0), "upper": (1, 1), "lower": (-1, 1), "destination": (0, 2)}

    first = service.assign_ports(graph, positions).assignments_by_switch["switch"]
    second = service.assign_ports(graph, positions).assignments_by_switch["switch"]

    assert first == second
    assert [item.clockwise_index for item in first] == sorted(item.clockwise_index for item in first)
    assert next(item for item in first if item.target_node_id == "upper").is_initial_route


def _graph(targets: tuple[str, ...]) -> LayoutGraph:
    nodes = ("start", "switch", *targets, "destination")
    recipe = GraphRecipe(
        level_id="ports",
        difficulty="medium",
        nodes=tuple(GraphRecipeNode(node_id, "switch" if node_id == "switch" else node_id) for node_id in nodes),
        edges=(GraphRecipeEdge("start", "switch"),) + tuple(GraphRecipeEdge("switch", target) for target in targets),
        required_path=("start", "switch", targets[0]),
        tap_node_ids=(),
        topology_rules=RecipeTopologyRules(
            allows_cycles=False,
            allows_rejoin=False,
            allows_revisit=False,
            allows_return_path=False,
            allows_ring=False,
            allowed_cycle_count=0,
            requires_package_gate=False,
            requires_unique_solution=False,
            requires_swift_runtime_validation=False,
        ),
    )
    return LayoutGraph.from_recipe(recipe)
