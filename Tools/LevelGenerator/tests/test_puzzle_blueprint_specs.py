from __future__ import annotations

import pytest

from app.models import ObjectiveSpec, StateTransitionSpec


def test_objective_spec_preserves_graph_independent_phase_intent() -> None:
    objective = ObjectiveSpec(
        id="pickup_a",
        kind="PICKUP",
        sequence_index=1,
        phase_entry_role="approach_pickup_a",
        phase_exit_role="leave_pickup_a",
        reveal_policy="whenActive",
    )

    assert objective.kind == "pickup"
    assert objective.sequence_index == 1
    assert objective.phase_entry_role == "approach_pickup_a"
    assert objective.phase_exit_role == "leave_pickup_a"
    assert objective.is_terminal is False


def test_objective_spec_identifies_terminal_destination() -> None:
    objective = ObjectiveSpec(
        id="destination",
        kind="destination",
        sequence_index=3,
        phase_entry_role="destination_approach",
        phase_exit_role="level_complete",
    )

    assert objective.is_terminal is True


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"id": ""}, "id must not be empty"),
        ({"kind": "bonus"}, "kind must be one of"),
        ({"sequence_index": -1}, "non-negative integer"),
        ({"reveal_policy": "random"}, "reveal_policy must be one of"),
    ],
)
def test_objective_spec_rejects_invalid_intent(overrides, message: str) -> None:
    values = {
        "id": "pickup_a",
        "kind": "pickup",
        "sequence_index": 0,
        "phase_entry_role": "pickup_entry",
        "phase_exit_role": "pickup_exit",
    }
    values.update(overrides)

    with pytest.raises(ValueError, match=message):
        ObjectiveSpec(**values)


def test_state_transition_spec_models_visible_objective_and_route_effects() -> None:
    transition = StateTransitionSpec(
        id="pickup_opens_return",
        from_phase_index=0,
        to_phase_index=1,
        trigger_objective_id="pickup_a",
        required_completed_objective_ids=("checkpoint_a",),
        revealed_objective_ids=("destination",),
        opened_edge_roles=("return_shortcut",),
        closed_edge_roles=("outbound_only",),
    )

    assert transition.trigger_objective_id == "pickup_a"
    assert transition.trigger_decision_id is None
    assert transition.changes_route_state is True


def test_state_transition_spec_requires_one_trigger_and_forward_phase_progress() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        StateTransitionSpec(id="invalid", from_phase_index=0, to_phase_index=1)

    with pytest.raises(ValueError, match="greater than"):
        StateTransitionSpec(
            id="invalid",
            from_phase_index=1,
            to_phase_index=1,
            trigger_objective_id="pickup_a",
        )


def test_state_transition_spec_rejects_conflicting_edge_effects() -> None:
    with pytest.raises(ValueError, match="both opened and closed"):
        StateTransitionSpec(
            id="invalid",
            from_phase_index=0,
            to_phase_index=1,
            trigger_decision_id="choose_return",
            opened_edge_roles=("return",),
            closed_edge_roles=("return",),
        )
