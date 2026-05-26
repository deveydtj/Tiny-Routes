from __future__ import annotations

from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.python_solution_simulator_service import PythonSolutionSimulatorService
from app.templates.package_gate_template import PackageGateTemplate
from app.templates.single_switch_template import SingleSwitchTemplate


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
