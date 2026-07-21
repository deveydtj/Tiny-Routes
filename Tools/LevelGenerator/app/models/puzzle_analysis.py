"""Raw strategic, policy, outcome, cost, and presentation analysis values."""

from __future__ import annotations

from dataclasses import dataclass

from .policy_evaluation import PolicyEvaluationResult
from .static_policy import StaticPolicySearchResult


def _non_negative_number(value: int | float, field_name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be non-negative")


@dataclass(frozen=True, order=True)
class PuzzleOutcomeCount:
    """One recovery or terminal-failure class and its exact trace count."""

    outcome_code: str
    count: int

    def __post_init__(self) -> None:
        if not isinstance(self.outcome_code, str) or not self.outcome_code.strip():
            raise ValueError("outcome_code cannot be empty")
        object.__setattr__(self, "outcome_code", self.outcome_code.strip())
        if not isinstance(self.count, int) or isinstance(self.count, bool) or self.count < 1:
            raise ValueError("count must be a positive integer")


@dataclass(frozen=True)
class PuzzleAnalysis:
    """Unweighted evidence consumed by production gates and later ranking."""

    meaningful_decisions: int
    planning_decisions: int
    adaptive_decisions: int
    dependency_depth: int
    independent_decision_ratio: float
    static_policy_result: StaticPolicySearchResult
    agent_results: tuple[PolicyEvaluationResult, ...]
    objective_phases: int
    state_changes: int
    revisits: int
    successful_strategy_classes: int
    optimal_uniqueness: bool
    recovery_failure_distribution: tuple[PuzzleOutcomeCount, ...]
    equivalent_choices: int
    no_op_choices: int
    optimal_accepted_taps: int
    optimal_route_distance: float
    optimal_travel_time_seconds: float
    visual_complexity: float

    def __post_init__(self) -> None:
        integer_fields = (
            "meaningful_decisions",
            "planning_decisions",
            "adaptive_decisions",
            "dependency_depth",
            "objective_phases",
            "state_changes",
            "revisits",
            "successful_strategy_classes",
            "equivalent_choices",
            "no_op_choices",
            "optimal_accepted_taps",
        )
        for field_name in integer_fields:
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if (
            not isinstance(self.independent_decision_ratio, (int, float))
            or isinstance(self.independent_decision_ratio, bool)
            or not 0 <= self.independent_decision_ratio <= 1
        ):
            raise ValueError("independent_decision_ratio must be between zero and one")
        object.__setattr__(
            self,
            "independent_decision_ratio",
            round(float(self.independent_decision_ratio), 9),
        )
        if not isinstance(self.static_policy_result, StaticPolicySearchResult):
            raise ValueError("static_policy_result must be a StaticPolicySearchResult")
        agents = tuple(self.agent_results)
        if any(not isinstance(item, PolicyEvaluationResult) for item in agents):
            raise ValueError("agent_results must contain PolicyEvaluationResult values")
        names = tuple(item.policy_name for item in agents)
        if len(names) != len(set(names)):
            raise ValueError("agent_results must have unique policy names")
        object.__setattr__(self, "agent_results", agents)
        if not isinstance(self.optimal_uniqueness, bool):
            raise ValueError("optimal_uniqueness must be a Boolean")
        distribution = tuple(self.recovery_failure_distribution)
        if any(not isinstance(item, PuzzleOutcomeCount) for item in distribution):
            raise ValueError(
                "recovery_failure_distribution must contain PuzzleOutcomeCount values"
            )
        codes = tuple(item.outcome_code for item in distribution)
        if len(codes) != len(set(codes)):
            raise ValueError("recovery_failure_distribution codes must be unique")
        object.__setattr__(self, "recovery_failure_distribution", distribution)
        for field_name in (
            "optimal_route_distance",
            "optimal_travel_time_seconds",
            "visual_complexity",
        ):
            value = getattr(self, field_name)
            _non_negative_number(value, field_name)
            object.__setattr__(self, field_name, round(float(value), 9))

    @property
    def meaningful_decision_count(self) -> int:
        return self.meaningful_decisions

    @property
    def planning_decision_count(self) -> int:
        return self.planning_decisions

    @property
    def adaptive_decision_count(self) -> int:
        return self.adaptive_decisions

    @property
    def objective_phase_count(self) -> int:
        return self.objective_phases

    @property
    def state_change_count(self) -> int:
        return self.state_changes

    @property
    def revisit_count(self) -> int:
        return self.revisits

    @property
    def successful_strategy_class_count(self) -> int:
        return self.successful_strategy_classes

    @property
    def optimal_unique(self) -> bool:
        return self.optimal_uniqueness

    @property
    def equivalent_choice_count(self) -> int:
        return self.equivalent_choices

    @property
    def no_op_choice_count(self) -> int:
        return self.no_op_choices

    @property
    def route_distance_cost(self) -> float:
        return self.optimal_route_distance

    @property
    def timing_cost_seconds(self) -> float:
        return self.optimal_travel_time_seconds

    def agent_result_for(self, policy_name: str) -> PolicyEvaluationResult:
        for result in self.agent_results:
            if result.policy_name == policy_name:
                return result
        raise KeyError(policy_name)
