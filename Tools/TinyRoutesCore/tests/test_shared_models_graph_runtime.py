import pytest
import tiny_routes_core.models as shared_models

from tiny_routes_core.graph import (GraphIndex, GraphValidationError, cycle_node_ids,
                                    normalize_active_edges, reachable_node_ids, rejoin_node_ids,
                                    usable_outgoing_edges)
from tiny_routes_core.models import (LevelDocument, RouteEdge, RouteGraph, RouteNode,
                                     RouteObjective, RouteObjectiveKind, Solution)
from tiny_routes_core.simulation import RuntimeState


def test_shared_models_export_only_canonical_type_names():
    assert shared_models.RouteNode is RouteNode
    assert shared_models.RouteEdge is RouteEdge
    assert shared_models.RouteGraph is RouteGraph
    assert shared_models.RouteObjective is RouteObjective
    assert shared_models.RouteObjectiveKind is RouteObjectiveKind
    assert shared_models.Solution is Solution
    for deprecated_name in (
        "RouteNodeModel",
        "RouteEdgeModel",
        "RouteGraphModel",
        "SolutionActionModel",
        "SolutionModel",
    ):
        assert not hasattr(shared_models, deprecated_name)


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


def test_route_objective_round_trips_all_kinds_and_unknown_fields():
    for sequence_index, kind in enumerate(RouteObjectiveKind):
        raw = {
            "id": f"objective_{sequence_index}",
            "nodeID": f"node_{sequence_index}",
            "kind": kind.value,
            "sequenceIndex": sequence_index,
            "revealPolicy": "whenActive",
            "displayMetadata": {
                "title": f"Stop {sequence_index + 1}",
                "marker": {"color": "blue", "priority": sequence_index},
            },
            "futureBehavior": {"enabled": True},
        }

        objective = RouteObjective.from_dict(raw)

        assert objective.kind is kind
        assert objective.to_dict() == raw
        clone = objective.clone()
        clone.displayMetadata["marker"]["color"] = "orange"
        assert objective.displayMetadata["marker"]["color"] == "blue"


def test_level_document_round_trips_optional_objectives_without_rewriting_legacy_levels():
    legacy = level_dict()
    assert LevelDocument.from_dict(legacy).to_dict() == legacy
    assert LevelDocument.from_dict(legacy).objectives is None

    schema_three = level_dict()
    schema_three["schemaVersion"] = 3
    schema_three["objectives"] = [
        {
            "id": "pickup_package",
            "nodeID": "package",
            "kind": "pickup",
            "sequenceIndex": 0,
            "revealPolicy": "always",
        },
        {
            "id": "finish_delivery",
            "nodeID": "destination",
            "kind": "destination",
            "sequenceIndex": 1,
            "revealPolicy": "whenActive",
            "displayMetadata": None,
            "futureStyle": "flag",
        },
    ]

    level = LevelDocument.from_dict(schema_three)

    assert [objective.id for objective in level.objectives] == [
        "pickup_package",
        "finish_delivery",
    ]
    assert level.to_dict() == schema_three


def test_route_objective_rejects_unknown_kind_and_nonobject_display_metadata():
    raw = {
        "id": "unknown",
        "nodeID": "node",
        "kind": "mystery",
        "sequenceIndex": 0,
        "revealPolicy": "always",
    }
    with pytest.raises(ValueError):
        RouteObjective.from_dict(raw)

    raw["kind"] = "checkpoint"
    raw["displayMetadata"] = ["not", "an", "object"]
    with pytest.raises(TypeError, match="displayMetadata must be an object or null"):
        RouteObjective.from_dict(raw)


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
