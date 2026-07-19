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
