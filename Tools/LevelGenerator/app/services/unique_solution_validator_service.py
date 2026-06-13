from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class UniqueSolutionValidationIssue:
    severity: str
    code: str
    message: str
    related_node_id: str | None = None
    related_edge_id: str | None = None


@dataclass(frozen=True)
class UniqueSolutionSearchState:
    """State required for future exhaustive unique-solution traversal."""

    current_node_id: str
    active_edge_by_node_id: tuple[tuple[str, str | None], ...]
    has_collected_package: bool
    visited_node_ids: tuple[str, ...]
    tap_history: tuple[str, ...]
    revisit_counts: tuple[tuple[str, int], ...]
    traversal_depth: int
    current_edge_id: str | None = None
    elapsed_time_seconds: float = 0.0


@dataclass(frozen=True)
class UniqueSolutionValidationConfig:
    max_taps: int
    max_traversal_depth: int
    allow_loops: bool
    allow_rejoins: bool
    allow_revisits: bool
    require_package_gate: bool
    max_explored_states: int = 50000


@dataclass(frozen=True)
class UniqueSolutionValidationResult:
    requires_unique_solution: bool
    is_exhaustive: bool
    solution_count: int | None = None
    issues: tuple[UniqueSolutionValidationIssue, ...] = field(default_factory=tuple)
    initial_state: UniqueSolutionSearchState | None = None
    config: UniqueSolutionValidationConfig | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    explored_states: int = 0
    max_depth_reached: int = 0
    termination_reason: str = "not_started"
    terminal_reason_counts: tuple[tuple[str, int], ...] = field(default_factory=tuple)


class UniqueSolutionValidatorService:
    """Counts bounded structural solutions for generated levels."""

    def validate_unique_solution(self, generated_level) -> UniqueSolutionValidationResult:
        topology_rules = self._topology_rules(generated_level)
        requires_unique_solution = bool(topology_rules.get("requiresUniqueSolution", False))
        config = self._config(generated_level, topology_rules)
        initial_state = self._initial_state(generated_level)

        if not requires_unique_solution:
            return UniqueSolutionValidationResult(
                requires_unique_solution=False,
                is_exhaustive=False,
                initial_state=initial_state,
                config=config,
                notes=("unique_solution_not_required_by_topology_rules",),
            )

        enumeration = self._enumerate_solutions(generated_level, initial_state, config)
        issues = self._issues_for_result(enumeration)
        return UniqueSolutionValidationResult(
            requires_unique_solution=True,
            is_exhaustive=enumeration.is_exhaustive,
            solution_count=enumeration.solution_count,
            issues=issues,
            initial_state=initial_state,
            config=config,
            notes=enumeration.notes,
            explored_states=enumeration.explored_states,
            max_depth_reached=enumeration.max_depth_reached,
            termination_reason=enumeration.termination_reason,
            terminal_reason_counts=enumeration.terminal_reason_counts,
        )

    def validateUniqueSolution(self, generated_level) -> UniqueSolutionValidationResult:
        return self.validate_unique_solution(generated_level)

    def _topology_rules(self, generated_level) -> dict[str, Any]:
        metadata = getattr(generated_level, "mechanic_metadata", {}) or {}
        topology_rules = metadata.get("topologyRules")
        return dict(topology_rules) if isinstance(topology_rules, dict) else {}

    def _config(
        self,
        generated_level,
        topology_rules: dict[str, Any],
    ) -> UniqueSolutionValidationConfig:
        level = generated_level.level_document
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        valid_outgoing_counts = [
            len(self._valid_outgoing_edge_ids(node, edge_by_id))
            for node in level.graph.nodes
        ]
        max_switch_rotation_taps = max((count - 1 for count in valid_outgoing_counts), default=0)
        max_taps = max(
            int(getattr(level, "parTaps", 0) or 0),
            len(getattr(generated_level.solution, "actions", ()) or ()),
            int(getattr(generated_level.solution, "maxTaps", 0) or 0),
        )
        max_depth = max(8, len(level.graph.nodes) * 4)
        if topology_rules.get("allowsCycles") or topology_rules.get("allowsRevisit"):
            max_depth = max(max_depth, len(level.graph.nodes) * 8)
        max_taps = max(max_taps, max_depth * max_switch_rotation_taps)
        max_explored_states = max(
            50000,
            len(level.graph.nodes) * max(1, len(level.graph.edges)) * 512,
        )

        return UniqueSolutionValidationConfig(
            max_taps=max_taps,
            max_traversal_depth=max_depth,
            allow_loops=bool(topology_rules.get("allowsCycles", False)),
            allow_rejoins=bool(topology_rules.get("allowsRejoin", False)),
            allow_revisits=bool(topology_rules.get("allowsRevisit", False)),
            require_package_gate=bool(topology_rules.get("requiresPackageGate", False)),
            max_explored_states=max_explored_states,
        )

    def _initial_state(self, generated_level) -> UniqueSolutionSearchState:
        level = generated_level.level_document
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        active_edges: list[tuple[str, str | None]] = []
        for node in level.graph.nodes:
            valid_edges = self._valid_outgoing_edge_ids(node, edge_by_id)
            active_edges.append((node.id, valid_edges[0] if valid_edges else None))

        visited = (level.startNodeID,)
        revisit_counts = tuple(sorted(Counter(visited).items()))
        return UniqueSolutionSearchState(
            current_node_id=level.startNodeID,
            active_edge_by_node_id=tuple(sorted(active_edges)),
            has_collected_package=level.startNodeID == level.packageNodeID,
            visited_node_ids=visited,
            tap_history=(),
            revisit_counts=revisit_counts,
            traversal_depth=0,
        )

    def _enumerate_solutions(
        self,
        generated_level,
        initial_state: UniqueSolutionSearchState,
        config: UniqueSolutionValidationConfig,
    ) -> "_EnumerationResult":
        level = generated_level.level_document
        node_by_id = {node.id: node for node in level.graph.nodes}
        edge_by_id = {edge.id: edge for edge in level.graph.edges}
        queue: deque[UniqueSolutionSearchState] = deque([initial_state])
        solution_count = 0
        explored_states = 0
        max_depth_reached = initial_state.traversal_depth
        terminal_reasons: Counter[str] = Counter()
        depth_limited = False
        state_limited = False

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
                else:
                    terminal_reasons["destination_before_package"] += 1
                continue

            if state.traversal_depth >= config.max_traversal_depth:
                depth_limited = True
                terminal_reasons["max_traversal_depth_reached"] += 1
                continue

            node = node_by_id.get(state.current_node_id)
            if node is None:
                terminal_reasons["missing_current_node"] += 1
                continue

            valid_edges = self._valid_outgoing_edge_ids(node, edge_by_id)
            if not valid_edges:
                terminal_reasons["dead_end"] += 1
                continue

            for tap_count in self._tap_options(valid_edges):
                if len(state.tap_history) + tap_count > config.max_taps:
                    terminal_reasons["max_taps_reached"] += 1
                    continue

                active_edges = dict(state.active_edge_by_node_id)
                next_edge_id = self._rotated_edge_id(active_edges.get(node.id), valid_edges, tap_count)
                if next_edge_id is None:
                    terminal_reasons["active_edge_missing"] += 1
                    continue

                edge = edge_by_id.get(next_edge_id)
                if edge is None or edge.fromNodeID != node.id:
                    terminal_reasons["active_edge_invalid"] += 1
                    continue

                active_edges[node.id] = next_edge_id
                next_node_id = edge.toNodeID
                visited_node_ids = (*state.visited_node_ids, next_node_id)
                tap_history = state.tap_history + ((node.id,) * tap_count)
                queue.append(
                    UniqueSolutionSearchState(
                        current_node_id=next_node_id,
                        active_edge_by_node_id=tuple(sorted(active_edges.items())),
                        has_collected_package=(
                            state.has_collected_package or next_node_id == level.packageNodeID
                        ),
                        visited_node_ids=visited_node_ids,
                        tap_history=tap_history,
                        revisit_counts=tuple(sorted(Counter(visited_node_ids).items())),
                        traversal_depth=state.traversal_depth + 1,
                        current_edge_id=edge.id,
                        elapsed_time_seconds=state.elapsed_time_seconds,
                    )
                )

        if state_limited:
            termination_reason = "max_explored_states_reached"
        elif depth_limited:
            termination_reason = "max_traversal_depth_reached"
        else:
            termination_reason = "exhausted"

        is_exhaustive = not state_limited and not depth_limited
        notes: tuple[str, ...] = ("bounded_structural_enumeration",)
        if config.allow_loops:
            notes = (*notes, "declared_loops_traversed_with_depth_limit")
        if config.allow_revisits:
            notes = (*notes, "revisits_traversed_with_depth_limit")
        if config.allow_rejoins:
            notes = (*notes, "rejoin_paths_counted_separately")

        return _EnumerationResult(
            solution_count=solution_count,
            explored_states=explored_states,
            max_depth_reached=max_depth_reached,
            termination_reason=termination_reason,
            terminal_reason_counts=tuple(sorted(terminal_reasons.items())),
            is_exhaustive=is_exhaustive,
            notes=notes,
        )

    def _issues_for_result(self, result: "_EnumerationResult") -> tuple[UniqueSolutionValidationIssue, ...]:
        if result.solution_count > 1:
            return (
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="unique_solution_multiple_solutions",
                    message=(
                        "Unique solution search found more than one valid package-before-destination solution "
                        f"(solutions={result.solution_count}, exploredStates={result.explored_states})."
                    ),
                ),
            )
        if not result.is_exhaustive:
            return (
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="unique_solution_search_limit_reached",
                    message=(
                        "Unique solution search hit a traversal limit before proving uniqueness "
                        f"(solutions={result.solution_count}, exploredStates={result.explored_states}, "
                        f"maxDepthReached={result.max_depth_reached}, termination={result.termination_reason})."
                    ),
                ),
            )
        if result.solution_count == 0:
            return (
                UniqueSolutionValidationIssue(
                    severity="error",
                    code="unique_solution_not_found",
                    message=(
                        "Unique solution search found no valid package-before-destination solution "
                        f"(exploredStates={result.explored_states})."
                    ),
                ),
            )
        return ()

    def _valid_outgoing_edge_ids(self, node, edge_by_id: dict[str, Any]) -> list[str]:
        return [
            edge_id
            for edge_id in node.outgoingEdgeIDs
            if edge_id in edge_by_id and edge_by_id[edge_id].fromNodeID == node.id
        ]

    def _tap_options(self, valid_edge_ids: list[str]) -> range:
        if len(valid_edge_ids) <= 1:
            return range(1)
        return range(len(valid_edge_ids))

    def _rotated_edge_id(
        self,
        current_edge_id: str | None,
        valid_edge_ids: list[str],
        tap_count: int,
    ) -> str | None:
        if not valid_edge_ids:
            return None
        current_index = (
            valid_edge_ids.index(current_edge_id)
            if current_edge_id in valid_edge_ids
            else 0
        )
        return valid_edge_ids[(current_index + tap_count) % len(valid_edge_ids)]


@dataclass(frozen=True)
class _EnumerationResult:
    solution_count: int
    explored_states: int
    max_depth_reached: int
    termination_reason: str
    terminal_reason_counts: tuple[tuple[str, int], ...]
    is_exhaustive: bool
    notes: tuple[str, ...]
