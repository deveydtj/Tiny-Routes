from __future__ import annotations

import json

from app.cli import main_generate, main_validate


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
        ]
    )

    assert code == 0


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
    assert report["acceptedLevels"][0]["recipeFamily"] == "single_switch"
    assert report["acceptedLevels"][0]["recipeVariant"] is not None


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
