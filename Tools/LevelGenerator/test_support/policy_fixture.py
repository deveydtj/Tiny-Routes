"""Shared structural policy fixture with a genuine two-decision dependency."""

from tiny_routes_core.models import LevelDocument


def two_step_policy_level() -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "policy_evaluation_fixture",
            "name": "Policy Evaluation Fixture",
            "startNodeID": "start",
            "packageNodeID": "destination",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 30,
            "parTaps": 1,
            "objectives": [
                {
                    "id": "destination_objective",
                    "nodeID": "destination",
                    "kind": "destination",
                    "sequenceIndex": 0,
                    "revealPolicy": "always",
                }
            ],
            "graph": {
                "nodes": [
                    {
                        "id": "start",
                        "x": 0,
                        "y": 0,
                        "outgoingEdgeIDs": ["tempting", "planned"],
                    },
                    {
                        "id": "near_junction",
                        "x": 8,
                        "y": 0,
                        "outgoingEdgeIDs": ["near_trap_a", "near_trap_b"],
                    },
                    {
                        "id": "far_junction",
                        "x": 4,
                        "y": 4,
                        "outgoingEdgeIDs": ["finish", "far_trap"],
                    },
                    {"id": "dead_a", "x": 9, "y": 1, "outgoingEdgeIDs": []},
                    {"id": "dead_b", "x": 9, "y": -1, "outgoingEdgeIDs": []},
                    {"id": "dead_c", "x": 5, "y": 5, "outgoingEdgeIDs": []},
                    {"id": "destination", "x": 10, "y": 0, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "tempting", "fromNodeID": "start", "toNodeID": "near_junction"},
                    {"id": "planned", "fromNodeID": "start", "toNodeID": "far_junction"},
                    {"id": "near_trap_a", "fromNodeID": "near_junction", "toNodeID": "dead_a"},
                    {"id": "near_trap_b", "fromNodeID": "near_junction", "toNodeID": "dead_b"},
                    {"id": "finish", "fromNodeID": "far_junction", "toNodeID": "destination"},
                    {"id": "far_trap", "fromNodeID": "far_junction", "toNodeID": "dead_c"},
                ],
            },
        }
    )


def deep_policy_level(*, multi_stop: bool) -> LevelDocument:
    """Build a choice whose benefit appears beyond two local transitions."""

    objectives = []
    if multi_stop:
        objectives.append(
            {
                "id": "pickup_objective",
                "nodeID": "pickup",
                "kind": "pickup",
                "sequenceIndex": 0,
                "revealPolicy": "always",
            }
        )
    objectives.append(
        {
            "id": "destination_objective",
            "nodeID": "destination",
            "kind": "destination",
            "sequenceIndex": len(objectives),
            "revealPolicy": "always",
        }
    )
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "cross_phase_fixture" if multi_stop else "objective_state_fixture",
            "name": "Deep Policy Fixture",
            "startNodeID": "start",
            "packageNodeID": "pickup" if multi_stop else "destination",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 60,
            "parTaps": 1,
            "objectives": objectives,
            "graph": {
                "nodes": [
                    {"id": "start", "x": 0, "y": 0, "outgoingEdgeIDs": ["tempting", "planned"]},
                    {"id": "near_one", "x": 8, "y": 0, "outgoingEdgeIDs": ["near_advance", "near_trap"]},
                    {"id": "near_two", "x": 9, "y": 0, "outgoingEdgeIDs": ["near_dead_a", "near_dead_b"]},
                    {"id": "far_one", "x": 1, "y": 5, "outgoingEdgeIDs": ["far_advance", "far_trap"]},
                    {"id": "far_two", "x": 5, "y": 5, "outgoingEdgeIDs": ["collect", "far_dead"]},
                    {"id": "pickup", "x": 10, "y": 0, "outgoingEdgeIDs": ["to_finish_hub"]},
                    {"id": "finish_hub", "x": 11, "y": 0, "outgoingEdgeIDs": ["finish", "finish_trap"]},
                    {"id": "destination", "x": 12, "y": 0, "outgoingEdgeIDs": []},
                    {"id": "dead_a", "x": 10, "y": 1, "outgoingEdgeIDs": []},
                    {"id": "dead_b", "x": 10, "y": -1, "outgoingEdgeIDs": []},
                    {"id": "dead_c", "x": 8, "y": 2, "outgoingEdgeIDs": []},
                    {"id": "dead_d", "x": 4, "y": 7, "outgoingEdgeIDs": []},
                    {"id": "dead_e", "x": 6, "y": 7, "outgoingEdgeIDs": []},
                    {"id": "dead_f", "x": 11, "y": 2, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "tempting", "fromNodeID": "start", "toNodeID": "near_one"},
                    {"id": "planned", "fromNodeID": "start", "toNodeID": "far_one"},
                    {"id": "near_advance", "fromNodeID": "near_one", "toNodeID": "near_two"},
                    {"id": "near_trap", "fromNodeID": "near_one", "toNodeID": "dead_c"},
                    {"id": "near_dead_a", "fromNodeID": "near_two", "toNodeID": "dead_a"},
                    {"id": "near_dead_b", "fromNodeID": "near_two", "toNodeID": "dead_b"},
                    {"id": "far_advance", "fromNodeID": "far_one", "toNodeID": "far_two"},
                    {"id": "far_trap", "fromNodeID": "far_one", "toNodeID": "dead_d"},
                    {"id": "collect", "fromNodeID": "far_two", "toNodeID": "pickup"},
                    {"id": "far_dead", "fromNodeID": "far_two", "toNodeID": "dead_e"},
                    {"id": "to_finish_hub", "fromNodeID": "pickup", "toNodeID": "finish_hub"},
                    {"id": "finish", "fromNodeID": "finish_hub", "toNodeID": "destination"},
                    {"id": "finish_trap", "fromNodeID": "finish_hub", "toNodeID": "dead_f"},
                ],
            },
        }
    )
