from __future__ import annotations

import json

from app.cli import _config_from_args, build_generate_parser, main_generate, main_validate


def test_cli_valid_dry_run(tmp_path, capsys) -> None:
    code = main_generate(
        [
            "--start",
            "12",
            "--count",
            "1",
            "--difficulty",
            "tutorial",
            "--template",
            "straight_delivery",
            "--seed",
            "1",
            "--dry-run",
            "--output-levels",
            str(tmp_path / "levels"),
            "--output-solutions",
            str(tmp_path / "solutions"),
            "--report",
            str(tmp_path / "report.md"),
            "--json-report",
            str(tmp_path / "report.json"),
            "--recipe-pool-size",
            "1",
            "--layouts-per-recipe",
            "1",
            "--road-shapes-per-layout",
            "1",
            "--candidate-pool-size",
            "1",
        ]
    )

    assert code == 0
    assert "Accepted level_012" in capsys.readouterr().out


def test_cli_invalid_start_returns_1_from_generation_validation(tmp_path) -> None:
    code = main_generate(
        [
            "--start",
            "0",
            "--count",
            "1",
            "--difficulty",
            "tutorial",
            "--output-levels",
            str(tmp_path / "levels"),
            "--output-solutions",
            str(tmp_path / "solutions"),
        ]
    )

    assert code == 2


def test_cli_invalid_difficulty_returns_2() -> None:
    code = main_generate(["--start", "12", "--count", "1", "--difficulty", "extreme"])

    assert code == 2


def test_cli_auto_difficulty_dry_run(tmp_path) -> None:
    code = main_generate(
        [
            "--start",
            "9",
            "--count",
            "2",
            "--difficulty",
            "auto",
            "--template",
            "mixed",
            "--dry-run",
            "--no-compare-existing",
            "--output-levels",
            str(tmp_path / "levels"),
            "--output-solutions",
            str(tmp_path / "solutions"),
            "--report",
            str(tmp_path / "report.md"),
            "--json-report",
            str(tmp_path / "report.json"),
            "--recipe-pool-size",
            "1",
            "--layouts-per-recipe",
            "1",
            "--road-shapes-per-layout",
            "1",
            "--candidate-pool-size",
            "1",
        ]
    )

    assert code == 0


def test_cli_defaults_create_recipe_first_config() -> None:
    argv = ["--start", "12", "--count", "1", "--difficulty", "easy"]
    args = build_generate_parser().parse_args(argv)

    config = _config_from_args(args, argv)

    assert config.generation_mode == "recipe_first"
    assert config.recipe_pool_size == 4
    assert config.layouts_per_recipe == 3
    assert config.road_shapes_per_layout == 3
    assert config.layout_orientation_preference == "auto"
    assert config.vertical_route_probability == 0.35
    assert config.prefer_vertical_for_long_routes is True
    assert config.candidate_pool_size == 25
    assert config.max_attempts_per_level == 300


def test_cli_parses_layout_orientation_options() -> None:
    argv = [
        "--start",
        "12",
        "--count",
        "1",
        "--difficulty",
        "easy",
        "--layout-orientation",
        "vertical",
        "--vertical-route-probability",
        "0.8",
        "--no-prefer-vertical-for-long-routes",
    ]
    args = build_generate_parser().parse_args(argv)

    config = _config_from_args(args, argv)

    assert config.layout_orientation_preference == "vertical"
    assert config.vertical_route_probability == 0.8
    assert config.prefer_vertical_for_long_routes is False


def test_cli_accepts_recipe_architecture_options_for_recipe_generation(tmp_path) -> None:
    code = main_generate(
        [
            "--start",
            "12",
            "--count",
            "1",
            "--difficulty",
            "easy",
            "--template",
            "single_switch",
            "--generation-mode",
            "recipe-first",
            "--recipe-pool-size",
            "3",
            "--layouts-per-recipe",
            "2",
            "--road-shapes-per-layout",
            "2",
            "--layout-orientation",
            "vertical",
            "--vertical-route-probability",
            "1.0",
            "--candidate-pool-size",
            "1",
            "--dry-run",
            "--output-levels",
            str(tmp_path / "levels"),
            "--output-solutions",
            str(tmp_path / "solutions"),
            "--report",
            str(tmp_path / "report.md"),
            "--json-report",
            str(tmp_path / "report.json"),
        ]
    )

    assert code == 0
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["generationMode"] == "recipe_first"
    assert report["recipePoolSize"] == 3
    assert report["layoutsPerRecipe"] == 2
    assert report["roadShapesPerLayout"] == 2
    assert report["layoutOrientationPreference"] == "vertical"
    assert report["verticalRouteProbability"] == 1.0
    assert report["acceptedLevels"][0]["recipeFamily"] == "single_switch"
    assert report["acceptedLevels"][0]["recipeVariant"] is not None
    assert report["acceptedLevels"][0]["layoutOrientation"] == "vertical"


def test_cli_explicit_legacy_template_mode_still_generates(tmp_path) -> None:
    code = main_generate(
        [
            "--start",
            "12",
            "--count",
            "1",
            "--difficulty",
            "tutorial",
            "--template",
            "straight_delivery",
            "--generation-mode",
            "legacy-template",
            "--candidate-pool-size",
            "1",
            "--dry-run",
            "--output-levels",
            str(tmp_path / "levels"),
            "--output-solutions",
            str(tmp_path / "solutions"),
            "--report",
            str(tmp_path / "report.md"),
            "--json-report",
            str(tmp_path / "report.json"),
        ]
    )

    assert code == 0
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["generationMode"] == "legacy_template"
    assert report["acceptedLevels"][0]["recipeFamily"] is None


def test_validate_cli_validates_written_files(tmp_path) -> None:
    generate_code = main_generate(
        [
            "--start",
            "12",
            "--count",
            "1",
            "--difficulty",
            "tutorial",
            "--template",
            "straight_delivery",
            "--seed",
            "1",
            "--output-levels",
            str(tmp_path / "levels"),
            "--output-solutions",
            str(tmp_path / "solutions"),
            "--report",
            str(tmp_path / "report.md"),
            "--json-report",
            str(tmp_path / "report.json"),
            "--recipe-pool-size",
            "1",
            "--layouts-per-recipe",
            "1",
            "--road-shapes-per-layout",
            "1",
            "--candidate-pool-size",
            "1",
        ]
    )
    assert generate_code == 0

    validate_code = main_validate(
        [
            "--levels",
            "level_012",
            "--output-levels",
            str(tmp_path / "levels"),
            "--output-solutions",
            str(tmp_path / "solutions"),
        ]
    )

    assert validate_code == 0
    solution = json.loads((tmp_path / "solutions" / "level_012.solution.json").read_text(encoding="utf-8"))
    assert "isPlaceholder" not in solution
