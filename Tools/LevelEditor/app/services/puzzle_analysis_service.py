from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from statistics import fmean

from tiny_routes_core.models import (
    LevelDocument,
    SolutionAction,
    Solution,
    SwitchInteractionMode,
)

from .runtime_solution_service import RuntimeSolutionService


@dataclass(frozen=True)
class PuzzleRecommendation:
    """A plain-language design suggestion that can point back to the canvas."""

    message: str
    related_node_id: str | None = None


@dataclass(frozen=True)
class PuzzleAnalysis:
    decision_count: int = 0
    unique_switches_used: int = 0
    repeated_visits: int = 0
    state_changes_on_revisit: int = 0
    independent_decision_ratio: float = 0.0
    equivalent_solutions: int = 0
    failure_outcomes: tuple[tuple[str, int], ...] = ()
    activation_window_lengths: tuple[float, ...] = ()
    decision_spacings: tuple[float, ...] = ()
    estimated_difficulty: str = "Easy"
    legacy_front_load_possible: bool = False
    recommendations: tuple[PuzzleRecommendation, ...] = ()

    @property
    def minimum_activation_window(self) -> float | None:
        return min(self.activation_window_lengths, default=None)

    @property
    def average_activation_window(self) -> float | None:
        if not self.activation_window_lengths:
            return None
        return round(fmean(self.activation_window_lengths), 3)


@dataclass(frozen=True)
class _RouteChoice:
    node_id: str
    edge_id: str
    package_collected: bool


@dataclass(frozen=True)
class _Route:
    path: tuple[str, ...]
    choices: tuple[_RouteChoice, ...]
    outcome: str


class PuzzleAnalysisService:
    """Measure topology and runtime decision quality for an editor document.

    The route metrics mirror the generator's ``DecisionProfileService`` while
    accepting the shared level model directly. Runtime metrics come from the
    same parity simulator used by solution search and editor playtesting.
    """

    def __init__(self, runtime_service: RuntimeSolutionService | None = None) -> None:
        self._runtime = runtime_service or RuntimeSolutionService()

    def analyze(
        self,
        level: LevelDocument,
        solution: Solution | None,
        *,
        route_limit: int = 512,
    ) -> PuzzleAnalysis:
        routes = self._enumerate_routes(level, max(1, route_limit))
        successes = tuple(route for route in routes if route.outcome == "completed")
        failures = tuple(route for route in routes if route.outcome != "completed")
        replay = self._safe_replay(level, solution)

        choices = self._replay_choices(level, replay)
        if not choices and successes:
            choices = min(
                successes,
                key=lambda route: (len(route.choices), len(route.path), route.path),
            ).choices

        switch_counts = Counter(choice.node_id for choice in choices)
        repeated_visits = sum(count - 1 for count in switch_counts.values())
        state_changes = self._state_changes_on_revisit(choices)
        independent_ratio = self._independent_decision_ratio(choices)
        minimum_choices = min((len(route.choices) for route in successes), default=0)
        equivalent_solutions = sum(
            len(route.choices) == minimum_choices for route in successes
        )
        failure_outcomes = tuple(sorted(Counter(route.outcome for route in failures).items()))
        timings = self._safe_timings(level, solution)
        windows = tuple(
            round(item.window_close_seconds - item.window_open_seconds, 3)
            for item in timings
            if item.window_open_seconds is not None
            and item.window_close_seconds is not None
            and item.window_close_seconds >= item.window_open_seconds
        )
        numeric_actions = tuple(
            action
            for action in (solution.actions if solution is not None else ())
            if isinstance(action.timeSeconds, (int, float))
            and not isinstance(action.timeSeconds, bool)
        )
        tap_times = tuple(
            float(action.timeSeconds)
            for action in sorted(numeric_actions, key=lambda item: float(item.timeSeconds))
        )
        spacings = tuple(
            round(later - earlier, 3)
            for earlier, later in zip(tap_times, tap_times[1:])
        )
        front_load_possible = self._legacy_front_load_possible(level, solution)
        difficulty = self._estimate_difficulty(
            len(choices), repeated_visits, independent_ratio, windows, spacings
        )
        recommendations = self._recommendations(
            choices=choices,
            equivalent_solutions=equivalent_solutions,
            failure_outcomes=failure_outcomes,
            windows=windows,
            front_load_possible=front_load_possible,
            replay=replay,
            solution=solution,
        )

        return PuzzleAnalysis(
            decision_count=len(choices),
            unique_switches_used=len(switch_counts),
            repeated_visits=repeated_visits,
            state_changes_on_revisit=state_changes,
            independent_decision_ratio=independent_ratio,
            equivalent_solutions=equivalent_solutions,
            failure_outcomes=failure_outcomes,
            activation_window_lengths=windows,
            decision_spacings=spacings,
            estimated_difficulty=difficulty,
            legacy_front_load_possible=front_load_possible,
            recommendations=recommendations,
        )

    def _enumerate_routes(self, level: LevelDocument, route_limit: int) -> tuple[_Route, ...]:
        node_ids = {node.id for node in level.graph.nodes}
        outgoing: dict[str, list[tuple[str, str]]] = {}
        for edge in level.graph.edges:
            if edge.fromNodeID in node_ids and edge.toNodeID in node_ids:
                outgoing.setdefault(edge.fromNodeID, []).append((edge.id, edge.toNodeID))

        max_steps = max(8, len(node_ids) * 3)
        routes: list[_Route] = []

        def visit(
            node_id: str,
            path: tuple[str, ...],
            choices: tuple[_RouteChoice, ...],
            package_collected: bool,
        ) -> None:
            if len(routes) >= route_limit:
                return
            package_collected = package_collected or node_id == level.packageNodeID
            if node_id == level.destinationNodeID:
                outcome = "completed" if package_collected else "destination before package"
                routes.append(_Route(path, choices, outcome))
                return
            edges = outgoing.get(node_id, ())
            if not edges:
                routes.append(_Route(path, choices, "dead end"))
                return
            if len(path) >= max_steps:
                routes.append(_Route(path, choices, "loop or step limit"))
                return
            for edge_id, target_id in edges:
                next_choices = choices
                if len(edges) > 1:
                    next_choices = (*choices, _RouteChoice(
                        node_id, edge_id, package_collected
                    ))
                visit(target_id, (*path, target_id), next_choices, package_collected)

        if level.startNodeID in node_ids:
            visit(
                level.startNodeID,
                (level.startNodeID,),
                (),
                level.startNodeID == level.packageNodeID,
            )
        return tuple(routes)

    def _safe_replay(self, level: LevelDocument, solution: Solution | None):
        if solution is None:
            return None
        try:
            return self._runtime.replay(level, solution)
        except (KeyError, TypeError, ValueError):
            return None

    def _safe_timings(self, level: LevelDocument, solution: Solution | None):
        if solution is None:
            return ()
        try:
            return self._runtime.analyze(level, solution)
        except (KeyError, TypeError, ValueError):
            return ()

    def _replay_choices(self, level: LevelDocument, replay) -> tuple[_RouteChoice, ...]:
        if replay is None or not replay.passed:
            return ()
        outgoing_counts = Counter(edge.fromNodeID for edge in level.graph.edges)
        package_collected = level.startNodeID == level.packageNodeID
        choices: list[_RouteChoice] = []
        for event in replay.events:
            if event.kind == "collect_package":
                package_collected = True
            if (
                event.kind == "begin_edge"
                and event.node_id is not None
                and event.edge_id is not None
                and outgoing_counts[event.node_id] > 1
            ):
                choices.append(_RouteChoice(
                    event.node_id, event.edge_id, package_collected
                ))
        return tuple(choices)

    def _state_changes_on_revisit(self, choices: tuple[_RouteChoice, ...]) -> int:
        previous: dict[str, str] = {}
        changes = 0
        for choice in choices:
            if choice.node_id in previous and previous[choice.node_id] != choice.edge_id:
                changes += 1
            previous[choice.node_id] = choice.edge_id
        return changes

    def _independent_decision_ratio(self, choices: tuple[_RouteChoice, ...]) -> float:
        if not choices:
            return 0.0
        dependent_indexes: set[int] = set()
        previous_by_node: dict[str, int] = {}
        for index, choice in enumerate(choices):
            if choice.node_id in previous_by_node:
                dependent_indexes.add(index)
            previous_by_node[choice.node_id] = index
            if index and choices[index - 1].package_collected != choice.package_collected:
                dependent_indexes.add(index)
        return round((len(choices) - len(dependent_indexes)) / len(choices), 4)

    def _legacy_front_load_possible(
        self, level: LevelDocument, solution: Solution | None
    ) -> bool:
        if solution is None or not solution.actions:
            return False
        diagnostic_level = level.clone()
        diagnostic_level.rules = replace(
            diagnostic_level.rules,
            switch_interaction_mode=SwitchInteractionMode.LEGACY_GLOBAL,
        )
        diagnostic_solution = solution.clone()
        diagnostic_solution.actions = [
            SolutionAction(timeSeconds=0.0, tapNodeID=action.tapNodeID)
            for action in solution.actions
        ]
        replay = self._safe_replay(diagnostic_level, diagnostic_solution)
        return bool(replay is not None and replay.passed)

    def _estimate_difficulty(
        self,
        decisions: int,
        revisits: int,
        independent_ratio: float,
        windows: tuple[float, ...],
        spacings: tuple[float, ...],
    ) -> str:
        score = decisions + revisits * 2
        if decisions >= 3 and independent_ratio <= 0.67:
            score += 2
        if windows and min(windows) < 0.8:
            score += 2
        if spacings and min(spacings) < 1.0:
            score += 1
        if score >= 9:
            return "Expert"
        if score >= 6:
            return "Hard"
        if score >= 3:
            return "Medium"
        return "Easy"

    def _recommendations(
        self,
        *,
        choices: tuple[_RouteChoice, ...],
        equivalent_solutions: int,
        failure_outcomes: tuple[tuple[str, int], ...],
        windows: tuple[float, ...],
        front_load_possible: bool,
        replay,
        solution: Solution | None,
    ) -> tuple[PuzzleRecommendation, ...]:
        recommendations: list[PuzzleRecommendation] = []
        choice_nodes = tuple(dict.fromkeys(choice.node_id for choice in choices))
        if not choices:
            recommendations.append(PuzzleRecommendation(
                "Add a meaningful route decision; the successful route currently uses no switches."
            ))
        independent_ratio = self._independent_decision_ratio(choices)
        if len(choices) >= 2 and independent_ratio > 0.75:
            recommendations.append(PuzzleRecommendation(
                "Most decisions are independent. Reuse a switch or make a later choice depend on an earlier route.",
                choice_nodes[0] if choice_nodes else None,
            ))
        if equivalent_solutions > 1:
            recommendations.append(PuzzleRecommendation(
                f"There are {equivalent_solutions} minimum-decision solutions. Differentiate the alternate routes.",
                choice_nodes[0] if choice_nodes else None,
            ))
        if not failure_outcomes and choices:
            recommendations.append(PuzzleRecommendation(
                "Every bounded route succeeds. Add a readable consequence for at least one wrong choice.",
                choice_nodes[0] if choice_nodes else None,
            ))
        if windows and min(windows) < 0.5:
            tight_index = windows.index(min(windows))
            node_id = None
            if solution is not None and tight_index < len(solution.actions):
                node_id = solution.actions[tight_index].tapNodeID
            recommendations.append(PuzzleRecommendation(
                f"The tightest activation window is {min(windows):.2f}s. Add road length or increase look-ahead time.",
                node_id,
            ))
        if front_load_possible:
            node_id = solution.actions[0].tapNodeID if solution and solution.actions else None
            recommendations.append(PuzzleRecommendation(
                "All saved taps can be front-loaded in legacy mode. Keep live "
                "look-ahead enabled so timing remains meaningful.",
                node_id,
            ))
        if solution is not None and replay is not None and not replay.passed:
            failed_node = replay.taps[-1].action.tapNodeID if replay.taps else None
            reason = replay.failure_reason or replay.state.outcome.value
            recommendations.append(PuzzleRecommendation(
                "The saved solution does not complete the level "
                f"({reason.replace('_', ' ')}). Record or find a verified solution.",
                failed_node,
            ))
        return tuple(recommendations)
