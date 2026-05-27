from __future__ import annotations

from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.python_solution_simulator_service import PythonSolutionSimulatorService
from app.templates.package_gate_template import PackageGateTemplate
from app.templates.four_way_intersection_template import FourWayIntersectionTemplate
from app.templates.single_switch_template import SingleSwitchTemplate
from .late_tap_chain_fixture import (
    build_late_tap_chain_generated_level,
    late_tap_chain_new_times,
    late_tap_chain_old_times,
)


def test_python_solution_simulator_completes_generated_solution() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = PackageGateTemplate().generate("level_012", 12, preset, RandomSource(3))

    result = PythonSolutionSimulatorService().simulate(generated)

    assert result.passed is True
    assert result.reached_package is True
    assert result.reached_destination is True
    assert result.tap_count == len(generated.solution.actions)


def test_python_solution_simulator_fails_when_required_tap_is_missing() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(2))
    generated.solution.actions = []

    result = PythonSolutionSimulatorService().simulate(generated)

    assert result.passed is False
    assert result.failure_reason in {"dead_end", "time_expired"}


def test_python_solution_simulator_records_four_way_switch_timeline_details() -> None:
    preset = DifficultyService().get_preset("expert")
    generated = FourWayIntersectionTemplate().generate("level_099", 99, preset, RandomSource(3))

    result = PythonSolutionSimulatorService().simulate(generated)

    tap_steps = [step for step in result.steps if step.event == "tap_switch"]
    assert result.passed is True
    assert len(tap_steps) == 2
    assert "previousEdge=" in tap_steps[0].detail
    assert "blockedBecauseCurrentEdgeStartsAtTappedNode=false" in tap_steps[0].detail


def test_python_solution_simulator_rejects_late_switch_tap_after_runtime_commitment() -> None:
    simulator = PythonSolutionSimulatorService()

    late_result = simulator.simulate(build_late_tap_chain_generated_level(late_tap_chain_old_times()))
    early_result = simulator.simulate(build_late_tap_chain_generated_level(late_tap_chain_new_times()))

    assert late_result.passed is False
    assert late_result.failure_reason == "tap_ignored_current_edge"
    late_tap_steps = [step for step in late_result.steps if step.event == "tap_switch"]
    assert late_tap_steps[1].node_id == "switch_b"
    assert "blockedBecauseCurrentEdgeStartsAtTappedNode=true" in late_tap_steps[1].detail
    assert early_result.passed is True
