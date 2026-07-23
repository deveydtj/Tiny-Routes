from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from app.services import StrategySearchService


def _branch_level(*, lower_y: float = -1.0, lower_destination: str = "destination") -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "decision_consequence_fixture",
            "name": "Decision Consequence Fixture",
            "startNodeID": "start",
            "packageNodeID": "destination",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 30,
            "parTaps": 0,
            "objectives": [
                {
                    "id": "destination",
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
                        "outgoingEdgeIDs": ["upper", "lower"],
                    },
                    {
                        "id": "upper_mid",
                        "x": 1,
                        "y": 1,
                        "outgoingEdgeIDs": ["upper_finish"],
                    },
                    {
                        "id": "lower_mid",
                        "x": 1,
                        "y": lower_y,
                        "outgoingEdgeIDs": ["lower_finish"],
                    },
                    {"id": "dead", "x": 2, "y": lower_y, "outgoingEdgeIDs": []},
                    {"id": "destination", "x": 2, "y": 0, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "upper", "fromNodeID": "start", "toNodeID": "upper_mid"},
                    {
                        "id": "upper_finish",
                        "fromNodeID": "upper_mid",
                        "toNodeID": "destination",
                    },
                    {"id": "lower", "fromNodeID": "start", "toNodeID": "lower_mid"},
                    {
                        "id": "lower_finish",
                        "fromNodeID": "lower_mid",
                        "toNodeID": lower_destination,
                    },
                ],
            },
        }
    )


def _first_action(level: LevelDocument):
    result = StrategySearchService().search(level)
    assert result.canonical_optimal_strategy is not None
    return result.canonical_optimal_strategy.actions[0]


def test_equal_decorative_split_does_not_count_as_a_decision() -> None:
    action = _first_action(_branch_level())

    assert action.meaningful_decision is False
    assert action.consequence_evidence is not None
    assert action.consequence_evidence.distinct_consequence_count == 1
    assert action.consequence_evidence.equivalent_choice_count == 1
    assert action.consequence_evidence.differing_dimensions == ()


def test_route_cost_difference_is_a_material_decision_consequence() -> None:
    action = _first_action(_branch_level(lower_y=-2.0))

    assert action.meaningful_decision is True
    assert action.consequence_evidence is not None
    assert "route_cost" in action.consequence_evidence.differing_dimensions
    assert action.consequence_evidence.equivalent_choice_count == 0


def test_failure_risk_and_recoverability_are_material_consequences() -> None:
    action = _first_action(_branch_level(lower_destination="dead"))

    assert action.meaningful_decision is True
    assert action.consequence_evidence is not None
    assert "risk" in action.consequence_evidence.differing_dimensions
    assert "recoverability" in action.consequence_evidence.differing_dimensions

