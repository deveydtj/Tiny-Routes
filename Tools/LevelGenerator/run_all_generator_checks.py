#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local Tiny Routes LevelGenerator checks.")
    parser.add_argument("--python", default=sys.executable, help="Python interpreter to use for checks.")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--skip-production-validation", action="store_true")
    parser.add_argument("--swift-tests", action="store_true", help="Run optional Swift tests during production validation.")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    commands: list[list[str]] = []
    if not args.skip_tests:
        commands.append([args.python, "-m", "pytest", "Tools/LevelGenerator/tests"])
    if not args.skip_smoke:
        commands.append(
            [
                args.python,
                "Tools/LevelGenerator/generate_levels.py",
                "--start",
                "99",
                "--count",
                "2",
                "--difficulty",
                "easy",
                "--template",
                "mixed",
                "--seed",
                "123",
                "--dry-run",
                "--report",
                "/tmp/tiny-routes-smoke.md",
                "--json-report",
                "/tmp/tiny-routes-smoke.json",
            ]
        )
    if not args.skip_production_validation:
        level_ids = sorted(
            path.stem
            for path in (repo_root / "TinyRoutes" / "Resources" / "Levels").glob("level_*.json")
        )
        commands.append(
            [
                args.python,
                "Tools/LevelGenerator/validate_generated_levels.py",
                "--levels",
                *level_ids,
                "--swift-tests" if args.swift_tests else "--no-swift-tests",
            ]
        )

    for command in commands:
        print("+ " + " ".join(command))
        completed = subprocess.run(command, cwd=repo_root, check=False)
        if completed.returncode != 0:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
