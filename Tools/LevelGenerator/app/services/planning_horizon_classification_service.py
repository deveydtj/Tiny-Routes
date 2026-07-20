"""Classify the minimum information horizon for every optimal decision."""

from __future__ import annotations

from tiny_routes_core.models import LevelDocument

from ..models.planning_horizon import (
    PlanningHorizon,
    PlanningHorizonDecision,
    PlanningHorizonReport,
)
from ..models.puzzle_state import PuzzleState
from ..models.strategy_search import StrategySearchResult
from .puzzle_state_transition_service import (
    PuzzleStateTransitionService,
    StructuralDecision,
)
from .strategy_search_service import StrategySearchConfig, StrategySearchService


class PlanningHorizonClassificationService:
    """Use shared visible-state policies to measure optimal planning depth.

    The first matching policy establishes the minimum local horizon. Decisions
    that defeat both bounded lookahead policies are separated into current
    objective-state reasoning and anticipation across a future phase boundary.
    """

    def __init__(
        self,
        *,
        transition_service: PuzzleStateTransitionService | None = None,
        search_service: StrategySearchService | None = None,
    ) -> None:
        self._transitions = transition_service or PuzzleStateTransitionService()
        self._search = search_service or StrategySearchService(
            transition_service=self._transitions,
        )

    def classify(
        self,
        level: LevelDocument,
        search_result: StrategySearchResult | None = None,
        *,
        search_config: StrategySearchConfig | None = None,
    ) -> PlanningHorizonReport:
        initial_state = self._transitions.initial_state(level)
        proof = search_result or self._search.search(
            level,
            initial_state=initial_state,
            config=search_config,
        )
        self._require_optimum(proof)
        trace = proof.canonical_optimal_strategy
        assert trace is not None

        # Agent modules depend on the transition service, so imports remain
        # local to avoid an agents/services package initialization cycle.
        from ..agents.greedy_objective_agent import GreedyObjectiveAgent
        from ..agents.one_step_lookahead_agent import OneStepLookaheadAgent
        from ..agents.player_agent import PlayerObservation
        from ..agents.two_step_planning_agent import TwoStepPlanningAgent

        states = self._replay_states(level, initial_state, proof)
        greedy = GreedyObjectiveAgent(level)
        one_step = OneStepLookaheadAgent(
            level,
            transition_service=self._transitions,
        )
        two_step = TwoStepPlanningAgent(
            level,
            transition_service=self._transitions,
        )
        decisions: list[PlanningHorizonDecision] = []

        for ordinal, (state, optimal_action) in enumerate(zip(states, trace.actions)):
            actions = self._transitions.available_actions(level, state)
            optimal = next(
                (
                    action
                    for action in actions
                    if action.selected_edge_id == optimal_action.selected_edge_id
                ),
                None,
            )
            if optimal is None:
                raise ValueError("optimal strategy contains a non-visible decision")
            observation = PlayerObservation(state, actions)
            selected_by = {
                "greedy_objective": greedy.choose_action(observation),
                "one_step_lookahead": one_step.choose_action(observation),
                "two_step_planning": two_step.choose_action(observation),
            }
            matches = tuple(
                name
                for name, selected in selected_by.items()
                if selected is not None
                and selected.selected_edge_id == optimal.selected_edge_id
            )
            horizon, rationale = self._minimum_horizon(
                ordinal,
                states,
                actions,
                matches,
            )
            decisions.append(
                PlanningHorizonDecision(
                    decision_ordinal=ordinal,
                    objective_index=state.objective_index,
                    node_id=optimal.node_id,
                    optimal_edge_id=optimal.selected_edge_id,
                    horizon=horizon,
                    matched_policy_names=matches,
                    rationale=rationale,
                )
            )
        return PlanningHorizonReport(
            level_id=level.id,
            decisions=tuple(decisions),
            strategy_proof_exhaustive=proof.exhaustive,
        )

    def _minimum_horizon(
        self,
        ordinal: int,
        states: tuple[PuzzleState, ...],
        visible_actions: tuple[StructuralDecision, ...],
        matches: tuple[str, ...],
    ) -> tuple[PlanningHorizon, str]:
        if len(visible_actions) == 1:
            return (
                PlanningHorizon.IMMEDIATE_EDGE_ONLY,
                "The optimal road is the only visible legal action.",
            )
        if "greedy_objective" in matches:
            return (
                PlanningHorizon.IMMEDIATE_EDGE_ONLY,
                "Immediate edge geometry toward the active objective prefers the optimum.",
            )
        if "one_step_lookahead" in matches:
            return (
                PlanningHorizon.ONE_TRANSITION,
                "One complete structural transition is sufficient to prefer the optimum.",
            )
        if "two_step_planning" in matches:
            return (
                PlanningHorizon.TWO_TRANSITIONS,
                "The optimum first becomes preferable after expanding a second decision.",
            )
        if self._anticipates_future_phase(ordinal, states):
            return (
                PlanningHorizon.CROSS_PHASE_KNOWLEDGE,
                "The optimal choice must anticipate a later decision after objective state changes.",
            )
        return (
            PlanningHorizon.OBJECTIVE_STATE_KNOWLEDGE,
            "Bounded local lookahead is insufficient; the current ordered-objective state is required.",
        )

    @staticmethod
    def _anticipates_future_phase(
        ordinal: int,
        states: tuple[PuzzleState, ...],
    ) -> bool:
        current = states[ordinal]
        return any(
            states[index].objective_index > current.objective_index
            for index in range(ordinal + 1, len(states))
        )

    def _replay_states(
        self,
        level: LevelDocument,
        initial_state: PuzzleState,
        proof: StrategySearchResult,
    ) -> tuple[PuzzleState, ...]:
        trace = proof.canonical_optimal_strategy
        assert trace is not None
        state = initial_state
        states: list[PuzzleState] = []
        for action in trace.actions:
            states.append(state)
            state = self._transitions.apply_decision(
                level,
                state,
                action.selected_edge_id,
            ).state
        if state != trace.final_state:
            raise ValueError("optimal strategy cannot be replayed for horizon classification")
        return tuple(states)

    @staticmethod
    def _require_optimum(result: StrategySearchResult) -> None:
        if not result.exhaustive:
            raise ValueError("planning-horizon classification requires an exhaustive proof")
        if result.canonical_optimal_strategy is None:
            raise ValueError("planning-horizon classification requires a successful strategy")

    report = classify


# Short alias retained for callers that name the task rather than the operation.
PlanningHorizonClassifier = PlanningHorizonClassificationService
PlanningHorizonClassifierService = PlanningHorizonClassificationService
