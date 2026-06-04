from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..generation_config import (
    DEFAULT_CANDIDATE_POOL_SIZE,
    DEFAULT_GENERATION_MODE,
    DEFAULT_LAYOUTS_PER_RECIPE,
    DEFAULT_LAYOUT_ORIENTATION_PREFERENCE,
    DEFAULT_LAYOUT_SIZE_PROFILE,
    DEFAULT_MAX_ATTEMPTS_PER_LEVEL,
    DEFAULT_RECIPE_POOL_SIZE,
    DEFAULT_ROAD_SHAPES_PER_LAYOUT,
    DEFAULT_VERTICAL_ROUTE_PROBABILITY,
    GenerationConfig,
)
from ..paths import get_default_levels_directory, get_default_reports_directory, get_default_solutions_directory


@dataclass
class GuiGenerationState:
    start_level_number: str = "12"
    count: str = "1"
    difficulty: str = "tutorial"
    template_name: str = "mixed"
    generation_mode: str = DEFAULT_GENERATION_MODE
    recipe_pool_size: str = str(DEFAULT_RECIPE_POOL_SIZE)
    layouts_per_recipe: str = str(DEFAULT_LAYOUTS_PER_RECIPE)
    road_shapes_per_layout: str = str(DEFAULT_ROAD_SHAPES_PER_LAYOUT)
    layout_orientation_preference: str = DEFAULT_LAYOUT_ORIENTATION_PREFERENCE
    layout_size_profile: str = DEFAULT_LAYOUT_SIZE_PROFILE
    vertical_route_probability: str = str(DEFAULT_VERTICAL_ROUTE_PROBABILITY)
    prefer_vertical_for_long_routes: bool = True
    seed: str = ""
    dry_run: bool = True
    overwrite: bool = False
    run_swift_tests: bool = False
    compare_against_existing: bool = True
    levels_output_dir: str = ""
    solutions_output_dir: str = ""
    report_path: str = ""
    json_report_path: str = ""
    map_seed_path: str = ""
    debug_failures_dir: str = ""
    max_attempts_per_level: str = str(DEFAULT_MAX_ATTEMPTS_PER_LEVEL)
    candidate_pool_size: str = str(DEFAULT_CANDIDATE_POOL_SIZE)
    swift_timeout_seconds: str = "180"


def parse_positive_int(value: str, field_name: str) -> int:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} is required.")
    try:
        parsed = int(stripped)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a whole number.") from exc
    if parsed <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return parsed


def parse_probability(value: str, field_name: str) -> float:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} is required.")
    try:
        parsed = float(stripped)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a number.") from exc
    if parsed < 0.0 or parsed > 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")
    return parsed


def to_generation_config(state: GuiGenerationState) -> GenerationConfig:
    start_level_number = parse_positive_int(state.start_level_number, "Start level number")
    count = parse_positive_int(state.count, "Count")
    max_attempts_per_level = parse_positive_int(state.max_attempts_per_level, "Max attempts per level")
    candidate_pool_size = parse_positive_int(state.candidate_pool_size, "Candidate pool size")
    recipe_pool_size = parse_positive_int(state.recipe_pool_size, "Recipe pool size")
    layouts_per_recipe = parse_positive_int(state.layouts_per_recipe, "Layouts per recipe")
    road_shapes_per_layout = parse_positive_int(state.road_shapes_per_layout, "Road shapes per layout")
    vertical_route_probability = parse_probability(state.vertical_route_probability, "Vertical route probability")
    swift_timeout_seconds = parse_positive_int(state.swift_timeout_seconds, "Swift timeout seconds")
    seed = _parse_optional_int(state.seed, "Seed")

    try:
        levels_output_dir = _path_or_default(state.levels_output_dir, get_default_levels_directory)
        solutions_output_dir = _path_or_default(state.solutions_output_dir, get_default_solutions_directory)
        report_path = _path_or_default(
            state.report_path,
            lambda: get_default_reports_directory() / "last_generation_report.md",
        )
        json_report_path = _path_or_default(
            state.json_report_path,
            lambda: get_default_reports_directory() / "last_generation_report.json",
        )
    except FileNotFoundError as exc:
        raise ValueError("Default output paths could not be resolved. Choose output and report paths manually.") from exc

    command_arguments = _build_command_arguments(
        state,
        start_level_number=start_level_number,
        count=count,
        seed=seed,
        max_attempts_per_level=max_attempts_per_level,
        candidate_pool_size=candidate_pool_size,
        recipe_pool_size=recipe_pool_size,
        layouts_per_recipe=layouts_per_recipe,
        road_shapes_per_layout=road_shapes_per_layout,
        vertical_route_probability=vertical_route_probability,
        swift_timeout_seconds=swift_timeout_seconds,
        levels_output_dir=levels_output_dir,
        solutions_output_dir=solutions_output_dir,
        report_path=report_path,
        json_report_path=json_report_path,
    )

    return GenerationConfig(
        start_level_number=start_level_number,
        count=count,
        difficulty=state.difficulty,
        template_name=state.template_name,
        generation_mode=state.generation_mode,
        recipe_pool_size=recipe_pool_size,
        layouts_per_recipe=layouts_per_recipe,
        road_shapes_per_layout=road_shapes_per_layout,
        layout_orientation_preference=state.layout_orientation_preference,
        layout_size_profile=state.layout_size_profile,
        vertical_route_probability=vertical_route_probability,
        prefer_vertical_for_long_routes=state.prefer_vertical_for_long_routes,
        seed=seed,
        dry_run=state.dry_run,
        overwrite=state.overwrite,
        run_swift_tests=state.run_swift_tests,
        compare_against_existing=state.compare_against_existing,
        levels_output_dir=levels_output_dir,
        solutions_output_dir=solutions_output_dir,
        report_path=report_path,
        json_report_path=json_report_path,
        map_seed_path=Path(state.map_seed_path).expanduser() if state.map_seed_path.strip() else None,
        debug_failures_dir=Path(state.debug_failures_dir).expanduser() if state.debug_failures_dir.strip() else None,
        max_attempts_per_level=max_attempts_per_level,
        candidate_pool_size=candidate_pool_size,
        swift_timeout_seconds=swift_timeout_seconds,
        command_arguments=command_arguments,
    )


def build_command_preview(state: GuiGenerationState) -> str:
    args = ["python", "Tools/LevelGenerator/generate_levels.py"]
    _append_pair(args, "--start", state.start_level_number)
    _append_pair(args, "--count", state.count)
    _append_pair(args, "--difficulty", state.difficulty)
    _append_pair(args, "--template", state.template_name)
    _append_pair(args, "--generation-mode", state.generation_mode)
    _append_pair(args, "--recipe-pool-size", state.recipe_pool_size)
    _append_pair(args, "--layouts-per-recipe", state.layouts_per_recipe)
    _append_pair(args, "--road-shapes-per-layout", state.road_shapes_per_layout)
    _append_pair(args, "--layout-orientation", state.layout_orientation_preference)
    _append_pair(args, "--layout-size-profile", state.layout_size_profile)
    _append_pair(args, "--vertical-route-probability", state.vertical_route_probability)
    if state.prefer_vertical_for_long_routes:
        args.append("--prefer-vertical-for-long-routes")
    else:
        args.append("--no-prefer-vertical-for-long-routes")
    _append_pair(args, "--seed", state.seed)
    if state.dry_run:
        args.append("--dry-run")
    if state.overwrite:
        args.append("--overwrite")
    if state.run_swift_tests:
        args.append("--swift-tests")
    else:
        args.append("--no-swift-tests")
    if state.compare_against_existing:
        args.append("--compare-existing")
    else:
        args.append("--no-compare-existing")
    _append_pair(args, "--output-levels", state.levels_output_dir)
    _append_pair(args, "--output-solutions", state.solutions_output_dir)
    _append_pair(args, "--report", state.report_path)
    _append_pair(args, "--json-report", state.json_report_path)
    _append_pair(args, "--map-seed-path", state.map_seed_path)
    _append_pair(args, "--debug-failures", state.debug_failures_dir)
    _append_pair(args, "--max-attempts-per-level", state.max_attempts_per_level)
    _append_pair(args, "--candidate-pool-size", state.candidate_pool_size)
    _append_pair(args, "--swift-timeout-seconds", state.swift_timeout_seconds)
    return " ".join(_quote_command_part(part) for part in args)


def _path_or_default(value: str, default_factory) -> Path:
    if value.strip():
        return Path(value).expanduser()
    return default_factory()


def _parse_optional_int(value: str, field_name: str) -> int | None:
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return int(stripped)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a whole number.") from exc


def _build_command_arguments(
    state: GuiGenerationState,
    *,
    start_level_number: int,
    count: int,
    seed: int | None,
    max_attempts_per_level: int,
    candidate_pool_size: int,
    recipe_pool_size: int,
    layouts_per_recipe: int,
    road_shapes_per_layout: int,
    vertical_route_probability: float,
    swift_timeout_seconds: int,
    levels_output_dir: Path,
    solutions_output_dir: Path,
    report_path: Path,
    json_report_path: Path,
) -> list[str]:
    args = [
        "--start",
        str(start_level_number),
        "--count",
        str(count),
        "--difficulty",
        state.difficulty,
        "--template",
        state.template_name,
        "--generation-mode",
        state.generation_mode,
        "--recipe-pool-size",
        str(recipe_pool_size),
        "--layouts-per-recipe",
        str(layouts_per_recipe),
        "--road-shapes-per-layout",
        str(road_shapes_per_layout),
        "--layout-orientation",
        state.layout_orientation_preference,
        "--layout-size-profile",
        state.layout_size_profile,
        "--vertical-route-probability",
        str(vertical_route_probability),
    ]
    args.append("--prefer-vertical-for-long-routes" if state.prefer_vertical_for_long_routes else "--no-prefer-vertical-for-long-routes")
    if seed is not None:
        args.extend(["--seed", str(seed)])
    if state.dry_run:
        args.append("--dry-run")
    if state.overwrite:
        args.append("--overwrite")
    args.append("--swift-tests" if state.run_swift_tests else "--no-swift-tests")
    args.append("--compare-existing" if state.compare_against_existing else "--no-compare-existing")
    args.extend(
        [
            "--output-levels",
            str(levels_output_dir),
            "--output-solutions",
            str(solutions_output_dir),
            "--report",
            str(report_path),
            "--json-report",
            str(json_report_path),
        ]
    )
    if state.debug_failures_dir.strip():
        args.extend(["--debug-failures", str(Path(state.debug_failures_dir).expanduser())])
    if state.map_seed_path.strip():
        args.extend(["--map-seed-path", str(Path(state.map_seed_path).expanduser())])
    args.extend(["--max-attempts-per-level", str(max_attempts_per_level)])
    args.extend(["--candidate-pool-size", str(candidate_pool_size)])
    args.extend(["--swift-timeout-seconds", str(swift_timeout_seconds)])
    return args


def _append_pair(args: list[str], flag: str, value: str) -> None:
    if value.strip():
        args.extend([flag, value.strip()])


def _quote_command_part(value: str) -> str:
    if not value or any(character.isspace() for character in value):
        return "'" + value.replace("'", "'\"'\"'") + "'"
    return value
