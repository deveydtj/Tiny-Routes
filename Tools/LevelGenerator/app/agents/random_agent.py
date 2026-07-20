"""Uniform seeded baseline policy over player-visible legal actions."""

from __future__ import annotations

from ..random_source import RandomSource
from ..services.puzzle_state_transition_service import StructuralDecision
from .player_agent import PlayerObservation


class RandomAgent:
    """Choose uniformly from the currently visible legal actions.

    The agent receives no level document or hidden graph data. A seed controls
    its stateful choice stream so policy evaluation runs are reproducible.
    """

    def __init__(self, seed: int = 0) -> None:
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("seed must be an integer")
        self.seed = seed
        self._random = RandomSource(seed)

    def choose_action(
        self,
        observation: PlayerObservation,
    ) -> StructuralDecision | None:
        if observation.state.is_terminal or not observation.available_actions:
            return None
        return self._random.choice(observation.available_actions)

    choose_decision = choose_action
