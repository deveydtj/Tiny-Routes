"""Proof-backed par-tap and runtime-limit derivation evidence."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .strategy_search import StrategyCost


def _finite_non_negative(value: int | float, field_name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(float(value))
        or value < 0
    ):
        raise ValueError(f"{field_name} must be a finite non-negative number")
    return round(float(value), 9)


@dataclass(frozen=True)
class ParTapDerivationResult:
    """Fail-closed result for par derived from an exhaustive optimal proof."""

    accepted: bool
    par_taps: int | None
    optimal_cost: StrategyCost | None
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.accepted, bool):
            raise ValueError("accepted must be a Boolean")
        if self.optimal_cost is not None and not isinstance(self.optimal_cost, StrategyCost):
            raise ValueError("optimal_cost must be a StrategyCost")
        reasons = tuple(sorted(set(self.rejection_reasons)))
        if self.accepted:
            if reasons:
                raise ValueError("accepted par derivation cannot have rejection reasons")
            if self.optimal_cost is None or self.par_taps is None:
                raise ValueError("accepted par derivation requires optimal cost evidence")
            if self.par_taps != self.optimal_cost.accepted_taps:
                raise ValueError("par_taps must equal the optimal accepted-tap cost")
        elif not reasons:
            raise ValueError("rejected par derivation requires a rejection reason")
        if self.par_taps is not None and (
            not isinstance(self.par_taps, int)
            or isinstance(self.par_taps, bool)
            or self.par_taps < 0
        ):
            raise ValueError("par_taps must be a non-negative integer")
        object.__setattr__(self, "rejection_reasons", reasons)


@dataclass(frozen=True)
class RuntimeDistributionSummary:
    """Deterministic travel-time distribution for optimal and near-optimal routes."""

    samples_seconds: tuple[float, ...]
    median_seconds: float
    upper_quartile_seconds: float
    maximum_seconds: float

    def __post_init__(self) -> None:
        samples = tuple(
            _finite_non_negative(value, "runtime sample")
            for value in self.samples_seconds
        )
        if not samples:
            raise ValueError("runtime distribution requires at least one sample")
        if samples != tuple(sorted(samples)):
            raise ValueError("runtime distribution samples must be sorted")
        object.__setattr__(self, "samples_seconds", samples)
        for field_name in (
            "median_seconds",
            "upper_quartile_seconds",
            "maximum_seconds",
        ):
            object.__setattr__(
                self,
                field_name,
                _finite_non_negative(getattr(self, field_name), field_name),
            )
        if not (
            samples[0]
            <= self.median_seconds
            <= self.upper_quartile_seconds
            <= self.maximum_seconds
            == samples[-1]
        ):
            raise ValueError("runtime distribution summary must match its samples")

    @property
    def sample_count(self) -> int:
        return len(self.samples_seconds)


@dataclass(frozen=True)
class TimeLimitDerivationResult:
    """Auditable time-limit calculation or a fail-closed rejection."""

    accepted: bool
    time_limit_seconds: int | None
    par_taps: int | None
    optimal_travel_time_seconds: float | None
    runtime_distribution: RuntimeDistributionSummary | None
    distribution_reference_seconds: float | None
    planning_allowance_seconds: float
    input_allowance_seconds: float
    available_planning_margin_seconds: float
    star_time_thresholds_seconds: tuple[int, ...] = ()
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.accepted, bool):
            raise ValueError("accepted must be a Boolean")
        if self.runtime_distribution is not None and not isinstance(
            self.runtime_distribution,
            RuntimeDistributionSummary,
        ):
            raise ValueError("runtime_distribution must be a RuntimeDistributionSummary")
        reasons = tuple(sorted(set(self.rejection_reasons)))
        if self.accepted:
            if reasons:
                raise ValueError("accepted time derivation cannot have rejection reasons")
            if any(
                value is None
                for value in (
                    self.time_limit_seconds,
                    self.par_taps,
                    self.optimal_travel_time_seconds,
                    self.runtime_distribution,
                    self.distribution_reference_seconds,
                )
            ):
                raise ValueError("accepted time derivation requires complete evidence")
        elif not reasons:
            raise ValueError("rejected time derivation requires a rejection reason")
        if self.time_limit_seconds is not None and (
            not isinstance(self.time_limit_seconds, int)
            or isinstance(self.time_limit_seconds, bool)
            or self.time_limit_seconds < 1
        ):
            raise ValueError("time_limit_seconds must be a positive integer")
        if self.par_taps is not None and (
            not isinstance(self.par_taps, int)
            or isinstance(self.par_taps, bool)
            or self.par_taps < 0
        ):
            raise ValueError("par_taps must be a non-negative integer")
        for field_name in (
            "planning_allowance_seconds",
            "input_allowance_seconds",
            "available_planning_margin_seconds",
        ):
            object.__setattr__(
                self,
                field_name,
                _finite_non_negative(getattr(self, field_name), field_name),
            )
        for field_name in (
            "optimal_travel_time_seconds",
            "distribution_reference_seconds",
        ):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _finite_non_negative(value, field_name))
        thresholds = tuple(self.star_time_thresholds_seconds)
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 1
            for value in thresholds
        ):
            raise ValueError("star time thresholds must be positive integers")
        if thresholds != tuple(sorted(thresholds)):
            raise ValueError("star time thresholds must be ordered fastest to slowest")
        if (
            self.time_limit_seconds is not None
            and thresholds
            and thresholds[-1] != self.time_limit_seconds
        ):
            raise ValueError("the slowest star threshold must equal the time limit")
        object.__setattr__(self, "star_time_thresholds_seconds", thresholds)
        object.__setattr__(self, "rejection_reasons", reasons)
