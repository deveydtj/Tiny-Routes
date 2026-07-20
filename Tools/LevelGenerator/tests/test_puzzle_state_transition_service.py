from __future__ import annotations

import pytest

from tiny_routes_core.models import LevelDocument

from app.models import PuzzleTerminalOutcome
from app.services import PuzzleStateTransitionError, PuzzleStateTransitionService


def _stateful_level() -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "structural_fixture",
            "name": "Structural Fixture",
            "startNodeID": "start",
            "packageNodeID": "pickup",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 60,
            "parTaps": 1,
            "objectives": [
                {
                    "id": "pickup_a",
                    "nodeID": "pickup",
                    "kind": "pickup",
                    "sequenceIndex": 0,
                    "revealPolicy": "always",
                },
                {
                    "id": "destination",
                    "nodeID": "destination",
                    "kind": "destination",
                    "sequenceIndex": 1,
                    "revealPolicy": "whenActive",
                },
            ],
            "graph": {
                "nodes": [
                    {"id": "start", "x": 0, "y": 0, "outgoingEdgeIDs": ["start_hub"]},
                    {
                        "id": "hub",
                        "x": 1,
                        "y": 0,
                        "outgoingEdgeIDs": ["hub_pickup", "hub_dead", "hub_destination"],
                    },
                    {"id": "pickup", "x": 2, "y": 0, "outgoingEdgeIDs": ["pickup_hub"]},
                    {"id": "dead", "x": 1, "y": -1, "outgoingEdgeIDs": []},
                    {"id": "destination", "x": 1, "y": 1, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "start_hub", "fromNodeID": "start", "toNodeID": "hub"},
                    {
                        "id": "hub_pickup",
                        "fromNodeID": "hub",
                        "toNodeID": "pickup",
                        "availabilityRule": {"forbiddenCompletedObjectiveIDs": ["pickup_a"]},
                    },
                    {"id": "hub_dead", "fromNodeID": "hub", "toNodeID": "dead"},
                    {
                        "id": "hub_destination",
                        "fromNodeID": "hub",
                        "toNodeID": "destination",
                        "availabilityRule": {"requiredCompletedObjectiveIDs": ["pickup_a"]},
                    },
                    {
                        "id": "pickup_hub",
                        "fromNodeID": "pickup",
                        "toNodeID": "hub",
                        "availabilityRule": {"usageLimit": 1},
                    },
                ],
            },
        }
    )


def test_transition_collapses_pass_through_motion_and_applies_objective_state() -> None:
    level = _stateful_level()
    service = PuzzleStateTransitionService()
    initial = service.initial_state(level)

    at_hub = service.apply_decision(level, initial, "start_hub")
    assert at_hub.visited_node_ids == ("hub",)
    assert at_hub.state.current_node_id == "hub"
    assert [choice.selected_edge_id for choice in service.available_decisions(level, at_hub.state)] == [
        "hub_pickup",
        "hub_dead",
    ]

    revisited = service.apply_decision(level, at_hub.state, "hub_pickup")
    assert revisited.traversed_edge_ids == ("hub_pickup", "pickup_hub")
    assert revisited.visited_node_ids == ("pickup", "hub")
    assert revisited.completed_objective_ids == ("pickup_a",)
    assert revisited.state.objective_index == 1
    assert revisited.state.visit_count_map["hub"] == 2
    assert revisited.state.consumed_edge_ids == ("pickup_hub",)
    assert "hub_pickup" not in revisited.state.available_edge_ids
    assert "hub_destination" in revisited.state.available_edge_ids
    assert revisited.state.active_switch_map["hub"] == "hub_dead"

    completed = service.apply_decision(level, revisited.state, "hub_destination")
    assert completed.decision.tap_count == 1
    assert completed.state.accepted_tap_count == 1
    assert completed.state.terminal_outcome is PuzzleTerminalOutcome.SUCCESS
    assert completed.completed_objective_ids == ("destination",)


def test_transition_reports_dead_end_and_rejects_unavailable_roads() -> None:
    level = _stateful_level()
    service = PuzzleStateTransitionService()
    at_hub = service.apply_decision(level, service.initial_state(level), "start_hub")

    failed = service.apply_decision(level, at_hub.state, "hub_dead")
    assert failed.state.terminal_outcome is PuzzleTerminalOutcome.FAILURE
    assert failed.failure_reason == "structural_dead_end"

    with pytest.raises(PuzzleStateTransitionError) as error:
        service.apply_decision(level, at_hub.state, "hub_destination")
    assert error.value.code == "structural_edge_not_selectable"
