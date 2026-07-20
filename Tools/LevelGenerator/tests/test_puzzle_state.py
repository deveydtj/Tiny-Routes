from __future__ import annotations

from dataclasses import replace

import pytest

from app.models import PuzzleState, PuzzleTerminalOutcome


def test_initial_state_is_compact_hashable_and_tracks_start_visit() -> None:
    state = PuzzleState.initial(
        start_node_id="start",
        available_edge_ids=("edge_b", "edge_a"),
        active_switch_edge_ids=(("hub", "edge_b"),),
    )

    assert state.current_node_id == "start"
    assert state.current_edge_id is None
    assert state.available_edge_ids == ("edge_a", "edge_b")
    assert state.active_switch_map == {"hub": "edge_b"}
    assert state.visit_count_map == {"start": 1}
    assert hash(state) == hash(replace(state))


def test_equivalent_unordered_inputs_produce_the_same_canonical_state() -> None:
    first = PuzzleState(
        current_node_id=None,
        current_edge_id="edge_active",
        objective_index=2,
        completed_objective_ids=("pickup_b", "pickup_a"),
        available_edge_ids=("edge_c", "edge_active", "edge_b"),
        consumed_edge_ids=("edge_a",),
        active_switch_edge_ids=(("switch_b", "edge_c"), ("switch_a", "edge_b")),
        visit_counts=(("hub", 2), ("start", 1)),
        accepted_tap_count=3,
        elapsed_time_seconds=4,
    )
    second = PuzzleState(
        current_node_id=None,
        current_edge_id="edge_active",
        objective_index=2,
        completed_objective_ids=("pickup_a", "pickup_b"),
        available_edge_ids=("edge_b", "edge_c", "edge_active"),
        consumed_edge_ids=("edge_a",),
        active_switch_edge_ids=(("switch_a", "edge_b"), ("switch_b", "edge_c")),
        visit_counts=(("start", 1), ("hub", 2)),
        accepted_tap_count=3,
        elapsed_time_seconds=4.0,
    )

    assert first == second
    assert hash(first) == hash(second)


def test_state_tracks_objectives_usage_switches_visits_cost_and_outcome() -> None:
    state = PuzzleState.initial(
        start_node_id="start",
        available_edge_ids=("outbound", "return"),
        active_switch_edge_ids=(("hub", "outbound"),),
    )
    completed = state.evolve(
        current_node_id="destination",
        objective_index=1,
        completed_objective_ids=("pickup",),
        available_edge_ids=("return",),
        consumed_edge_ids=("outbound",),
        active_switch_edge_ids=(("hub", "return"),),
        visit_counts=(("start", 1), ("hub", 2), ("destination", 1)),
        accepted_tap_count=2,
        elapsed_time_seconds=8.25,
        terminal_outcome=PuzzleTerminalOutcome.SUCCESS,
    )

    assert completed.is_terminal
    assert completed.terminal_outcome is PuzzleTerminalOutcome.SUCCESS
    assert completed.accepted_tap_count == 2
    assert completed.elapsed_time_seconds == 8.25
    assert state.terminal_outcome is PuzzleTerminalOutcome.ACTIVE


@pytest.mark.parametrize(
    "changes, message",
    (
        ({"current_node_id": "node", "current_edge_id": "edge"}, "exactly one"),
        ({"current_node_id": None, "current_edge_id": None}, "exactly one"),
        (
            {"available_edge_ids": ("edge",), "consumed_edge_ids": ("edge",)},
            "both available and consumed",
        ),
        (
            {"available_edge_ids": (), "active_switch_edge_ids": (("hub", "edge"),)},
            "active switch edges must be available",
        ),
        (
            {"objective_index": 1, "completed_objective_ids": ()},
            "objective_index must equal",
        ),
        ({"visit_counts": (("start", 0),)}, "omit zero"),
    ),
)
def test_invalid_or_noncanonical_state_is_rejected(changes, message) -> None:
    values = {
        "current_node_id": "start",
        "current_edge_id": None,
        "objective_index": 0,
        "available_edge_ids": ("edge",),
        "active_switch_edge_ids": (("hub", "edge"),),
        "visit_counts": (("start", 1),),
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        PuzzleState(**values)
