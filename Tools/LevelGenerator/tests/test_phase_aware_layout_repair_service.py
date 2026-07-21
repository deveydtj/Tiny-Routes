from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.models.layout_constraints import ConstraintViolation, RepairOperationKind
from app.models.layout_graph import LayoutGraph
from app.models.layout_result import LayoutResult
from app.models.recipe_topology_rules import RecipeTopologyRules
from app.services.layout_repair_service import LayoutRepairConfig, LayoutRepairService


def test_phase_candidates_cover_every_locked_repair_operation_without_graph_changes() -> None:
    graph = LayoutGraph.from_recipe(_stateful_recipe())
    positions = _positions()
    shapes = {edge.edge_id: "horizontalFirst" for edge in graph.edges}
    service = LayoutRepairService(LayoutRepairConfig(grid_size=0.1, maximum_attempts=256))
    graph_signature = _graph_signature(graph)

    candidates = tuple(service._phase_candidates(
        graph,
        positions,
        shapes,
        {},
        {},
        ConstraintViolation(
            "layout_state_lock_indicator_objective_overlap",
            "fixture",
            node_id="package",
            edge_id="layout_edge_4",
        ),
    ))
    kinds = {operation.kind for operation, _ in candidates}

    assert {
        RepairOperationKind.MOVE_STATEFUL_HUB,
        RepairOperationKind.WIDEN_RETURN_LANE,
        RepairOperationKind.RELOCATE_OBJECTIVE_MARKER,
        RepairOperationKind.MOVE_LOCK_INDICATOR,
        RepairOperationKind.SWAP_BRANCH_LANES,
        RepairOperationKind.EXPAND_PHASE_SPACING,
        RepairOperationKind.CHANGE_BEND_ORDER,
    }.issubset(kinds)
    assert _graph_signature(graph) == graph_signature


def test_phase_aware_repair_is_deterministic_and_retains_overlay_geometry() -> None:
    graph = LayoutGraph.from_recipe(_stateful_recipe())
    layout = LayoutResult(
        positions=_positions(),
        objective_marker_positions={"package": (-0.55, 0.0)},
    )
    service = LayoutRepairService(LayoutRepairConfig(grid_size=0.1, maximum_attempts=96))

    first = service.repair_phase_aware(layout, graph)
    second = service.repair_phase_aware(layout, graph)

    assert first.positions == second.positions
    assert first.objective_marker_positions == second.objective_marker_positions
    assert first.lock_indicator_positions == second.lock_indicator_positions
    assert first.repair_operations == second.repair_operations
    assert _graph_signature(graph) == _graph_signature(LayoutGraph.from_recipe(_stateful_recipe()))


def _positions() -> dict[str, tuple[float, float]]:
    return {
        "start": (-1.0, -0.8),
        "hub": (-0.6, 0.0),
        "package": (0.0, 0.6),
        "return": (-0.6, 0.6),
        "destination": (0.65, -0.45),
        "dead": (0.65, 0.65),
    }


def _graph_signature(graph: LayoutGraph) -> tuple[object, ...]:
    return (
        tuple((node.node_id, node.outgoing_node_ids) for node in graph.nodes),
        tuple(
            (edge.edge_id, edge.from_node_id, edge.to_node_id, edge.availability)
            for edge in graph.edges
        ),
        tuple((objective.objective_id, objective.node_id) for objective in graph.objectives),
    )


def _stateful_recipe() -> GraphRecipe:
    return GraphRecipe(
        level_id="phase_repair_fixture",
        difficulty="hard",
        nodes=tuple(
            GraphRecipeNode(node_id, role)
            for node_id, role in (
                ("start", "start"),
                ("hub", "switch"),
                ("package", "package"),
                ("return", "route"),
                ("destination", "destination"),
                ("dead", "route"),
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
        required_path=("start", "hub", "package", "return", "hub", "destination"),
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
