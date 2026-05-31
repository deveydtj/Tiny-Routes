from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DifficultyMetrics:
    required_tap_count: int
    switch_count: int
    four_way_switch_count: int
    repeated_tap_count: int
    solution_path_length: int
    false_branch_count: int
    loop_count: int
    average_time_between_required_taps: float | None
    minimum_reaction_window_before_required_switch: float | None
    visual_complexity_score: float
    route_crossing_score: float
    package_detour_complexity: float
    mechanical_score: float
    visual_score: float
    estimated_band: str
    explanations: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "requiredTapCount": self.required_tap_count,
            "switchCount": self.switch_count,
            "fourWaySwitchCount": self.four_way_switch_count,
            "repeatedTapCount": self.repeated_tap_count,
            "solutionPathLength": self.solution_path_length,
            "falseBranchCount": self.false_branch_count,
            "loopCount": self.loop_count,
            "averageTimeBetweenRequiredTaps": self.average_time_between_required_taps,
            "minimumReactionWindowBeforeRequiredSwitch": self.minimum_reaction_window_before_required_switch,
            "visualComplexityScore": self.visual_complexity_score,
            "routeCrossingScore": self.route_crossing_score,
            "packageDetourComplexity": self.package_detour_complexity,
            "mechanicalScore": self.mechanical_score,
            "visualScore": self.visual_score,
            "estimatedBand": self.estimated_band,
            "explanations": list(self.explanations),
        }


@dataclass(frozen=True)
class GenerationQualityScore:
    total: float
    readability: float
    uniqueness: float
    difficulty_fit: float
    route_interest: float
    abstract_mechanic_quality: float = 1.0
    runtime_solvability: float = 1.0
    switch_clarity: float = 1.0
    mobile_tap_comfort: float = 1.0
    visual_appeal: float = 1.0
    campaign_pacing: float = 1.0
    mechanical_difficulty: float = 0.0
    visual_difficulty: float = 0.0
    estimated_difficulty_band: str | None = None
    penalties: tuple[str, ...] = field(default_factory=tuple)
    details: dict[str, Any] = field(default_factory=dict)
