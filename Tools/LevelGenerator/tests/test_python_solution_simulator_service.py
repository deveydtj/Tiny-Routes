from __future__ import annotations

import pytest

from app.random_source import RandomSource
from app.level_editor_imports import LevelDocument, RouteEdgeModel, RouteGraphModel, RouteNodeModel, SolutionActionModel, SolutionModel
from app.models.generated_level import GeneratedLevel
from app.services.difficulty_service import DifficultyService
from app.services.python_solution_simulator_service import PythonSolutionSimulatorService
from app.services.route_timing_service import RouteTimingService
from app.templates.package_gate_template import PackageGateTemplate
from app.templates.four_way_intersection_template import FourWayIntersectionTemplate
from app.templates.return_loop_template import ReturnLoopTemplate
from app.templates.ring_route_template import RingRouteTemplate
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


def test_python_solution_simulator_arrival_time_for_repeated_switch_tap_uses_next_visit() -> None:
    preset = DifficultyService().get_preset("expert")
    generated = FourWayIntersectionTemplate().generate("level_099", 99, preset, RandomSource(4))
    simulator = PythonSolutionSimulatorService()

    assert simulator.arrival_time_for_action(generated, 0) == pytest.approx(1.05, abs=0.001)
    assert simulator.arrival_time_for_action(generated, 1) == pytest.approx(3.378, abs=0.001)


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


def test_python_solution_simulator_uses_runtime_road_length_for_straight_road() -> None:
    generated = _single_route_fixture("straight", package_position=(2.0, 0.0), destination_position=(4.0, 0.0))

    result = PythonSolutionSimulatorService().simulate(generated)

    assert result.passed is True
    assert result.elapsed_time_seconds == pytest.approx(4.0, abs=0.001)


def test_python_solution_simulator_uses_runtime_road_length_for_horizontal_first_l_road() -> None:
    generated = _single_route_fixture(
        "horizontal_first",
        package_position=(2.0, 1.0),
        destination_position=(2.0, 2.0),
        first_shape="horizontalFirst",
    )
    expected_first_edge = RouteTimingService().edge_length((0.0, 0.0), (2.0, 1.0), "horizontalFirst")

    result = PythonSolutionSimulatorService().simulate(generated)

    assert result.passed is True
    assert result.steps[1].time_seconds == pytest.approx(expected_first_edge, abs=0.001)


def test_python_solution_simulator_uses_runtime_road_length_for_vertical_first_l_road() -> None:
    generated = _single_route_fixture(
        "vertical_first",
        package_position=(2.0, 1.0),
        destination_position=(3.0, 1.0),
        first_shape="verticalFirst",
    )
    expected_first_edge = RouteTimingService().edge_length((0.0, 0.0), (2.0, 1.0), "verticalFirst")

    result = PythonSolutionSimulatorService().simulate(generated)

    assert result.passed is True
    assert result.steps[1].time_seconds == pytest.approx(expected_first_edge, abs=0.001)


def test_python_solution_simulator_models_swift_pass_through_connector_timing() -> None:
    generated = _single_route_fixture(
        "connector",
        package_position=(1.0, 0.0),
        destination_position=(1.0, 1.0),
    )
    timing = RouteTimingService()
    connector = timing.perpendicular_connector(
        (0.0, 0.0),
        (1.0, 0.0),
        None,
        (1.0, 0.0),
        (1.0, 1.0),
        None,
    )
    assert connector is not None
    expected_elapsed = (
        connector.entry_distance_along_incoming_path
        + connector.length
        + (timing.edge_length((1.0, 0.0), (1.0, 1.0), None) - connector.exit_distance_along_outgoing_path)
    )

    result = PythonSolutionSimulatorService().simulate(generated)

    assert result.passed is True
    assert result.elapsed_time_seconds == pytest.approx(expected_elapsed, abs=0.001)
    assert [step.event for step in result.steps] == [
        "begin_edge",
        "arrive_node",
        "collect_package",
        "begin_transition",
        "end_transition",
        "arrive_node",
    ]


def test_python_solution_simulator_parity_fixture_return_loop_completes() -> None:
    preset = DifficultyService().get_preset("medium")
    generated = ReturnLoopTemplate().generate("level_099", 99, preset, RandomSource(7))

    result = PythonSolutionSimulatorService().simulate(generated)

    assert result.passed is True
    assert any(step.event == "tap_switch" for step in result.steps)


def test_python_solution_simulator_parity_fixture_ring_route_completes() -> None:
    preset = DifficultyService().get_preset("hard")
    generated = RingRouteTemplate().generate("level_099", 99, preset, RandomSource(8))

    result = PythonSolutionSimulatorService().simulate(generated)

    assert result.passed is True
    assert result.reached_package is True


def test_python_solution_simulator_parity_fixture_four_way_switch_completes() -> None:
    preset = DifficultyService().get_preset("expert")
    generated = FourWayIntersectionTemplate().generate("level_099", 99, preset, RandomSource(5))

    result = PythonSolutionSimulatorService().simulate(generated)

    assert result.passed is True
    assert len([step for step in result.steps if step.event == "tap_switch"]) >= 1


def _single_route_fixture(
    suffix: str,
    *,
    package_position: tuple[float, float],
    destination_position: tuple[float, float],
    first_shape: str | None = None,
) -> GeneratedLevel:
    level = LevelDocument(
        id=f"level_parity_{suffix}",
        name=f"Parity {suffix}",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id="start", x=0.0, y=0.0, outgoingEdgeIDs=["e_start_package"]),
                RouteNodeModel(
                    id="package",
                    x=package_position[0],
                    y=package_position[1],
                    outgoingEdgeIDs=["e_package_destination"],
                ),
                RouteNodeModel(id="destination", x=destination_position[0], y=destination_position[1], outgoingEdgeIDs=[]),
            ],
            edges=[
                RouteEdgeModel(
                    id="e_start_package",
                    fromNodeID="start",
                    toNodeID="package",
                    roadShape=first_shape,
                ),
                RouteEdgeModel(
                    id="e_package_destination",
                    fromNodeID="package",
                    toNodeID="destination",
                    roadShape=None,
                ),
            ],
        ),
        startNodeID="start",
        packageNodeID="package",
        destinationNodeID="destination",
        timeLimitSeconds=20,
        parTaps=0,
    )
    solution = SolutionModel(
        levelID=level.id,
        description="No taps.",
        expectedOutcome="completed",
        maxTaps=0,
        requiresWithinTimeLimit=True,
        actions=[],
    )
    return GeneratedLevel(
        level_document=level,
        solution=solution,
        template_name="parity_fixture",
        difficulty="tutorial",
        seed=1,
    )
