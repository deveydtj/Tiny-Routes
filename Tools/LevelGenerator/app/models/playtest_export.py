"""Typed inputs and evidence for blinded generator playtest exports."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _label(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


@dataclass(frozen=True)
class PlaytestSample:
    """One researcher-labelled level before identities are blinded."""

    source_id: str
    level_payload: dict[str, Any]
    difficulty: str
    blueprint_archetype: str
    objective_count: int
    recovery_pattern: str
    failure_pattern: str
    layout_profile: str
    known_weak: bool = False
    automated_metrics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in (
            "source_id",
            "difficulty",
            "blueprint_archetype",
            "recovery_pattern",
            "failure_pattern",
            "layout_profile",
        ):
            object.__setattr__(
                self, field_name, _label(getattr(self, field_name), field_name)
            )
        object.__setattr__(self, "difficulty", self.difficulty.lower())
        if self.difficulty not in {"easy", "medium", "hard", "expert"}:
            raise ValueError("difficulty must be easy, medium, hard, or expert")
        if not isinstance(self.level_payload, dict) or not self.level_payload:
            raise ValueError("level_payload must be a non-empty object")
        if (
            not isinstance(self.objective_count, int)
            or isinstance(self.objective_count, bool)
            or self.objective_count < 2
        ):
            raise ValueError("objective_count must be an integer of at least two")
        if not isinstance(self.known_weak, bool):
            raise ValueError("known_weak must be a Boolean")
        if not isinstance(self.automated_metrics, dict):
            raise ValueError("automated_metrics must be an object")


@dataclass(frozen=True)
class BlindedPlaytestExportResult:
    output_directory: Path
    tester_directory: Path
    researcher_directory: Path
    sample_count: int
    fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "outputDirectory": str(self.output_directory),
            "testerDirectory": str(self.tester_directory),
            "researcherDirectory": str(self.researcher_directory),
            "sampleCount": self.sample_count,
            "fingerprint": self.fingerprint,
        }
