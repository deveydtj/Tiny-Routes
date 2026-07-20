"""Objective policy that evaluates one complete structural transition."""

from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from ..models import PuzzleTerminalOutcome
from ..services.puzzle_state_transition_service import (
    PuzzleStateTransitionService,
    StructuralDecision,
)
from ._objective_policy import ObjectivePolicyContext
from .player_agent import PlayerObservation


class OneStepLookaheadAgent:
    """Choose the best visible result after exactly one road decision.

    Immediate failure is avoided, objective progress is preferred, and the
    remaining estimate combines distance traveled with straight-line distance
    to the newly active objective. The policy never expands a second decision.
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
        transition = self._transitions.transition(
            self._context.level,
            observation.state,
            action,
        )
        successor = transition.state
        outcome_rank = {
            PuzzleTerminalOutcome.SUCCESS: 0,
            PuzzleTerminalOutcome.ACTIVE: 1,
            PuzzleTerminalOutcome.FAILURE: 2,
        }[successor.terminal_outcome]
        remaining_objectives = self._context.remaining_objective_count(successor)
        estimated_distance = transition.route_distance
        if successor.terminal_outcome is PuzzleTerminalOutcome.ACTIVE:
            estimated_distance += self._context.distance_to_current_objective(successor)
        return (
            outcome_rank,
            remaining_objectives,
            round(estimated_distance, 9),
            action.tap_count,
        )

    choose_decision = choose_action
