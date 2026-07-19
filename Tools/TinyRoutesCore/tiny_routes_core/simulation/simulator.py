"""Deterministic event-driven Tiny Routes runtime simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from tiny_routes_core.models import LevelDocument, SolutionAction, SwitchInteractionMode
from .results import LevelOutcome
from .runtime_state import ObjectiveProgressEvent, RuntimeState
from .switch_eligibility import NUMERIC_TOLERANCE, edge_length, switch_eligibility


class TapResultCode(str, Enum):
    ACCEPTED = "accepted"
    LEVEL_FINISHED = "level_finished"
    AFTER_ROUTE_COMMITMENT = "tap_after_route_commitment"
    NOT_SWITCHABLE = "tap_node_is_not_switchable"
    BEFORE_ACTIVATION_WINDOW = "tap_before_activation_window"
    NONELIGIBLE_SWITCH = "tap_noneligible_switch"
    COOLDOWN = "tap_cooldown"


@dataclass(frozen=True)
class SimulationEvent:
    time_seconds: float
    kind: str
    node_id: str | None = None
    edge_id: str | None = None
    detail: str = ""
    objective_id: str | None = None
    objective_index: int | None = None


@dataclass(frozen=True)
class TapRecord:
    action: SolutionAction
    code: TapResultCode
    expected_node_id: str | None = None
    active_edge_id: str | None = None


@dataclass
class RuntimeSimulationResult:
    state: RuntimeState
    events: list[SimulationEvent] = field(default_factory=list)
    taps: list[TapRecord] = field(default_factory=list)
    failure_reason: str | None = None
    safety_step_limit: int | None = None

    @property
    def passed(self) -> bool:
        return self.state.outcome == LevelOutcome.COMPLETED


class RuntimeSimulator:
    def __init__(self, *, speed: float = 1.0, maximum_step_count: int | None = None):
        self.speed = speed
        self.maximum_step_count = maximum_step_count

    def simulate(
        self,
        level: LevelDocument,
        actions: Iterable[SolutionAction] = (),
        *,
        end_time: float | None = None,
    ) -> RuntimeSimulationResult:
        state = RuntimeState.initialize(level)
        result = self._make_result(state)
        ordered = sorted(enumerate(actions), key=lambda pair: (float(pair[1].timeSeconds), pair[0]))
        for _, action in ordered:
            target = float(action.timeSeconds)
            if target + NUMERIC_TOLERANCE < state.elapsed_time:
                result.failure_reason = "solution_actions_not_monotonic"
                return result
            self._advance_to(level, result, min(target, float(level.timeLimitSeconds)))
            if state.outcome != LevelOutcome.IN_PROGRESS:
                return result
            record = self._apply_tap(result, action)
            result.taps.append(record)
            result.events.append(SimulationEvent(state.elapsed_time, "tap_accepted" if record.code == TapResultCode.ACCEPTED else "tap_rejected", action.tapNodeID, record.active_edge_id, record.code.value))
            if record.code != TapResultCode.ACCEPTED:
                result.failure_reason = record.code.value
                return result

        requested_end = float(level.timeLimitSeconds) if end_time is None else min(float(end_time), float(level.timeLimitSeconds))
        self._advance_to(level, result, requested_end)
        if (result.failure_reason is None and state.outcome == LevelOutcome.IN_PROGRESS
                and requested_end >= float(level.timeLimitSeconds) - NUMERIC_TOLERANCE):
            state.outcome = LevelOutcome.FAILED_TIME_LIMIT
            result.failure_reason = "time_expired"
            result.events.append(SimulationEvent(state.elapsed_time, "time_expired"))
        return result

    def begin(self, level: LevelDocument) -> RuntimeSimulationResult:
        """Create an incremental simulation session for interactive clients."""
        return self._make_result(RuntimeState.initialize(level))

    def _make_result(self, state: RuntimeState) -> RuntimeSimulationResult:
        result = RuntimeSimulationResult(state)
        self._append_objective_events(result, state.objective_events)
        if state.outcome == LevelOutcome.COMPLETED:
            result.events.append(SimulationEvent(state.elapsed_time, "complete", state.current_node_id))
        elif state.outcome == LevelOutcome.FAILED_MISSING_PACKAGE:
            result.failure_reason = "reached_destination_without_package"
            result.events.append(SimulationEvent(
                state.elapsed_time,
                "destination_without_package",
                state.current_node_id,
            ))
        return result

    def _append_objective_events(
        self,
        result: RuntimeSimulationResult,
        events: Iterable[ObjectiveProgressEvent],
    ) -> None:
        for event in events:
            if event.kind == "objective_completed" and event.objective_kind.value == "pickup":
                result.events.append(SimulationEvent(
                    result.state.elapsed_time,
                    "collect_package",
                    event.node_id,
                    objective_id=event.objective_id,
                    objective_index=event.sequence_index,
                ))
            result.events.append(SimulationEvent(
                result.state.elapsed_time,
                event.kind,
                event.node_id,
                detail=f"{event.objective_id}:{event.sequence_index}",
                objective_id=event.objective_id,
                objective_index=event.sequence_index,
            ))

    def advance(
        self,
        level: LevelDocument,
        result: RuntimeSimulationResult,
        target_time: float,
    ) -> None:
        """Advance an incremental session to an absolute elapsed time."""
        if target_time + NUMERIC_TOLERANCE < result.state.elapsed_time:
            raise ValueError("target_time cannot move an incremental simulation backwards")
        self._advance_to(level, result, min(float(target_time), float(level.timeLimitSeconds)))
        if (result.failure_reason is None
                and result.state.outcome == LevelOutcome.IN_PROGRESS
                and target_time >= float(level.timeLimitSeconds) - NUMERIC_TOLERANCE):
            result.state.outcome = LevelOutcome.FAILED_TIME_LIMIT
            result.failure_reason = "time_expired"
            result.events.append(SimulationEvent(result.state.elapsed_time, "time_expired"))

    def tap(
        self,
        result: RuntimeSimulationResult,
        node_id: str,
    ) -> TapRecord:
        """Apply and record a tap at the current time in an incremental session."""
        action = SolutionAction(timeSeconds=result.state.elapsed_time, tapNodeID=node_id)
        record = self._apply_tap(result, action)
        result.taps.append(record)
        result.events.append(SimulationEvent(
            result.state.elapsed_time,
            "tap_accepted" if record.code == TapResultCode.ACCEPTED else "tap_rejected",
            node_id,
            record.active_edge_id,
            record.code.value,
        ))
        return record

    def _advance_to(self, level: LevelDocument, result: RuntimeSimulationResult, target_time: float) -> None:
        state = result.state
        limit = self.maximum_step_count if self.maximum_step_count is not None else max(len(state.runtime_graph.index.edges_by_id), 1) * 4
        steps = 0
        while state.outcome == LevelOutcome.IN_PROGRESS and state.elapsed_time < target_time - NUMERIC_TOLERANCE:
            if steps >= limit:
                result.failure_reason = "max_step_count_exceeded"
                result.safety_step_limit = limit
                result.events.append(SimulationEvent(state.elapsed_time, "safety_limit", detail=str(limit)))
                return
            if state.current_edge_id is None:
                state.runtime_graph.normalize_for_objective_state(
                    state.completed_objective_ids,
                    state.active_objective_index,
                )
                edge_id = state.runtime_graph.active_edge_ids.get(state.current_node_id)
                if edge_id is None:
                    state.outcome = LevelOutcome.FAILED_DEAD_END
                    result.failure_reason = "dead_end"
                    result.events.append(SimulationEvent(state.elapsed_time, "dead_end", state.current_node_id))
                    return
                state.current_edge_id = edge_id
                state.edge_progress = 0.0
                state.runtime_graph.record_edge_traversal(edge_id)
                result.events.append(SimulationEvent(state.elapsed_time, "begin_edge", state.current_node_id, edge_id))

            length = edge_length(state, state.current_edge_id)
            remaining_distance = max(0.0, (1.0 - state.edge_progress) * length)
            available_distance = max(0.0, target_time - state.elapsed_time) * self.speed
            if length > NUMERIC_TOLERANCE and available_distance + NUMERIC_TOLERANCE < remaining_distance:
                delta = available_distance / length
                state.edge_progress = min(1.0, state.edge_progress + delta)
                elapsed = available_distance / self.speed
                state.elapsed_time += elapsed
                state.remaining_time = max(0.0, float(level.timeLimitSeconds) - state.elapsed_time)
                state.tap_cooldown_remaining = max(0.0, state.tap_cooldown_remaining - elapsed)
                return

            travel_time = remaining_distance / self.speed if self.speed > 0 else 0.0
            state.elapsed_time += travel_time
            state.remaining_time = max(0.0, float(level.timeLimitSeconds) - state.elapsed_time)
            state.tap_cooldown_remaining = max(0.0, state.tap_cooldown_remaining - travel_time)
            edge = state.runtime_graph.index.edges_by_id[state.current_edge_id]
            arrived_edge_id = edge.id
            state.current_node_id = edge.toNodeID
            state.current_edge_id = None
            state.edge_progress = 0.0
            state.visited_node_ids.append(state.current_node_id)
            steps += 1
            result.events.append(SimulationEvent(state.elapsed_time, "arrive_node", state.current_node_id, arrived_edge_id))
            objective_events = state.process_objective_arrival(
                state.current_node_id,
                preserve_legacy_destination_failure=level.schema_version < 3,
                cascade_legacy_same_node=level.schema_version < 3,
            )
            self._append_objective_events(result, objective_events)
            if state.outcome == LevelOutcome.COMPLETED:
                result.events.append(SimulationEvent(state.elapsed_time, "complete", state.current_node_id))
                return
            if state.outcome == LevelOutcome.FAILED_MISSING_PACKAGE:
                result.failure_reason = "reached_destination_without_package"
                result.events.append(SimulationEvent(
                    state.elapsed_time,
                    "destination_without_package",
                    state.current_node_id,
                ))
                return

        if state.elapsed_time < target_time:
            elapsed = target_time - state.elapsed_time
            state.elapsed_time = target_time
            state.remaining_time = max(0.0, float(level.timeLimitSeconds) - target_time)
            state.tap_cooldown_remaining = max(0.0, state.tap_cooldown_remaining - elapsed)

    def _apply_tap(self, result: RuntimeSimulationResult, action: SolutionAction) -> TapRecord:
        state, node_id = result.state, action.tapNodeID
        index = state.runtime_graph.index
        if state.outcome != LevelOutcome.IN_PROGRESS:
            return TapRecord(action, TapResultCode.LEVEL_FINISHED)
        if state.current_edge_id is not None and index.edges_by_id[state.current_edge_id].fromNodeID == node_id:
            return TapRecord(action, TapResultCode.AFTER_ROUTE_COMMITMENT)
        outgoing = (
            state.runtime_graph.usable_outgoing(
                node_id,
                state.completed_objective_ids,
                state.active_objective_index,
            )
            if node_id in index.nodes_by_id
            else ()
        )
        if len(outgoing) < 2:
            return TapRecord(action, TapResultCode.NOT_SWITCHABLE)
        if state.rules.switch_interaction_mode == SwitchInteractionMode.LIVE_LOOKAHEAD:
            snapshot = switch_eligibility(state, speed=self.speed)
            if snapshot.eligible_node_id != node_id:
                code = TapResultCode.BEFORE_ACTIVATION_WINDOW if snapshot.upcoming_node_id == node_id else TapResultCode.NONELIGIBLE_SWITCH
                return TapRecord(action, code, snapshot.eligible_node_id)
            if state.tap_cooldown_remaining > NUMERIC_TOLERANCE:
                return TapRecord(action, TapResultCode.COOLDOWN, snapshot.eligible_node_id)
        current = state.runtime_graph.active_edge_ids.get(node_id)
        current_index = next((i for i, edge in enumerate(outgoing) if edge.id == current), -1)
        next_edge = outgoing[(current_index + 1) % len(outgoing)]
        state.runtime_graph.active_edge_ids[node_id] = next_edge.id
        state.accepted_tap_count += 1
        if state.rules.switch_interaction_mode == SwitchInteractionMode.LIVE_LOOKAHEAD:
            state.tap_cooldown_remaining = max(float(state.rules.switch_tap_cooldown_seconds), 0.0)
        return TapRecord(action, TapResultCode.ACCEPTED, node_id, next_edge.id)
