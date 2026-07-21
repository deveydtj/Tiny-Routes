from app.models.composition_state import (
    AssignedStateEffect,
    CompositionGraph,
    CompositionState,
    ObjectivePhaseBoundary,
)
from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.models.layout_graph import LayoutCorridorKind, LayoutGraph
from app.models.motif_contract import MotifEdgeStateChangeKind
from app.models.recipe_topology_rules import RecipeTopologyRules


def test_legacy_recipe_infers_cross_phase_hub_and_state_relationships() -> None:
    graph = LayoutGraph.from_recipe(_revisited_hub_recipe())

    nodes = {node.node_id: node for node in graph.nodes}
    edges = {(edge.from_node_id, edge.to_node_id): edge for edge in graph.edges}
    assert graph.objective_phase_count == 2
    assert graph.stateful_hub_node_ids == ("hub",)
    assert nodes["hub"].objective_phase_indices == (0, 1)
    assert nodes["hub"].is_revisited_hub
    assert nodes["hub"].footprint.width == 1.85
    assert edges[("hub", "destination")].objective_phase_indices == (1,)
    assert edges[("hub", "destination")].corridor_kinds == (
        LayoutCorridorKind.PRIMARY,
    )
    assert edges[("hub", "destination")].state_relationships[0].kind is (
        MotifEdgeStateChangeKind.OPEN
    )
    assert edges[("hub", "package")].state_relationships[0].kind is (
        MotifEdgeStateChangeKind.CLOSE
    )


def test_composition_adapter_retains_phase_effect_and_strategy_corridors() -> None:
    state = CompositionState(
        blueprint_id="layout_blueprint",
        unfulfilled_decision_ids=(),
        open_ports=(),
        objective_phase_boundaries=(
            ObjectivePhaseBoundary("pickup", 0, "start", "pickup"),
            ObjectivePhaseBoundary("destination", 1, "pickup", "destination"),
        ),
        current_graph=CompositionGraph(
            nodes=tuple(
                GraphRecipeNode(node_id, "switch" if node_id == "hub" else "route")
                for node_id in (
                    "start",
                    "hub",
                    "pickup",
                    "return",
                    "alternate",
                    "destination",
                )
            ),
            edges=tuple(GraphRecipeEdge(*pair) for pair in (
                ("start", "hub"),
                ("hub", "pickup"),
                ("pickup", "return"),
                ("return", "hub"),
                ("hub", "destination"),
                ("hub", "alternate"),
                ("alternate", "destination"),
            )),
        ),
        assigned_state_effects=(
            AssignedStateEffect(
                "pickup_unlock",
                "destination_exit",
                "hub",
                "destination",
                MotifEdgeStateChangeKind.OPEN,
            ),
        ),
    )

    graph = LayoutGraph.from_composition_state(
        state,
        primary_route=(
            "start", "hub", "pickup", "return", "hub", "destination"
        ),
        phase_routes=(
            ("start", "hub", "pickup"),
            ("pickup", "return", "hub", "destination"),
        ),
        alternate_routes=(("hub", "alternate", "destination"),),
        recovery_routes=(("alternate", "destination"),),
    )

    edges = {(edge.from_node_id, edge.to_node_id): edge for edge in graph.edges}
    assert graph.stateful_hub_node_ids == ("hub",)
    assert edges[("hub", "destination")].state_relationships[0].transition_id == (
        "pickup_unlock"
    )
    assert edges[("hub", "alternate")].corridor_kinds == (
        LayoutCorridorKind.ALTERNATE,
    )
    assert edges[("alternate", "destination")].corridor_kinds == (
        LayoutCorridorKind.ALTERNATE,
        LayoutCorridorKind.RECOVERY,
    )


def _revisited_hub_recipe() -> GraphRecipe:
    return GraphRecipe(
        level_id="phase_layout_fixture",
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
