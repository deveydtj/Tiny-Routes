import pytest
import tiny_routes_core.models as shared_models

from tiny_routes_core.graph import (GraphIndex, GraphValidationError, cycle_node_ids,
                                    normalize_active_edges, reachable_node_ids, rejoin_node_ids,
                                    usable_outgoing_edges)
from tiny_routes_core.models import (EdgeAvailabilityRule, LevelDocument, RouteEdge,
                                     RouteGraph, RouteNode, RouteObjective,
                                     RouteObjectiveKind, Solution)
from tiny_routes_core.simulation import RuntimeState
from tiny_routes_core.validation import validate_level_objectives


def test_shared_models_export_only_canonical_type_names():
    assert shared_models.RouteNode is RouteNode
    assert shared_models.RouteEdge is RouteEdge
    assert shared_models.RouteGraph is RouteGraph
    assert shared_models.EdgeAvailabilityRule is EdgeAvailabilityRule
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


def schema_three_level_dict():
    raw = level_dict()
    raw["schemaVersion"] = 3
    raw["objectives"] = [
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
        },
    ]
    return raw


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


def test_legacy_objective_adapter_is_deterministic_and_does_not_rewrite_source():
    for schema_version in (1, 2):
        raw = level_dict()
        raw["schemaVersion"] = schema_version
        level = LevelDocument.from_dict(raw)

        effective = level.effective_objectives

        assert [objective.id for objective in effective] == [
            "legacy_pickup",
            "legacy_destination",
        ]
        assert [objective.nodeID for objective in effective] == ["package", "destination"]
        assert [objective.kind for objective in effective] == [
            RouteObjectiveKind.PICKUP,
            RouteObjectiveKind.DESTINATION,
        ]
        assert [objective.sequenceIndex for objective in effective] == [0, 1]
        assert level.objectives is None
        assert level.to_dict() == raw


def test_schema_three_effective_objectives_use_authored_sequence():
    level = LevelDocument.from_dict(schema_three_level_dict())

    effective = level.effective_objectives

    assert [objective.id for objective in effective] == [
        "pickup_package",
        "finish_delivery",
    ]
    effective[0].id = "changed"
    assert level.objectives[0].id == "pickup_package"


def test_schema_three_objective_validation_accepts_valid_sequence():
    assert validate_level_objectives(
        LevelDocument.from_dict(schema_three_level_dict())
    ) == ()


@pytest.mark.parametrize(
    ("mutate", "expected_codes"),
    [
        (
            lambda raw: raw["objectives"].__setitem__(1, {
                **raw["objectives"][1], "id": "pickup_package",
            }),
            {"duplicate_objective_id"},
        ),
        (
            lambda raw: raw["objectives"][1].__setitem__("sequenceIndex", 2),
            {"noncontiguous_objective_sequence_indices", "objective_array_order_mismatch"},
        ),
        (
            lambda raw: raw["objectives"][0].__setitem__("nodeID", "missing"),
            {"objective_node_not_found", "legacy_package_objective_conflict"},
        ),
        (
            lambda raw: raw["objectives"][1].__setitem__("kind", "checkpoint"),
            {"invalid_terminal_objective_count"},
        ),
        (
            lambda raw: raw["objectives"].reverse(),
            {"objective_array_order_mismatch"},
        ),
    ],
)
def test_schema_three_objective_validation_rejects_invalid_contracts(mutate, expected_codes):
    raw = schema_three_level_dict()
    mutate(raw)

    codes = {issue.code for issue in validate_level_objectives(LevelDocument.from_dict(raw))}

    assert expected_codes <= codes


def test_objective_validation_rejects_schema_conflicts_and_missing_schema_three_data():
    legacy_with_objectives = schema_three_level_dict()
    legacy_with_objectives["schemaVersion"] = 2
    assert {issue.code for issue in validate_level_objectives(
        LevelDocument.from_dict(legacy_with_objectives)
    )} == {"objectives_require_schema_3"}

    missing = schema_three_level_dict()
    del missing["objectives"]
    assert {issue.code for issue in validate_level_objectives(
        LevelDocument.from_dict(missing)
    )} == {"schema_3_objectives_required"}

    conflicting = schema_three_level_dict()
    conflicting["packageNodeID"] = "switch"
    conflicting["destinationNodeID"] = "package"
    assert {
        issue.code for issue in validate_level_objectives(LevelDocument.from_dict(conflicting))
    } >= {
        "legacy_package_objective_conflict",
        "legacy_destination_objective_conflict",
    }


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


def test_structured_edge_availability_rule_round_trips_losslessly():
    raw = schema_three_level_dict()
    raw["graph"]["edges"][1]["availabilityRule"] = {
        "requiredCompletedObjectiveIDs": ["pickup_package"],
        "forbiddenCompletedObjectiveIDs": ["future_checkpoint"],
        "minimumObjectiveIndex": 1,
        "maximumObjectiveIndex": 2,
        "usageLimit": 1,
        "futureCondition": {"trace": True},
    }

    level = LevelDocument.from_dict(raw)
    rule = level.graph.edges[1].availabilityRule

    assert rule is not None
    assert rule.requiredCompletedObjectiveIDs == ["pickup_package"]
    assert rule.forbiddenCompletedObjectiveIDs == ["future_checkpoint"]
    assert rule.minimumObjectiveIndex == 1
    assert rule.maximumObjectiveIndex == 2
    assert rule.usageLimit == 1
    assert level.to_dict() == raw


@pytest.mark.parametrize(
    ("availability", "required", "forbidden"),
    [
        ("always", [], []),
        ("beforePackage", [], ["pickup_package"]),
        ("afterPackage", ["pickup_package"], []),
    ],
)
def test_legacy_edge_availability_adapts_to_effective_pickup_objective(
    availability, required, forbidden
):
    raw = schema_three_level_dict()
    raw["graph"]["edges"][1]["availability"] = availability
    level = LevelDocument.from_dict(raw)

    rule = level.effective_edge_availability_rule(level.graph.edges[1])

    assert rule.requiredCompletedObjectiveIDs == required
    assert rule.forbiddenCompletedObjectiveIDs == forbidden
    assert level.to_dict() == raw


def test_version_two_edge_availability_uses_legacy_pickup_adapter_id():
    raw = level_dict()
    raw["schemaVersion"] = 2
    raw["graph"]["edges"][1]["availability"] = "afterPackage"
    level = LevelDocument.from_dict(raw)

    rule = level.effective_edge_availability_rule(level.graph.edges[1])

    assert rule.requiredCompletedObjectiveIDs == ["legacy_pickup"]
    assert level.to_dict() == raw


def test_authored_structured_rule_is_the_effective_source_of_truth():
    raw = schema_three_level_dict()
    raw["graph"]["edges"][1].update({
        "availability": "beforePackage",
        "availabilityRule": {"requiredCompletedObjectiveIDs": ["finish_delivery"]},
    })
    level = LevelDocument.from_dict(raw)

    rule = level.effective_edge_availability_rule(level.graph.edges[1])

    assert rule.requiredCompletedObjectiveIDs == ["finish_delivery"]
    assert rule.forbiddenCompletedObjectiveIDs == []


def test_runtime_rejects_conditional_nonterminal_dead_end_in_either_phase():
    raw = level_dict()
    raw["graph"]["edges"][0]["availability"] = "afterPackage"

    with pytest.raises(GraphValidationError) as caught:
        RuntimeState.initialize(LevelDocument.from_dict(raw))

    assert "conditional_road_dead_end:start:before_package" in caught.value.codes
