#!/usr/bin/env python3
"""Run a small deterministic generator dry run without changing repository files."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="Python interpreter containing generator dependencies.")
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    python_path = Path(args.python)
    python = str(repo_root / python_path) if not python_path.is_absolute() and python_path.parent != Path(".") else args.python

    with tempfile.TemporaryDirectory(prefix="tiny-routes-smoke-") as output_directory:
        output = Path(output_directory)
        command = [
            python,
            "generate_levels.py",
            "--start", "99",
            "--count", "2",
            "--difficulty", "easy",
            "--template", "mixed",
            "--seed", "123",
            "--dry-run",
            "--report", str(output / "report.md"),
            "--json-report", str(output / "report.json"),
            "--recipe-pool-size", "2",
            "--layouts-per-recipe", "1",
            "--road-shapes-per-layout", "1",
            "--candidate-pool-size", "2",
            "--max-attempts-per-level", "50",
        ]
        print("==> " + " ".join(command), flush=True)
        return subprocess.run(
            command,
            cwd=repo_root / "Tools" / "LevelGenerator",
            check=False,
        ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
