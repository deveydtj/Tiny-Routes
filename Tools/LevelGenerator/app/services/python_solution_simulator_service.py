from __future__ import annotations

from ..models.simulation import SimulationResult, SimulationStep


class PythonSolutionSimulatorService:
    def simulate(self, generated_level, max_step_count: int = 1000) -> SimulationResult:
        level = generated_level.level_document
        solution = generated_level.solution
        nodes = {node.id: node for node in level.graph.nodes}
        edges = {edge.id: edge for edge in level.graph.edges}
        active_edges: dict[str, str | None] = {}
        steps: list[SimulationStep] = []

        for node in level.graph.nodes:
            valid_edges = self._valid_outgoing_edge_ids(node, edges)
            active_edges[node.id] = valid_edges[0] if valid_edges else None

        if level.startNodeID not in nodes:
            return self._failed("missing_start_node", steps)

        state = _SimulationState(current_node_id=level.startNodeID)
        if state.current_node_id == level.packageNodeID:
            state.reached_package = True
        terminal = self._evaluate_terminal(level, state, steps)
        if terminal is not None:
            return terminal

        actions = sorted(solution.actions, key=lambda action: float(action.timeSeconds))
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

            if state.current_edge_id is None:
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

            edge = edges.get(state.current_edge_id)
            if edge is None:
                return self._failed("active_edge_missing", steps, state)
            edge_length = max(self._edge_length(nodes, edge), 1e-9)
            remaining_edge_distance = edge_length - state.distance_along_edge
            remaining_time = target_time - state.elapsed_time_seconds
            if remaining_time < remaining_edge_distance - tolerance:
                state.distance_along_edge += remaining_time
                state.elapsed_time_seconds = target_time
                return None

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
        state.elapsed_time_seconds = target_time
        return None

    def _rotate_switch(self, nodes, edges, active_edges, state, node_id: str, steps: list[SimulationStep]) -> SimulationResult | None:
        node = nodes.get(node_id)
        if node is None:
            return self._failed("tap_node_missing", steps, state)
        if state.current_edge_id is not None and edges[state.current_edge_id].fromNodeID == node_id:
            return self._failed("tap_ignored_current_edge", steps, state)
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
        active_edges[node_id] = valid_edges[next_index]
        target_node_id = edges[active_edges[node_id]].toNodeID
        steps.append(
            SimulationStep(
                time_seconds=round(state.elapsed_time_seconds, 3),
                event="tap_switch",
                node_id=node_id,
                edge_id=active_edges[node_id],
                detail=f"{previous_edge_id or '(none)'} -> {active_edges[node_id]} -> {target_node_id}",
            )
        )
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
        return abs(float(from_node.x) - float(to_node.x)) + abs(float(from_node.y) - float(to_node.y))


class _SimulationState:
    def __init__(self, current_node_id: str) -> None:
        self.current_node_id = current_node_id
        self.current_edge_id: str | None = None
        self.distance_along_edge = 0.0
        self.elapsed_time_seconds = 0.0
        self.tap_count = 0
        self.reached_package = False
        self.step_count = 0
