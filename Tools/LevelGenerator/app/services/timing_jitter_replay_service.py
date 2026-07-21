"""Replay runtime solutions through a deterministic timing robustness envelope."""

from __future__ import annotations

from math import ceil, floor
from typing import Iterable

from tiny_routes_core.models import LevelDocument, SolutionAction
from tiny_routes_core.simulation import RuntimeSimulator, TapResultCode

from ..models.runtime_solution_search import RuntimeSolutionAction
from ..models.timing_jitter import (
    TimingJitterReplayConfig,
    TimingJitterReplayReport,
    TimingJitterScenarioResult,
)


class TimingJitterReplayService:
    """Prove a schedule survives timestamp, frame-step, and speed variation."""

    def __init__(self, config: TimingJitterReplayConfig | None = None) -> None:
        self.config = config or TimingJitterReplayConfig()

    def replay(
        self,
        level: LevelDocument,
        actions: Iterable[RuntimeSolutionAction | SolutionAction],
        *,
        config: TimingJitterReplayConfig | None = None,
    ) -> TimingJitterReplayReport:
        config = config or self.config
        canonical = tuple(
            RuntimeSolutionAction(
                float(action.timeSeconds if isinstance(action, SolutionAction) else action.time_seconds),
                action.tapNodeID if isinstance(action, SolutionAction) else action.tap_node_id,
                None if isinstance(action, SolutionAction) else action.expected_edge_after_tap,
            )
            for action in actions
        )
        scenarios = self._scenarios(canonical, config)
        results = tuple(
            self._replay_scenario(level, scenario_id, varied_actions, speed)
            for scenario_id, varied_actions, speed in scenarios
        )
        failures = tuple(
            f"solution_jitter_failure:{result.scenario_id}:{result.failure_reason}"
            for result in results
            if not result.passed
        )
        return TimingJitterReplayReport(not failures, results, failures)

    replay_solution = replay

    def _scenarios(
        self,
        actions: tuple[RuntimeSolutionAction, ...],
        config: TimingJitterReplayConfig,
    ) -> tuple[tuple[str, tuple[RuntimeSolutionAction, ...], float], ...]:
        scenarios: list[tuple[str, tuple[RuntimeSolutionAction, ...], float]] = [
            ("baseline", actions, 1.0)
        ]
        for offset in config.timing_offsets_seconds:
            label = self._seconds_label(offset)
            scenarios.append((
                f"uniform_{label}",
                self._offset_actions(actions, (offset,) * len(actions)),
                1.0,
            ))
            if config.include_individual_tap_variations and len(actions) > 1:
                alternating = tuple(
                    offset if index % 2 == 0 else -offset
                    for index in range(len(actions))
                )
                scenarios.append((
                    f"alternating_{label}",
                    self._offset_actions(actions, alternating),
                    1.0,
                ))
        for frame_step in config.frame_step_seconds:
            hz = round(1.0 / frame_step)
            scenarios.extend((
                (
                    f"frame_{hz}hz_floor",
                    self._quantized_actions(actions, frame_step, mode="floor"),
                    1.0,
                ),
                (
                    f"frame_{hz}hz_ceil",
                    self._quantized_actions(actions, frame_step, mode="ceil"),
                    1.0,
                ),
            ))
        for variation in config.speed_variations:
            scenarios.append((
                f"speed_{self._percent_label(variation)}",
                actions,
                1.0 + variation,
            ))
        return tuple(scenarios)

    @staticmethod
    def _offset_actions(
        actions: tuple[RuntimeSolutionAction, ...],
        offsets: tuple[float, ...],
    ) -> tuple[RuntimeSolutionAction, ...]:
        return tuple(
            RuntimeSolutionAction(
                max(0.0, round(action.time_seconds + offset, 9)),
                action.tap_node_id,
                action.expected_edge_after_tap,
            )
            for action, offset in zip(actions, offsets)
        )

    @staticmethod
    def _quantized_actions(
        actions: tuple[RuntimeSolutionAction, ...],
        frame_step: float,
        *,
        mode: str,
    ) -> tuple[RuntimeSolutionAction, ...]:
        quantize = floor if mode == "floor" else ceil
        return tuple(
            RuntimeSolutionAction(
                round(max(0.0, quantize(action.time_seconds / frame_step) * frame_step), 9),
                action.tap_node_id,
                action.expected_edge_after_tap,
            )
            for action in actions
        )

    @staticmethod
    def _replay_scenario(
        level: LevelDocument,
        scenario_id: str,
        actions: tuple[RuntimeSolutionAction, ...],
        speed: float,
    ) -> TimingJitterScenarioResult:
        solution_actions = tuple(
            SolutionAction(action.time_seconds, action.tap_node_id)
            for action in actions
        )
        replay = RuntimeSimulator(speed=speed).simulate(level, solution_actions)
        rejected_index = next(
            (
                index
                for index, tap in enumerate(replay.taps)
                if tap.code is not TapResultCode.ACCEPTED
            ),
            None,
        )
        expected_edges_match = all(
            action.expected_edge_after_tap is None
            or index >= len(replay.taps)
            or replay.taps[index].active_edge_id == action.expected_edge_after_tap
            for index, action in enumerate(actions)
        )
        passed = (
            replay.passed
            and rejected_index is None
            and len(replay.taps) == len(actions)
            and expected_edges_match
        )
        if passed:
            reason = None
        elif rejected_index is not None:
            reason = replay.taps[rejected_index].code.value
        elif not expected_edges_match:
            reason = "jitter_selected_edge_mismatch"
        else:
            reason = replay.failure_reason or "jitter_runtime_replay_failed"
        return TimingJitterScenarioResult(
            scenario_id=scenario_id,
            actions=actions,
            speed=round(speed, 9),
            passed=passed,
            failure_reason=reason,
            rejected_tap_index=rejected_index,
            elapsed_time_seconds=round(replay.state.elapsed_time, 9),
        )

    @staticmethod
    def _seconds_label(value: float) -> str:
        sign = "plus" if value >= 0 else "minus"
        return f"{sign}_{round(abs(value) * 1000)}ms"

    @staticmethod
    def _percent_label(value: float) -> str:
        sign = "plus" if value >= 0 else "minus"
        return f"{sign}_{abs(value) * 100:.3f}pct".replace(".", "_")
