from __future__ import annotations

from dataclasses import replace

from app.models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from app.services.graph_isomorphism_service import GraphIsomorphismService


def _recipe() -> GraphRecipe:
    return GraphRecipe(
        level_id="level_graph_iso",
        difficulty="medium",
        nodes=(
            GraphRecipeNode("start", "start"),
            GraphRecipeNode("choice", "switch"),
            GraphRecipeNode("package", "package"),
            GraphRecipeNode("detour", "route"),
            GraphRecipeNode("destination", "destination"),
        ),
        edges=(
            GraphRecipeEdge("start", "choice"),
            GraphRecipeEdge("choice", "detour", "beforePackage"),
            GraphRecipeEdge("choice", "package"),
            GraphRecipeEdge("detour", "choice"),
            GraphRecipeEdge("package", "choice"),
            GraphRecipeEdge("choice", "destination", "afterPackage", usage_limit=1),
        ),
        required_path=("start", "choice", "package", "choice", "destination"),
        tap_node_ids=("choice", "choice"),
        family_name="original_family",
        variant_name="primary",
        notes=("coordinates and author notes are intentionally ignored",),
    )


def _renamed(recipe: GraphRecipe) -> GraphRecipe:
    names = {
        "start": "origin_27",
        "choice": "junction_beta",
        "package": "pickup_z",
        "detour": "lane_m",
        "destination": "terminal_q",
    }
    nodes = tuple(
        GraphRecipeNode(names[node.id], node.role)
        for node in reversed(recipe.nodes)
    )
    edges = tuple(
        GraphRecipeEdge(
            names[edge.from_node_id],
            names[edge.to_node_id],
            edge.availability,
            edge.usage_limit,
        )
        for edge in recipe.edges
    )
    return replace(
        recipe,
        level_id="renamed_and_mirrored_layout_fixture",
        nodes=nodes,
        edges=edges,
        required_path=tuple(names[node_id] for node_id in recipe.required_path),
        tap_node_ids=tuple(names[node_id] for node_id in recipe.tap_node_ids),
        package_node_id=names[recipe.package_node_id],
        destination_node_id=names[recipe.destination_node_id],
        family_name="metadata_only_rename",
        variant_name="alternate",
        notes=("different metadata",),
    )


def test_role_aware_signature_ignores_ids_node_order_and_metadata() -> None:
    service = GraphIsomorphismService()
    first = _recipe()
    second = _renamed(first)

    assert service.signature_for(first) == service.signature_for(second)
    assert service.are_isomorphic(first, second)
    assert service.node_mapping(first, second) == {
        "start": "origin_27",
        "choice": "junction_beta",
        "detour": "lane_m",
        "package": "pickup_z",
        "destination": "terminal_q",
    }


def test_node_roles_and_objective_phases_are_structural() -> None:
    service = GraphIsomorphismService()
    recipe = _recipe()
    changed_role = replace(
        recipe,
        nodes=tuple(
            replace(node, role="route") if node.id == "choice" else node
            for node in recipe.nodes
        ),
    )
    changed_objective = replace(
        recipe,
        package_node_id="detour",
    )

    assert not service.are_isomorphic(recipe, changed_role)
    assert not service.are_isomorphic(recipe, changed_objective)


def test_authored_switch_order_and_edge_state_are_structural() -> None:
    service = GraphIsomorphismService()
    recipe = _recipe()
    reordered = replace(
        recipe,
        edges=(recipe.edges[0], recipe.edges[2], recipe.edges[1], *recipe.edges[3:]),
    )
    changed_state = replace(
        recipe,
        edges=tuple(
            replace(edge, usage_limit=None)
            if edge.to_node_id == "destination"
            else edge
            for edge in recipe.edges
        ),
    )

    assert not service.are_isomorphic(recipe, reordered)
    assert not service.are_isomorphic(recipe, changed_state)
    assert service.node_mapping(recipe, reordered) is None
