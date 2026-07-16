#!/usr/bin/env python3
"""Run Python tests, the generator smoke check, and optional Swift tests."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(command: list[str], cwd: Path) -> int:
    print("\n==> " + " ".join(command), flush=True)
    return subprocess.run(command, cwd=cwd, check=False).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="Python interpreter containing all Python dependencies.")
    parser.add_argument("--swift-tests", action="store_true", help="Also run the TinyRoutes Xcode test scheme (macOS only).")
    parser.add_argument(
        "--destination",
        default="platform=iOS Simulator,name=iPhone 16 Pro,OS=18.5",
        help="xcodebuild destination used with --swift-tests.",
    )
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    scripts = repo_root / "scripts"
    python_path = Path(args.python)
    python = str(repo_root / python_path) if not python_path.is_absolute() and python_path.parent != Path(".") else args.python

    commands = [
        [python, str(scripts / "run_python_tests.py"), "--python", python],
        [python, str(scripts / "run_generator_smoke.py"), "--python", python],
    ]
    if args.swift_tests:
        commands.append([
            python,
            str(scripts / "run_swift_tests.py"),
            "--destination",
            args.destination,
        ])

    results = [run(command, repo_root) for command in commands]
    return 1 if any(results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
