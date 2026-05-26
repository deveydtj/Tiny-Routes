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
