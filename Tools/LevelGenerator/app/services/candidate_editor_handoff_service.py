from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..repositories.generated_level_repository import GeneratedLevelRepository


@dataclass(frozen=True)
class CandidateEditorHandoff:
    level_path: Path
    solution_path: Path
    quality_path: Path


class CandidateEditorHandoffService:
    """Materialize an in-memory candidate as an editor-safe draft bundle."""

    def __init__(self, repository: GeneratedLevelRepository | None = None) -> None:
        self._repository = repository or GeneratedLevelRepository()

    def write(self, candidate: Any, draft_root: Path) -> CandidateEditorHandoff:
        bundle_dir = Path(draft_root) / f"{candidate.level_id}-seed-{candidate.seed}"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        level_path = bundle_dir / f"{candidate.level_id}.json"
        solution_path = bundle_dir / f"{candidate.level_id}.solution.json"
        quality_path = bundle_dir / f"{candidate.level_id}.quality.json"

        self._repository.write_level(candidate.level_document, level_path, overwrite=True)
        self._repository.write_solution(candidate.solution, solution_path, overwrite=True)
        quality_path.write_text(
            json.dumps(self._quality_payload(candidate), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return CandidateEditorHandoff(level_path, solution_path, quality_path)

    @staticmethod
    def _quality_payload(candidate: Any) -> dict[str, Any]:
        quality = getattr(candidate, "quality_score", None)
        decision_profile = getattr(candidate, "decision_profile", None)
        return {
            "schemaVersion": 1,
            "levelID": candidate.level_id,
            "source": "Tiny Routes Level Generator",
            "difficulty": candidate.difficulty,
            "template": candidate.template_name,
            "seed": candidate.seed,
            "quality": None if quality is None else {
                "totalScore": quality.total_score,
                "categoryScores": dict(quality.category_scores),
                "estimatedDifficultyBand": quality.estimated_difficulty_band,
                "topPositiveFactors": list(quality.top_positive_factors),
                "topNegativeFactors": list(quality.top_negative_factors),
                "penalties": list(quality.penalties),
            },
            "decisionQuality": None if decision_profile is None else {
                "requiredDecisionCount": decision_profile.required_decision_count,
                "uniqueSwitchCount": decision_profile.unique_switch_count,
                "repeatedSwitchVisitCount": decision_profile.repeated_switch_decision_count,
                "independentDecisionRatio": decision_profile.independent_decision_ratio,
                "equivalentSuccessfulSolutionCount": (
                    decision_profile.equivalent_minimum_solution_count
                ),
            },
            "notes": list(getattr(candidate, "generation_notes", ()) or ()),
            "warnings": list(getattr(candidate, "warning_messages", ()) or ()),
        }
