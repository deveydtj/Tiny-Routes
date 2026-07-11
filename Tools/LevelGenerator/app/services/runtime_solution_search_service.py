from __future__ import annotations

from collections import Counter

from tiny_routes_core.models import SolutionAction, SwitchInteractionMode
from tiny_routes_core.simulation import RuntimeSimulator, TapResultCode, switch_eligibility

from ..models.runtime_solution_search import (
    RuntimeDecisionTimingDiagnostic,
    RuntimeSolutionAction,
    RuntimeSolutionSearchResult,
)


class RuntimeSolutionSearchService:
    """Schedules topology decisions only inside real runtime eligibility windows."""

    def __init__(self, *, safety_margin_seconds: float = 0.12, search_step_seconds: float = 0.02) -> None:
        self.safety_margin_seconds = safety_margin_seconds
        self.search_step_seconds = search_step_seconds

    def search(self, level, topology_solution) -> RuntimeSolutionSearchResult:
        if level.rules.switch_interaction_mode != SwitchInteractionMode.LIVE_LOOKAHEAD:
            return RuntimeSolutionSearchResult(False, failure_reason="runtime_search_requires_live_lookahead")

        encounters = self._decision_encounters(level, topology_solution)
        actions: list[RuntimeSolutionAction] = []
        diagnostics: list[RuntimeDecisionTimingDiagnostic] = []
        visit_counts: Counter[str] = Counter()
        search_time = 0.0

        for node_id, rotation_count in encounters:
            visit_counts[node_id] += 1
            opening = self._find_window_open(level, actions, node_id, search_time)
            if opening is None:
                diagnostic = RuntimeDecisionTimingDiagnostic(
                    node_id, visit_counts[node_id], rotation_count, None, None,
                    safety_margin_seconds=self.safety_margin_seconds,
                    failure_reason="activation_window_not_found",
                )
                return RuntimeSolutionSearchResult(
                    False, tuple(actions), tuple((*diagnostics, diagnostic)), "activation_window_not_found"
                )

            window_open, travel_time = opening
            window_close = window_open + travel_time
            cooldown = max(float(level.rules.switch_tap_cooldown_seconds), 0.0)
            spacing = cooldown + 0.001
            first_tap = window_open + self.safety_margin_seconds
            tap_times = tuple(first_tap + (index * spacing) for index in range(rotation_count))
            if tap_times and tap_times[-1] > window_close - self.safety_margin_seconds + 1e-9:
                diagnostic = RuntimeDecisionTimingDiagnostic(
                    node_id, visit_counts[node_id], rotation_count, window_open, window_close,
                    tap_times, self.safety_margin_seconds, "insufficient_rotation_window",
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
                    )
                    return RuntimeSolutionSearchResult(
                        False, tuple(actions), tuple((*diagnostics, diagnostic)), reason, replay
                    )
                actions.append(RuntimeSolutionAction(tap_time, node_id, replay.taps[-1].active_edge_id))

            diagnostics.append(RuntimeDecisionTimingDiagnostic(
                node_id, visit_counts[node_id], rotation_count, window_open, window_close,
                tap_times, self.safety_margin_seconds,
            ))
            # Moving beyond commitment is essential when the same switch is revisited.
            search_time = window_close + self.search_step_seconds

        final_actions = [SolutionAction(action.time_seconds, action.tap_node_id) for action in actions]
        final_replay = RuntimeSimulator().simulate(level, final_actions)
        if not final_replay.passed or any(tap.code != TapResultCode.ACCEPTED for tap in final_replay.taps):
            return RuntimeSolutionSearchResult(
                False, tuple(actions), tuple(diagnostics),
                final_replay.failure_reason or "final_runtime_replay_failed", final_replay,
            )
        return RuntimeSolutionSearchResult(True, tuple(actions), tuple(diagnostics), replay_result=final_replay)

    def _find_window_open(self, level, actions, node_id: str, start_time: float) -> tuple[float, float] | None:
        prior = [SolutionAction(action.time_seconds, action.tap_node_id) for action in actions]
        limit = float(level.timeLimitSeconds)
        time = max(0.0, start_time)
        while time <= limit + 1e-9:
            replay = RuntimeSimulator().simulate(level, prior, end_time=time)
            if replay.failure_reason is not None or replay.state.outcome.value != "inProgress":
                return None
            snapshot = switch_eligibility(replay.state)
            if snapshot.eligible_node_id == node_id and snapshot.travel_time_seconds is not None:
                # Eligibility gives the exact remaining travel time, so derive both
                # boundaries without relying on approximate route geometry.
                close = time + snapshot.travel_time_seconds
                opening = max(start_time, close - float(level.rules.switch_lookahead_seconds))
                opened_state = RuntimeSimulator().simulate(level, prior, end_time=opening).state
                opened_snapshot = switch_eligibility(opened_state)
                if opened_snapshot.eligible_node_id == node_id:
                    return opening, close - opening
                return time, snapshot.travel_time_seconds
            time += self.search_step_seconds
        return None

    def _decision_encounters(self, level, topology_solution) -> list[tuple[str, int]]:
        path = list(topology_solution.required_path)
        remaining = Counter(topology_solution.decision_node_ids)
        active_index: dict[str, int] = {}
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        node_by_id = {node.id: node for node in level.graph.nodes}
        encounters: list[tuple[str, int]] = []
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
                encounters.append((node_id, rotations))
                remaining[node_id] -= rotations
        # Malformed/legacy metadata should fail explicitly instead of silently
        # dropping topology decisions that cannot be mapped to a route visit.
        if any(count != 0 for count in remaining.values()):
            return [(node_id, count) for node_id, count in Counter(topology_solution.decision_node_ids).items() if count]
        return encounters
