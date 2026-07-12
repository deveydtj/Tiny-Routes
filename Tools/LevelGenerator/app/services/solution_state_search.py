from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class SolutionStateSearchResult:
    solution_count: int
    explored_states: int
    max_depth_reached: int
    termination_reason: str
    terminal_reason_counts: tuple[tuple[str, int], ...]
    is_exhaustive: bool
    notes: tuple[str, ...]
    successful_path_summaries: tuple[Any, ...]
    destination_before_package_summaries: tuple[Any, ...]
    failure_path_summaries: tuple[Any, ...]
    shortest_valid_route_length: int | None


class SolutionStateSearch:
    """Performs bounded decision-state traversal without formatting validation reports."""

    def __init__(self, path_summary_limit: int = 24) -> None:
        self.path_summary_limit = path_summary_limit

    def search(
        self,
        generated_level,
        initial_state,
        config,
        *,
        state_factory: Callable[..., Any],
        path_summary_factory: Callable[[Any, str, Any], Any],
    ) -> SolutionStateSearchResult:
        level = generated_level.level_document
        node_by_id = {node.id: node for node in level.graph.nodes}
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        queue = deque([initial_state])
        solution_count = 0
        explored_states = 0
        max_depth_reached = initial_state.traversal_depth
        terminal_reasons: Counter[str] = Counter()
        depth_limited = False
        state_limited = False
        successes: list[Any] = []
        package_bypasses: list[Any] = []
        failures: list[Any] = []

        def record(target: list[Any], state, reason: str) -> None:
            if len(target) < self.path_summary_limit:
                target.append(path_summary_factory(state, reason, level))

        while queue:
            if explored_states >= config.max_explored_states:
                state_limited = True
                break
            state = queue.popleft()
            explored_states += 1
            max_depth_reached = max(max_depth_reached, state.traversal_depth)
            if state.current_node_id == level.destinationNodeID:
                if state.has_collected_package:
                    solution_count += 1
                    terminal_reasons["success"] += 1
                    record(successes, state, "success")
                else:
                    terminal_reasons["destination_before_package"] += 1
                    record(package_bypasses, state, "destination_before_package")
                continue
            if state.traversal_depth >= config.max_traversal_depth:
                depth_limited = True
                terminal_reasons["max_traversal_depth_reached"] += 1
                record(failures, state, "max_traversal_depth_reached")
                continue
            node = node_by_id.get(state.current_node_id)
            if node is None:
                terminal_reasons["missing_current_node"] += 1
                record(failures, state, "missing_current_node")
                continue
            valid_edges = self._valid_outgoing_edge_ids(node, edge_by_id)
            if not valid_edges:
                terminal_reasons["dead_end"] += 1
                record(failures, state, "dead_end")
                continue
            for decision_count in self._decision_options(valid_edges):
                if len(state.tap_history) + decision_count > config.max_taps:
                    terminal_reasons["max_taps_reached"] += 1
                    record(failures, state, "max_taps_reached")
                    continue
                active_edges = dict(state.active_edge_by_node_id)
                next_edge_id = self._rotated_edge_id(active_edges.get(node.id), valid_edges, decision_count)
                edge = edge_by_id.get(next_edge_id) if next_edge_id else None
                if edge is None or edge.fromNodeID != node.id:
                    terminal_reasons["active_edge_invalid"] += 1
                    record(failures, state, "active_edge_invalid")
                    continue
                active_edges[node.id] = next_edge_id
                next_node_id = edge.toNodeID
                visited = (*state.visited_node_ids, next_node_id)
                decisions = state.tap_history + ((node.id,) * decision_count)
                queue.append(state_factory(
                    current_node_id=next_node_id,
                    active_edge_by_node_id=tuple(sorted(active_edges.items())),
                    has_collected_package=state.has_collected_package or next_node_id == level.packageNodeID,
                    visited_node_ids=visited,
                    traversed_edge_ids=(*state.traversed_edge_ids, edge.id),
                    tap_history=decisions,
                    revisit_counts=tuple(sorted(Counter(visited).items())),
                    traversal_depth=state.traversal_depth + 1,
                    current_edge_id=edge.id,
                    elapsed_time_seconds=state.elapsed_time_seconds,
                ))

        termination_reason = (
            "max_explored_states_reached" if state_limited
            else "max_traversal_depth_reached" if depth_limited
            else "exhausted"
        )
        notes = ["bounded_structural_enumeration"]
        if config.allow_loops:
            notes.append("declared_loops_traversed_with_depth_limit")
        if config.allow_revisits:
            notes.append("revisits_traversed_with_depth_limit")
        if config.allow_rejoins:
            notes.append("rejoin_paths_counted_separately")
        return SolutionStateSearchResult(
            solution_count=solution_count,
            explored_states=explored_states,
            max_depth_reached=max_depth_reached,
            termination_reason=termination_reason,
            terminal_reason_counts=tuple(sorted(terminal_reasons.items())),
            is_exhaustive=not state_limited and not depth_limited,
            notes=tuple(notes),
            successful_path_summaries=tuple(successes),
            destination_before_package_summaries=tuple(package_bypasses),
            failure_path_summaries=tuple(failures),
            shortest_valid_route_length=min((summary.route_length for summary in successes), default=None),
        )

    @staticmethod
    def _valid_outgoing_edge_ids(node, edge_by_id: dict[str, Any]) -> list[str]:
        return [edge_id for edge_id in node.outgoingEdgeIDs if edge_id in edge_by_id and edge_by_id[edge_id].fromNodeID == node.id]

    @staticmethod
    def _decision_options(valid_edge_ids: list[str]) -> range:
        return range(1) if len(valid_edge_ids) <= 1 else range(len(valid_edge_ids))

    @staticmethod
    def _rotated_edge_id(current_edge_id: str | None, valid_edge_ids: list[str], decision_count: int) -> str | None:
        if not valid_edge_ids:
            return None
        current_index = valid_edge_ids.index(current_edge_id) if current_edge_id in valid_edge_ids else 0
        return valid_edge_ids[(current_index + decision_count) % len(valid_edge_ids)]
