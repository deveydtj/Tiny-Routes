import pytest

from tiny_routes_core.graph import (GraphIndex, GraphValidationError, cycle_node_ids,
                                    normalize_active_edges, reachable_node_ids, rejoin_node_ids,
                                    usable_outgoing_edges)
from tiny_routes_core.models import (LevelDocument, RouteEdge, RouteGraph, RouteNode,
                                     Solution)
from tiny_routes_core.simulation import RuntimeState


def level_dict():
    return {
        "id": "test", "name": "Test", "schemaVersion": 99,
        "graph": {"extension": True, "nodes": [
            {"id": "start", "x": 0, "y": 0, "outgoingEdgeIDs": ["a"], "nodeExtra": 1},
            {"id": "switch", "x": 1, "y": 0, "outgoingEdgeIDs": ["b", "c"]},
            {"id": "package", "x": 2, "y": 0, "outgoingEdgeIDs": ["d"]},
            {"id": "destination", "x": 3, "y": 0, "outgoingEdgeIDs": []},
        ], "edges": [
            {"id": "a", "fromNodeID": "start", "toNodeID": "switch"},
            {"id": "b", "fromNodeID": "switch", "toNodeID": "package", "edgeExtra": 2},
            {"id": "c", "fromNodeID": "switch", "toNodeID": "destination"},
            {"id": "d", "fromNodeID": "package", "toNodeID": "destination"},
        ]}, "startNodeID": "start", "packageNodeID": "package",
        "destinationNodeID": "destination", "timeLimitSeconds": 20, "parTaps": 1,
        "rules": {"switchInteractionMode": "liveLookahead", "futureRule": "kept"},
    }


def test_level_and_solution_round_trip_unknown_fields_and_clone_independently():
    raw = level_dict(); level = LevelDocument.from_dict(raw)
    assert level.to_dict() == raw
    clone = level.clone(); clone.graph.nodes[0].outgoingEdgeIDs.append("changed")
    assert level.graph.nodes[0].outgoingEdgeIDs == ["a"]
    solution_raw = {"levelID": "test", "description": None, "expectedOutcome": "completed",
                    "maxTaps": 1, "requiresWithinTimeLimit": True,
                    "actions": [{"timeSeconds": 1, "tapNodeID": "switch", "note": "keep"}],
                    "extension": [1, 2]}
    assert Solution.from_dict(solution_raw).to_dict() == solution_raw


def test_index_preserves_order_and_duplicate_errors_are_deterministic():
    index = GraphIndex.build(LevelDocument.from_dict(level_dict()).graph)
    assert [edge.id for edge in index.outgoing_by_node_id["switch"]] == ["b", "c"]
    graph = RouteGraph([RouteNode("x", 0, 0), RouteNode("x", 1, 1)], [])
    with pytest.raises(GraphValidationError) as caught: GraphIndex.build(graph)
    assert caught.value.codes == ("duplicate_node_id:x",)


def test_queries_and_active_normalization_are_stable():
    index = GraphIndex.build(LevelDocument.from_dict(level_dict()).graph)
    assert reachable_node_ids(index, "start") == ("start", "switch", "package", "destination")
    assert rejoin_node_ids(index, "switch") == ("destination",)
    assert cycle_node_ids(index) == ()
    assert normalize_active_edges(index, {"switch": "missing"})["switch"] == "b"


def test_runtime_initialization_and_copy_are_safe():
    state = RuntimeState.initialize(LevelDocument.from_dict(level_dict()))
    assert state.current_node_id == "start" and state.current_edge_id == "a"
    assert state.switch_active_edge_ids["switch"] == "b"
    clone = state.clone(); clone.switch_active_edge_ids["switch"] = "c"; clone.visited_node_ids.append("switch")
    assert state.switch_active_edge_ids["switch"] == "b"
    assert state.visited_node_ids == ["start"]


def test_runtime_reports_invalid_special_nodes_as_validation_errors():
    raw = level_dict(); raw["startNodeID"] = "missing"
    with pytest.raises(GraphValidationError) as caught: RuntimeState.initialize(LevelDocument.from_dict(raw))
    assert caught.value.codes == ("missing_start_node:missing",)


def test_package_state_queries_preserve_authored_order_and_normalize_active_edge():
    raw = level_dict()
    raw["graph"]["edges"][1]["availability"] = "beforePackage"
    raw["graph"]["edges"][2]["availability"] = "afterPackage"
    index = GraphIndex.build(LevelDocument.from_dict(raw).graph)

    assert [edge.id for edge in usable_outgoing_edges(index, "switch", False)] == ["b"]
    assert [edge.id for edge in usable_outgoing_edges(index, "switch", True)] == ["c"]
    assert normalize_active_edges(
        index,
        {"switch": "b"},
        package_collected=True,
    )["switch"] == "c"
    assert reachable_node_ids(index, "switch", package_collected=False) == (
        "switch", "package", "destination",
    )


def test_runtime_rejects_conditional_nonterminal_dead_end_in_either_phase():
    raw = level_dict()
    raw["graph"]["edges"][0]["availability"] = "afterPackage"

    with pytest.raises(GraphValidationError) as caught:
        RuntimeState.initialize(LevelDocument.from_dict(raw))

    assert "conditional_road_dead_end:start:before_package" in caught.value.codes
