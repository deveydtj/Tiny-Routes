from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from app.models import (
    AlternateSuccessKind,
    MeaningfulChoiceOutcomeKind,
    PuzzleState,
    PuzzleTerminalOutcome,
    StrategyAction,
    StrategyCost,
    StrategySearchResult,
    StrategyStateTransition,
    StrategyTrace,
)
from app.services import (
    AlternateSuccessClassificationService,
    FailureRecoveryClassificationService,
    StrategySearchService,
)


def _minimal_level() -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "alternate_success_fixture",
            "name": "Alternate Success Fixture",
            "startNodeID": "start",
            "packageNodeID": "destination",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 30,
            "parTaps": 1,
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
                        "outgoingEdgeIDs": ["optimal", "equal", "slower", "higher_tap"],
                    },
                    {"id": "destination", "x": 0, "y": 1, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": edge_id, "fromNodeID": "start", "toNodeID": "destination"}
                    for edge_id in ("optimal", "equal", "slower", "higher_tap")
                ],
            },
        }
    )


def _success(edge_id: str, cost: StrategyCost) -> StrategyTrace:
    final_state = PuzzleState(
        current_node_id="destination",
        current_edge_id=None,
        objective_index=1,
        completed_objective_ids=("destination",),
        terminal_outcome=PuzzleTerminalOutcome.SUCCESS,
    )
    transition = StrategyStateTransition(
        objective_index_before=0,
        objective_index_after=1,
        completed_objective_ids=("destination",),
    )
    return StrategyTrace(
        actions=(
            StrategyAction(
                node_id="start",
                selected_edge_id=edge_id,
                tap_count=cost.accepted_taps,
                traversed_edge_ids=(edge_id,),
                visited_node_ids=("destination",),
                completed_objective_ids=("destination",),
                meaningful_decision=True,
                state_transition=transition,
            ),
        ),
        cost=cost,
        final_state=final_state,
        outcome_code="success",
    )


def test_alternate_successes_are_classified_by_locked_cost_order() -> None:
    optimal = _success("optimal", StrategyCost(1, 2, 2))
    equal = _success("equal", StrategyCost(1, 2, 2))
    slower = _success("slower", StrategyCost(1, 3, 3))
    higher_tap = _success("higher_tap", StrategyCost(2, 1, 1))
    search_result = StrategySearchResult(
        optimal_cost=optimal.cost,
        canonical_optimal_strategy=optimal,
        equal_cost_optimal_strategies=(optimal, equal),
        near_optimal_strategies=(slower, higher_tap),
        longer_successful_strategies=(),
        failure_outcomes=(),
        explored_state_count=1,
        exhaustive=True,
    )

    report = AlternateSuccessClassificationService().classify(
        _minimal_level(),
        search_result,
    )

    assert report.exhaustive
    assert {
        item.strategy_class.canonical_trace.actions[0].selected_edge_id: item.kind
        for item in report.classifications
    } == {
        "equal": AlternateSuccessKind.EQUAL_COST_ROUTE,
        "slower": AlternateSuccessKind.SUCCESSFUL_SLOWER_ROUTE,
        "higher_tap": AlternateSuccessKind.SUCCESSFUL_HIGHER_TAP_ROUTE,
    }
    higher_tap_result = next(
        item
        for item in report.classifications
        if item.kind is AlternateSuccessKind.SUCCESSFUL_HIGHER_TAP_ROUTE
    )
    assert higher_tap_result.accepted_tap_delta == 1
    assert higher_tap_result.travel_time_delta_seconds == -1


def _failure_recovery_level() -> LevelDocument:
    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": "failure_recovery_fixture",
            "name": "Failure Recovery Fixture",
            "startNodeID": "start",
            "packageNodeID": "pickup",
            "destinationNodeID": "destination",
            "timeLimitSeconds": 60,
            "parTaps": 0,
            "objectives": [
                {
                    "id": "pickup",
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
                    "revealPolicy": "always",
                },
            ],
            "graph": {
                "nodes": [
                    {
                        "id": "start",
                        "x": 0,
                        "y": 0,
                        "outgoingEdgeIDs": [
                            "optimal",
                            "dead_choice",
                            "early_destination",
                            "detour",
                            "loop_choice",
                            "trap_choice",
                        ],
                    },
                    {"id": "pickup", "x": 1, "y": 0, "outgoingEdgeIDs": ["to_hub"]},
                    {
                        "id": "hub",
                        "x": 2,
                        "y": 0,
                        "outgoingEdgeIDs": ["finish", "hub_dead_choice"],
                    },
                    {
                        "id": "detour_mid",
                        "x": 0,
                        "y": 1,
                        "outgoingEdgeIDs": ["detour_to_pickup"],
                    },
                    {"id": "loop", "x": 0, "y": 2, "outgoingEdgeIDs": ["loop_again"]},
                    {
                        "id": "trap",
                        "x": -1,
                        "y": 0,
                        "outgoingEdgeIDs": ["trap_left", "trap_right"],
                    },
                    {"id": "dead", "x": -2, "y": 0, "outgoingEdgeIDs": []},
                    {"id": "dead_two", "x": -2, "y": 1, "outgoingEdgeIDs": []},
                    {"id": "destination", "x": 3, "y": 0, "outgoingEdgeIDs": []},
                ],
                "edges": [
                    {"id": "optimal", "fromNodeID": "start", "toNodeID": "pickup"},
                    {"id": "dead_choice", "fromNodeID": "start", "toNodeID": "dead"},
                    {
                        "id": "early_destination",
                        "fromNodeID": "start",
                        "toNodeID": "destination",
                    },
                    {"id": "detour", "fromNodeID": "start", "toNodeID": "detour_mid"},
                    {
                        "id": "detour_to_pickup",
                        "fromNodeID": "detour_mid",
                        "toNodeID": "pickup",
                    },
                    {"id": "loop_choice", "fromNodeID": "start", "toNodeID": "loop"},
                    {"id": "loop_again", "fromNodeID": "loop", "toNodeID": "loop"},
                    {"id": "trap_choice", "fromNodeID": "start", "toNodeID": "trap"},
                    {"id": "trap_left", "fromNodeID": "trap", "toNodeID": "dead"},
                    {"id": "trap_right", "fromNodeID": "trap", "toNodeID": "dead_two"},
                    {"id": "to_hub", "fromNodeID": "pickup", "toNodeID": "hub"},
                    {"id": "finish", "fromNodeID": "hub", "toNodeID": "destination"},
                    {"id": "hub_dead_choice", "fromNodeID": "hub", "toNodeID": "dead"},
                ],
            },
        }
    )


def test_failure_and_recovery_report_classifies_each_non_optimal_choice() -> None:
    level = _failure_recovery_level()
    search_result = StrategySearchService().search(level)

    report = FailureRecoveryClassificationService().classify(level, search_result)

    assert search_result.exhaustive
    assert report.exhaustive
    by_choice = {
        (item.key.node_id, item.key.selected_edge_id): item
        for item in report.classifications
    }
    assert by_choice[("start", "dead_choice")].kind is (
        MeaningfulChoiceOutcomeKind.IMMEDIATE_DEAD_END
    )
    assert by_choice[("start", "early_destination")].kind is (
        MeaningfulChoiceOutcomeKind.OBJECTIVE_ORDER_FAILURE
    )
    assert by_choice[("start", "detour")].kind is (
        MeaningfulChoiceOutcomeKind.RECOVERABLE_DETOUR
    )
    assert by_choice[("start", "detour")].rejoins_optimal_route
    assert by_choice[("start", "loop_choice")].kind is (
        MeaningfulChoiceOutcomeKind.LOOP_UNTIL_TIME_EXPIRES
    )
    assert by_choice[("start", "trap_choice")].kind is (
        MeaningfulChoiceOutcomeKind.STATE_TRAP
    )
    assert by_choice[("hub", "hub_dead_choice")].kind is (
        MeaningfulChoiceOutcomeKind.IMMEDIATE_DEAD_END
    )
