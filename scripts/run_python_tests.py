#!/usr/bin/env python3
"""Run both Python tool suites in isolated working directories."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SUITES = ("Tools/LevelGenerator", "Tools/LevelEditor")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="Python interpreter containing pytest and tool dependencies.")
    parser.add_argument("pytest_args", nargs="*", help="Additional arguments passed to each pytest invocation.")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    python_path = Path(args.python)
    python = str(repo_root / python_path) if not python_path.is_absolute() and python_path.parent != Path(".") else args.python
    failures: list[tuple[str, int]] = []
    for relative_directory in SUITES:
        working_directory = repo_root / relative_directory
        command = [python, "-m", "pytest", "tests", *args.pytest_args]
        print(f"\n==> {relative_directory}: {' '.join(command)}", flush=True)
        completed = subprocess.run(command, cwd=working_directory, check=False)
        if completed.returncode != 0:
            failures.append((relative_directory, completed.returncode))

    if failures:
        print("\nPython suite failures:", file=sys.stderr)
        for suite, returncode in failures:
            print(f"  {suite}: exit {returncode}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
