from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, replace

from ..models.abstract_puzzle_solution import (
    AbstractPuzzleSolutionMetadata,
    AbstractPuzzleSwitchState,
)
from ..models.difficulty_preset import DifficultyPreset
from ..models.graph_recipe import GraphRecipe, GraphRecipeEdge


class AbstractPuzzleSolverError(ValueError):
    def __init__(self, code: str, message: str, details: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


@dataclass(frozen=True)
class _SearchState:
    node_id: str
    switch_indices: tuple[int, ...]
    collected_package: bool
    path: tuple[str, ...]
    decisions: tuple[str, ...]


@dataclass(frozen=True)
class _CompletedPath:
    state: _SearchState
    reason: str


class AbstractPuzzleSolverService:
    def solve(self, recipe: GraphRecipe, preset: DifficultyPreset) -> GraphRecipe:
        metadata = self.solve_metadata(recipe, preset)
        return replace(
            recipe,
            required_path=metadata.required_path,
            tap_node_ids=metadata.solution_tap_node_ids,
            solved_metadata=metadata,
            notes=(
                *recipe.notes,
                f"Topology solver decisions: {metadata.minimum_required_decisions}",
                f"Abstract solver alternates: {metadata.alternate_path_count}",
                f"Abstract solver dead ends: {metadata.dead_end_count}",
                f"Abstract solver loops: {metadata.loop_count}",
            ),
        )

    def solve_metadata(self, recipe: GraphRecipe, preset: DifficultyPreset) -> AbstractPuzzleSolutionMetadata:
        issues = recipe.validate()
        if issues:
            raise AbstractPuzzleSolverError(
                "abstract_recipe_invalid",
                f"Invalid graph recipe: {', '.join(issues)}",
                tuple(issues),
            )

        outgoing_by_node_id = self._outgoing_by_node_id(recipe.edges)
        switch_ids = tuple(
            node.id
            for node in recipe.nodes
            if len(outgoing_by_node_id.get(node.id, ())) > 1
        )
        if any(len(outgoing_by_node_id[node_id]) > preset.max_outgoing_edges_per_switch for node_id in switch_ids):
            offenders = tuple(
                node_id
                for node_id in switch_ids
                if len(outgoing_by_node_id[node_id]) > preset.max_outgoing_edges_per_switch
            )
            raise AbstractPuzzleSolverError(
                "abstract_switch_too_many_outgoing_edges",
                f"Switch has too many outgoing edges for {preset.name}: {', '.join(offenders)}",
                offenders,
            )

        switch_index_by_id = {node_id: index for index, node_id in enumerate(switch_ids)}
        max_taps = max(preset.required_tap_range[1], len(switch_ids)) + (2 if preset.allow_repeated_switch_taps else 0)
        max_state_count = 900 if preset.name in {"hard", "expert"} else 300
        max_path_steps = max(16, len(recipe.nodes) * 3)

        starts_with_package = recipe.package_node_id == "start"
        initial_indices = self._normalize_switch_indices(
            tuple(0 for _ in switch_ids),
            switch_ids,
            outgoing_by_node_id,
            starts_with_package,
        )
        start_state = _SearchState(
            node_id="start",
            switch_indices=initial_indices,
            collected_package=starts_with_package,
            path=("start",),
            decisions=(),
        )
        queue: deque[_SearchState] = deque([start_state])
        seen: set[tuple[str, tuple[int, ...], bool, int, tuple[str, ...]]] = set()
        successes: list[_CompletedPath] = []
        failures: list[_CompletedPath] = []
        destination_before_package = False
        state_count = 0

        while queue and state_count < max_state_count:
            state = queue.popleft()
            state_count += 1
            seen_key = (
                state.node_id,
                state.switch_indices,
                state.collected_package,
                len(state.decisions),
                state.path[-min(len(state.path), len(recipe.nodes)) :],
            )
            if seen_key in seen:
                continue
            seen.add(seen_key)

            if len(state.path) > max_path_steps:
                failures.append(_CompletedPath(state, "abstract_path_step_limit"))
                continue

            if state.node_id == recipe.destination_node_id:
                if state.collected_package:
                    successes.append(_CompletedPath(state, "success"))
                else:
                    destination_before_package = True
                    failures.append(_CompletedPath(state, "abstract_destination_before_package"))
                continue

            authored_outgoing = outgoing_by_node_id.get(state.node_id, ())
            outgoing = self._usable_outgoing(authored_outgoing, state.collected_package)
            if not outgoing:
                failures.append(_CompletedPath(state, "abstract_dead_end"))
                continue

            for tap_count in self._tap_options(state.node_id, outgoing, state, preset):
                next_decisions = state.decisions + ((state.node_id,) * tap_count)
                if len(next_decisions) > max_taps:
                    failures.append(_CompletedPath(state, "topology_decision_limit"))
                    continue
                switch_indices = state.switch_indices
                active_index = 0
                if state.node_id in switch_index_by_id:
                    switch_tuple_index = switch_index_by_id[state.node_id]
                    current_authored_index = switch_indices[switch_tuple_index]
                    current_edge = authored_outgoing[current_authored_index]
                    current_usable_index = next(
                        (
                            index
                            for index, candidate in enumerate(outgoing)
                            if candidate is current_edge
                        ),
                        0,
                    )
                    active_usable_index = (current_usable_index + tap_count) % len(outgoing)
                    active_edge = outgoing[active_usable_index]
                    active_index = authored_outgoing.index(active_edge)
                    switch_indices = (
                        switch_indices[:switch_tuple_index]
                        + (active_index,)
                        + switch_indices[switch_tuple_index + 1 :]
                    )
                    edge = active_edge
                else:
                    edge = outgoing[0]
                next_node_id = edge.to_node_id
                collected_package = (
                    state.collected_package
                    or next_node_id == recipe.package_node_id
                )
                if collected_package != state.collected_package:
                    switch_indices = self._normalize_switch_indices(
                        switch_indices,
                        switch_ids,
                        outgoing_by_node_id,
                        collected_package,
                    )
                queue.append(
                    _SearchState(
                        node_id=next_node_id,
                        switch_indices=switch_indices,
                        collected_package=collected_package,
                        path=(*state.path, next_node_id),
                        decisions=next_decisions,
                    )
                )

        if queue:
            failures.append(_CompletedPath(start_state, "abstract_state_limit"))

        if not successes:
            reason_counts = Counter(path.reason for path in failures)
            reasons = tuple(sorted(reason_counts))
            preferred_code = "abstract_no_solution"
            if destination_before_package and set(reasons) <= {"abstract_destination_before_package"}:
                preferred_code = "abstract_destination_before_package"
            raise AbstractPuzzleSolverError(
                preferred_code,
                f"Abstract puzzle has no valid package-before-destination solution: {', '.join(reasons) or 'none'}",
                reasons,
            )

        if destination_before_package and not preset.allow_return_loops:
            raise AbstractPuzzleSolverError(
                "abstract_destination_before_package",
                "Destination is reachable before the package for this difficulty.",
            )

        successes.sort(key=lambda path: (len(path.state.decisions), len(path.state.path), path.state.decisions, path.state.path))
        solution = successes[0].state
        minimum_taps = len(solution.decisions)
        minimum_successes = [path for path in successes if len(path.state.decisions) == minimum_taps]
        if len(minimum_successes) > 8:
            raise AbstractPuzzleSolverError(
                "abstract_too_many_equivalent_solutions",
                f"Abstract puzzle has {len(minimum_successes)} equivalent minimum-tap solutions.",
            )
        if minimum_taps > preset.required_tap_range[1]:
            raise AbstractPuzzleSolverError(
                "abstract_too_many_required_taps",
                f"Abstract puzzle requires {minimum_taps} taps, above {preset.required_tap_range[1]} for {preset.name}.",
            )

        repeated_switch_usage = any(count > 1 for count in Counter(solution.decisions).values())
        if repeated_switch_usage and not preset.allow_repeated_switch_taps:
            raise AbstractPuzzleSolverError(
                "abstract_repeated_switch_taps_not_allowed",
                f"Abstract solution repeats a switch tap before {preset.name} allows it.",
            )

        dead_end_nodes = {
            path.state.node_id
            for path in failures
            if path.reason == "abstract_dead_end" and path.state.node_id != recipe.destination_node_id
        }
        false_route_count = len([path for path in failures if path.reason != "topology_decision_limit"])
        loop_count = self._loop_count([path.state.path for path in successes + failures])
        optional_tap_count = max((len(path.state.decisions) for path in successes), default=minimum_taps) - minimum_taps
        switch_states = self._solution_switch_states(solution, switch_ids, outgoing_by_node_id)
        has_state_dependent_roads = any(edge.availability != "always" for edge in recipe.edges)
        if (
            switch_ids
            and not has_state_dependent_roads
            and not dead_end_nodes
            and len(successes) <= 1
            and minimum_taps == 0
        ):
            raise AbstractPuzzleSolverError(
                "abstract_no_meaningful_choice",
                "Abstract puzzle contains switch nodes but no meaningful switch decision.",
            )

        return AbstractPuzzleSolutionMetadata(
            decision_node_ids=solution.decisions,
            solution_switch_states=switch_states,
            required_path=solution.path,
            alternate_path_count=max(0, len(successes) - 1),
            dead_end_count=len(dead_end_nodes),
            failure_path_count=len(failures),
            false_route_count=false_route_count,
            loop_count=loop_count,
            minimum_required_decisions=minimum_taps,
            optional_tap_count=optional_tap_count,
            repeated_switch_usage=repeated_switch_usage,
            package_before_destination=(
                solution.path.index(recipe.package_node_id) < solution.path.index(recipe.destination_node_id)
            ),
            failure_reasons=tuple(sorted(Counter(path.reason for path in failures))),
        )

    def _outgoing_by_node_id(self, edges: tuple[GraphRecipeEdge, ...]) -> dict[str, tuple[GraphRecipeEdge, ...]]:
        outgoing: dict[str, list[GraphRecipeEdge]] = {}
        for edge in edges:
            outgoing.setdefault(edge.from_node_id, []).append(edge)
        return {node_id: tuple(edges) for node_id, edges in outgoing.items()}

    def _usable_outgoing(
        self,
        outgoing: tuple[GraphRecipeEdge, ...],
        collected_package: bool,
    ) -> tuple[GraphRecipeEdge, ...]:
        phase_availability = "afterPackage" if collected_package else "beforePackage"
        return tuple(
            edge
            for edge in outgoing
            if edge.availability in {"always", phase_availability}
        )

    def _normalize_switch_indices(
        self,
        switch_indices: tuple[int, ...],
        switch_ids: tuple[str, ...],
        outgoing_by_node_id: dict[str, tuple[GraphRecipeEdge, ...]],
        collected_package: bool,
    ) -> tuple[int, ...]:
        normalized: list[int] = []
        for node_id, requested_index in zip(switch_ids, switch_indices):
            authored = outgoing_by_node_id[node_id]
            usable = self._usable_outgoing(authored, collected_package)
            if not usable:
                normalized.append(requested_index)
                continue
            requested_edge = (
                authored[requested_index]
                if 0 <= requested_index < len(authored)
                else None
            )
            normalized_edge = requested_edge if requested_edge in usable else usable[0]
            normalized.append(authored.index(normalized_edge))
        return tuple(normalized)

    def _tap_options(
        self,
        node_id: str,
        outgoing: tuple[GraphRecipeEdge, ...],
        state: _SearchState,
        preset: DifficultyPreset,
    ) -> range:
        if len(outgoing) <= 1:
            return range(1)
        if not preset.allow_repeated_switch_taps and node_id in state.decisions:
            return range(1)
        max_taps_here = len(outgoing)
        if not preset.allow_repeated_switch_taps:
            max_taps_here = min(max_taps_here, 2)
        return range(max_taps_here)

    def _solution_switch_states(
        self,
        solution: _SearchState,
        switch_ids: tuple[str, ...],
        outgoing_by_node_id: dict[str, tuple[GraphRecipeEdge, ...]],
    ) -> tuple[AbstractPuzzleSwitchState, ...]:
        states: list[AbstractPuzzleSwitchState] = []
        for node_id, active_index in zip(switch_ids, solution.switch_indices):
            outgoing = outgoing_by_node_id.get(node_id, ())
            if not outgoing:
                continue
            states.append(
                AbstractPuzzleSwitchState(
                    node_id=node_id,
                    active_edge_index=active_index,
                    active_target_node_id=outgoing[active_index].to_node_id,
                )
            )
        return tuple(states)

    def _loop_count(self, paths: list[tuple[str, ...]]) -> int:
        count = 0
        for path in paths:
            visits = Counter(path)
            count += sum(visit_count - 1 for visit_count in visits.values() if visit_count > 1)
        return count
