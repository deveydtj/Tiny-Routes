from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from tiny_routes_core.models import SolutionAction, SwitchInteractionMode
from tiny_routes_core.simulation import RuntimeSimulator, TapResultCode, switch_eligibility

from ..models.runtime_solution_search import (
    RuntimeDecisionTimingDiagnostic,
    RuntimeSolutionAction,
    RuntimeSolutionSearchResult,
)
from ..models.strategy_search import StrategyTrace
from .timing_jitter_replay_service import TimingJitterReplayService


@dataclass(frozen=True)
class _DecisionEncounter:
    node_id: str
    rotation_count: int
    selected_edge_id: str | None = None
    objective_index: int | None = None


class RuntimeSolutionSearchService:
    """Schedule exact structural choices inside canonical runtime windows.

    Exact V3 traces carry their objective phase and selected road into runtime
    scheduling. The runtime simulator remains the source of truth for road
    availability, switch normalization, one-use consumption, and eligibility.
    Legacy topology metadata is retained as a compatibility input.
    """

    def __init__(
        self,
        *,
        safety_margin_seconds: float = 0.12,
        search_step_seconds: float = 0.02,
        jitter_replay_service: TimingJitterReplayService | None = None,
    ) -> None:
        self.safety_margin_seconds = safety_margin_seconds
        self.search_step_seconds = search_step_seconds
        self.jitter_replay_service = jitter_replay_service or TimingJitterReplayService()

    def search(self, level, topology_solution) -> RuntimeSolutionSearchResult:
        if level.rules.switch_interaction_mode != SwitchInteractionMode.LIVE_LOOKAHEAD:
            return RuntimeSolutionSearchResult(False, failure_reason="runtime_search_requires_live_lookahead")

        state_aware = isinstance(topology_solution, StrategyTrace)
        encounters = self._decision_encounters(level, topology_solution)
        actions: list[RuntimeSolutionAction] = []
        diagnostics: list[RuntimeDecisionTimingDiagnostic] = []
        visit_counts: Counter[str] = Counter()
        search_time = 0.0

        for encounter in encounters:
            node_id = encounter.node_id
            visit_counts[node_id] += 1
            opening = self._find_window_open(level, actions, node_id, search_time)
            if opening is None:
                diagnostic = RuntimeDecisionTimingDiagnostic(
                    node_id, visit_counts[node_id], encounter.rotation_count, None, None,
                    safety_margin_seconds=self.safety_margin_seconds,
                    failure_reason="activation_window_not_found",
                    objective_index=encounter.objective_index,
                    selected_edge_id=encounter.selected_edge_id,
                )
                return RuntimeSolutionSearchResult(
                    False, tuple(actions), tuple((*diagnostics, diagnostic)), "activation_window_not_found"
                )

            window_open, travel_time, opened_replay = opening
            window_close = window_open + travel_time
            opened_state = opened_replay.state
            state_fields = self._state_fields(opened_state)
            if (
                encounter.objective_index is not None
                and opened_state.active_objective_index != encounter.objective_index
            ):
                diagnostic = RuntimeDecisionTimingDiagnostic(
                    node_id, visit_counts[node_id], encounter.rotation_count, window_open, window_close,
                    safety_margin_seconds=self.safety_margin_seconds,
                    failure_reason="runtime_objective_state_mismatch",
                    selected_edge_id=encounter.selected_edge_id,
                    **state_fields,
                )
                return RuntimeSolutionSearchResult(
                    False, tuple(actions), tuple((*diagnostics, diagnostic)), "runtime_objective_state_mismatch",
                    opened_replay,
                )

            outgoing = opened_state.runtime_graph.usable_outgoing(
                node_id,
                opened_state.completed_objective_ids,
                opened_state.active_objective_index,
            )
            selected_edge_id = encounter.selected_edge_id
            if selected_edge_id is not None and selected_edge_id not in {edge.id for edge in outgoing}:
                diagnostic = RuntimeDecisionTimingDiagnostic(
                    node_id, visit_counts[node_id], encounter.rotation_count, window_open, window_close,
                    safety_margin_seconds=self.safety_margin_seconds,
                    failure_reason="runtime_strategy_edge_unavailable",
                    selected_edge_id=selected_edge_id,
                    **state_fields,
                )
                return RuntimeSolutionSearchResult(
                    False, tuple(actions), tuple((*diagnostics, diagnostic)), "runtime_strategy_edge_unavailable",
                    opened_replay,
                )

            rotation_count = encounter.rotation_count
            if selected_edge_id is not None:
                current_edge_id = opened_state.runtime_graph.active_edge_ids.get(node_id)
                current_index = next(
                    (index for index, edge in enumerate(outgoing) if edge.id == current_edge_id),
                    0,
                )
                desired_index = next(
                    index for index, edge in enumerate(outgoing) if edge.id == selected_edge_id
                )
                runtime_rotation_count = (desired_index - current_index) % len(outgoing)
                if runtime_rotation_count != rotation_count:
                    diagnostic = RuntimeDecisionTimingDiagnostic(
                        node_id, visit_counts[node_id], rotation_count, window_open, window_close,
                        safety_margin_seconds=self.safety_margin_seconds,
                        failure_reason="runtime_strategy_rotation_mismatch",
                        selected_edge_id=selected_edge_id,
                        **state_fields,
                    )
                    return RuntimeSolutionSearchResult(
                        False, tuple(actions), tuple((*diagnostics, diagnostic)),
                        "runtime_strategy_rotation_mismatch", opened_replay,
                    )

            cooldown = max(float(level.rules.switch_tap_cooldown_seconds), 0.0)
            jitter_spacing = (
                2.0 * self.jitter_replay_service.config.maximum_timing_offset_seconds
                if state_aware
                and self.jitter_replay_service.config.include_individual_tap_variations
                else 0.0
            )
            spacing = cooldown + jitter_spacing + 0.001
            tap_times = (
                self._centered_tap_times(
                    window_open,
                    window_close,
                    rotation_count,
                    spacing,
                )
                if state_aware
                else self._legacy_tap_times(
                    window_open,
                    window_close,
                    rotation_count,
                    spacing,
                )
            )
            if tap_times is None:
                attempted = tuple(
                    window_open + self.safety_margin_seconds + index * spacing
                    for index in range(rotation_count)
                )
                diagnostic = RuntimeDecisionTimingDiagnostic(
                    node_id, visit_counts[node_id], rotation_count, window_open, window_close,
                    attempted, self.safety_margin_seconds, "insufficient_rotation_window",
                    selected_edge_id=selected_edge_id,
                    **state_fields,
                )
                return RuntimeSolutionSearchResult(
                    False, tuple(actions), tuple((*diagnostics, diagnostic)), "insufficient_rotation_window"
                )

            for tap_time in tap_times:
                prefix = [SolutionAction(action.time_seconds, action.tap_node_id) for action in actions]
                prefix.append(SolutionAction(tap_time, node_id))
                replay = RuntimeSimulator().simulate(level, prefix, end_time=tap_time)
                if not replay.taps or replay.taps[-1].code != TapResultCode.ACCEPTED:
                    reason = replay.failure_reason or "runtime_replay_rejected_action"
                    diagnostic = RuntimeDecisionTimingDiagnostic(
                        node_id, visit_counts[node_id], rotation_count, window_open, window_close,
                        tap_times, self.safety_margin_seconds, reason,
                        selected_edge_id=selected_edge_id,
                        **state_fields,
                    )
                    return RuntimeSolutionSearchResult(
                        False, tuple(actions), tuple((*diagnostics, diagnostic)), reason, replay
                    )
                actions.append(RuntimeSolutionAction(tap_time, node_id, replay.taps[-1].active_edge_id))

            if selected_edge_id is not None:
                selected_replay = RuntimeSimulator().simulate(
                    level,
                    [SolutionAction(action.time_seconds, action.tap_node_id) for action in actions],
                    end_time=tap_times[-1] if tap_times else window_open,
                )
                if selected_replay.state.runtime_graph.active_edge_ids.get(node_id) != selected_edge_id:
                    diagnostic = RuntimeDecisionTimingDiagnostic(
                        node_id, visit_counts[node_id], rotation_count, window_open, window_close,
                        tap_times, self.safety_margin_seconds, "runtime_selected_edge_mismatch",
                        selected_edge_id=selected_edge_id,
                        **state_fields,
                    )
                    return RuntimeSolutionSearchResult(
                        False, tuple(actions), tuple((*diagnostics, diagnostic)),
                        "runtime_selected_edge_mismatch", selected_replay,
                    )

            diagnostics.append(RuntimeDecisionTimingDiagnostic(
                node_id, visit_counts[node_id], rotation_count, window_open, window_close,
                tap_times, self.safety_margin_seconds,
                selected_edge_id=selected_edge_id,
                **state_fields,
            ))
            # Advancing beyond commitment distinguishes phase-specific revisits.
            search_time = window_close + self.search_step_seconds

        final_actions = [SolutionAction(action.time_seconds, action.tap_node_id) for action in actions]
        final_replay = RuntimeSimulator().simulate(level, final_actions)
        if not final_replay.passed or any(tap.code != TapResultCode.ACCEPTED for tap in final_replay.taps):
            return RuntimeSolutionSearchResult(
                False, tuple(actions), tuple(diagnostics),
                final_replay.failure_reason or "final_runtime_replay_failed", final_replay,
            )

        jitter_report = None
        if state_aware:
            jitter_report = self.jitter_replay_service.replay(level, actions)
            if not jitter_report.passed:
                return RuntimeSolutionSearchResult(
                    False,
                    tuple(actions),
                    tuple(diagnostics),
                    "solution_jitter_failure",
                    final_replay,
                    jitter_report,
                )
        return RuntimeSolutionSearchResult(
            True,
            tuple(actions),
            tuple(diagnostics),
            replay_result=final_replay,
            jitter_report=jitter_report,
        )

    def _find_window_open(
        self,
        level,
        actions,
        node_id: str,
        start_time: float,
    ) -> tuple[float, float, object] | None:
        prior = [SolutionAction(action.time_seconds, action.tap_node_id) for action in actions]
        limit = float(level.timeLimitSeconds)
        time = max(0.0, start_time)
        while time <= limit + 1e-9:
            replay = RuntimeSimulator().simulate(level, prior, end_time=time)
            if replay.failure_reason is not None or replay.state.outcome.value != "inProgress":
                return None
            snapshot = switch_eligibility(replay.state)
            if snapshot.eligible_node_id == node_id and snapshot.travel_time_seconds is not None:
                close = time + snapshot.travel_time_seconds
                opening = max(start_time, close - float(level.rules.switch_lookahead_seconds))
                opened_replay = RuntimeSimulator().simulate(level, prior, end_time=opening)
                opened_snapshot = switch_eligibility(opened_replay.state)
                if opened_snapshot.eligible_node_id == node_id:
                    return opening, close - opening, opened_replay
                return time, snapshot.travel_time_seconds, replay
            time += self.search_step_seconds
        return None

    def _decision_encounters(self, level, topology_solution) -> list[_DecisionEncounter]:
        if isinstance(topology_solution, StrategyTrace):
            return [
                _DecisionEncounter(
                    action.node_id,
                    action.tap_count,
                    action.selected_edge_id,
                    (
                        action.state_transition.objective_index_before
                        if action.state_transition is not None
                        else None
                    ),
                )
                for action in topology_solution.actions
                if action.tap_count > 0 or action.meaningful_decision is not False
            ]

        path = list(topology_solution.required_path)
        remaining = Counter(topology_solution.decision_node_ids)
        active_index: dict[str, int] = {}
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        node_by_id = {node.id: node for node in level.graph.nodes}
        encounters: list[_DecisionEncounter] = []
        for node_id, next_node_id in zip(path, path[1:]):
            node = node_by_id.get(node_id)
            if node is None:
                continue
            outgoing = [edge_by_id[edge_id] for edge_id in node.outgoingEdgeIDs if edge_id in edge_by_id]
            if len(outgoing) < 2:
                continue
            current = active_index.get(node_id, 0)
            desired = next((index for index, edge in enumerate(outgoing) if edge.toNodeID == next_node_id), None)
            if desired is None:
                continue
            rotations = (desired - current) % len(outgoing)
            active_index[node_id] = desired
            if rotations:
                encounters.append(_DecisionEncounter(node_id, rotations))
                remaining[node_id] -= rotations
        if any(count != 0 for count in remaining.values()):
            return [
                _DecisionEncounter(node_id, count)
                for node_id, count in Counter(topology_solution.decision_node_ids).items()
                if count
            ]
        return encounters

    def _centered_tap_times(
        self,
        window_open: float,
        window_close: float,
        rotation_count: int,
        spacing: float,
    ) -> tuple[float, ...] | None:
        if rotation_count == 0:
            return ()
        safe_open = window_open + self.safety_margin_seconds
        safe_close = window_close - self.safety_margin_seconds
        burst_span = (rotation_count - 1) * spacing
        if safe_open + burst_span > safe_close + 1e-9:
            return None
        first_tap = safe_open + max(0.0, safe_close - safe_open - burst_span) / 2.0
        return tuple(
            round(first_tap + index * spacing, 9)
            for index in range(rotation_count)
        )

    def _legacy_tap_times(
        self,
        window_open: float,
        window_close: float,
        rotation_count: int,
        spacing: float,
    ) -> tuple[float, ...] | None:
        tap_times = tuple(
            window_open + self.safety_margin_seconds + index * spacing
            for index in range(rotation_count)
        )
        if tap_times and tap_times[-1] > window_close - self.safety_margin_seconds + 1e-9:
            return None
        return tap_times

    @staticmethod
    def _state_fields(state) -> dict[str, object]:
        active = state.active_objective
        available = tuple(
            edge.id
            for edge in state.runtime_graph.index.graph.edges
            if state.runtime_graph.edge_is_usable(
                edge,
                state.completed_objective_ids,
                state.active_objective_index,
            )
        )
        consumed = tuple(
            sorted(
                edge_id
                for edge_id, count in state.runtime_graph.edge_usage_counts.items()
                if count > 0
                and state.runtime_graph.availability_rules_by_edge_id[edge_id].usageLimit is not None
                and count >= state.runtime_graph.availability_rules_by_edge_id[edge_id].usageLimit
            )
        )
        return {
            "objective_index": state.active_objective_index,
            "active_objective_id": active.id if active is not None else None,
            "completed_objective_ids": tuple(
                objective.id
                for objective in state.objectives
                if objective.id in state.completed_objective_ids
            ),
            "available_edge_ids": available,
            "consumed_edge_ids": consumed,
        }
