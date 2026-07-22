"""Deterministic aggregate health evidence for production V3 generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip().lower()


def _rate(value: float, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    normalized = round(float(value), 9)
    if not 0.0 <= normalized <= 1.0:
        raise ValueError(f"{field_name} must be between zero and one")
    return normalized


@dataclass(frozen=True)
class GeneratorHealthSlice:
    """Health metrics for one difficulty or blueprint-archetype cohort."""

    key: str
    attempt_count: int
    completed_pipeline_count: int
    accepted_candidate_count: int
    completion_rate: float
    candidate_yield: float
    dominant_rejections: tuple[tuple[str, int], ...]
    static_policy_rejection_rate: float
    agent_performance: tuple[tuple[str, float], ...]
    mean_decision_metrics: tuple[tuple[str, float], ...]
    layout_repair_rate: float
    runtime_robustness_rate: float
    static_policy_solvable_output_count: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _identifier(self.key, "key"))
        for field_name in (
            "attempt_count",
            "completed_pipeline_count",
            "accepted_candidate_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.completed_pipeline_count > self.attempt_count:
            raise ValueError("completed_pipeline_count cannot exceed attempt_count")
        if self.accepted_candidate_count > self.attempt_count:
            raise ValueError("accepted_candidate_count cannot exceed attempt_count")
        if (
            not isinstance(self.static_policy_solvable_output_count, int)
            or isinstance(self.static_policy_solvable_output_count, bool)
            or self.static_policy_solvable_output_count < 0
        ):
            raise ValueError(
                "static_policy_solvable_output_count must be a non-negative integer"
            )
        if self.static_policy_solvable_output_count > self.accepted_candidate_count:
            raise ValueError(
                "static_policy_solvable_output_count cannot exceed accepted_candidate_count"
            )
        for field_name in (
            "completion_rate",
            "candidate_yield",
            "static_policy_rejection_rate",
            "layout_repair_rate",
            "runtime_robustness_rate",
        ):
            object.__setattr__(self, field_name, _rate(getattr(self, field_name), field_name))
        for field_name in ("agent_performance", "mean_decision_metrics"):
            values = tuple(getattr(self, field_name))
            keys = tuple(item[0] for item in values)
            if keys != tuple(sorted(set(keys))):
                raise ValueError(f"{field_name} must be sorted and unique")
            object.__setattr__(self, field_name, values)
        rejections = tuple(self.dominant_rejections)
        rejection_keys = tuple(item[0] for item in rejections)
        if len(rejection_keys) != len(set(rejection_keys)):
            raise ValueError("dominant_rejections must have unique codes")
        if any(
            not isinstance(count, int) or isinstance(count, bool) or count < 1
            for _, count in rejections
        ):
            raise ValueError("dominant_rejections counts must be positive integers")
        if rejections != tuple(sorted(rejections, key=lambda item: (-item[1], item[0]))):
            raise ValueError("dominant_rejections must be ordered by count then code")
        object.__setattr__(self, "dominant_rejections", rejections)
        for _, value in self.agent_performance:
            _rate(value, "agent_performance")
        for _, value in self.mean_decision_metrics:
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                raise ValueError("mean_decision_metrics values must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "attemptCount": self.attempt_count,
            "completedPipelineCount": self.completed_pipeline_count,
            "acceptedCandidateCount": self.accepted_candidate_count,
            "completionRate": self.completion_rate,
            "candidateYield": self.candidate_yield,
            "dominantRejections": [
                {"code": code, "count": count}
                for code, count in self.dominant_rejections
            ],
            "staticPolicyRejectionRate": self.static_policy_rejection_rate,
            "agentPerformance": {
                policy: success_rate for policy, success_rate in self.agent_performance
            },
            "meanDecisionMetrics": dict(self.mean_decision_metrics),
            "layoutRepairRate": self.layout_repair_rate,
            "runtimeRobustnessRate": self.runtime_robustness_rate,
            "staticPolicySolvableOutputCount": (
                self.static_policy_solvable_output_count
            ),
        }


@dataclass(frozen=True)
class PortfolioDiversityMetrics:
    selected_count: int
    topology_ratio: float
    behavior_ratio: float
    archetype_ratio: float
    mechanic_ratio: float
    aggregate_score: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.selected_count, int)
            or isinstance(self.selected_count, bool)
            or self.selected_count < 0
        ):
            raise ValueError("selected_count must be a non-negative integer")
        for field_name in (
            "topology_ratio",
            "behavior_ratio",
            "archetype_ratio",
            "mechanic_ratio",
            "aggregate_score",
        ):
            object.__setattr__(self, field_name, _rate(getattr(self, field_name), field_name))

    def to_dict(self) -> dict[str, Any]:
        return {
            "selectedCount": self.selected_count,
            "topologyRatio": self.topology_ratio,
            "behaviorRatio": self.behavior_ratio,
            "archetypeRatio": self.archetype_ratio,
            "mechanicRatio": self.mechanic_ratio,
            "aggregateScore": self.aggregate_score,
        }


@dataclass(frozen=True)
class GeneratorHealthReport:
    """One schema-versioned health snapshot suitable for CI trend storage."""

    root_seed: int
    run_completed: bool
    overall: GeneratorHealthSlice
    by_difficulty: tuple[GeneratorHealthSlice, ...]
    by_archetype: tuple[GeneratorHealthSlice, ...]
    portfolio_diversity: PortfolioDiversityMetrics
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.root_seed, int) or isinstance(self.root_seed, bool):
            raise ValueError("root_seed must be an integer")
        if not isinstance(self.run_completed, bool):
            raise ValueError("run_completed must be a Boolean")
        if not isinstance(self.overall, GeneratorHealthSlice):
            raise TypeError("overall must be a GeneratorHealthSlice")
        for field_name in ("by_difficulty", "by_archetype"):
            values = tuple(getattr(self, field_name))
            if any(not isinstance(item, GeneratorHealthSlice) for item in values):
                raise TypeError(f"{field_name} must contain GeneratorHealthSlice values")
            keys = tuple(item.key for item in values)
            if keys != tuple(sorted(set(keys))):
                raise ValueError(f"{field_name} must be sorted and unique")
            object.__setattr__(self, field_name, values)
        if not isinstance(self.portfolio_diversity, PortfolioDiversityMetrics):
            raise TypeError("portfolio_diversity must be PortfolioDiversityMetrics")
        if self.schema_version != 1:
            raise ValueError("unsupported generator health schema version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "rootSeed": self.root_seed,
            "runCompleted": self.run_completed,
            "overall": self.overall.to_dict(),
            "byDifficulty": [item.to_dict() for item in self.by_difficulty],
            "byArchetype": [item.to_dict() for item in self.by_archetype],
            "portfolioDiversity": self.portfolio_diversity.to_dict(),
        }


@dataclass(frozen=True)
class GeneratorHealthThresholds:
    """Locked limits used to distinguish churn from systemic regressions."""

    minimum_attempt_count: int = 20
    maximum_dominant_rejection_share: float = 0.70
    maximum_dominant_rejection_share_increase: float = 0.20
    minimum_candidate_yield: float = 0.02
    maximum_candidate_yield_drop: float = 0.15
    maximum_decision_metric_drift: float = 0.30
    maximum_behavior_duplicate_rate: float = 0.25
    maximum_behavior_duplicate_rate_increase: float = 0.10
    require_completed_run: bool = True

    def __post_init__(self) -> None:
        if (
            not isinstance(self.minimum_attempt_count, int)
            or isinstance(self.minimum_attempt_count, bool)
            or self.minimum_attempt_count < 1
        ):
            raise ValueError("minimum_attempt_count must be a positive integer")
        for field_name in (
            "maximum_dominant_rejection_share",
            "maximum_dominant_rejection_share_increase",
            "minimum_candidate_yield",
            "maximum_candidate_yield_drop",
            "maximum_decision_metric_drift",
            "maximum_behavior_duplicate_rate",
            "maximum_behavior_duplicate_rate_increase",
        ):
            object.__setattr__(
                self,
                field_name,
                _rate(getattr(self, field_name), field_name),
            )
        if not isinstance(self.require_completed_run, bool):
            raise ValueError("require_completed_run must be a Boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "minimumAttemptCount": self.minimum_attempt_count,
            "maximumDominantRejectionShare": self.maximum_dominant_rejection_share,
            "maximumDominantRejectionShareIncrease": (
                self.maximum_dominant_rejection_share_increase
            ),
            "minimumCandidateYield": self.minimum_candidate_yield,
            "maximumCandidateYieldDrop": self.maximum_candidate_yield_drop,
            "maximumDecisionMetricDrift": self.maximum_decision_metric_drift,
            "maximumBehaviorDuplicateRate": self.maximum_behavior_duplicate_rate,
            "maximumBehaviorDuplicateRateIncrease": (
                self.maximum_behavior_duplicate_rate_increase
            ),
            "requireCompletedRun": self.require_completed_run,
        }


@dataclass(frozen=True)
class GeneratorHealthAnomaly:
    """One stable CI/stress failure with current and baseline evidence."""

    code: str
    cohort: str
    metric: str
    actual: float
    required: str
    baseline: float | None = None

    def __post_init__(self) -> None:
        for field_name in ("code", "cohort", "metric", "required"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} cannot be empty")
            object.__setattr__(self, field_name, value.strip())
        for field_name in ("actual", "baseline"):
            value = getattr(self, field_name)
            if value is None and field_name == "baseline":
                continue
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"{field_name} must be numeric")
            object.__setattr__(self, field_name, round(float(value), 9))

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "cohort": self.cohort,
            "metric": self.metric,
            "actual": self.actual,
            "required": self.required,
            "baseline": self.baseline,
        }


@dataclass(frozen=True)
class GeneratorHealthAnomalyReport:
    """Deterministic result consumed by CI and campaign stress runners."""

    current_root_seed: int
    baseline_root_seed: int | None
    thresholds: GeneratorHealthThresholds
    anomalies: tuple[GeneratorHealthAnomaly, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        for field_name in ("current_root_seed", "baseline_root_seed"):
            value = getattr(self, field_name)
            if value is None and field_name == "baseline_root_seed":
                continue
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"{field_name} must be an integer")
        if not isinstance(self.thresholds, GeneratorHealthThresholds):
            raise TypeError("thresholds must be GeneratorHealthThresholds")
        anomalies = tuple(self.anomalies)
        if any(not isinstance(item, GeneratorHealthAnomaly) for item in anomalies):
            raise TypeError("anomalies must contain GeneratorHealthAnomaly values")
        if anomalies != tuple(sorted(set(anomalies), key=_anomaly_sort_key)):
            raise ValueError("anomalies must be sorted and unique")
        object.__setattr__(self, "anomalies", anomalies)
        if self.schema_version != 1:
            raise ValueError("unsupported generator anomaly schema version")

    @property
    def passed(self) -> bool:
        return not self.anomalies

    @property
    def rejection_codes(self) -> tuple[str, ...]:
        return tuple(item.code for item in self.anomalies)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "passed": self.passed,
            "currentRootSeed": self.current_root_seed,
            "baselineRootSeed": self.baseline_root_seed,
            "thresholds": self.thresholds.to_dict(),
            "anomalies": [item.to_dict() for item in self.anomalies],
        }


def _anomaly_sort_key(item: GeneratorHealthAnomaly) -> tuple[Any, ...]:
    return (
        item.code,
        item.cohort,
        item.metric,
        item.actual,
        item.required,
        float("-inf") if item.baseline is None else item.baseline,
    )
