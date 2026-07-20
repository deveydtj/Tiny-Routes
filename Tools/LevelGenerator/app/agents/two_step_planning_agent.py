"""Objective policy that plans across exactly two structural transitions."""

from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from ..models import PuzzleTerminalOutcome
from ..services.puzzle_state_transition_service import (
    PuzzleStateTransitionService,
    StructuralDecision,
    StructuralTransitionResult,
)
from ._objective_policy import ObjectivePolicyContext
from .player_agent import PlayerObservation


class TwoStepPlanningAgent:
    """Choose using the best visible outcome within a two-decision horizon.

    Each observed action is advanced through one canonical structural
    transition. Active successors then expand every legal next decision once.
    The frontier is ranked by terminal outcome, objective progress, traveled
    plus straight-line distance, and taps. No third decision is expanded.
    """

    def __init__(
        self,
        level: LevelDocument,
        *,
        transition_service: PuzzleStateTransitionService | None = None,
    ) -> None:
        self._context = ObjectivePolicyContext(level)
        self._transitions = transition_service or PuzzleStateTransitionService()

    def choose_action(
        self,
        observation: PlayerObservation,
    ) -> StructuralDecision | None:
        if observation.state.is_terminal or not observation.available_actions:
            return None

        scored_actions = (
            (self._score(observation, action), ordinal, action)
            for ordinal, action in enumerate(observation.available_actions)
        )
        return min(scored_actions, key=lambda item: (item[0], item[1]))[2]

    def _score(
        self,
        observation: PlayerObservation,
        action: StructuralDecision,
    ) -> tuple[int, int, float, int]:
        first = self._transitions.transition(
            self._context.level,
            observation.state,
            action,
        )
        if first.state.is_terminal:
            return self._frontier_score(
                first,
                route_distance=first.route_distance,
                tap_count=action.tap_count,
            )

        next_actions = self._transitions.available_actions(
            self._context.level,
            first.state,
        )
        if not next_actions:
            return self._frontier_score(
                first,
                route_distance=first.route_distance,
                tap_count=action.tap_count,
            )

        frontier_scores = []
        for next_action in next_actions:
            second = self._transitions.transition(
                self._context.level,
                first.state,
                next_action,
            )
            frontier_scores.append(
                self._frontier_score(
                    second,
                    route_distance=first.route_distance + second.route_distance,
                    tap_count=action.tap_count + next_action.tap_count,
                )
            )
        return min(frontier_scores)

    def _frontier_score(
        self,
        transition: StructuralTransitionResult,
        *,
        route_distance: float,
        tap_count: int,
    ) -> tuple[int, int, float, int]:
        successor = transition.state
        outcome_rank = {
            PuzzleTerminalOutcome.SUCCESS: 0,
            PuzzleTerminalOutcome.ACTIVE: 1,
            PuzzleTerminalOutcome.FAILURE: 2,
        }[successor.terminal_outcome]
        estimated_distance = route_distance
        if successor.terminal_outcome is PuzzleTerminalOutcome.ACTIVE:
            estimated_distance += self._context.distance_to_current_objective(successor)
        return (
            outcome_rank,
            self._context.remaining_objective_count(successor),
            round(estimated_distance, 9),
            tap_count,
        )

    choose_decision = choose_action
