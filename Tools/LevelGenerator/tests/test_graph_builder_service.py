from __future__ import annotations

from app.services.graph_builder_service import GraphBuilderService


def test_outgoing_edge_ids_match_edges_and_preserve_order() -> None:
    builder = GraphBuilderService()
    builder.add_node("start", 0, 0)
    builder.add_node("wrong", 1, -1)
    builder.add_node("package", 1, 1)

    wrong = builder.add_edge("start", "wrong")
    package = builder.add_edge("start", "package")
    level = builder.build_level_document("level_012", "Level 012", "start", "package", "package", 30, 1)

    assert level.graph.nodes[0].outgoingEdgeIDs == [wrong.id, package.id]
    assert [edge.id for edge in level.graph.edges] == [wrong.id, package.id]


def test_switch_outgoing_road_shapes_are_adjusted_for_distinct_visual_starts() -> None:
    builder = GraphBuilderService()
    builder.add_node("switch", 0, 0)
    builder.add_node("wrong", 1, -1)
    builder.add_node("package", 1, 1)

    wrong = builder.add_edge("switch", "wrong")
    package = builder.add_edge("switch", "package")
    level = builder.build_level_document("level_012", "Level 012", "switch", "package", "package", 30, 1)
    edges = {edge.id: edge for edge in level.graph.edges}

    assert edges[wrong.id].roadShape == "horizontalFirst"
    assert edges[package.id].roadShape == "verticalFirst"


def test_builder_preserves_authored_road_availability() -> None:
    builder = GraphBuilderService()
    builder.add_node("start", 0, 0)
    builder.add_node("package", 1, 0)

    edge = builder.add_edge("start", "package", availability="beforePackage")
    level = builder.build_level_document(
        "level_012", "Level 012", "start", "package", "package", 30, 0
    )

    assert level.graph.edges[0].id == edge.id
    assert level.graph.edges[0].availability == "beforePackage"
    assert level.graph.edges[0].to_dict()["availability"] == "beforePackage"
