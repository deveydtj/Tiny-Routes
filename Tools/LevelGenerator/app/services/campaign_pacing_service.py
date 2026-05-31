from __future__ import annotations

from dataclasses import dataclass, field

from ..models.candidate_signature import CandidateSignature


@dataclass(frozen=True)
class CampaignPacingResult:
    score: float
    penalties: tuple[str, ...] = field(default_factory=tuple)
    details: dict[str, object] = field(default_factory=dict)


class CampaignPacingService:
    def score(
        self,
        candidate: CandidateSignature,
        previous_signatures: list[CandidateSignature],
        *,
        estimated_band: str,
        target_band: str,
    ) -> CampaignPacingResult:
        if not previous_signatures:
            return CampaignPacingResult(
                score=1.0,
                details={
                    "previousLevelID": None,
                    "sameRecipeFamilyStreak": 0,
                    "tapCountDeltaFromPrevious": 0,
                    "estimatedBand": estimated_band,
                    "targetBand": target_band,
                },
            )

        previous = previous_signatures[-1]
        penalties: list[str] = []
        score = 1.0
        tap_delta = candidate.required_tap_count - previous.required_tap_count
        if tap_delta > 2:
            score -= 0.25
            penalties.append("campaign_tap_count_spike")
        if candidate.template_name == previous.template_name:
            score -= 0.18
            penalties.append("campaign_repeated_recipe_family")
        if (
            candidate.template_name == previous.template_name
            and candidate.required_tap_count == previous.required_tap_count
            and candidate.switch_count == previous.switch_count
        ):
            score -= 0.20
            penalties.append("campaign_adjacent_duplicate_mechanics")
        if self._band_index(estimated_band) - self._band_index(target_band) > 1:
            score -= 0.22
            penalties.append("campaign_difficulty_cliff")
        same_family_streak = 1
        for signature in reversed(previous_signatures):
            if signature.template_name != candidate.template_name:
                break
            same_family_streak += 1
        if same_family_streak >= 3:
            score -= 0.14
            penalties.append("campaign_recipe_family_streak")

        return CampaignPacingResult(
            score=round(max(0.0, min(1.0, score)), 4),
            penalties=tuple(dict.fromkeys(penalties)),
            details={
                "previousLevelID": previous.level_id,
                "sameRecipeFamilyStreak": same_family_streak,
                "tapCountDeltaFromPrevious": tap_delta,
                "estimatedBand": estimated_band,
                "targetBand": target_band,
            },
        )

    def _band_index(self, band: str) -> int:
        bands = ("tutorial", "easy", "medium", "hard", "expert")
        return bands.index(band) if band in bands else -1
