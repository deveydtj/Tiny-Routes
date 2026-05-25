from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .paths import (
    get_default_levels_directory,
    get_default_reports_directory,
    get_default_solutions_directory,
)


@dataclass(frozen=True)
class GenerationConfig:
    start_level_number: int
    count: int
    difficulty: str
    template_name: str = "mixed"
    seed: int | None = None
    dry_run: bool = False
    overwrite: bool = False
    run_swift_tests: bool = False
    levels_output_dir: Path = field(default_factory=get_default_levels_directory)
    solutions_output_dir: Path = field(default_factory=get_default_solutions_directory)
    report_path: Path | None = field(
        default_factory=lambda: get_default_reports_directory() / "last_generation_report.md"
    )
    json_report_path: Path | None = field(
        default_factory=lambda: get_default_reports_directory() / "last_generation_report.json"
    )
    debug_failures_dir: Path | None = None
    max_attempts_per_level: int = 100
    swift_timeout_seconds: int = 180
    sync_xcode_project: bool = True
    command_arguments: list[str] | None = None

    def __post_init__(self) -> None:
        if self.start_level_number <= 0:
            raise ValueError("start_level_number must be greater than zero")
        if self.count <= 0:
            raise ValueError("count must be greater than zero")
        if self.max_attempts_per_level <= 0:
            raise ValueError("max_attempts_per_level must be greater than zero")

        object.__setattr__(self, "difficulty", self.difficulty.strip().lower())
        object.__setattr__(self, "template_name", self.template_name.strip().lower())
        object.__setattr__(self, "levels_output_dir", Path(self.levels_output_dir))
        object.__setattr__(self, "solutions_output_dir", Path(self.solutions_output_dir))
        if self.report_path is not None:
            object.__setattr__(self, "report_path", Path(self.report_path))
        if self.json_report_path is not None:
            object.__setattr__(self, "json_report_path", Path(self.json_report_path))
        if self.debug_failures_dir is not None:
            object.__setattr__(self, "debug_failures_dir", Path(self.debug_failures_dir))

    @property
    def base_seed(self) -> int:
        return self.seed if self.seed is not None else 0
