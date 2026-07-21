"""Typed deterministic evidence for runtime timing-jitter replay."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .runtime_solution_search import RuntimeSolutionAction


def _finite_non_negative(value: float, field_name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{field_name} must be finite and non-negative")
    return value


@dataclass(frozen=True)
class TimingJitterReplayConfig:
    """The required deterministic robustness envelope for one solution."""

    timing_offsets_seconds: tuple[float, ...] = (-0.1, -0.05, 0.05, 0.1)
    frame_step_seconds: tuple[float, ...] = (1.0 / 60.0, 1.0 / 30.0)
    speed_variations: tuple[float, ...] = (-0.001, 0.001)
    include_individual_tap_variations: bool = True

    def __post_init__(self) -> None:
        offsets = tuple(float(value) for value in self.timing_offsets_seconds)
        if any(not math.isfinite(value) for value in offsets):
            raise ValueError("timing_offsets_seconds must be finite")
        frame_steps = tuple(
            _finite_non_negative(value, "frame_step_seconds")
            for value in self.frame_step_seconds
        )
        if any(value == 0 for value in frame_steps):
            raise ValueError("frame_step_seconds must be positive")
        speed_variations = tuple(float(value) for value in self.speed_variations)
        if any(
            not math.isfinite(value) or 1.0 + value <= 0
            for value in speed_variations
        ):
            raise ValueError("speed_variations must retain a positive runtime speed")
        object.__setattr__(self, "timing_offsets_seconds", offsets)
        object.__setattr__(self, "frame_step_seconds", frame_steps)
        object.__setattr__(self, "speed_variations", speed_variations)

    @property
    def maximum_timing_offset_seconds(self) -> float:
        return max((abs(value) for value in self.timing_offsets_seconds), default=0.0)


@dataclass(frozen=True)
class TimingJitterScenarioResult:
    scenario_id: str
    actions: tuple[RuntimeSolutionAction, ...]
    speed: float
    passed: bool
    failure_reason: str | None = None
    rejected_tap_index: int | None = None
    elapsed_time_seconds: float = 0.0


@dataclass(frozen=True)
class TimingJitterReplayReport:
    passed: bool
    scenarios: tuple[TimingJitterScenarioResult, ...]
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        scenarios = tuple(self.scenarios)
        reasons = tuple(sorted(set(self.rejection_reasons)))
        if self.passed != all(scenario.passed for scenario in scenarios):
            raise ValueError("passed must match all jitter scenario results")
        if self.passed and reasons:
            raise ValueError("a passing jitter report cannot have rejection reasons")
        if not self.passed and not reasons:
            raise ValueError("a failing jitter report requires a rejection reason")
        object.__setattr__(self, "scenarios", scenarios)
        object.__setattr__(self, "rejection_reasons", reasons)

    @property
    def failure_reason(self) -> str | None:
        return None if self.passed else "solution_jitter_failure"
