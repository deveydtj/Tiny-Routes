from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from statistics import fmean
from typing import Callable

from ..models.abstract_puzzle_solution import AbstractPuzzleSolutionMetadata
from ..models.decision_profile import DecisionProfile
from ..models.graph_recipe import GraphRecipe
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
        outgoing: dict[str, list[str]] = {}
        for edge in recipe.edges:
            outgoing.setdefault(edge.from_node_id, []).append(edge.to_node_id)
        max_steps = max(8, len(recipe.nodes) * 3)
        routes: list[_Route] = []

        def visit(node: str, path: tuple[str, ...], choices: tuple[_Choice, ...], has_package: bool) -> None:
            if len(routes) >= route_limit:
                return
            has_package = has_package or node == recipe.package_node_id
            if node == recipe.destination_node_id:
                outcome = "success" if has_package else "destination_before_package"
                routes.append(_Route(path, choices, outcome))
                return
            edges = outgoing.get(node, ())
            if not edges:
                routes.append(_Route(path, choices, "dead_end"))
                return
            if len(path) >= max_steps:
                routes.append(_Route(path, choices, "loop_or_step_limit"))
                return
            for index, target in enumerate(edges):
                next_choices = choices
                if len(edges) > 1:
                    next_choices = (*choices, _Choice(node, index, has_package))
                visit(target, (*path, target), next_choices, has_package)

        visit("start", ("start",), (), recipe.package_node_id == "start")
        return tuple(routes)

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
        outgoing: dict[str, list[str]] = {}
        for edge in recipe.edges:
            outgoing.setdefault(edge.from_node_id, []).append(edge.to_node_id)
        count = 0
        for targets in outgoing.values():
            if len(targets) < 2:
                continue
            signatures = [self._linear_signature(target, outgoing) for target in targets]
            count += len(signatures) - len(set(signatures))
        return count

    def _linear_signature(self, node: str, outgoing: dict[str, list[str]]) -> str:
        seen: set[str] = set()
        while node not in seen and len(outgoing.get(node, ())) == 1:
            seen.add(node)
            node = outgoing[node][0]
        return node
