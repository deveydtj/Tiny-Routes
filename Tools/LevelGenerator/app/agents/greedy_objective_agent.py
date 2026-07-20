"""Greedy policy that points each switch toward the highlighted objective."""

from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from ..services.puzzle_state_transition_service import StructuralDecision
from ._objective_policy import ObjectivePolicyContext
from .player_agent import PlayerObservation


class GreedyObjectiveAgent:
    """Choose the road whose immediate endpoint is nearest the objective.

    The policy deliberately performs no route simulation and does not inspect
    later intersections. Equal-distance choices retain the legal action order,
    making the baseline deterministic and representative of local arrow
    tapping rather than strategic planning.
    """

    def __init__(self, level: LevelDocument) -> None:
        self._context = ObjectivePolicyContext(level)

    def choose_action(
        self,
        observation: PlayerObservation,
    ) -> StructuralDecision | None:
        if observation.state.is_terminal or not observation.available_actions:
            return None
        return min(
            observation.available_actions,
            key=lambda action: self._context.action_endpoint_distance(
                observation.state,
                action,
            ),
        )

    choose_decision = choose_action
