"""Load and validate immutable, evidence-backed quality profile versions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..models.puzzle_experience_target import PuzzleExperienceTarget
from ..models.quality_profile import (
    CURRENT_QUALITY_PROFILE_VERSION,
    CalibratedQualityProfile,
    QualityProfileEvidence,
)


class QualityProfileService:
    def __init__(self, profiles_directory: Path | None = None) -> None:
        self.profiles_directory = Path(
            profiles_directory
            or Path(__file__).resolve().parents[2] / "config" / "quality_profiles"
        )

    def load_current(self) -> CalibratedQualityProfile:
        return self.load(CURRENT_QUALITY_PROFILE_VERSION)

    def load(self, version: str) -> CalibratedQualityProfile:
        if not isinstance(version, str) or not version.strip():
            raise ValueError("quality profile version cannot be empty")
        if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version.strip()):
            raise ValueError("quality profile version must use MAJOR.MINOR.PATCH")
        path = self.profiles_directory / f"production_v3_{version.strip()}.json"
        if not path.is_file():
            raise ValueError(f"unknown production V3 quality profile: {version}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        profile = self._from_dict(payload)
        if profile.version != version.strip():
            raise ValueError("quality profile filename and declared version differ")
        return profile

    def validate_transition(
        self,
        previous: CalibratedQualityProfile,
        candidate: CalibratedQualityProfile,
    ) -> None:
        if previous.profile_id != candidate.profile_id:
            raise ValueError("quality profile identity cannot change during tuning")
        if previous.fingerprint == candidate.fingerprint:
            return
        if previous.version == candidate.version:
            raise ValueError("quality tuning changes require an explicit version change")
        if tuple(map(int, candidate.version.split("."))) <= tuple(
            map(int, previous.version.split("."))
        ):
            raise ValueError("quality tuning requires a higher semantic version")
        if previous.evidence.playtest_evidence == candidate.evidence.playtest_evidence:
            raise ValueError("quality tuning requires updated playtest evidence")
        if previous.evidence.fixed_seed_comparison == candidate.evidence.fixed_seed_comparison:
            raise ValueError("quality tuning requires an updated fixed-seed comparison")
        for key, previous_value in previous.protected_invariants.items():
            candidate_value = candidate.protected_invariants.get(key)
            if isinstance(previous_value, bool):
                if previous_value and candidate_value is not True:
                    raise ValueError(f"protected invariant {key} cannot be weakened")
            elif (
                not isinstance(candidate_value, (int, float))
                or isinstance(candidate_value, bool)
                or candidate_value < previous_value
            ):
                raise ValueError(f"protected invariant {key} cannot be weakened")

    @staticmethod
    def _from_dict(payload: dict[str, Any]) -> CalibratedQualityProfile:
        targets = {
            difficulty: QualityProfileService._target(difficulty, values)
            for difficulty, values in payload["difficultyTargets"].items()
        }
        evidence = payload["evidence"]
        return CalibratedQualityProfile(
            profile_id=payload["profileID"],
            version=payload["version"],
            schema_version=payload.get("schemaVersion", 1),
            evidence=QualityProfileEvidence(
                playtest_evidence=evidence["playtestEvidence"],
                fixed_seed_comparison=evidence["fixedSeedComparison"],
            ),
            protected_invariants=dict(payload["protectedInvariants"]),
            ranking_weights={
                key: float(value) for key, value in payload["rankingWeights"].items()
            },
            archetype_frequencies={
                key: float(value)
                for key, value in payload["archetypeFrequencies"].items()
            },
            difficulty_targets=targets,
            notes=str(payload.get("notes", "")),
        )

    @staticmethod
    def _target(difficulty: str, values: dict[str, Any]) -> PuzzleExperienceTarget:
        pair = lambda key: tuple(values[key])
        return PuzzleExperienceTarget(
            difficulty=difficulty,
            objective_count_range=pair("objectiveCountRange"),
            meaningful_decision_range=pair("meaningfulDecisionRange"),
            planning_decision_minimum=values["planningDecisionMinimum"],
            adaptive_decision_minimum=values["adaptiveDecisionMinimum"],
            dependency_depth_range=pair("dependencyDepthRange"),
            state_change_range=pair("stateChangeRange"),
            revisit_range=pair("revisitRange"),
            successful_route_class_range=pair("successfulRouteClassRange"),
            recoverable_mistake_range=pair("recoverableMistakeRange"),
            fatal_mistake_cap=values["fatalMistakeCap"],
            decision_window_targets=pair("decisionWindowTargets"),
            rapid_multi_tap_encounter_cap=values["rapidMultiTapEncounterCap"],
            maximum_taps_per_rapid_burst=values["maximumTapsPerRapidBurst"],
            minimum_state_change_visibility_seconds=values[
                "minimumStateChangeVisibilitySeconds"
            ],
            allowed_mechanic_categories=tuple(values["allowedMechanicCategories"]),
            layout_complexity_target=values["layoutComplexityTarget"],
            desired_solve_time_range=pair("desiredSolveTimeRange"),
        )
