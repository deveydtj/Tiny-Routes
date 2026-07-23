"""Material-consequence classification for exact structural decisions."""

from __future__ import annotations

from dataclasses import dataclass

from tiny_routes_core.models import LevelDocument

from ..models.puzzle_state import PuzzleState, PuzzleTerminalOutcome
from ..models.strategy_search import DecisionConsequenceEvidence
from .puzzle_state_transition_service import (
    PuzzleStateTransitionService,
    StructuralTransitionResult,
)


@dataclass(frozen=True)
class _ChoiceConsequence:
    future_state: tuple[object, ...]
    objective_progress: tuple[object, ...]
    route_cost: float
    risk: str
    recoverability: bool
    later_switch_requirements: tuple[object, ...]


class DecisionConsequenceService:
    """Compare selectable roads by player-relevant downstream consequences.

    Structural movement already advances to the next decision, objective, or
    terminal boundary.  Comparing that exact successor makes decorative
    split/rejoin geometry disappear while retaining differences in route state,
    objective progress, cost, failure risk, recoverability, and the next switch
    requirement.
    """

    _DIMENSIONS = (
        "future_state",
        "objective_progress",
        "route_cost",
        "risk",
        "recoverability",
        "later_switch_requirements",
    )

    def __init__(
        self,
        transition_service: PuzzleStateTransitionService | None = None,
    ) -> None:
        self.transition_service = transition_service or PuzzleStateTransitionService()

    def analyze(
        self,
        level: LevelDocument,
        state: PuzzleState,
    ) -> dict[str, DecisionConsequenceEvidence]:
        decisions = self.transition_service.available_decisions(level, state)
        transitions = tuple(
            self.transition_service.transition(level, state, decision)
            for decision in decisions
        )
        profiles = {
            transition.decision.selected_edge_id: self._profile(
                level,
                transition,
            )
            for transition in transitions
        }
        distinct_profiles = set(profiles.values())
        differing_dimensions = tuple(
            dimension
            for dimension in self._DIMENSIONS
            if len(
                {
                    getattr(profile, dimension)
                    for profile in profiles.values()
                }
            )
            >= 2
        )
        choice_count = len(profiles)
        distinct_count = len(distinct_profiles)
        equivalent_count = choice_count - distinct_count
        return {
            edge_id: DecisionConsequenceEvidence(
                choice_count=choice_count,
                distinct_consequence_count=distinct_count,
                differing_dimensions=differing_dimensions,
                equivalent_choice_count=equivalent_count,
                equivalent_selected_edge_ids=tuple(
                    sorted(
                        other_edge_id
                        for other_edge_id, other_profile in profiles.items()
                        if other_edge_id != edge_id and other_profile == profile
                    )
                ),
                exhaustive=True,
            )
            for edge_id, profile in profiles.items()
        }

    def _profile(
        self,
        level: LevelDocument,
        transition: StructuralTransitionResult,
    ) -> _ChoiceConsequence:
        successor = transition.state
        root_node_id = transition.decision.node_id
        active_switches = tuple(
            item
            for item in successor.active_switch_edge_ids
            if item[0] != root_node_id
        )
        next_decisions = self.transition_service.available_decisions(level, successor)
        later_requirements: tuple[object, ...] = ()
        if next_decisions:
            later_requirements = (
                successor.objective_index,
                successor.current_node_id,
                tuple(decision.selected_edge_id for decision in next_decisions),
            )
        risk = transition.failure_reason or (
            "success"
            if successor.terminal_outcome is PuzzleTerminalOutcome.SUCCESS
            else "active"
        )
        return _ChoiceConsequence(
            # Objective fields, cost counters, and visit history have dedicated
            # consequence dimensions and must not create duplicate differences.
            future_state=(
                successor.current_node_id,
                successor.available_edge_ids,
                successor.consumed_edge_ids,
                active_switches,
            ),
            objective_progress=(
                successor.objective_index,
                transition.completed_objective_ids,
            ),
            route_cost=round(transition.route_distance, 9),
            risk=risk,
            recoverability=(
                successor.terminal_outcome is not PuzzleTerminalOutcome.FAILURE
            ),
            later_switch_requirements=later_requirements,
        )
