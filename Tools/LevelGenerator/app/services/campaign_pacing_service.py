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
                    "sameTopologyClassInRecentWindow": 0,
                    "nearbyMechanicTagOverlap": 0.0,
                    "tapCountDeltaFromPrevious": 0,
                    "repeatedSpecialMechanics": (),
                    "sameMapSizeProfileInRecentWindow": 0,
                    "mapSizeProfile": candidate.layout_size_profile,
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
        recent_topology_matches = (
            sum(
                1
                for signature in previous_signatures[-3:]
                if candidate.topology_class
                and signature.topology_class == candidate.topology_class
            )
            if candidate.topology_class
            else 0
        )
        if recent_topology_matches:
            score -= min(0.18, 0.06 * recent_topology_matches)
            penalties.append("campaign_repeated_topology_class")
        if candidate.primary_mechanic_tag and candidate.primary_mechanic_tag == previous.primary_mechanic_tag:
            score -= 0.07
            penalties.append("campaign_repeated_primary_mechanic")
        if candidate.required_tap_count == previous.required_tap_count and candidate.switch_count == previous.switch_count:
            score -= 0.08
            penalties.append("campaign_repeated_switch_count_pattern")
        nearby_mechanic_tag_overlap = self._nearby_mechanic_tag_overlap(candidate, previous_signatures)
        if nearby_mechanic_tag_overlap >= 0.5:
            score -= 0.08
            penalties.append("campaign_nearby_mechanic_tag_overlap")
        repeated_special_mechanics = self._repeated_special_mechanics(candidate, previous_signatures)
        if repeated_special_mechanics:
            score -= min(0.18, 0.06 * len(repeated_special_mechanics))
            penalties.extend(f"campaign_repeated_{mechanic}_usage" for mechanic in repeated_special_mechanics)
        recent_same_map_size = sum(
            1
            for signature in previous_signatures[-3:]
            if signature.layout_size_profile == candidate.layout_size_profile
        )
        if candidate.layout_size_profile == "large_portrait" and recent_same_map_size:
            score -= min(0.18, 0.09 * recent_same_map_size)
            penalties.append("campaign_repeated_large_portrait_profile")
        elif recent_same_map_size >= 3 and target_band not in {"tutorial", "easy"}:
            score -= 0.06
            penalties.append("campaign_repeated_map_size_profile")
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
                "sameTopologyClassInRecentWindow": recent_topology_matches,
                "nearbyMechanicTagOverlap": nearby_mechanic_tag_overlap,
                "tapCountDeltaFromPrevious": tap_delta,
                "repeatedSpecialMechanics": repeated_special_mechanics,
                "sameMapSizeProfileInRecentWindow": recent_same_map_size,
                "mapSizeProfile": candidate.layout_size_profile,
                "estimatedBand": estimated_band,
                "targetBand": target_band,
            },
        )

    def _nearby_mechanic_tag_overlap(
        self,
        candidate: CandidateSignature,
        previous_signatures: list[CandidateSignature],
    ) -> float:
        candidate_tags = set(candidate.mechanic_tags)
        if not candidate_tags:
            return 0.0
        recent_tags = set()
        for signature in previous_signatures[-5:]:
            recent_tags.update(signature.mechanic_tags)
        if not recent_tags:
            return 0.0
        return round(len(candidate_tags & recent_tags) / len(candidate_tags), 4)

    def _repeated_special_mechanics(
        self,
        candidate: CandidateSignature,
        previous_signatures: list[CandidateSignature],
    ) -> tuple[str, ...]:
        candidate_tags = set(candidate.mechanic_tags)
        mechanic_tags = {
            "fake_shortcut": {"fake_shortcut"},
            "hub": {"hub"},
            "loop_revisit": {"loop", "revisit", "repeated_tap", "ring", "package_inside_loop"},
        }
        repeated: list[str] = []
        recent = previous_signatures[-2:]
        for mechanic, tags in mechanic_tags.items():
            if not candidate_tags.intersection(tags):
                continue
            if any(set(signature.mechanic_tags).intersection(tags) for signature in recent):
                repeated.append(mechanic)
        return tuple(repeated)

    def _band_index(self, band: str) -> int:
        bands = ("tutorial", "easy", "medium", "hard", "expert")
        return bands.index(band) if band in bands else -1
