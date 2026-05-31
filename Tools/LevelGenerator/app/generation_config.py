from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .paths import (
    get_default_levels_directory,
    get_default_reports_directory,
    get_default_solutions_directory,
)

GENERATION_MODES = ("legacy_template", "recipe_first", "hybrid")


@dataclass(frozen=True)
class GenerationConfig:
    start_level_number: int
    count: int
    difficulty: str
    template_name: str = "mixed"
    generation_mode: str = "legacy_template"
    recipe_pool_size: int = 1
    layouts_per_recipe: int = 1
    road_shapes_per_layout: int = 1
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
    map_seed_path: Path | None = None
    debug_failures_dir: Path | None = None
    max_attempts_per_level: int = 100
    candidate_pool_size: int = 1
    swift_timeout_seconds: int = 180
    sync_xcode_project: bool = True
    compare_against_existing: bool = True
    command_arguments: list[str] | None = None

    def __post_init__(self) -> None:
        if self.start_level_number <= 0:
            raise ValueError("start_level_number must be greater than zero")
        if self.count <= 0:
            raise ValueError("count must be greater than zero")
        if self.max_attempts_per_level <= 0:
            raise ValueError("max_attempts_per_level must be greater than zero")
        if self.candidate_pool_size <= 0:
            raise ValueError("candidate_pool_size must be greater than zero")

        object.__setattr__(self, "difficulty", self.difficulty.strip().lower())
        object.__setattr__(self, "template_name", self.template_name.strip().lower())
        object.__setattr__(self, "generation_mode", self.generation_mode.strip().lower().replace("-", "_"))
        object.__setattr__(self, "levels_output_dir", Path(self.levels_output_dir))
        object.__setattr__(self, "solutions_output_dir", Path(self.solutions_output_dir))
        if self.report_path is not None:
            object.__setattr__(self, "report_path", Path(self.report_path))
        if self.json_report_path is not None:
            object.__setattr__(self, "json_report_path", Path(self.json_report_path))
        if self.map_seed_path is not None:
            object.__setattr__(self, "map_seed_path", Path(self.map_seed_path))
        if self.debug_failures_dir is not None:
            object.__setattr__(self, "debug_failures_dir", Path(self.debug_failures_dir))
        if self.generation_mode not in GENERATION_MODES:
            valid = ", ".join(GENERATION_MODES)
            raise ValueError(f"generation_mode must be one of: {valid}")
        if self.recipe_pool_size <= 0:
            raise ValueError("recipe_pool_size must be greater than zero")
        if self.layouts_per_recipe <= 0:
            raise ValueError("layouts_per_recipe must be greater than zero")
        if self.road_shapes_per_layout <= 0:
            raise ValueError("road_shapes_per_layout must be greater than zero")

    @property
    def base_seed(self) -> int:
        return self.seed if self.seed is not None else 0

    @property
    def uses_legacy_templates(self) -> bool:
        return self.generation_mode in {"legacy_template", "hybrid"}
