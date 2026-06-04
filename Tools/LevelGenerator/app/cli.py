from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .generation_config import (
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
    LAYOUT_ORIENTATION_PREFERENCES,
    LAYOUT_SIZE_PROFILES,
)
from .paths import (
    get_default_levels_directory,
    get_default_reports_directory,
    get_default_solutions_directory,
)
from .services.difficulty_service import DifficultyService
from .services.level_generation_service import LevelGenerationService
from .services.level_validation_runner_service import ExistingLevelValidationConfig, LevelValidationRunnerService
from .templates.template_registry import TemplateRegistry


def main_generate(argv: list[str] | None = None) -> int:
    parser = build_generate_parser()
    try:
        args = parser.parse_args(argv)
        config = _config_from_args(args, argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    except ValueError as exc:
        parser.print_usage(sys.stderr)
        print(f"{parser.prog}: error: {exc}", file=sys.stderr)
        return 2

    _print_generation_summary(config)
    result = LevelGenerationService().generate(config)
    _print_generation_result(config, result)
    return 0 if result.passed else 1


def main_validate(argv: list[str] | None = None) -> int:
    parser = build_validate_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    result = LevelValidationRunnerService().validate_existing_levels(
        ExistingLevelValidationConfig(
            level_ids=args.levels,
            difficulty=args.difficulty,
            run_swift_tests=args.swift_tests,
            levels_output_dir=Path(args.output_levels),
            solutions_output_dir=Path(args.output_solutions),
            swift_timeout_seconds=args.swift_timeout_seconds,
        )
    )

    for level_id in result.validated_level_ids:
        print(f"Validated {level_id}")
    if result.swift_summary.passed is not None:
        print(result.swift_summary.summary)
    if result.failures:
        for failure in result.failures:
            print(failure, file=sys.stderr)
        return 1
    return 0


def build_generate_parser() -> argparse.ArgumentParser:
    difficulty_names = [*DifficultyService().valid_names, "auto"]
    template_names = TemplateRegistry().valid_names
    parser = argparse.ArgumentParser(description="Generate Tiny Routes level and solution JSON files.")
    parser.add_argument("--start", type=int, required=True, help="First level number to generate, e.g. 12 for level_012.")
    parser.add_argument("--count", type=int, required=True, help="Number of accepted levels to generate.")
    parser.add_argument("--difficulty", required=True, choices=difficulty_names, help="Difficulty preset to use.")
    parser.add_argument("--template", default="mixed", choices=template_names, help="Template to use. Default: mixed.")
    parser.add_argument(
        "--generation-mode",
        default=DEFAULT_GENERATION_MODE,
        choices=("legacy-template", "legacy_template", "recipe-first", "recipe_first", "hybrid"),
        help="Generation architecture mode. Default: recipe-first. legacy-template and hybrid remain available.",
    )
    parser.add_argument(
        "--recipe-pool-size",
        type=int,
        default=DEFAULT_RECIPE_POOL_SIZE,
        help="Abstract recipes to solve before layout.",
    )
    parser.add_argument(
        "--layouts-per-recipe",
        type=int,
        default=DEFAULT_LAYOUTS_PER_RECIPE,
        help="Layout variants to try for each solved recipe.",
    )
    parser.add_argument(
        "--road-shapes-per-layout",
        type=int,
        default=DEFAULT_ROAD_SHAPES_PER_LAYOUT,
        help="Road-shape strategies to try for each layout.",
    )
    parser.add_argument(
        "--layout-orientation",
        choices=LAYOUT_ORIENTATION_PREFERENCES,
        default=DEFAULT_LAYOUT_ORIENTATION_PREFERENCE,
        help="Layout orientation/profile preference. Default: portrait_vertical.",
    )
    parser.add_argument(
        "--layout-size-profile",
        choices=LAYOUT_SIZE_PROFILES,
        default=DEFAULT_LAYOUT_SIZE_PROFILE,
        help="Playable layout size profile. Default: difficulty_curve.",
    )
    parser.add_argument(
        "--vertical-route-probability",
        type=float,
        default=DEFAULT_VERTICAL_ROUTE_PROBABILITY,
        help="Chance of vertical route candidates when orientation is mixed or auto. Default: 0.35.",
    )
    parser.add_argument(
        "--prefer-vertical-for-long-routes",
        action="store_true",
        dest="prefer_vertical_for_long_routes",
        help="Prefer vertical candidates for longer routes. Default: enabled.",
    )
    parser.add_argument(
        "--no-prefer-vertical-for-long-routes",
        action="store_false",
        dest="prefer_vertical_for_long_routes",
        help="Do not raise vertical preference for longer routes.",
    )
    parser.set_defaults(prefer_vertical_for_long_routes=True)
    parser.add_argument("--seed", type=int, default=None, help="Deterministic base seed.")
    parser.add_argument("--dry-run", action="store_true", help="Generate and validate without writing level files.")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing existing output files.")
    parser.add_argument("--swift-tests", action="store_true", dest="swift_tests", help="Run Swift solvability tests after writing.")
    parser.add_argument("--no-swift-tests", action="store_false", dest="swift_tests", help="Skip Swift solvability tests.")
    parser.set_defaults(swift_tests=False)
    parser.add_argument("--output-levels", type=Path, default=get_default_levels_directory(), help="Output directory for level JSON.")
    parser.add_argument("--output-solutions", type=Path, default=get_default_solutions_directory(), help="Output directory for solution sidecars.")
    parser.add_argument(
        "--report",
        type=Path,
        default=get_default_reports_directory() / "last_generation_report.md",
        help="Markdown generation report path.",
    )
    parser.add_argument(
        "--json-report",
        type=Path,
        default=get_default_reports_directory() / "last_generation_report.json",
        help="Machine-readable generation report path.",
    )
    parser.add_argument("--map-seed-path", type=Path, default=None, help="Optional simplified map seed JSON path.")
    parser.add_argument("--debug-failures", type=Path, default=None, help="Directory for rejected candidate debug files.")
    parser.add_argument(
        "--max-attempts-per-level",
        type=int,
        default=DEFAULT_MAX_ATTEMPTS_PER_LEVEL,
        help="Candidate attempts before failing a level.",
    )
    parser.add_argument(
        "--candidate-pool-size",
        type=int,
        default=DEFAULT_CANDIDATE_POOL_SIZE,
        help="Valid candidates to score before choosing the best one.",
    )
    parser.add_argument("--swift-timeout-seconds", type=int, default=180, help="Timeout for optional Swift tests.")
    parser.add_argument(
        "--compare-existing",
        action="store_true",
        dest="compare_against_existing",
        help="Reject candidates that are too similar to existing levels in the output folders. Default: enabled.",
    )
    parser.add_argument(
        "--no-compare-existing",
        action="store_false",
        dest="compare_against_existing",
        help="Skip similarity checks against existing levels.",
    )
    parser.set_defaults(compare_against_existing=True)
    parser.add_argument(
        "--xcodegen",
        action="store_true",
        dest="sync_xcode_project",
        help="Regenerate TinyRoutes.xcodeproj after writing production resource files. Default: enabled.",
    )
    parser.add_argument(
        "--no-xcodegen",
        action="store_false",
        dest="sync_xcode_project",
        help="Do not regenerate TinyRoutes.xcodeproj after writing production resource files.",
    )
    parser.set_defaults(sync_xcode_project=True)
    return parser


def build_validate_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate existing generated Tiny Routes level files.")
    parser.add_argument("--levels", nargs="+", required=True, help="Level IDs to validate, such as level_012.")
    parser.add_argument("--difficulty", choices=DifficultyService().valid_names, default=None, help="Optionally enforce a difficulty preset.")
    parser.add_argument("--swift-tests", action="store_true", help="Run Swift solvability tests after Python validation.")
    parser.add_argument("--no-swift-tests", action="store_false", dest="swift_tests", help="Skip Swift solvability tests.")
    parser.set_defaults(swift_tests=False)
    parser.add_argument("--output-levels", type=Path, default=get_default_levels_directory(), help="Directory containing level JSON.")
    parser.add_argument("--output-solutions", type=Path, default=get_default_solutions_directory(), help="Directory containing solution sidecars.")
    parser.add_argument("--swift-timeout-seconds", type=int, default=180, help="Timeout for optional Swift tests.")
    return parser


def _config_from_args(args: argparse.Namespace, argv: list[str] | None) -> GenerationConfig:
    return GenerationConfig(
        start_level_number=args.start,
        count=args.count,
        difficulty=args.difficulty,
        template_name=args.template,
        generation_mode=args.generation_mode,
        recipe_pool_size=args.recipe_pool_size,
        layouts_per_recipe=args.layouts_per_recipe,
        road_shapes_per_layout=args.road_shapes_per_layout,
        layout_orientation_preference=args.layout_orientation,
        layout_size_profile=args.layout_size_profile,
        vertical_route_probability=args.vertical_route_probability,
        prefer_vertical_for_long_routes=args.prefer_vertical_for_long_routes,
        seed=args.seed,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        run_swift_tests=args.swift_tests,
        levels_output_dir=args.output_levels,
        solutions_output_dir=args.output_solutions,
        report_path=args.report,
        json_report_path=args.json_report,
        map_seed_path=args.map_seed_path,
        debug_failures_dir=args.debug_failures,
        max_attempts_per_level=args.max_attempts_per_level,
        candidate_pool_size=args.candidate_pool_size,
        swift_timeout_seconds=args.swift_timeout_seconds,
        sync_xcode_project=args.sync_xcode_project,
        compare_against_existing=args.compare_against_existing,
        command_arguments=list(argv) if argv is not None else sys.argv[1:],
    )


def _print_generation_summary(config: GenerationConfig) -> None:
    mode = "dry run" if config.dry_run else "write"
    print(
        f"Generating {config.count} {config.difficulty} level(s) starting at "
        f"{config.start_level_number:03d} with template={config.template_name} "
        f"generation_mode={config.generation_mode} layout_size={config.layout_size_profile} "
        f"seed={config.seed} mode={mode}."
    )


def _print_generation_result(config: GenerationConfig, result) -> None:
    for generated_level in result.accepted:
        print(
            f"Accepted {generated_level.level_id} template={generated_level.template_name} "
            f"seed={generated_level.seed} nodes={generated_level.node_count} taps={generated_level.required_tap_count}"
        )
    if result.rejected_candidate_count:
        print(f"Rejected candidates: {result.rejected_candidate_count}")
    if config.dry_run:
        for generated_level in result.accepted:
            print(f"Would write {config.levels_output_dir / (generated_level.level_id + '.json')}")
            print(f"Would write {config.solutions_output_dir / (generated_level.level_id + '.solution.json')}")
    else:
        for path in result.written_level_paths + result.written_solution_paths:
            print(f"Wrote {path}")
    print(result.swift_test_summary.summary)
    if result.report_path:
        print(f"Report: {result.report_path}")
    if result.json_report_path:
        print(f"JSON report: {result.json_report_path}")
    for message in result.messages:
        print(message, file=sys.stderr)
