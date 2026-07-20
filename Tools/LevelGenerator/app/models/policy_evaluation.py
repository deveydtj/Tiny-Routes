"""Typed deterministic player-policy evaluation evidence."""

from __future__ import annotations

from dataclasses import dataclass

from .strategy_search import StrategyCost


def _identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


def _non_negative(value: int | float, field_name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be non-negative")


@dataclass(frozen=True, order=True)
class PolicyFailureCount:
    """Stable aggregate count for one terminal policy failure code."""

    code: str
    count: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _identifier(self.code, "code"))
        if not isinstance(self.count, int) or isinstance(self.count, bool) or self.count < 1:
            raise ValueError("count must be a positive integer")


@dataclass(frozen=True, order=True)
class PolicyDivergence:
    """A visible decision where a policy departed from the proven optimum."""

    run_index: int
    decision_ordinal: int
    objective_index: int
    node_id: str
    selected_edge_id: str
    optimal_edge_id: str

    def __post_init__(self) -> None:
        for field_name in ("run_index", "decision_ordinal", "objective_index"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        for field_name in ("node_id", "selected_edge_id", "optimal_edge_id"):
            object.__setattr__(
                self,
                field_name,
                _identifier(getattr(self, field_name), field_name),
            )


@dataclass(frozen=True)
class PolicyRunResult:
    """One complete, bounded structural simulation of one player policy."""

    run_index: int
    succeeded: bool
    accepted_taps: int
    completion_time_seconds: float
    route_distance: float
    outcome_code: str
    divergences: tuple[PolicyDivergence, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.run_index, int) or isinstance(self.run_index, bool) or self.run_index < 0:
            raise ValueError("run_index must be a non-negative integer")
        if not isinstance(self.succeeded, bool):
            raise ValueError("succeeded must be a Boolean")
        if not isinstance(self.accepted_taps, int) or isinstance(self.accepted_taps, bool):
            raise ValueError("accepted_taps must be an integer")
        _non_negative(self.accepted_taps, "accepted_taps")
        _non_negative(self.completion_time_seconds, "completion_time_seconds")
        _non_negative(self.route_distance, "route_distance")
        object.__setattr__(
            self,
            "completion_time_seconds",
            round(float(self.completion_time_seconds), 9),
        )
        object.__setattr__(self, "route_distance", round(float(self.route_distance), 9))
        object.__setattr__(self, "outcome_code", _identifier(self.outcome_code, "outcome_code"))
        divergences = tuple(self.divergences)
        if any(item.run_index != self.run_index for item in divergences):
            raise ValueError("divergences must belong to their policy run")
        object.__setattr__(self, "divergences", divergences)


@dataclass(frozen=True)
class PolicyRegret:
    """Average successful-policy cost above the exact optimum."""

    accepted_taps: float
    completion_time_seconds: float
    route_distance: float

    def __post_init__(self) -> None:
        for field_name in ("accepted_taps", "completion_time_seconds", "route_distance"):
            _non_negative(getattr(self, field_name), field_name)
            object.__setattr__(self, field_name, round(float(getattr(self, field_name)), 9))


@dataclass(frozen=True)
class PolicyEvaluationResult:
    """Aggregate metrics for all deterministic runs of one named policy."""

    policy_name: str
    runs: tuple[PolicyRunResult, ...]
    optimal_cost: StrategyCost

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_name", _identifier(self.policy_name, "policy_name"))
        runs = tuple(self.runs)
        if not runs:
            raise ValueError("a policy evaluation requires at least one run")
        if tuple(item.run_index for item in runs) != tuple(range(len(runs))):
            raise ValueError("policy run indices must be contiguous from zero")
        object.__setattr__(self, "runs", runs)

    @property
    def run_count(self) -> int:
        return len(self.runs)

    @property
    def success_count(self) -> int:
        return sum(run.succeeded for run in self.runs)

    @property
    def success_rate(self) -> float:
        return self.success_count / self.run_count

    @property
    def successful_runs(self) -> tuple[PolicyRunResult, ...]:
        return tuple(run for run in self.runs if run.succeeded)

    @property
    def average_taps(self) -> float | None:
        successful = self.successful_runs
        if not successful:
            return None
        return round(sum(run.accepted_taps for run in successful) / len(successful), 9)

    @property
    def average_completion_time_seconds(self) -> float | None:
        successful = self.successful_runs
        if not successful:
            return None
        return round(
            sum(run.completion_time_seconds for run in successful) / len(successful),
            9,
        )

    @property
    def average_route_distance(self) -> float | None:
        successful = self.successful_runs
        if not successful:
            return None
        return round(sum(run.route_distance for run in successful) / len(successful), 9)

    @property
    def failure_types(self) -> tuple[PolicyFailureCount, ...]:
        counts: dict[str, int] = {}
        for run in self.runs:
            if not run.succeeded:
                counts[run.outcome_code] = counts.get(run.outcome_code, 0) + 1
        return tuple(PolicyFailureCount(code, counts[code]) for code in sorted(counts))

    @property
    def divergences(self) -> tuple[PolicyDivergence, ...]:
        return tuple(item for run in self.runs for item in run.divergences)

    @property
    def regret_relative_to_optimum(self) -> PolicyRegret | None:
        taps = self.average_taps
        duration = self.average_completion_time_seconds
        distance = self.average_route_distance
        if taps is None or duration is None or distance is None:
            return None
        return PolicyRegret(
            accepted_taps=max(0.0, taps - self.optimal_cost.accepted_taps),
            completion_time_seconds=max(
                0.0,
                duration - self.optimal_cost.travel_time_seconds,
            ),
            route_distance=max(0.0, distance - self.optimal_cost.route_distance),
        )


@dataclass(frozen=True)
class PolicyEvaluationReport:
    """Complete policy suite evidence for one level and one exact optimum."""

    level_id: str
    optimal_cost: StrategyCost
    evaluations: tuple[PolicyEvaluationResult, ...]
    strategy_proof_exhaustive: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "level_id", _identifier(self.level_id, "level_id"))
        if not isinstance(self.strategy_proof_exhaustive, bool):
            raise ValueError("strategy_proof_exhaustive must be a Boolean")
        evaluations = tuple(self.evaluations)
        if not evaluations:
            raise ValueError("a policy evaluation report requires at least one policy")
        names = tuple(item.policy_name for item in evaluations)
        if len(names) != len(set(names)):
            raise ValueError("policy names must be unique")
        if any(item.optimal_cost != self.optimal_cost for item in evaluations):
            raise ValueError("all policy evaluations must use the report optimum")
        object.__setattr__(self, "evaluations", evaluations)

    def evaluation_for(self, policy_name: str) -> PolicyEvaluationResult:
        """Return one named policy result or fail loudly on report misuse."""

        for evaluation in self.evaluations:
            if evaluation.policy_name == policy_name:
                return evaluation
        raise KeyError(policy_name)
