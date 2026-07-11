from __future__ import annotations

from dataclasses import dataclass

from tiny_routes_core.models import SwitchInteractionMode
from tiny_routes_core.simulation import RuntimeSimulator

from ..models.simulation import SimulationResult, SimulationStep
from .route_timing_service import RouteTimingService


class PythonSolutionSimulatorService:
    def __init__(self) -> None:
        self.route_timing = RouteTimingService()

    def simulate(self, generated_level, max_step_count: int = 1000) -> SimulationResult:
        if generated_level.level_document.rules.switch_interaction_mode == SwitchInteractionMode.LIVE_LOOKAHEAD:
            return self._simulate_live_lookahead(generated_level, max_step_count)
        level, nodes, edges, active_edges, state, steps, terminal = self._prepare_simulation(generated_level)
        if terminal is not None:
            return terminal

        actions = sorted(generated_level.solution.actions, key=lambda action: float(action.timeSeconds))
        for action in actions:
            action_time = float(action.timeSeconds)
            if action_time < state.elapsed_time_seconds:
                return self._failed("solution_actions_not_monotonic", steps, state)
            terminal = self._advance_to_time(level, nodes, edges, active_edges, state, action_time, steps, max_step_count)
            if terminal is not None:
                return terminal
            terminal = self._rotate_switch(nodes, edges, active_edges, state, action.tapNodeID, steps)
            if terminal is not None:
                return terminal
            state.tap_count += 1

        terminal = self._advance_to_time(
            level,
            nodes,
            edges,
            active_edges,
            state,
            float(level.timeLimitSeconds),
            steps,
            max_step_count,
        )
        if terminal is not None:
            return terminal
        return self._failed("time_expired", steps, state)

    def _simulate_live_lookahead(self, generated_level, max_step_count: int) -> SimulationResult:
        """Compatibility adapter over the shared parity runtime.

        Generator callers keep their established result model while all version-2
        interaction decisions are made by ``tiny_routes_core``.
        """
        core_result = RuntimeSimulator(maximum_step_count=max_step_count).simulate(
            generated_level.level_document,
            generated_level.solution.actions,
        )
        steps = [
            SimulationStep(
                time_seconds=round(event.time_seconds, 3),
                event=event.kind,
                node_id=event.node_id,
                edge_id=event.edge_id,
                detail=event.detail,
            )
            for event in core_result.events
        ]
        return SimulationResult(
            passed=core_result.passed,
            outcome="completed" if core_result.passed else "failed",
            failure_reason=core_result.failure_reason,
            elapsed_time_seconds=round(core_result.state.elapsed_time, 3),
            tap_count=core_result.state.accepted_tap_count,
            reached_package=core_result.state.package_collected,
            reached_destination=core_result.passed,
            steps=steps,
        )

    def arrival_time_for_action(self, generated_level, action_index: int, max_step_count: int = 1000) -> float | None:
        sorted_actions = sorted(generated_level.solution.actions, key=lambda action: float(action.timeSeconds))
        if action_index < 0 or action_index >= len(sorted_actions):
            raise IndexError("action_index is out of range")

        target_action = sorted_actions[action_index]
        level, nodes, edges, active_edges, state, steps, terminal = self._prepare_simulation(generated_level)
        if terminal is not None:
            return None

        for action in sorted_actions[:action_index]:
            action_time = float(action.timeSeconds)
            if action_time < state.elapsed_time_seconds:
                return None
            terminal = self._advance_to_time(level, nodes, edges, active_edges, state, action_time, steps, max_step_count)
            if terminal is not None:
                return None
            terminal = self._rotate_switch(nodes, edges, active_edges, state, action.tapNodeID, steps)
            if terminal is not None:
                return None
            state.tap_count += 1

        action_time = float(target_action.timeSeconds)
        if action_time < state.elapsed_time_seconds:
            return None
        terminal = self._advance_to_time(level, nodes, edges, active_edges, state, action_time, steps, max_step_count)
        if terminal is not None:
            return None

        return self._arrival_time_from_current_state(
            level,
            nodes,
            edges,
            active_edges,
            state,
            target_action.tapNodeID,
            steps,
            max_step_count,
        )

    def _advance_to_time(
        self,
        level,
        nodes,
        edges,
        active_edges,
        state,
        target_time: float,
        steps: list[SimulationStep],
        max_step_count: int,
    ) -> SimulationResult | None:
        tolerance = 1e-9
        while state.elapsed_time_seconds < target_time - tolerance:
            if state.step_count > max_step_count:
                return self._failed("max_step_count_exceeded", steps, state)
            if state.transition is not None:
                transition = state.transition
                remaining_transition_distance = transition.length - state.distance_along_transition
                remaining_time = target_time - state.elapsed_time_seconds
                if remaining_time < remaining_transition_distance - tolerance:
                    state.distance_along_transition += remaining_time
                    state.elapsed_time_seconds = target_time
                    return None

                state.elapsed_time_seconds += max(remaining_transition_distance, 0.0)
                state.current_edge_id = transition.to_edge_id
                state.distance_along_edge = transition.exit_distance_along_to_edge
                state.transition = None
                state.distance_along_transition = 0.0
                state.step_count += 1
                steps.append(
                    SimulationStep(
                        time_seconds=round(state.elapsed_time_seconds, 3),
                        event="end_transition",
                        node_id=state.current_node_id,
                        edge_id=state.current_edge_id,
                    )
                )
                continue

            terminal = self._begin_edge_if_needed(level, nodes, edges, active_edges, state, steps)
            if terminal is not None:
                return terminal

            edge = edges.get(state.current_edge_id)
            if edge is None:
                return self._failed("active_edge_missing", steps, state)

            edge_length = max(self._edge_length(nodes, edge), 1e-9)
            transition = self._smooth_transition(nodes, edges, active_edges, edge)
            edge_target_distance = transition.entry_distance_along_from_edge if transition is not None else edge_length
            remaining_edge_distance = edge_target_distance - state.distance_along_edge
            remaining_time = target_time - state.elapsed_time_seconds
            if remaining_time < remaining_edge_distance - tolerance:
                state.distance_along_edge += remaining_time
                state.elapsed_time_seconds = target_time
                return None

            terminal = self._advance_to_current_edge_target(level, nodes, edges, active_edges, state, steps, transition)
            if terminal is not None:
                return terminal
        state.elapsed_time_seconds = target_time
        return None

    def _rotate_switch(self, nodes, edges, active_edges, state, node_id: str, steps: list[SimulationStep]) -> SimulationResult | None:
        node = nodes.get(node_id)
        if node is None:
            return self._failed("tap_node_missing", steps, state)
        valid_edges = self._valid_outgoing_edge_ids(node, edges)
        if len(valid_edges) <= 1:
            return self._failed("tap_node_is_not_switchable", steps, state)
        if len(valid_edges) > 4:
            return self._failed("switch_has_too_many_outgoing_edges", steps, state)
        current_edge_id = active_edges.get(node_id)
        next_index = 0
        if current_edge_id in valid_edges:
            next_index = (valid_edges.index(current_edge_id) + 1) % len(valid_edges)
        previous_edge_id = active_edges.get(node_id)
        next_edge_id = valid_edges[next_index]
        blocked_by_current_edge = state.current_edge_id is not None and edges[state.current_edge_id].fromNodeID == node_id
        blocked_by_transition = state.transition is not None and state.current_node_id == node_id
        target_node_id = edges[next_edge_id].toNodeID
        steps.append(
            SimulationStep(
                time_seconds=round(state.elapsed_time_seconds, 3),
                event="tap_switch",
                node_id=node_id,
                edge_id=current_edge_id,
                detail=self._tap_detail(
                    previous_edge_id,
                    next_edge_id,
                    target_node_id,
                    state.current_node_id,
                    state.current_edge_id,
                    blocked_by_current_edge,
                    blocked_by_transition,
                ),
            )
        )
        if blocked_by_current_edge:
            return self._failed("tap_ignored_current_edge", steps, state)
        if blocked_by_transition:
            return self._failed("tap_ignored_transition_node", steps, state)

        active_edges[node_id] = next_edge_id
        return None

    def _evaluate_terminal(self, level, state, steps: list[SimulationStep]) -> SimulationResult | None:
        if state.current_node_id != level.destinationNodeID:
            return None
        if not state.reached_package:
            return self._failed("reached_destination_without_package", steps, state)
        return SimulationResult(
            passed=True,
            outcome="completed",
            elapsed_time_seconds=round(state.elapsed_time_seconds, 3),
            tap_count=state.tap_count,
            reached_package=True,
            reached_destination=True,
            steps=list(steps),
        )

    def _failed(self, reason: str, steps: list[SimulationStep], state=None) -> SimulationResult:
        return SimulationResult(
            passed=False,
            outcome="failed",
            failure_reason=reason,
            elapsed_time_seconds=round(getattr(state, "elapsed_time_seconds", 0.0), 3),
            tap_count=getattr(state, "tap_count", 0),
            reached_package=getattr(state, "reached_package", False),
            reached_destination=False,
            steps=list(steps),
        )

    def _valid_outgoing_edge_ids(self, node, edges) -> list[str]:
        return [
            edge_id
            for edge_id in node.outgoingEdgeIDs
            if edge_id in edges and edges[edge_id].fromNodeID == node.id
        ]

    def _edge_length(self, nodes, edge) -> float:
        from_node = nodes[edge.fromNodeID]
        to_node = nodes[edge.toNodeID]
        return self.route_timing.edge_length(from_node, to_node, edge.roadShape)

    def _prepare_simulation(self, generated_level):
        level = generated_level.level_document
        nodes = {node.id: node for node in level.graph.nodes}
        edges = {edge.id: edge for edge in level.graph.edges}
        active_edges: dict[str, str | None] = {}
        steps: list[SimulationStep] = []

        for node in level.graph.nodes:
            valid_edges = self._valid_outgoing_edge_ids(node, edges)
            active_edges[node.id] = valid_edges[0] if valid_edges else None

        if level.startNodeID not in nodes:
            return level, nodes, edges, active_edges, _SimulationState(current_node_id=level.startNodeID), steps, self._failed(
                "missing_start_node",
                steps,
            )

        state = _SimulationState(current_node_id=level.startNodeID)
        if state.current_node_id == level.packageNodeID:
            state.reached_package = True
        terminal = self._evaluate_terminal(level, state, steps)
        return level, nodes, edges, active_edges, state, steps, terminal

    def _begin_edge_if_needed(self, level, nodes, edges, active_edges, state, steps: list[SimulationStep]) -> SimulationResult | None:
        if state.current_edge_id is not None:
            return None

        terminal = self._evaluate_terminal(level, state, steps)
        if terminal is not None:
            return terminal

        edge_id = active_edges.get(state.current_node_id)
        if edge_id is None:
            return self._failed("dead_end", steps, state)

        state.current_edge_id = edge_id
        state.distance_along_edge = 0.0
        state.step_count += 1
        steps.append(
            SimulationStep(
                time_seconds=round(state.elapsed_time_seconds, 3),
                event="begin_edge",
                node_id=state.current_node_id,
                edge_id=edge_id,
            )
        )
        return None

    def _smooth_transition(self, nodes, edges, active_edges, edge) -> "_Transition | None":
        node = nodes.get(edge.toNodeID)
        if node is None:
            return None
        valid_outgoing_edge_ids = self._valid_outgoing_edge_ids(node, edges)
        next_edge_id = active_edges.get(node.id)
        if len(valid_outgoing_edge_ids) != 1 or next_edge_id not in valid_outgoing_edge_ids:
            return None
        next_edge = edges.get(next_edge_id)
        if next_edge is None or next_edge.fromNodeID != node.id:
            return None
        connector = self.route_timing.perpendicular_connector(
            nodes[edge.fromNodeID],
            nodes[edge.toNodeID],
            edge.roadShape,
            nodes[next_edge.fromNodeID],
            nodes[next_edge.toNodeID],
            next_edge.roadShape,
        )
        if connector is None:
            return None
        return _Transition(
            node_id=node.id,
            to_edge_id=next_edge_id,
            length=connector.length,
            entry_distance_along_from_edge=connector.entry_distance_along_incoming_path,
            exit_distance_along_to_edge=connector.exit_distance_along_outgoing_path,
        )

    def _advance_to_current_edge_target(
        self,
        level,
        nodes,
        edges,
        active_edges,
        state,
        steps: list[SimulationStep],
        transition: "_Transition | None" = None,
    ) -> SimulationResult | None:
        edge = edges.get(state.current_edge_id)
        if edge is None:
            return self._failed("active_edge_missing", steps, state)

        edge_length = max(self._edge_length(nodes, edge), 1e-9)
        transition = transition if transition is not None else self._smooth_transition(nodes, edges, active_edges, edge)
        edge_target_distance = transition.entry_distance_along_from_edge if transition is not None else edge_length
        remaining_edge_distance = edge_target_distance - state.distance_along_edge
        state.elapsed_time_seconds += remaining_edge_distance
        state.current_node_id = edge.toNodeID
        state.current_edge_id = None
        state.distance_along_edge = 0.0
        state.step_count += 1
        steps.append(
            SimulationStep(
                time_seconds=round(state.elapsed_time_seconds, 3),
                event="arrive_node",
                node_id=state.current_node_id,
                edge_id=edge.id,
            )
        )
        if state.current_node_id == level.packageNodeID:
            state.reached_package = True
            steps.append(
                SimulationStep(
                    time_seconds=round(state.elapsed_time_seconds, 3),
                    event="collect_package",
                    node_id=state.current_node_id,
                )
            )
        terminal = self._evaluate_terminal(level, state, steps)
        if terminal is not None:
            return terminal

        if transition is not None:
            state.transition = transition
            state.distance_along_transition = 0.0
            steps.append(
                SimulationStep(
                    time_seconds=round(state.elapsed_time_seconds, 3),
                    event="begin_transition",
                    node_id=state.current_node_id,
                    edge_id=transition.to_edge_id,
                    detail=(
                        f"entryDistance={transition.entry_distance_along_from_edge:.3f}"
                        f" exitDistance={transition.exit_distance_along_to_edge:.3f}"
                        f" length={transition.length:.3f}"
                    ),
                )
            )
        return None

    def _advance_across_current_edge(self, level, nodes, edges, active_edges, state, steps: list[SimulationStep]) -> SimulationResult | None:
        terminal = self._advance_to_current_edge_target(level, nodes, edges, active_edges, state, steps)
        if terminal is not None:
            return terminal
        if state.transition is None:
            return None

        transition = state.transition
        state.elapsed_time_seconds += max(transition.length - state.distance_along_transition, 0.0)
        state.current_edge_id = transition.to_edge_id
        state.distance_along_edge = transition.exit_distance_along_to_edge
        state.transition = None
        state.distance_along_transition = 0.0
        state.step_count += 1
        steps.append(
            SimulationStep(
                time_seconds=round(state.elapsed_time_seconds, 3),
                event="end_transition",
                node_id=state.current_node_id,
                edge_id=state.current_edge_id,
            )
        )
        return None

    def _advance_until_node(
        self,
        level,
        nodes,
        edges,
        active_edges,
        state,
        target_node_id: str,
        steps: list[SimulationStep],
        max_step_count: int,
    ) -> float | None:
        if target_node_id not in nodes:
            return None

        while True:
            if state.current_edge_id is None and state.current_node_id == target_node_id:
                return state.elapsed_time_seconds
            if state.step_count > max_step_count:
                return None

            terminal = self._begin_edge_if_needed(level, nodes, edges, active_edges, state, steps)
            if terminal is not None:
                return state.elapsed_time_seconds if state.current_node_id == target_node_id else None

            terminal = self._advance_across_current_edge(level, nodes, edges, active_edges, state, steps)
            if terminal is not None and state.current_node_id != target_node_id:
                return None

    def _arrival_time_from_current_state(
        self,
        level,
        nodes,
        edges,
        active_edges,
        state,
        target_node_id: str,
        steps: list[SimulationStep],
        max_step_count: int,
    ) -> float | None:
        if target_node_id not in nodes:
            return None

        if state.current_edge_id is None and state.current_node_id == target_node_id:
            return state.elapsed_time_seconds

        if state.current_edge_id is not None:
            edge = edges.get(state.current_edge_id)
            if edge is None:
                return None
            if edge.fromNodeID == target_node_id:
                return self._last_arrival_time_for_node(steps, target_node_id)

        return self._advance_until_node(
            level,
            nodes,
            edges,
            active_edges,
            state,
            target_node_id,
            steps,
            max_step_count,
        )

    def _last_arrival_time_for_node(self, steps: list[SimulationStep], node_id: str) -> float | None:
        for step in reversed(steps):
            if step.event == "arrive_node" and step.node_id == node_id:
                return float(step.time_seconds)
        return None

    def _tap_detail(
        self,
        previous_edge_id: str | None,
        next_edge_id: str | None,
        target_node_id: str | None,
        current_node_id: str | None,
        current_edge_id: str | None,
        blocked_because_current_edge_starts_at_tapped_node: bool,
        blocked_because_transition_is_at_tapped_node: bool,
    ) -> str:
        return (
            f"previousEdge={previous_edge_id or '(none)'}"
            f" -> nextEdge={next_edge_id or '(none)'}"
            f" -> targetNode={target_node_id or '(none)'}"
            f" currentNode={current_node_id or '(none)'}"
            f" currentEdge={current_edge_id or '(none)'}"
            f" blockedBecauseCurrentEdgeStartsAtTappedNode="
            f"{'true' if blocked_because_current_edge_starts_at_tapped_node else 'false'}"
            f" blockedBecauseTransitionIsAtTappedNode="
            f"{'true' if blocked_because_transition_is_at_tapped_node else 'false'}"
        )


@dataclass(frozen=True)
class _Transition:
    node_id: str
    to_edge_id: str
    length: float
    entry_distance_along_from_edge: float
    exit_distance_along_to_edge: float


class _SimulationState:
    def __init__(self, current_node_id: str) -> None:
        self.current_node_id = current_node_id
        self.current_edge_id: str | None = None
        self.distance_along_edge = 0.0
        self.transition: _Transition | None = None
        self.distance_along_transition = 0.0
        self.elapsed_time_seconds = 0.0
        self.tap_count = 0
        self.reached_package = False
        self.step_count = 0
