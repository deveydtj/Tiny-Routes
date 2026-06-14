from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .generated_level import GeneratedLevel


@dataclass
class SwiftTestSummary:
    command: list[str] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    exit_code: int | None = None
    passed: bool | None = None
    summary: str = "Swift tests were not run."
    stdout_tail: str = ""
    stderr_tail: str = ""
    failure_details: list[str] = field(default_factory=list)
    failure_reasons: list[str] = field(default_factory=list)


@dataclass
class GenerationResult:
    accepted: list[GeneratedLevel] = field(default_factory=list)
    candidate_selection_summaries: list[dict[str, Any]] = field(default_factory=list)
    candidate_generation_count: int = 0
    candidate_validation_count: int = 0
    candidate_generation_counts_by_difficulty: dict[str, int] = field(default_factory=dict)
    candidate_validation_counts_by_difficulty: dict[str, int] = field(default_factory=dict)
    rejected_candidate_count: int = 0
    validation_rejection_count: int = 0
    filter_rejection_count: int = 0
    generation_error_count: int = 0
    rejection_reason_counts: dict[str, int] = field(default_factory=dict)
    rejection_reason_counts_by_difficulty: dict[str, dict[str, int]] = field(default_factory=dict)
    similarity_rejection_counts_by_difficulty: dict[str, int] = field(default_factory=dict)
    diversity_adjustment_decisions: list[dict[str, Any]] = field(default_factory=list)
    written_level_paths: list[Path] = field(default_factory=list)
    written_solution_paths: list[Path] = field(default_factory=list)
    swift_test_summary: SwiftTestSummary = field(default_factory=SwiftTestSummary)
    passed: bool = True
    messages: list[str] = field(default_factory=list)
    report_path: Path | None = None
    json_report_path: Path | None = None

    def add_rejections(self, reason_counts: dict[str, int]) -> None:
        for reason, count in reason_counts.items():
            self.rejection_reason_counts[reason] = self.rejection_reason_counts.get(reason, 0) + count
            self.rejected_candidate_count += count
