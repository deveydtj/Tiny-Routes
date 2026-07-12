from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .candidate_uniqueness_service import CandidateUniquenessService


@dataclass(frozen=True)
class PortfolioSelection:
    candidate: object
    objective_score: float
    rationale: str
    components: dict[str, float]


@dataclass(frozen=True)
class CandidatePortfolioSelectionResult:
    selections: tuple[PortfolioSelection, ...]

    @property
    def candidates(self) -> list[object]:
        return [selection.candidate for selection in self.selections]


class CandidatePortfolioSelectionService:
    """Select one candidate per planned level while optimizing the batch as a whole."""

    def __init__(self, uniqueness_service: CandidateUniquenessService | None = None) -> None:
        self.uniqueness_service = uniqueness_service or CandidateUniquenessService()

    def select(
        self,
        candidate_pools: Mapping[str, Sequence[object]],
        requested_levels: Sequence[tuple[str, str]],
        *,
        existing_signatures: Iterable[object] = (),
    ) -> CandidatePortfolioSelectionResult:
        selected: list[PortfolioSelection] = []
        recent_signatures: list[object] = []
        production_signatures = tuple(existing_signatures)

        for level_id, difficulty in requested_levels:
            eligible = [
                candidate
                for candidate in candidate_pools.get(level_id, ())
                if candidate.level_id == level_id and candidate.difficulty == difficulty
            ]
            if not eligible:
                raise ValueError(f"Candidate pool has no {difficulty} candidate for {level_id}.")

            ranked = sorted(
                (
                    self._rank(candidate, recent_signatures, production_signatures)
                    for candidate in eligible
                ),
                key=self._selection_key,
                reverse=True,
            )
            winner = ranked[0]
            selected.append(winner)
            recent_signatures.append(winner.candidate.candidate_signature)

        if len(selected) != len(requested_levels):
            raise ValueError("Portfolio selection did not satisfy the requested level count.")
        return CandidatePortfolioSelectionResult(tuple(selected))

    def _rank(self, candidate, selected_signatures, existing_signatures) -> PortfolioSelection:
        signature = candidate.candidate_signature
        quality = candidate.quality_score
        individual_quality = min(max(float(getattr(quality, "total_score", 0.0)) / 100.0, 0.0), 1.0)
        difficulty_fit = min(max(float(getattr(quality, "difficulty_fit", 0.0)), 0.0), 1.0)
        decision_diversity = self._decision_diversity(signature, selected_signatures)
        visual_diversity = self._visual_diversity(signature, selected_signatures)
        production_distance = 1.0 - self._maximum_similarity(signature, existing_signatures)
        mechanic_progression = self._mechanic_progression(signature, selected_signatures)
        adjacent_variety = self._adjacent_variety(signature, selected_signatures)
        components = {
            "individualQuality": individual_quality,
            "difficultyFit": difficulty_fit,
            "decisionDiversity": decision_diversity,
            "visualDiversity": visual_diversity,
            "productionDistance": production_distance,
            "mechanicProgression": mechanic_progression,
            "adjacentVariety": adjacent_variety,
        }
        weights = {
            "individualQuality": 0.30,
            "difficultyFit": 0.15,
            "decisionDiversity": 0.22,
            "visualDiversity": 0.10,
            "productionDistance": 0.08,
            "mechanicProgression": 0.08,
            "adjacentVariety": 0.07,
        }
        objective = sum(components[name] * weight for name, weight in weights.items())
        strongest = sorted(components.items(), key=lambda item: (-item[1], item[0]))[:3]
        rationale = (
            f"Selected with portfolio objective {objective:.4f}; strongest factors: "
            + ", ".join(f"{name}={value:.3f}" for name, value in strongest)
            + ". Alternatives were ranked with deterministic signature and seed tie-breakers."
        )
        return PortfolioSelection(candidate, round(objective, 6), rationale, components)

    def _selection_key(self, selection: PortfolioSelection) -> tuple:
        candidate = selection.candidate
        signature = candidate.candidate_signature
        return (
            selection.objective_score,
            selection.components["decisionDiversity"],
            selection.components["visualDiversity"],
            float(getattr(candidate.quality_score, "total_score", 0.0)),
            signature.topology_hash,
            signature.layout_hash,
            signature.solution_hash,
            -int(candidate.seed),
        )

    def _maximum_similarity(self, signature, comparison_signatures) -> float:
        return max(
            (self.uniqueness_service.similarity_score(signature, other) for other in comparison_signatures),
            default=0.0,
        )

    def _visual_diversity(self, signature, selected_signatures) -> float:
        if not selected_signatures:
            return 1.0
        similarities = []
        for other in selected_signatures:
            same_silhouette = (
                signature.layout_silhouette == other.layout_silhouette
                or signature.layout_silhouette == other.mirrored_layout_silhouette
            )
            same_directions = signature.road_direction_histogram == other.road_direction_histogram
            similarities.append((0.65 if same_silhouette else 0.0) + (0.35 if same_directions else 0.0))
        return 1.0 - max(similarities, default=0.0)

    def _decision_diversity(self, signature, selected_signatures) -> float:
        if not selected_signatures:
            return 1.0
        similarities = []
        for other in selected_signatures:
            exact_dimensions = (
                signature.decision_dependency_pattern == other.decision_dependency_pattern,
                signature.switch_degree_sequence == other.switch_degree_sequence,
                signature.revisit_state_reversal_pattern == other.revisit_state_reversal_pattern,
                signature.failure_outcome_distribution == other.failure_outcome_distribution,
                signature.package_phase_pattern == other.package_phase_pattern,
                signature.solution_decision_timing_pattern == other.solution_decision_timing_pattern,
            )
            similarities.append(sum(exact_dimensions) / len(exact_dimensions))
        return 1.0 - max(similarities, default=0.0)

    def _mechanic_progression(self, signature, selected_signatures) -> float:
        if not selected_signatures:
            return 1.0
        used = {tag for other in selected_signatures for tag in other.mechanic_tags}
        tags = set(signature.mechanic_tags)
        return len(tags - used) / max(len(tags), 1) if tags else 0.5

    def _adjacent_variety(self, signature, selected_signatures) -> float:
        if not selected_signatures:
            return 1.0
        previous = selected_signatures[-1]
        differences = (
            signature.topology_class != previous.topology_class,
            signature.primary_mechanic_tag != previous.primary_mechanic_tag,
            signature.layout_orientation != previous.layout_orientation,
            signature.decision_dependency_pattern != previous.decision_dependency_pattern,
        )
        return sum(differences) / len(differences)
