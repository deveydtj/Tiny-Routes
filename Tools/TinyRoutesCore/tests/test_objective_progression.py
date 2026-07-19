from tiny_routes_core.models import LevelDocument
from tiny_routes_core.simulation import LevelOutcome, RuntimeSimulator, RuntimeState


def _level(nodes, edges, objectives, *, start="start", package="pickup", destination="destination"):
    return LevelDocument.from_dict({
        "schemaVersion": 3,
        "id": "objective_progression",
        "name": "Objective Progression",
        "graph": {"nodes": nodes, "edges": edges},
        "startNodeID": start,
        "packageNodeID": package,
        "destinationNodeID": destination,
        "timeLimitSeconds": 20,
        "parTaps": 0,
        "objectives": objectives,
    })


def _objective(objective_id, node_id, kind, index, reveal_policy="whenActive"):
    return {
        "id": objective_id,
        "nodeID": node_id,
        "kind": kind,
        "sequenceIndex": index,
        "revealPolicy": reveal_policy,
    }


def test_schema3_simulator_completes_ordered_objectives_and_emits_normalized_events():
    node_ids = ["start", "pickup", "checkpoint", "delivery", "destination"]
    nodes = [
        {
            "id": node_id,
            "x": float(index),
            "y": 0.0,
            "outgoingEdgeIDs": [f"e{index}"] if index < len(node_ids) - 1 else [],
        }
        for index, node_id in enumerate(node_ids)
    ]
    edges = [
        {
            "id": f"e{index}",
            "fromNodeID": node_ids[index],
            "toNodeID": node_ids[index + 1],
        }
        for index in range(len(node_ids) - 1)
    ]
    objectives = [
        _objective("collect", "pickup", "pickup", 0, "always"),
        _objective("inspect", "checkpoint", "checkpoint", 1),
        _objective("deliver", "delivery", "delivery", 2),
        _objective("finish", "destination", "destination", 3),
    ]

    result = RuntimeSimulator().simulate(_level(nodes, edges, objectives))

    assert result.state.outcome == LevelOutcome.COMPLETED
    assert result.state.active_objective is None
    assert result.state.completed_objective_ids == {"collect", "inspect", "deliver", "finish"}
    assert result.state.revealed_objective_ids == {"collect", "inspect", "deliver", "finish"}
    assert result.state.package_collected
    assert [
        event.objective_id
        for event in result.events
        if event.kind == "objective_completed"
    ] == ["collect", "inspect", "deliver", "finish"]
    assert result.events[-1].kind == "complete"


def test_schema3_future_objective_visit_is_recorded_without_legacy_failure():
    nodes = [
        {"id": "start", "x": 0.0, "y": 0.0, "outgoingEdgeIDs": ["to_destination"]},
        {"id": "destination", "x": 1.0, "y": 0.0, "outgoingEdgeIDs": ["to_pickup"]},
        {"id": "pickup", "x": 2.0, "y": 0.0, "outgoingEdgeIDs": ["back_to_destination"]},
    ]
    edges = [
        {"id": "to_destination", "fromNodeID": "start", "toNodeID": "destination"},
        {"id": "to_pickup", "fromNodeID": "destination", "toNodeID": "pickup"},
        {"id": "back_to_destination", "fromNodeID": "pickup", "toNodeID": "destination"},
    ]
    objectives = [
        _objective("collect", "pickup", "pickup", 0, "always"),
        _objective("finish", "destination", "destination", 1),
    ]

    result = RuntimeSimulator(maximum_step_count=8).simulate(_level(nodes, edges, objectives))

    assert result.state.outcome == LevelOutcome.COMPLETED
    assert result.failure_reason is None
    assert [
        event.objective_id
        for event in result.events
        if event.kind == "future_objective_visited"
    ] == ["finish"]


def test_schema3_arrival_completes_only_one_active_objective_and_fresh_state_restarts():
    nodes = [
        {"id": "start", "x": 0.0, "y": 0.0, "outgoingEdgeIDs": ["to_destination"]},
        {"id": "destination", "x": 1.0, "y": 0.0, "outgoingEdgeIDs": []},
    ]
    edges = [
        {"id": "to_destination", "fromNodeID": "start", "toNodeID": "destination"},
    ]
    objectives = [
        _objective("collect", "start", "pickup", 0, "always"),
        _objective("check", "start", "checkpoint", 1),
        _objective("finish", "destination", "destination", 2),
    ]
    level = _level(nodes, edges, objectives, package="start")

    progressed = RuntimeState.initialize(level)
    assert progressed.completed_objective_ids == {"collect"}
    assert progressed.active_objective is not None
    assert progressed.active_objective.id == "check"

    progressed.process_objective_arrival(
        "start",
        preserve_legacy_destination_failure=False,
    )
    assert progressed.completed_objective_ids == {"collect", "check"}

    restarted = RuntimeState.initialize(level)
    assert restarted.completed_objective_ids == {"collect"}
    assert restarted.active_objective_index == 1
    assert restarted.package_collected


def test_objective_road_filtering_normalizes_authored_choice_at_state_boundary():
    nodes = [
        {"id": "start", "x": 0.0, "y": 0.0, "outgoingEdgeIDs": ["to_hub"]},
        {
            "id": "hub",
            "x": 1.0,
            "y": 0.0,
            "outgoingEdgeIDs": ["one_use_checkpoint", "unlocked_destination"],
        },
        {"id": "checkpoint", "x": 2.0, "y": 0.0, "outgoingEdgeIDs": ["return_hub"]},
        {"id": "destination", "x": 3.0, "y": 0.0, "outgoingEdgeIDs": []},
    ]
    edges = [
        {"id": "to_hub", "fromNodeID": "start", "toNodeID": "hub"},
        {
            "id": "one_use_checkpoint",
            "fromNodeID": "hub",
            "toNodeID": "checkpoint",
            "availabilityRule": {"maximumObjectiveIndex": 0, "usageLimit": 1},
        },
        {
            "id": "unlocked_destination",
            "fromNodeID": "hub",
            "toNodeID": "destination",
            "availabilityRule": {
                "requiredCompletedObjectiveIDs": ["inspect"],
                "minimumObjectiveIndex": 1,
            },
        },
        {"id": "return_hub", "fromNodeID": "checkpoint", "toNodeID": "hub"},
    ]
    objectives = [
        _objective("inspect", "checkpoint", "checkpoint", 0, "always"),
        _objective("finish", "destination", "destination", 1),
    ]

    result = RuntimeSimulator().simulate(
        _level(nodes, edges, objectives, package="checkpoint")
    )

    assert result.state.outcome == LevelOutcome.COMPLETED
    assert result.state.runtime_graph.edge_usage_counts == {
        "to_hub": 1,
        "one_use_checkpoint": 1,
        "return_hub": 1,
        "unlocked_destination": 1,
    }
    assert result.state.visited_node_ids == [
        "start", "hub", "checkpoint", "hub", "destination",
    ]


def test_objective_road_rule_checks_required_forbidden_index_and_usage_state():
    nodes = [
        {"id": "start", "x": 0.0, "y": 0.0, "outgoingEdgeIDs": ["conditioned", "fallback"]},
        {"id": "checkpoint", "x": 1.0, "y": 0.0, "outgoingEdgeIDs": []},
        {"id": "destination", "x": 2.0, "y": 0.0, "outgoingEdgeIDs": []},
    ]
    edges = [
        {
            "id": "conditioned",
            "fromNodeID": "start",
            "toNodeID": "destination",
            "availabilityRule": {
                "requiredCompletedObjectiveIDs": ["inspect"],
                "forbiddenCompletedObjectiveIDs": ["finish"],
                "minimumObjectiveIndex": 1,
                "maximumObjectiveIndex": 2,
                "usageLimit": 1,
            },
        },
        {"id": "fallback", "fromNodeID": "start", "toNodeID": "checkpoint"},
    ]
    objectives = [
        _objective("inspect", "checkpoint", "checkpoint", 0, "always"),
        _objective("finish", "destination", "destination", 1),
    ]
    state = RuntimeState.initialize(
        _level(nodes, edges, objectives, package="checkpoint")
    )
    edge = state.runtime_graph.index.edges_by_id["conditioned"]

    assert not state.runtime_graph.edge_is_usable(edge, set(), 1)
    assert state.runtime_graph.edge_is_usable(edge, {"inspect"}, 1)
    assert not state.runtime_graph.edge_is_usable(edge, {"inspect", "finish"}, 1)
    assert not state.runtime_graph.edge_is_usable(edge, {"inspect"}, 0)
    state.runtime_graph.record_edge_traversal("conditioned")
    assert not state.runtime_graph.edge_is_usable(edge, {"inspect"}, 1)
