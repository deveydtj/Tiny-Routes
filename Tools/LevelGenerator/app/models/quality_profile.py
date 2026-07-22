"""Versioned calibration inputs for production V3 puzzle quality."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .puzzle_experience_target import PuzzleExperienceTarget


_SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
CURRENT_QUALITY_PROFILE_VERSION = "1.0.0"


@dataclass(frozen=True)
class QualityProfileEvidence:
    playtest_evidence: str
    fixed_seed_comparison: str

    def __post_init__(self) -> None:
        for field_name in ("playtest_evidence", "fixed_seed_comparison"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} cannot be empty")
            object.__setattr__(self, field_name, value.strip())

    def to_dict(self) -> dict[str, str]:
        return {
            "playtestEvidence": self.playtest_evidence,
            "fixedSeedComparison": self.fixed_seed_comparison,
        }


@dataclass(frozen=True)
class CalibratedQualityProfile:
    profile_id: str
    version: str
    evidence: QualityProfileEvidence
    protected_invariants: dict[str, Any]
    ranking_weights: dict[str, float]
    archetype_frequencies: dict[str, float]
    difficulty_targets: dict[str, PuzzleExperienceTarget]
    notes: str = ""
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not self.profile_id.strip():
            raise ValueError("profile_id cannot be empty")
        object.__setattr__(self, "profile_id", self.profile_id.strip())
        if not isinstance(self.version, str) or not _SEMVER.fullmatch(self.version):
            raise ValueError("version must use MAJOR.MINOR.PATCH semantic versioning")
        if not isinstance(self.evidence, QualityProfileEvidence):
            raise TypeError("evidence must be QualityProfileEvidence")
        if self.schema_version != 1:
            raise ValueError("unsupported quality profile schema version")
        required = {
            "minimumMeaningfulDecisions": 2,
            "minimumPlanningDecisions": 1,
            "minimumAdaptiveDecisions": 1,
            "requireStateChange": True,
            "rejectStaticPolicy": True,
            "rejectEquivalentChoices": True,
            "requireProvenUniqueOptimum": True,
        }
        for key, floor in required.items():
            actual = self.protected_invariants.get(key)
            if isinstance(floor, bool):
                if actual is not floor:
                    raise ValueError(f"protected invariant {key} cannot be disabled")
            elif not isinstance(actual, int) or isinstance(actual, bool) or actual < floor:
                raise ValueError(f"protected invariant {key} cannot be weakened")
        self._validate_distribution(self.ranking_weights, "ranking_weights")
        self._validate_distribution(
            self.archetype_frequencies, "archetype_frequencies"
        )
        expected = ("easy", "medium", "hard", "expert")
        if tuple(sorted(self.difficulty_targets, key=expected.index)) != expected:
            raise ValueError("difficulty_targets must define easy through expert")
        for key, target in self.difficulty_targets.items():
            if not isinstance(target, PuzzleExperienceTarget) or target.difficulty != key:
                raise ValueError("difficulty target key must match its target")
            if target.meaningful_decision_range[0] < required[
                "minimumMeaningfulDecisions"
            ]:
                raise ValueError("difficulty target weakens meaningful-decision invariant")
            if target.planning_decision_minimum < required[
                "minimumPlanningDecisions"
            ]:
                raise ValueError("difficulty target weakens planning invariant")
            if target.adaptive_decision_minimum < required[
                "minimumAdaptiveDecisions"
            ]:
                raise ValueError("difficulty target weakens adaptive invariant")
            if target.state_change_range[0] < 1:
                raise ValueError("difficulty target must require a state change")

    @staticmethod
    def _validate_distribution(values: dict[str, float], field_name: str) -> None:
        if not isinstance(values, dict) or not values:
            raise ValueError(f"{field_name} cannot be empty")
        if any(not isinstance(key, str) or not key.strip() for key in values):
            raise ValueError(f"{field_name} keys cannot be empty")
        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or float(value) < 0.0
            for value in values.values()
        ):
            raise ValueError(f"{field_name} values must be non-negative numbers")
        if abs(sum(float(value) for value in values.values()) - 1.0) > 1e-6:
            raise ValueError(f"{field_name} values must sum to one")

    @property
    def fingerprint(self) -> str:
        canonical = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def reference(self) -> dict[str, Any]:
        return {
            "id": self.profile_id,
            "version": self.version,
            "fingerprint": self.fingerprint,
            "schemaVersion": self.schema_version,
            "evidence": self.evidence.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "profileID": self.profile_id,
            "version": self.version,
            "evidence": self.evidence.to_dict(),
            "protectedInvariants": dict(sorted(self.protected_invariants.items())),
            "rankingWeights": dict(sorted(self.ranking_weights.items())),
            "archetypeFrequencies": dict(sorted(self.archetype_frequencies.items())),
            "difficultyTargets": {
                key: _target_to_dict(value)
                for key, value in sorted(self.difficulty_targets.items())
            },
            "notes": self.notes,
        }


def _target_to_dict(target: PuzzleExperienceTarget) -> dict[str, Any]:
    return {
        "objectiveCountRange": list(target.objective_count_range),
        "meaningfulDecisionRange": list(target.meaningful_decision_range),
        "planningDecisionMinimum": target.planning_decision_minimum,
        "adaptiveDecisionMinimum": target.adaptive_decision_minimum,
        "dependencyDepthRange": list(target.dependency_depth_range),
        "stateChangeRange": list(target.state_change_range),
        "revisitRange": list(target.revisit_range),
        "successfulRouteClassRange": list(target.successful_route_class_range),
        "recoverableMistakeRange": list(target.recoverable_mistake_range),
        "fatalMistakeCap": target.fatal_mistake_cap,
        "decisionWindowTargets": list(target.decision_window_targets),
        "rapidMultiTapEncounterCap": target.rapid_multi_tap_encounter_cap,
        "maximumTapsPerRapidBurst": target.maximum_taps_per_rapid_burst,
        "minimumStateChangeVisibilitySeconds": (
            target.minimum_state_change_visibility_seconds
        ),
        "allowedMechanicCategories": list(target.allowed_mechanic_categories),
        "layoutComplexityTarget": target.layout_complexity_target,
        "desiredSolveTimeRange": list(target.desired_solve_time_range),
    }
