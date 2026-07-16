from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from statistics import fmean
from typing import Callable

from ..models.abstract_puzzle_solution import AbstractPuzzleSolutionMetadata
from ..models.decision_profile import DecisionProfile
from ..models.graph_recipe import GraphRecipe, GraphRecipeEdge
from ..models.runtime_solution_search import RuntimeSolutionSearchResult


@dataclass(frozen=True)
class _Choice:
    node_id: str
    edge_index: int
    package_collected: bool


@dataclass(frozen=True)
class _Route:
    path: tuple[str, ...]
    choices: tuple[_Choice, ...]
    traversed_edges: tuple[GraphRecipeEdge, ...]
    package_states: tuple[bool, ...]
    outcome: str


class DecisionProfileService:
    """Builds deterministic evidence from bounded graph routes and runtime timing."""

    def analyze(
        self,
        recipe: GraphRecipe,
        topology_solutions: tuple[AbstractPuzzleSolutionMetadata, ...] = (),
        runtime_solution: RuntimeSolutionSearchResult | None = None,
        *,
        route_limit: int = 512,
        legacy_frontload_check: Callable[[], bool] | None = None,
    ) -> DecisionProfile:
        routes = self._enumerate_routes(recipe, route_limit=max(1, route_limit))
        successes = tuple(route for route in routes if route.outcome == "success")
        failures = tuple(route for route in routes if route.outcome != "success")
        metadata = topology_solutions[0] if topology_solutions else recipe.solved_metadata
        primary = self._primary_route(successes, metadata)
        choices = primary.choices if primary else ()
        counts = Counter(choice.node_id for choice in choices)
        repeated_count = sum(count - 1 for count in counts.values())
        state_changes = self._state_changes_on_revisit(choices)
        dependencies = self._ordered_dependencies(choices)
        independent = max(0, len(choices) - len(dependencies))
        minimum_choice_count = min((len(route.choices) for route in successes), default=0)
        equivalent_minimum = sum(len(route.choices) == minimum_choice_count for route in successes)
        before = sum(not choice.package_collected for choice in choices)
        after = len(choices) - before
        phase_metrics = self._package_phase_metrics(recipe, primary)
        impossible_conditions, irrelevant_conditions = self._availability_condition_counts(recipe)
        windows, tap_times, multi_taps = self._runtime_metrics(runtime_solution)
        failure_types = tuple(sorted({route.outcome for route in failures}))
        frontloadable = legacy_frontload_check() if legacy_frontload_check else self._frontloadable(choices)

        return DecisionProfile(
            required_decision_count=len(choices),
            unique_switch_count=len(counts),
            repeated_switch_decision_count=repeated_count,
            switch_state_change_on_revisit_count=state_changes,
            ordered_dependency_count=len(dependencies),
            independent_decision_ratio=round(independent / len(choices), 4) if choices else 0.0,
            equivalent_minimum_solution_count=equivalent_minimum,
            successful_alternate_route_count=max(0, len(successes) - 1),
            failure_route_count=len(failures),
            failure_outcome_types=failure_types,
            dead_end_choice_count=sum(route.outcome == "dead_end" for route in failures),
            destination_before_package_choice_count=sum(
                route.outcome == "destination_before_package" for route in failures
            ),
            recoverable_mistake_count=self._recoverable_choice_count(successes),
            route_revisit_count=self._route_revisit_count(primary.path if primary else ()),
            package_phase_decisions_before=before,
            package_phase_decisions_after=after,
            package_phase_transition_count=phase_metrics["transition_count"],
            state_dependent_route_change_count=phase_metrics["route_change_count"],
            roads_opened_after_package_count=phase_metrics["opened_count"],
            roads_closed_after_package_count=phase_metrics["closed_count"],
            impossible_availability_condition_count=impossible_conditions,
            irrelevant_availability_condition_count=irrelevant_conditions,
            minimum_window_seconds=min(windows) if windows else None,
            average_window_seconds=round(fmean(windows), 4) if windows else None,
            minimum_decision_spacing_seconds=min(self._spacings(tap_times), default=None),
            average_decision_spacing_seconds=(
                round(fmean(self._spacings(tap_times)), 4) if len(tap_times) > 1 else None
            ),
            multiple_taps_in_window_count=multi_taps,
            front_loaded_legacy_solution_possible=frontloadable,
            no_op_or_equivalent_choice_count=self._equivalent_choice_count(recipe),
        )

    def _enumerate_routes(self, recipe: GraphRecipe, route_limit: int) -> tuple[_Route, ...]:
        outgoing: dict[str, list[GraphRecipeEdge]] = {}
        for edge in recipe.edges:
            outgoing.setdefault(edge.from_node_id, []).append(edge)
        max_steps = max(8, len(recipe.nodes) * 3)
        routes: list[_Route] = []

        def visit(
            node: str,
            path: tuple[str, ...],
            choices: tuple[_Choice, ...],
            traversed_edges: tuple[GraphRecipeEdge, ...],
            package_states: tuple[bool, ...],
            has_package: bool,
        ) -> None:
            if len(routes) >= route_limit:
                return
            has_package = has_package or node == recipe.package_node_id
            package_states = (*package_states, has_package)
            if node == recipe.destination_node_id:
                outcome = "success" if has_package else "destination_before_package"
                routes.append(_Route(path, choices, traversed_edges, package_states, outcome))
                return
            authored_edges = outgoing.get(node, ())
            edges = tuple(edge for edge in authored_edges if self._edge_is_usable(edge, has_package))
            if not edges:
                routes.append(_Route(path, choices, traversed_edges, package_states, "dead_end"))
                return
            if len(path) >= max_steps:
                routes.append(_Route(path, choices, traversed_edges, package_states, "loop_or_step_limit"))
                return
            for edge in edges:
                next_choices = choices
                if len(edges) > 1:
                    next_choices = (*choices, _Choice(node, authored_edges.index(edge), has_package))
                visit(
                    edge.to_node_id,
                    (*path, edge.to_node_id),
                    next_choices,
                    (*traversed_edges, edge),
                    package_states,
                    has_package,
                )

        visit("start", ("start",), (), (), (), recipe.package_node_id == "start")
        return tuple(routes)

    def _package_phase_metrics(self, recipe: GraphRecipe, primary: _Route | None) -> dict[str, int]:
        metrics = {
            "transition_count": 0,
            "route_change_count": 0,
            "opened_count": 0,
            "closed_count": 0,
        }
        if primary is None:
            return metrics

        metrics["transition_count"] = sum(
            not before and after
            for before, after in zip(primary.package_states, primary.package_states[1:])
        )
        phases_by_node: dict[str, set[bool]] = {}
        for node_id, has_package in zip(primary.path, primary.package_states):
            phases_by_node.setdefault(node_id, set()).add(has_package)

        outgoing = self._outgoing_edges(recipe)
        changed_nodes = {
            node_id
            for node_id, phases in phases_by_node.items()
            if phases == {False, True}
            and self._usable_edge_indices(outgoing.get(node_id, ()), False)
            != self._usable_edge_indices(outgoing.get(node_id, ()), True)
        }
        metrics["route_change_count"] = len(changed_nodes)
        for index, edge in enumerate(primary.traversed_edges):
            source_phase = primary.package_states[index]
            if edge.from_node_id not in changed_nodes:
                continue
            if source_phase and edge.availability == "afterPackage":
                metrics["opened_count"] += 1
            elif not source_phase and edge.availability == "beforePackage":
                metrics["closed_count"] += 1
        return metrics

    def _availability_condition_counts(self, recipe: GraphRecipe) -> tuple[int, int]:
        reachable_states = self._reachable_node_states(recipe)
        outgoing = self._outgoing_edges(recipe)
        impossible = 0
        irrelevant = 0
        for edge in recipe.edges:
            if edge.availability == "always":
                continue
            required_phase = edge.availability == "afterPackage"
            required_state = (edge.from_node_id, required_phase)
            opposite_state = (edge.from_node_id, not required_phase)
            if required_state not in reachable_states:
                impossible += 1
                continue
            duplicate_target = any(
                candidate is not edge
                and candidate.to_node_id == edge.to_node_id
                and candidate.availability == "always"
                for candidate in outgoing.get(edge.from_node_id, ())
            )
            if opposite_state not in reachable_states or duplicate_target:
                irrelevant += 1
        return impossible, irrelevant

    def _reachable_node_states(self, recipe: GraphRecipe) -> set[tuple[str, bool]]:
        outgoing = self._outgoing_edges(recipe)
        starts_with_package = recipe.package_node_id == "start"
        pending = [("start", starts_with_package)]
        seen: set[tuple[str, bool]] = set()
        while pending:
            node_id, has_package = pending.pop()
            state = (node_id, has_package)
            if state in seen:
                continue
            seen.add(state)
            for edge in outgoing.get(node_id, ()):
                if not self._edge_is_usable(edge, has_package):
                    continue
                next_has_package = has_package or edge.to_node_id == recipe.package_node_id
                pending.append((edge.to_node_id, next_has_package))
        return seen

    def _outgoing_edges(self, recipe: GraphRecipe) -> dict[str, tuple[GraphRecipeEdge, ...]]:
        outgoing: dict[str, list[GraphRecipeEdge]] = {}
        for edge in recipe.edges:
            outgoing.setdefault(edge.from_node_id, []).append(edge)
        return {node_id: tuple(edges) for node_id, edges in outgoing.items()}

    def _usable_edge_indices(
        self,
        edges: tuple[GraphRecipeEdge, ...],
        has_package: bool,
    ) -> tuple[int, ...]:
        return tuple(
            index for index, edge in enumerate(edges)
            if self._edge_is_usable(edge, has_package)
        )

    def _edge_is_usable(self, edge: GraphRecipeEdge, has_package: bool) -> bool:
        phase = "afterPackage" if has_package else "beforePackage"
        return edge.availability in {"always", phase}

    def _primary_route(self, successes, metadata):
        if not successes:
            return None
        if metadata:
            for route in successes:
                if route.path == metadata.required_path:
                    return route
        return min(successes, key=lambda route: (len(route.choices), len(route.path), route.path))

    def _state_changes_on_revisit(self, choices: tuple[_Choice, ...]) -> int:
        previous: dict[str, int] = {}
        changes = 0
        for choice in choices:
            if choice.node_id in previous and previous[choice.node_id] != choice.edge_index:
                changes += 1
            previous[choice.node_id] = choice.edge_index
        return changes

    def _ordered_dependencies(self, choices: tuple[_Choice, ...]) -> set[tuple[int, int]]:
        dependencies: set[tuple[int, int]] = set()
        for earlier in range(len(choices)):
            for later in range(earlier + 1, len(choices)):
                if choices[earlier].node_id == choices[later].node_id:
                    dependencies.add((earlier, later))
                elif choices[earlier].package_collected != choices[later].package_collected:
                    dependencies.add((earlier, later))
                    break
        return dependencies

    def _runtime_metrics(self, result):
        if result is None:
            return (), (), 0
        windows = tuple(
            diagnostic.window_close_seconds - diagnostic.window_open_seconds
            for diagnostic in result.diagnostics
            if diagnostic.window_open_seconds is not None
            and diagnostic.window_close_seconds is not None
            and diagnostic.window_close_seconds >= diagnostic.window_open_seconds
        )
        tap_times = tuple(action.time_seconds for action in result.actions)
        multi_taps = sum(diagnostic.rotation_count > 1 for diagnostic in result.diagnostics)
        return windows, tap_times, multi_taps

    def _spacings(self, times: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(round(later - earlier, 4) for earlier, later in zip(times, times[1:]))

    def _route_revisit_count(self, path: tuple[str, ...]) -> int:
        return sum(count - 1 for count in Counter(path).values() if count > 1)

    def _recoverable_choice_count(self, successes: tuple[_Route, ...]) -> int:
        return sum(self._route_revisit_count(route.path) > 0 for route in successes)

    def _frontloadable(self, choices: tuple[_Choice, ...]) -> bool:
        return bool(choices) and len({choice.node_id for choice in choices}) == len(choices)

    def _equivalent_choice_count(self, recipe: GraphRecipe) -> int:
        authored = self._outgoing_edges(recipe)
        reachable_states = self._reachable_node_states(recipe)
        count = 0
        for node_id, has_package in sorted(reachable_states):
            usable = tuple(
                edge for edge in authored.get(node_id, ())
                if self._edge_is_usable(edge, has_package)
            )
            targets = tuple(edge.to_node_id for edge in usable)
            if len(targets) < 2:
                continue
            outgoing = {
                source: [
                    edge.to_node_id for edge in edges
                    if self._edge_is_usable(edge, has_package)
                ]
                for source, edges in authored.items()
            }
            signatures = [self._linear_signature(target, outgoing) for target in targets]
            count += len(signatures) - len(set(signatures))
        return count

    def _linear_signature(self, node: str, outgoing: dict[str, list[str]]) -> str:
        seen: set[str] = set()
        while node not in seen and len(outgoing.get(node, ())) == 1:
            seen.add(node)
            node = outgoing[node][0]
        return node
