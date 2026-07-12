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
        if self._decision_type(candidate) == self._decision_type(previous):
            score -= 0.08
            penalties.append("campaign_repeated_decision_type")

        new_mechanics = self._new_mechanics(candidate, previous_signatures)
        if target_band in {"tutorial", "easy"} and len(new_mechanics) > 1:
            score -= min(0.30, 0.12 * (len(new_mechanics) - 1))
            penalties.append("campaign_multiple_mechanics_introduced")

        dependency_delta = self._dependency_complexity(candidate) - self._dependency_complexity(previous)
        timing_delta = self._timing_pressure(candidate) - self._timing_pressure(previous)
        if timing_delta > 0.18 and dependency_delta <= 0:
            score -= 0.16
            penalties.append("campaign_timing_before_dependency_progression")

        previous_punitive = self._punitive_score(previous)
        candidate_punitive = self._punitive_score(candidate)
        if previous_punitive >= 0.65 and candidate_punitive >= 0.65:
            score -= 0.20
            penalties.append("campaign_missing_recovery_level")
        elif previous_punitive >= 0.65 and candidate_punitive <= 0.35:
            score = min(1.0, score + 0.08)
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
                "decisionType": self._decision_type(candidate),
                "newMechanics": new_mechanics,
                "dependencyComplexityDelta": round(dependency_delta, 4),
                "timingPressureDelta": round(timing_delta, 4),
                "previousPunitiveScore": round(previous_punitive, 4),
                "candidatePunitiveScore": round(candidate_punitive, 4),
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

    def _new_mechanics(
        self, candidate: CandidateSignature, previous_signatures: list[CandidateSignature]
    ) -> tuple[str, ...]:
        previously_seen = {
            tag for signature in previous_signatures for tag in signature.mechanic_tags
        }
        return tuple(sorted(set(candidate.mechanic_tags) - previously_seen))

    def _decision_type(self, signature: CandidateSignature) -> tuple[object, ...]:
        return (
            signature.required_tap_count,
            signature.switch_count,
            signature.switch_degree_sequence,
            signature.decision_dependency_pattern[:2],
            signature.revisit_state_reversal_pattern,
        )

    def _dependency_complexity(self, signature: CandidateSignature) -> float:
        dependencies, depth, density = signature.decision_dependency_pattern
        revisit_count, reversal_count, repeated_taps = signature.revisit_state_reversal_pattern
        return dependencies + depth + density + revisit_count + reversal_count + repeated_taps

    def _timing_pressure(self, signature: CandidateSignature) -> float:
        timings = signature.solution_decision_timing_pattern
        if len(timings) < 2:
            return 0.0
        gaps = [later - earlier for earlier, later in zip(timings, timings[1:]) if later > earlier]
        return 0.0 if not gaps else 1.0 / max(0.01, min(gaps))

    def _punitive_score(self, signature: CandidateSignature) -> float:
        outcomes = dict(signature.failure_outcome_distribution)
        total = sum(outcomes.values())
        if total <= 0:
            return 0.0
        punitive = sum(
            count for outcome, count in outcomes.items()
            if outcome not in {"success", "recoverable", "safe_dead_end"}
        )
        return punitive / total
