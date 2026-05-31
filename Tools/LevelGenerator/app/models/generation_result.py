from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

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


@dataclass
class GenerationResult:
    accepted: list[GeneratedLevel] = field(default_factory=list)
    rejected_candidate_count: int = 0
    rejection_reason_counts: dict[str, int] = field(default_factory=dict)
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
