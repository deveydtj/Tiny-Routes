#!/usr/bin/env python3
"""Run Python, generator, production-content, and optional Swift release checks."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
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
    parser.add_argument(
        "--reports-dir",
        type=Path,
        help="Optional directory in which to retain fixed-seed and production-corpus reports.",
    )
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    scripts = repo_root / "scripts"
    python_path = Path(args.python)
    python = str(repo_root / python_path) if not python_path.is_absolute() and python_path.parent != Path(".") else args.python

    temporary_reports: tempfile.TemporaryDirectory[str] | None = None
    if args.reports_dir is None:
        temporary_reports = tempfile.TemporaryDirectory(
            prefix="tiny-routes-release-checks-"
        )
        reports_dir = Path(temporary_reports.name)
    else:
        reports_dir = args.reports_dir.expanduser()
        if not reports_dir.is_absolute():
            reports_dir = repo_root / reports_dir
        reports_dir.mkdir(parents=True, exist_ok=True)

    commands = [
        [python, str(scripts / "run_python_tests.py"), "--python", python],
        [python, str(scripts / "run_generator_smoke.py"), "--python", python],
        [
            python,
            str(repo_root / "Tools/LevelGenerator/run_fixed_seed_regressions.py"),
            "--json-output",
            str(reports_dir / "fixed_seed_regressions.json"),
        ],
        [
            python,
            str(repo_root / "Tools/LevelGenerator/verify_production_corpus.py"),
            "--no-swift-tests",
            "--json-output",
            str(reports_dir / "production_corpus_verification.json"),
            "--markdown-output",
            str(reports_dir / "production_corpus_verification.md"),
        ],
    ]
    if args.swift_tests:
        commands.append([
            python,
            str(scripts / "run_swift_tests.py"),
            "--destination",
            args.destination,
        ])

    try:
        results = [run(command, repo_root) for command in commands]
        if args.reports_dir is not None:
            print(f"\nRelease reports: {reports_dir}", flush=True)
        return 1 if any(results) else 0
    finally:
        if temporary_reports is not None:
            temporary_reports.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
