from __future__ import annotations

from dataclasses import replace

from app.models import (
    PuzzleState,
    PuzzleTerminalOutcome,
    StrategyAction,
    StrategyCost,
    StrategyStateTransition,
    StrategyTrace,
)
from app.services import StrategyEquivalenceService


def _successful_trace(*actions: StrategyAction) -> StrategyTrace:
    final_state = PuzzleState(
        current_node_id="destination",
        current_edge_id=None,
        objective_index=1,
        completed_objective_ids=("destination",),
        available_edge_ids=(),
        visit_counts=(("destination", 1),),
        accepted_tap_count=1,
        terminal_outcome=PuzzleTerminalOutcome.SUCCESS,
    )
    return StrategyTrace(
        actions=actions,
        cost=StrategyCost(1, 4.0, 4.0),
        final_state=final_state,
        outcome_code="success",
    )


def test_classifier_ignores_pass_through_and_noop_trace_noise() -> None:
    pass_through = StrategyAction(
        node_id="start",
        selected_edge_id="only_road",
        tap_count=9,
        traversed_edge_ids=("only_road",),
        visited_node_ids=("switch",),
        meaningful_decision=False,
    )
    state_change = StrategyStateTransition(
        objective_index_before=0,
        objective_index_after=1,
        completed_objective_ids=("destination",),
    )
    decision = StrategyAction(
        node_id="switch",
        selected_edge_id="winning_road",
        tap_count=1,
        traversed_edge_ids=("winning_road",),
        visited_node_ids=("destination",),
        completed_objective_ids=("destination",),
        meaningful_decision=True,
        state_transition=state_change,
    )
    direct = _successful_trace(decision)
    noisy = _successful_trace(pass_through, decision)

    classes = StrategyEquivalenceService().classify((noisy, direct))

    assert len(classes) == 1
    assert classes[0].member_count == 2
    assert classes[0].key.meaningful_decisions == ((0, "switch", "winning_road"),)
    assert classes[0].key.objective_sequence == ("destination",)


def test_classifier_preserves_distinct_meaningful_road_choices() -> None:
    transition = StrategyStateTransition(
        objective_index_before=0,
        objective_index_after=1,
        completed_objective_ids=("destination",),
    )
    first_action = StrategyAction(
        node_id="switch",
        selected_edge_id="upper",
        tap_count=1,
        traversed_edge_ids=("upper",),
        visited_node_ids=("destination",),
        completed_objective_ids=("destination",),
        meaningful_decision=True,
        state_transition=transition,
    )
    first = _successful_trace(first_action)
    second = replace(
        first,
        actions=(replace(first_action, selected_edge_id="lower", traversed_edge_ids=("lower",)),),
    )

    assert len(StrategyEquivalenceService().classify((first, second))) == 2
    assert not StrategyEquivalenceService().are_equivalent(first, second)
