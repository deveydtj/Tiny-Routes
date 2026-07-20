"""Deterministic structural evaluation for player-visible policy agents."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tiny_routes_core.models import LevelDocument

from ..models.policy_evaluation import (
    PolicyDivergence,
    PolicyEvaluationReport,
    PolicyEvaluationResult,
    PolicyRunResult,
)
from ..models.puzzle_state import PuzzleState, PuzzleTerminalOutcome
from ..models.strategy_search import StrategySearchResult
from .puzzle_state_transition_service import PuzzleStateTransitionService
from .strategy_search_service import StrategySearchConfig, StrategySearchService


if TYPE_CHECKING:
    from ..agents.player_agent import PlayerAgent


AgentFactory = Callable[[int], "PlayerAgent"]


@dataclass(frozen=True)
class PolicyEvaluationConfig:
    """Bounded, reproducible policy-suite simulation settings."""

    random_run_count: int = 32
    deterministic_run_count: int = 1
    maximum_decisions_per_run: int = 64
    movement_speed: float = 1.0
    random_seed: int = 0

    def __post_init__(self) -> None:
        for field_name in (
            "random_run_count",
            "deterministic_run_count",
            "maximum_decisions_per_run",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{field_name} must be a positive integer")
        if (
            not isinstance(self.movement_speed, (int, float))
            or isinstance(self.movement_speed, bool)
            or self.movement_speed <= 0
        ):
            raise ValueError("movement_speed must be positive")
        if not isinstance(self.random_seed, int) or isinstance(self.random_seed, bool):
            raise ValueError("random_seed must be an integer")


class PolicyEvaluationService:
    """Measure policy success, costs, failures, regret, and optimal divergence."""

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

    def evaluate(
        self,
        level: LevelDocument,
        *,
        search_result: StrategySearchResult | None = None,
        config: PolicyEvaluationConfig | None = None,
        policy_factories: Mapping[str, AgentFactory] | None = None,
        run_counts: Mapping[str, int] | None = None,
        search_config: StrategySearchConfig | None = None,
    ) -> PolicyEvaluationReport:
        """Evaluate the standard suite or a supplied suite against one proof."""

        config = config or PolicyEvaluationConfig()
        initial_state = self._transitions.initial_state(level)
        effective_search_config = search_config or StrategySearchConfig(
            movement_speed=float(config.movement_speed),
        )
        proof = search_result or self._search.search(
            level,
            initial_state=initial_state,
            config=effective_search_config,
        )
        self._require_optimum(proof)
        factories = dict(policy_factories or self._standard_factories(level, proof, config))
        if not factories:
            raise ValueError("policy_factories cannot be empty")
        counts = dict(run_counts or {})
        optimal_by_state = self._optimal_actions_by_state(level, initial_state, proof)
        evaluations = tuple(
            self._evaluate_factory(
                level,
                name,
                factory,
                run_count=counts.get(
                    name,
                    config.random_run_count
                    if name == "random"
                    else config.deterministic_run_count,
                ),
                proof=proof,
                optimal_by_state=optimal_by_state,
                config=config,
            )
            for name, factory in factories.items()
        )
        return PolicyEvaluationReport(
            level_id=level.id,
            optimal_cost=proof.optimal_cost,
            evaluations=evaluations,
            strategy_proof_exhaustive=proof.exhaustive,
        )

    def evaluate_agent(
        self,
        level: LevelDocument,
        agent: "PlayerAgent" | AgentFactory,
        *,
        policy_name: str | None = None,
        run_count: int = 1,
        search_result: StrategySearchResult | None = None,
        config: PolicyEvaluationConfig | None = None,
        search_config: StrategySearchConfig | None = None,
    ) -> PolicyEvaluationResult:
        """Convenience entry point for one custom policy or agent factory."""

        config = config or PolicyEvaluationConfig()
        initial_state = self._transitions.initial_state(level)
        effective_search_config = search_config or StrategySearchConfig(
            movement_speed=float(config.movement_speed),
        )
        proof = search_result or self._search.search(
            level,
            initial_state=initial_state,
            config=effective_search_config,
        )
        self._require_optimum(proof)
        if callable(agent) and not hasattr(agent, "choose_action"):
            factory = agent
        else:
            factory = lambda _run_index: agent  # type: ignore[return-value]
        name = policy_name or agent.__class__.__name__
        return self._evaluate_factory(
            level,
            name,
            factory,
            run_count=run_count,
            proof=proof,
            optimal_by_state=self._optimal_actions_by_state(level, initial_state, proof),
            config=config,
        )

    def _standard_factories(
        self,
        level: LevelDocument,
        proof: StrategySearchResult,
        config: PolicyEvaluationConfig,
    ) -> dict[str, AgentFactory]:
        # Agent modules depend on the transition service, so imports remain
        # local to avoid an agents/services package initialization cycle.
        from ..agents.greedy_objective_agent import GreedyObjectiveAgent
        from ..agents.one_step_lookahead_agent import OneStepLookaheadAgent
        from ..agents.optimal_agent import OptimalAgent
        from ..agents.random_agent import RandomAgent
        from ..agents.two_step_planning_agent import TwoStepPlanningAgent

        return {
            "random": lambda run_index: RandomAgent(config.random_seed + run_index),
            "greedy_objective": lambda _run_index: GreedyObjectiveAgent(level),
            "one_step_lookahead": lambda _run_index: OneStepLookaheadAgent(
                level,
                transition_service=self._transitions,
            ),
            "two_step_planning": lambda _run_index: TwoStepPlanningAgent(
                level,
                transition_service=self._transitions,
            ),
            "optimal": lambda _run_index: OptimalAgent(
                level,
                search_result=proof,
                transition_service=self._transitions,
                search_service=self._search,
            ),
        }

    def _evaluate_factory(
        self,
        level: LevelDocument,
        policy_name: str,
        factory: AgentFactory,
        *,
        run_count: int,
        proof: StrategySearchResult,
        optimal_by_state: dict[PuzzleState, str],
        config: PolicyEvaluationConfig,
    ) -> PolicyEvaluationResult:
        if not isinstance(run_count, int) or isinstance(run_count, bool) or run_count < 1:
            raise ValueError("policy run counts must be positive integers")
        runs = tuple(
            self._run_policy(
                level,
                factory(run_index),
                run_index=run_index,
                optimal_by_state=optimal_by_state,
                config=config,
            )
            for run_index in range(run_count)
        )
        return PolicyEvaluationResult(policy_name, runs, proof.optimal_cost)

    def _run_policy(
        self,
        level: LevelDocument,
        agent: "PlayerAgent",
        *,
        run_index: int,
        optimal_by_state: dict[PuzzleState, str],
        config: PolicyEvaluationConfig,
    ) -> PolicyRunResult:
        from ..agents.player_agent import PlayerObservation

        if not hasattr(agent, "choose_action"):
            raise TypeError("policy factories must return a player agent")
        state = self._transitions.initial_state(level)
        taps = 0
        duration = 0.0
        distance = 0.0
        divergences: list[PolicyDivergence] = []
        outcome_code = self._initial_outcome_code(state)

        for decision_ordinal in range(config.maximum_decisions_per_run):
            if state.is_terminal:
                break
            actions = self._transitions.available_actions(level, state)
            if not actions:
                outcome_code = "structural_dead_end"
                break
            selected = agent.choose_action(PlayerObservation(state, actions))
            if selected is None:
                outcome_code = "policy_no_action"
                break
            legal = next(
                (
                    action
                    for action in actions
                    if action.node_id == selected.node_id
                    and action.selected_edge_id == selected.selected_edge_id
                    and action.tap_count == selected.tap_count
                ),
                None,
            )
            if legal is None:
                outcome_code = "policy_invalid_action"
                break

            optimal_edge_id = optimal_by_state.get(state)
            if optimal_edge_id is not None and legal.selected_edge_id != optimal_edge_id:
                divergences.append(
                    PolicyDivergence(
                        run_index=run_index,
                        decision_ordinal=decision_ordinal,
                        objective_index=state.objective_index,
                        node_id=legal.node_id,
                        selected_edge_id=legal.selected_edge_id,
                        optimal_edge_id=optimal_edge_id,
                    )
                )
            transition = self._transitions.transition(level, state, legal)
            taps += legal.tap_count
            distance += transition.route_distance
            duration += transition.route_distance / config.movement_speed
            state = transition.state
            outcome_code = transition.failure_reason or (
                "success"
                if state.terminal_outcome is PuzzleTerminalOutcome.SUCCESS
                else "active"
            )
            if state.is_terminal:
                break
        else:
            outcome_code = "policy_decision_limit_reached"

        succeeded = state.terminal_outcome is PuzzleTerminalOutcome.SUCCESS
        if state.terminal_outcome is PuzzleTerminalOutcome.FAILURE and outcome_code == "active":
            outcome_code = "structural_failure"
        return PolicyRunResult(
            run_index=run_index,
            succeeded=succeeded,
            accepted_taps=taps,
            completion_time_seconds=duration,
            route_distance=distance,
            outcome_code="success" if succeeded else outcome_code,
            divergences=tuple(divergences),
        )

    def _optimal_actions_by_state(
        self,
        level: LevelDocument,
        initial_state: PuzzleState,
        proof: StrategySearchResult,
    ) -> dict[PuzzleState, str]:
        trace = proof.canonical_optimal_strategy
        assert trace is not None
        state = initial_state
        result: dict[PuzzleState, str] = {}
        for action in trace.actions:
            result[state] = action.selected_edge_id
            transition = self._transitions.apply_decision(
                level,
                state,
                action.selected_edge_id,
            )
            state = transition.state
        if state != trace.final_state:
            raise ValueError("optimal strategy cannot be replayed for policy evaluation")
        return result

    @staticmethod
    def _initial_outcome_code(state: PuzzleState) -> str:
        if state.terminal_outcome is PuzzleTerminalOutcome.SUCCESS:
            return "success"
        if state.terminal_outcome is PuzzleTerminalOutcome.FAILURE:
            return "structural_initial_dead_end"
        return "active"

    @staticmethod
    def _require_optimum(result: StrategySearchResult) -> None:
        if not result.exhaustive:
            raise ValueError("policy evaluation requires an exhaustive strategy proof")
        if result.canonical_optimal_strategy is None or result.optimal_cost is None:
            raise ValueError("policy evaluation requires a successful optimal strategy")

    # Report is a concise synonym for orchestration callers.
    report = evaluate
