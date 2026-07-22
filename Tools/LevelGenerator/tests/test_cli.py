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
            "--generator-architecture",
            "v2_legacy",
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
    output = capsys.readouterr()
    assert "Accepted level_012" in output.out
    assert "v2_legacy is a non-production compatibility mode" in output.err


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
            "--generator-architecture",
            "v2_legacy",
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


def test_cli_defaults_to_production_v3() -> None:
    argv = ["--start", "12", "--count", "1", "--difficulty", "easy"]
    args = build_generate_parser().parse_args(argv)

    config = _config_from_args(args, argv)

    assert config.generator_architecture == "production_v3"
    assert config.generator_architecture_version == 3
    assert config.recipe_pool_size == 4
    assert config.layouts_per_recipe == 2
    assert config.road_shapes_per_layout == 2
    assert config.layout_orientation_preference == "portrait_vertical"
    assert config.layout_size_profile == "difficulty_curve"
    assert config.vertical_route_probability == 0.35
    assert config.prefer_vertical_for_long_routes is True
    assert config.candidate_pool_size == 4
    assert config.max_attempts_per_level == 120
    assert config.playtest_portfolio is False


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
        "--layout-size-profile",
        "large_portrait",
        "--vertical-route-probability",
        "0.8",
        "--no-prefer-vertical-for-long-routes",
    ]
    args = build_generate_parser().parse_args(argv)

    config = _config_from_args(args, argv)

    assert config.layout_orientation_preference == "vertical"
    assert config.layout_size_profile == "large_portrait"
    assert config.vertical_route_probability == 0.8
    assert config.prefer_vertical_for_long_routes is False


def test_cli_playtest_mode_disables_existing_similarity_by_default() -> None:
    argv = [
        "--start", "1", "--count", "50", "--difficulty", "auto",
        "--generator-architecture", "v2_legacy", "--playtest-mode",
    ]
    args = build_generate_parser().parse_args(argv)

    config = _config_from_args(args, argv)

    assert config.playtest_portfolio is True
    assert config.compare_against_existing is False
    assert config.playtest_uniqueness_window == 6
    assert config.candidate_pool_size == 1
    assert config.layout_orientation_preference == "auto"


def test_cli_playtest_mode_can_keep_existing_similarity_when_explicit() -> None:
    argv = [
        "--start",
        "1",
        "--count",
        "50",
        "--difficulty",
        "auto",
        "--generator-architecture",
        "v2_legacy",
        "--playtest-mode",
        "--compare-existing",
    ]
    args = build_generate_parser().parse_args(argv)

    config = _config_from_args(args, argv)

    assert config.playtest_portfolio is True
    assert config.compare_against_existing is True


def test_cli_accepts_recipe_architecture_options_for_recipe_generation(tmp_path) -> None:
    code = main_generate(
        [
            "--start",
            "12",
            "--count",
            "1",
            "--difficulty",
            "easy",
            "--generator-architecture",
            "v2_legacy",
            "--template",
            "single_switch",
            "--recipe-pool-size",
            "3",
            "--layouts-per-recipe",
            "2",
            "--road-shapes-per-layout",
            "2",
            "--layout-orientation",
            "vertical",
            "--layout-size-profile",
            "large_portrait",
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
    assert report["generatorArchitecture"] == "v2_legacy"
    assert report["generatorArchitectureVersion"] == 2
    assert report["generationMode"] == "recipe_first"
    assert report["recipePoolSize"] == 3
    assert report["layoutsPerRecipe"] == 2
    assert report["roadShapesPerLayout"] == 2
    assert report["layoutOrientationPreference"] == "vertical"
    assert report["layoutSizeProfile"] == "large_portrait"
    assert report["verticalRouteProbability"] == 1.0
    assert report["acceptedLevels"][0]["recipeFamily"] == "single_switch"
    assert report["acceptedLevels"][0]["recipeVariant"] is not None
    assert report["acceptedLevels"][0]["layoutOrientation"] == "vertical"
    assert report["acceptedLevels"][0]["layoutSizeProfile"] == "large_portrait"


def test_cli_rejects_removed_legacy_template_mode(tmp_path) -> None:
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

    assert code == 2
    assert not (tmp_path / "report.json").exists()


def test_cli_production_v3_never_falls_back_to_v2(tmp_path, capsys) -> None:
    code = main_generate(
        [
            "--start",
            "12",
            "--count",
            "1",
            "--difficulty",
            "easy",
            "--generator-architecture",
            "production_v3",
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

    assert code == 1
    assert "production_v3_requires_transactional_entrypoint" in capsys.readouterr().err
    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert payload["generatorArchitecture"] == "production_v3"
    assert payload["generatorArchitectureVersion"] == 3
    assert payload["acceptedLevels"] == []


def test_validate_cli_validates_written_files(tmp_path) -> None:
    generate_code = main_generate(
        [
            "--start",
            "12",
            "--count",
            "1",
            "--difficulty",
            "tutorial",
            "--generator-architecture",
            "v2_legacy",
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
