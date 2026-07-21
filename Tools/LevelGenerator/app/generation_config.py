from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .paths import (
    get_default_levels_directory,
    get_default_reports_directory,
    get_default_solutions_directory,
)

LAYOUT_ORIENTATION_PREFERENCES = ("portrait_vertical", "horizontal", "vertical", "mixed", "auto")
LAYOUT_SIZE_PROFILES = ("difficulty_curve", "standard_portrait", "large_portrait")
GENERATOR_ARCHITECTURES = ("v2_legacy", "production_v3")
DEFAULT_GENERATOR_ARCHITECTURE = "v2_legacy"
DEFAULT_RECIPE_POOL_SIZE = 4
DEFAULT_LAYOUTS_PER_RECIPE = 2
DEFAULT_ROAD_SHAPES_PER_LAYOUT = 2
DEFAULT_CANDIDATE_POOL_SIZE = 4
DEFAULT_MAX_ATTEMPTS_PER_LEVEL = 120
DEFAULT_LAYOUT_ORIENTATION_PREFERENCE = "portrait_vertical"
DEFAULT_LAYOUT_SIZE_PROFILE = "difficulty_curve"
DEFAULT_VERTICAL_ROUTE_PROBABILITY = 0.35
DEFAULT_PLAYTEST_PORTFOLIO_UNIQUENESS_WINDOW = 6


@dataclass(frozen=True)
class GenerationConfig:
    start_level_number: int
    count: int
    difficulty: str
    generator_architecture: str = DEFAULT_GENERATOR_ARCHITECTURE
    template_name: str = "mixed"
    recipe_pool_size: int = DEFAULT_RECIPE_POOL_SIZE
    layouts_per_recipe: int = DEFAULT_LAYOUTS_PER_RECIPE
    road_shapes_per_layout: int = DEFAULT_ROAD_SHAPES_PER_LAYOUT
    layout_orientation_preference: str = DEFAULT_LAYOUT_ORIENTATION_PREFERENCE
    layout_size_profile: str = DEFAULT_LAYOUT_SIZE_PROFILE
    vertical_route_probability: float = DEFAULT_VERTICAL_ROUTE_PROBABILITY
    prefer_vertical_for_long_routes: bool = True
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
    state_snapshot_previews: bool = False
    max_attempts_per_level: int = DEFAULT_MAX_ATTEMPTS_PER_LEVEL
    candidate_pool_size: int = DEFAULT_CANDIDATE_POOL_SIZE
    swift_timeout_seconds: int = 180
    sync_xcode_project: bool = True
    compare_against_existing: bool = True
    playtest_portfolio: bool = False
    playtest_uniqueness_window: int = DEFAULT_PLAYTEST_PORTFOLIO_UNIQUENESS_WINDOW
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
        if self.playtest_uniqueness_window <= 0:
            raise ValueError("playtest_uniqueness_window must be greater than zero")

        object.__setattr__(self, "difficulty", self.difficulty.strip().lower())
        object.__setattr__(
            self,
            "generator_architecture",
            self.generator_architecture.strip().lower().replace("-", "_"),
        )
        object.__setattr__(self, "template_name", self.template_name.strip().lower())
        object.__setattr__(
            self,
            "layout_orientation_preference",
            self.layout_orientation_preference.strip().lower().replace("-", "_"),
        )
        object.__setattr__(
            self,
            "layout_size_profile",
            self.layout_size_profile.strip().lower().replace("-", "_"),
        )
        object.__setattr__(self, "vertical_route_probability", float(self.vertical_route_probability))
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
        if self.layout_orientation_preference not in LAYOUT_ORIENTATION_PREFERENCES:
            valid = ", ".join(LAYOUT_ORIENTATION_PREFERENCES)
            raise ValueError(f"layout_orientation_preference must be one of: {valid}")
        if self.generator_architecture not in GENERATOR_ARCHITECTURES:
            valid = ", ".join(GENERATOR_ARCHITECTURES)
            raise ValueError(f"generator_architecture must be one of: {valid}")
        if self.layout_size_profile not in LAYOUT_SIZE_PROFILES:
            valid = ", ".join(LAYOUT_SIZE_PROFILES)
            raise ValueError(f"layout_size_profile must be one of: {valid}")
        if not 0.0 <= self.vertical_route_probability <= 1.0:
            raise ValueError("vertical_route_probability must be between 0.0 and 1.0")
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
    def generator_architecture_version(self) -> int:
        return 2 if self.generator_architecture == "v2_legacy" else 3
