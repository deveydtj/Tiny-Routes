from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import QObject, QElapsedTimer, QTimer, Signal

from tiny_routes_core.models import LevelDocument
from tiny_routes_core.simulation import (
    LevelOutcome,
    RuntimeSimulationResult,
    RuntimeSimulator,
    TapRecord,
    TapResultCode,
    switch_eligibility,
)

from app.models.playtest_state import PlaytestState


class PlaytestController(QObject):
    """Owns an isolated, timer-driven simulation of the authored level."""

    state_changed = Signal(object)
    stopped = Signal()

    def __init__(self, parent: QObject | None = None, *, speed: float = 1.0) -> None:
        super().__init__(parent)
        self._simulator = RuntimeSimulator(speed=speed)
        self._level: LevelDocument | None = None
        self._result: RuntimeSimulationResult | None = None
        self._rejected_taps: list[TapRecord] = []
        self._clock = QElapsedTimer()
        self._clock_base_seconds = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._on_tick)
        self._state = PlaytestState()

    @property
    def state(self) -> PlaytestState:
        return self._state

    @property
    def level_snapshot(self) -> LevelDocument | None:
        return deepcopy(self._level)

    def start(self, document: LevelDocument) -> None:
        self._level = deepcopy(document)
        self._result = self._simulator.begin(self._level)
        self._rejected_taps = []
        self._clock_base_seconds = 0.0
        self._clock.start()
        self._timer.start()
        self._publish(running=True, paused=False)

    def pause(self) -> None:
        if not self._state.running or self._state.paused:
            return
        self._advance_to_clock()
        self._timer.stop()
        self._clock_base_seconds = self._result.state.elapsed_time
        self._publish(running=True, paused=True)

    def resume(self) -> None:
        if not self._state.running or not self._state.paused:
            return
        self._clock_base_seconds = self._result.state.elapsed_time
        self._clock.restart()
        self._timer.start()
        self._publish(running=True, paused=False)

    def reset(self) -> None:
        if self._level is None:
            return
        was_paused = self._state.paused
        self._result = self._simulator.begin(self._level)
        self._rejected_taps = []
        self._clock_base_seconds = 0.0
        self._clock.restart()
        if was_paused:
            self._timer.stop()
        else:
            self._timer.start()
        self._publish(running=True, paused=was_paused)

    def stop(self) -> None:
        self._timer.stop()
        self._level = None
        self._result = None
        self._rejected_taps = []
        self._state = PlaytestState()
        self.state_changed.emit(self._state)
        self.stopped.emit()

    def tap(self, node_id: str) -> TapRecord | None:
        if self._result is None or self._state.paused:
            return None
        self._advance_to_clock()
        record = self._simulator.tap(self._result, node_id)
        if record.code != TapResultCode.ACCEPTED:
            self._rejected_taps.append(record)
        self._publish(running=True, paused=False)
        return record

    def advance_by(self, seconds: float) -> None:
        """Deterministic advancement hook used by tests and future timeline controls."""
        if self._level is None or self._result is None:
            return
        self._simulator.advance(self._level, self._result, self._result.state.elapsed_time + max(seconds, 0.0))
        self._clock_base_seconds = self._result.state.elapsed_time
        self._clock.restart()
        self._publish(running=True, paused=self._state.paused)

    def _on_tick(self) -> None:
        self._advance_to_clock()
        self._publish(running=True, paused=False)

    def _advance_to_clock(self) -> None:
        if self._level is None or self._result is None or self._state.paused:
            return
        target = self._clock_base_seconds + self._clock.elapsed() / 1000.0
        self._simulator.advance(self._level, self._result, target)
        if self._result.state.outcome != LevelOutcome.IN_PROGRESS:
            self._timer.stop()

    def _publish(self, *, running: bool, paused: bool) -> None:
        if self._result is None:
            return
        runtime = self._result.state
        eligible = switch_eligibility(runtime, speed=self._simulator.speed).eligible_node_id
        accepted = tuple(tap for tap in self._result.taps if tap.code == TapResultCode.ACCEPTED)
        self._state = PlaytestState(
            running=running,
            paused=paused,
            elapsed_time=runtime.elapsed_time,
            current_node_id=runtime.current_node_id,
            current_edge_id=runtime.current_edge_id,
            edge_progress=runtime.edge_progress,
            package_collected=runtime.package_collected,
            outcome=runtime.outcome,
            eligible_switch_id=eligible,
            accepted_taps=accepted,
            rejected_taps=tuple(self._rejected_taps),
        )
        self.state_changed.emit(self._state)
