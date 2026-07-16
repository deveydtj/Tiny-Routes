from __future__ import annotations

import json
from pathlib import Path

import pytest

from tiny_routes_core.models import LevelDocument, SolutionAction
from tiny_routes_core.simulation import (
    LevelOutcome,
    RuntimeSimulator,
    RuntimeState,
    SwitchEligibilityReason,
    switch_eligibility,
)


FIXTURES = Path(__file__).parents[3] / "SharedFixtures" / "RuntimeParity"


def _load(fixture_id: str):
    directory = FIXTURES / fixture_id
    level = LevelDocument.from_dict(json.loads((directory / "level.json").read_text()))
    events = json.loads((directory / "events.json").read_text())
    expected = json.loads((directory / "expected.json").read_text())
    actions = [SolutionAction.from_dict(item) for item in events["actions"]]
    return level, actions, expected


@pytest.mark.parametrize("offset,expected_reason", [
    (-1e-6, SwitchEligibilityReason.OUTSIDE_LOOKAHEAD_WINDOW),
    (0.0, SwitchEligibilityReason.ELIGIBLE),
    (1e-6, SwitchEligibilityReason.ELIGIBLE),
])
def test_eligibility_boundary(offset, expected_reason):
    level, _, _ = _load("two_way_inside_window")
    state = RuntimeState.initialize(level)
    # The switch is one distance unit away at speed one. Set the window around it.
    object.__setattr__(state.rules, "switch_lookahead_seconds", 1.0 + offset)
    assert switch_eligibility(state).reason == expected_reason


@pytest.mark.parametrize("fixture_id", [
    "straight_no_switch", "two_way_too_early", "two_way_inside_window",
    "noneligible_downstream_switch", "tap_after_commitment", "three_way_two_rotations",
    "four_way_three_rotations", "revisit_different_state", "package_before_destination",
    "destination_before_package", "dead_end_failure", "time_limit_failure",
    "cycle_safety_limit", "package_gate_normalization",
    "package_gate_revisit_rotation",
])
def test_shared_runtime_parity_fixture(fixture_id):
    level, actions, expected = _load(fixture_id)
    # Golden scripts were authored at the fixture replay speed of 0.6 units/second.
    simulator = RuntimeSimulator(speed=0.6, maximum_step_count=expected["safetyStepLimit"])
    result = simulator.simulate(level, actions)

    actual_outcome = "completed" if result.state.outcome == LevelOutcome.COMPLETED else "failed"
    assert actual_outcome == expected["expectedOutcome"]
    assert result.failure_reason == expected["failureReason"]
    assert result.state.accepted_tap_count == expected["acceptedTapCount"]
    assert result.state.package_collected == expected["reachedPackage"]
    assert (result.state.outcome == LevelOutcome.COMPLETED) == expected["reachedDestination"]
    assert result.safety_step_limit == expected["safetyStepLimit"]
    if "finalActiveEdgeIDs" in expected:
        assert result.state.switch_active_edge_ids == expected["finalActiveEdgeIDs"]


def test_simulation_is_deterministic():
    level, actions, _ = _load("three_way_two_rotations")
    first = RuntimeSimulator().simulate(level, actions)
    second = RuntimeSimulator().simulate(level, actions)
    assert first.events == second.events
    assert first.taps == second.taps
    assert first.state == second.state
