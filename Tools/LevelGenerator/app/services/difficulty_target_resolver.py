"""Resolve locked V3 production difficulty bands into experience targets."""

from __future__ import annotations

from ..models.puzzle_experience_target import PuzzleExperienceTarget
from .quality_profile_service import QualityProfileService


class DifficultyTargetResolver:
    """Provide immutable targets from the V3 player-experience matrix.

    Tutorial generation is intentionally absent. The production V3 contract
    starts at easy and never permits the zero- or one-decision tutorial shapes
    retained by the legacy generator.
    """

    band_order = ("easy", "medium", "hard", "expert")

    def __init__(
        self,
        quality_profile_service: QualityProfileService | None = None,
        *,
        quality_profile_version: str | None = None,
    ) -> None:
        service = quality_profile_service or QualityProfileService()
        self.quality_profile = (
            service.load(quality_profile_version)
            if quality_profile_version is not None
            else service.load_current()
        )
        self._targets = dict(self.quality_profile.difficulty_targets)

    @property
    def valid_names(self) -> list[str]:
        return list(self.band_order)

    def resolve(self, difficulty: str) -> PuzzleExperienceTarget:
        if not isinstance(difficulty, str):
            raise ValueError("difficulty must be a production V3 difficulty name")
        key = difficulty.strip().lower()
        try:
            return self._targets[key]
        except KeyError as exc:
            if key == "tutorial":
                raise ValueError(
                    "tutorial is not a production_v3 difficulty; use v2_legacy "
                    "for tutorial fixtures"
                ) from exc
            raise ValueError(f"Unknown production V3 difficulty target: {difficulty}") from exc

    def get_target(self, difficulty: str) -> PuzzleExperienceTarget:
        """Compatibility spelling for callers that use existing service APIs."""

        return self.resolve(difficulty)


DifficultyTargetResolverService = DifficultyTargetResolver
