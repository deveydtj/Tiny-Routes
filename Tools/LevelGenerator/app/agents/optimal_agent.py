"""Adapter from exact structural strategy proof to the player-agent protocol."""

from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from ..models import PuzzleState, StrategySearchResult
from ..services.puzzle_state_transition_service import (
    PuzzleStateTransitionService,
    StructuralDecision,
)
from ..services.strategy_search_service import (
    StrategySearchConfig,
    StrategySearchService,
)
from .player_agent import PlayerObservation


class OptimalAgent:
    """Expose a proven canonical optimum through ``choose_action``.

    A supplied proof is replayed into a state-to-action policy without reading
    serialized solution data. When no proof is supplied, the exact strategy
    service produces it. Observations outside the replayed canonical path are
    solved from that visible state, so the adapter remains state-aware.
    """

    def __init__(
        self,
        level: LevelDocument,
        *,
        search_result: StrategySearchResult | None = None,
        initial_state: PuzzleState | None = None,
        search_service: StrategySearchService | None = None,
        transition_service: PuzzleStateTransitionService | None = None,
        search_config: StrategySearchConfig | None = None,
    ) -> None:
        self._level = level.clone()
        self._transitions = transition_service or PuzzleStateTransitionService()
        self._search = search_service or StrategySearchService(
            transition_service=self._transitions,
        )
        self._search_config = search_config or StrategySearchConfig()
        self._initial_state = initial_state or self._transitions.initial_state(self._level)
        self._search_result = search_result or self._search.search(
            self._level,
            initial_state=self._initial_state,
            config=self._search_config,
        )
        self._require_complete_optimum(self._search_result)
        self._action_by_state: dict[PuzzleState, str] = {}
        self._adapt_trace(self._initial_state, self._search_result)

    @property
    def search_result(self) -> StrategySearchResult:
        """The exhaustive proof adapted for the initial policy path."""

        return self._search_result

    def choose_action(
        self,
        observation: PlayerObservation,
    ) -> StructuralDecision | None:
        if observation.state.is_terminal or not observation.available_actions:
            return None

        by_edge_id = {
            action.selected_edge_id: action
            for action in observation.available_actions
        }
        selected_edge_id = self._action_by_state.get(observation.state)
        if selected_edge_id in by_edge_id:
            return by_edge_id[selected_edge_id]

        result = self._search.search(
            self._level,
            initial_state=observation.state,
            config=self._search_config,
        )
        self._require_complete_optimum(result)
        self._adapt_trace(observation.state, result)
        selected_edge_id = self._action_by_state.get(observation.state)
        if selected_edge_id in by_edge_id:
            return by_edge_id[selected_edge_id]

        # A policy evaluator normally exposes every legal action. If it applies
        # an intentional subset, retain legal-action confinement deterministically.
        return observation.available_actions[0]

    def _adapt_trace(
        self,
        start: PuzzleState,
        result: StrategySearchResult,
    ) -> None:
        trace = result.canonical_optimal_strategy
        if trace is None:
            raise ValueError("optimal agent requires a successful strategy")

        state = start
        for strategy_action in trace.actions:
            action = next(
                (
                    candidate
                    for candidate in self._transitions.available_actions(self._level, state)
                    if candidate.selected_edge_id == strategy_action.selected_edge_id
                ),
                None,
            )
            if action is None or action.node_id != strategy_action.node_id:
                raise ValueError("optimal strategy cannot be replayed from its initial state")
            self._action_by_state[state] = action.selected_edge_id
            state = self._transitions.transition(self._level, state, action).state

        if state != trace.final_state:
            raise ValueError("optimal strategy replay does not match its proven final state")

    @staticmethod
    def _require_complete_optimum(result: StrategySearchResult) -> None:
        if not result.exhaustive:
            raise ValueError("optimal agent requires an exhaustive strategy proof")
        if result.canonical_optimal_strategy is None:
            raise ValueError("optimal agent requires a successful strategy")

    choose_decision = choose_action
