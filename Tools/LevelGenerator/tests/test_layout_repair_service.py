from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.models.layout_constraints import ConstraintViolation, RepairOperationKind
from app.models.layout_graph import LayoutGraph
from app.models.layout_result import LayoutResult
from app.models.recipe_topology_rules import RecipeTopologyRules
from app.services.graph_layout_service import GraphLayoutService
from app.services.layout_repair_service import LayoutRepairConfig, LayoutRepairService


def _recipe() -> GraphRecipe:
    return GraphRecipe(
        level_id="repair_fixture",
        difficulty="medium",
        nodes=tuple(GraphRecipeNode(node_id) for node_id in ("start", "a", "package", "destination")),
        edges=tuple(GraphRecipeEdge(*edge) for edge in (
            ("start", "a"), ("a", "package"), ("package", "destination")
        )),
        required_path=("start", "a", "package", "destination"),
        tap_node_ids=(),
        topology_rules=RecipeTopologyRules(
            allows_cycles=False,
            allows_rejoin=False,
            allows_revisit=False,
            allows_return_path=False,
            allows_ring=False,
            allowed_cycle_count=0,
            requires_package_gate=False,
            requires_unique_solution=True,
            requires_swift_runtime_validation=False,
        ),
    )


def _evaluate(positions, _shapes):
    return tuple(
        ConstraintViolation("node_spacing_failure", "overlap", node_id=second)
        for _, second in GraphLayoutService(minimum_node_distance=0.2).overlapping_pairs(positions)
    )


def test_known_overlapping_fixture_is_repaired_without_connectivity_change() -> None:
    graph = LayoutGraph.from_recipe(_recipe())
    original_edges = tuple((edge.from_node_id, edge.to_node_id) for edge in graph.edges)
    layout = LayoutResult(positions={
        "start": (0.0, 0.0), "a": (0.05, 0.0),
        "package": (0.5, 0.5), "destination": (0.8, 0.8),
    })
    result = LayoutRepairService(LayoutRepairConfig(grid_size=0.2)).repair(layout, graph, {}, _evaluate)

    assert not result.violations
    assert result.repair_operations[0].kind == RepairOperationKind.MOVE_NODE
    assert tuple((edge.from_node_id, edge.to_node_id) for edge in graph.edges) == original_edges


def test_same_input_produces_same_repair_sequence() -> None:
    graph = LayoutGraph.from_recipe(_recipe())
    layout = LayoutResult(positions={
        "start": (0.0, 0.0), "a": (0.05, 0.0),
        "package": (0.5, 0.5), "destination": (0.8, 0.8),
    })
    service = LayoutRepairService(LayoutRepairConfig(grid_size=0.2))

    first = service.repair(layout, graph, {}, _evaluate)
    second = service.repair(layout, graph, {}, _evaluate)

    assert first.positions == second.positions
    assert first.repair_operations == second.repair_operations
