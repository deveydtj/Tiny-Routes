from __future__ import annotations

from dataclasses import dataclass

from tiny_routes_core.models import LevelDocument, SolutionActionModel, SolutionModel
from tiny_routes_core.simulation import LevelOutcome, RuntimeSimulator, switch_eligibility


@dataclass(frozen=True)
class ActionTiming:
    node_id: str
    time_seconds: float
    window_open_seconds: float | None
    window_close_seconds: float | None

    @property
    def early_margin_seconds(self) -> float | None:
        return None if self.window_open_seconds is None else self.time_seconds - self.window_open_seconds

    @property
    def late_margin_seconds(self) -> float | None:
        return None if self.window_close_seconds is None else self.window_close_seconds - self.time_seconds


class RuntimeSolutionService:
    """Verified solution search and timing diagnostics backed by the parity simulator."""

    def __init__(self, *, search_step_seconds: float = 0.02, safety_margin_seconds: float = 0.08) -> None:
        self.search_step_seconds = search_step_seconds
        self.safety_margin_seconds = safety_margin_seconds
        self._simulator = RuntimeSimulator()

    def replay(self, level: LevelDocument, solution: SolutionModel, *, end_time: float | None = None):
        return self._simulator.simulate(level, solution.actions, end_time=end_time)

    def analyze(self, level: LevelDocument, solution: SolutionModel) -> tuple[ActionTiming, ...]:
        timings: list[ActionTiming] = []
        prefix: list[SolutionActionModel] = []
        for action in sorted(solution.actions, key=lambda value: float(value.timeSeconds)):
            at_tap = self._simulator.simulate(level, prefix, end_time=float(action.timeSeconds))
            snapshot = switch_eligibility(at_tap.state)
            if snapshot.upcoming_node_id == action.tapNodeID and snapshot.travel_time_seconds is not None:
                close = float(action.timeSeconds) + snapshot.travel_time_seconds
                opening = max(0.0, close - float(level.rules.switch_lookahead_seconds))
            else:
                opening = close = None
            timings.append(ActionTiming(action.tapNodeID, float(action.timeSeconds), opening, close))
            prefix.append(action)
        return tuple(timings)

    def find_verified(self, level: LevelDocument, *, maximum_actions: int = 12) -> SolutionModel | None:
        """Search branch choices at actual eligibility windows and return only a passing replay."""
        queue: list[tuple[tuple[SolutionActionModel, ...], float]] = [((), 0.0)]
        seen: set[tuple] = set()
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        node_by_id = {node.id: node for node in level.graph.nodes}

        while queue:
            actions, search_after = queue.pop(0)
            replay = self._simulator.simulate(level, actions)
            if replay.state.outcome == LevelOutcome.COMPLETED:
                return SolutionModel(
                    levelID=level.id,
                    description="Verified by Level Editor runtime search",
                    expectedOutcome="completed",
                    maxTaps=len(actions),
                    requiresWithinTimeLimit=True,
                    actions=list(actions),
                    isPlaceholder=False,
                )
            if len(actions) >= maximum_actions:
                continue
            opening = self._next_window(level, actions, search_after)
            if opening is None:
                continue
            node_id, open_time, close_time, state = opening
            outgoing = [edge_id for edge_id in node_by_id[node_id].outgoingEdgeIDs if edge_id in edge_by_id]
            cooldown = max(float(level.rules.switch_tap_cooldown_seconds), 0.0) + 0.001
            first_time = open_time + self.safety_margin_seconds
            for rotations in range(len(outgoing)):
                tap_times = [first_time + index * cooldown for index in range(rotations)]
                if tap_times and tap_times[-1] > close_time - self.safety_margin_seconds + 1e-9:
                    continue
                candidate = actions + tuple(
                    SolutionActionModel(timeSeconds=tap_time, tapNodeID=node_id) for tap_time in tap_times
                )
                probe_time = min(close_time + self.search_step_seconds, float(level.timeLimitSeconds))
                probe = self._simulator.simulate(level, candidate, end_time=probe_time)
                if probe.failure_reason is not None:
                    continue
                signature = (
                    probe.state.current_node_id,
                    probe.state.current_edge_id,
                    round(probe.state.edge_progress, 4),
                    probe.state.package_collected,
                    tuple(sorted(probe.state.switch_active_edge_ids.items())),
                )
                if signature in seen:
                    continue
                seen.add(signature)
                queue.append((candidate, probe_time))
        return None

    def _next_window(self, level, actions: tuple[SolutionActionModel, ...], start: float):
        time = max(0.0, start)
        while time <= float(level.timeLimitSeconds) + 1e-9:
            replay = self._simulator.simulate(level, actions, end_time=time)
            if replay.failure_reason is not None or replay.state.outcome != LevelOutcome.IN_PROGRESS:
                return None
            snapshot = switch_eligibility(replay.state)
            if snapshot.eligible_node_id and snapshot.travel_time_seconds is not None:
                close = time + snapshot.travel_time_seconds
                opening = max(start, close - float(level.rules.switch_lookahead_seconds))
                opened = self._simulator.simulate(level, actions, end_time=opening)
                return snapshot.eligible_node_id, opening, close, opened.state
            time += self.search_step_seconds
        return None
