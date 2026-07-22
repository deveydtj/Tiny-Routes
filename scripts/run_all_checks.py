#!/usr/bin/env python3
"""Run the complete Tiny Routes verification and release gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GateResult:
    name: str
    command: tuple[str, ...]
    exit_code: int

    @property
    def passed(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": list(self.command),
            "exitCode": self.exit_code,
            "passed": self.passed,
        }


def run(name: str, command: list[str], cwd: Path) -> GateResult:
    print("\n==> " + " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=cwd, check=False)
    return GateResult(name, tuple(command), completed.returncode)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _git_output(repo_root: Path, *arguments: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def _quality_profile(repo_root: Path) -> dict[str, Any]:
    model_path = (
        repo_root
        / "Tools/LevelGenerator/app/models/quality_profile.py"
    )
    try:
        model_source = model_path.read_text(encoding="utf-8")
    except OSError:
        model_source = ""
    match = re.search(
        r'^CURRENT_QUALITY_PROFILE_VERSION\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"',
        model_source,
        re.MULTILINE,
    )
    version = match.group(1) if match else None
    path = (
        repo_root
        / "Tools/LevelGenerator/config/quality_profiles"
        / f"production_v3_{version}.json"
    )
    if version is None or not path.is_file():
        return {"version": None, "sourceFingerprint": None, "path": None}
    payload = _read_json(path) or {}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return {
        "version": payload.get("version"),
        "sourceFingerprint": hashlib.sha256(canonical).hexdigest(),
        "path": str(path.relative_to(repo_root)),
    }


def _junit_totals(directory: Path) -> dict[str, int]:
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    if not directory.is_dir():
        return totals
    for path in sorted(directory.glob("*.xml")):
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError):
            continue
        suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
        for suite in suites:
            for key in totals:
                totals[key] += int(suite.attrib.get(key, 0))
    return totals


def _summary_payload(
    *,
    repo_root: Path,
    arguments: argparse.Namespace,
    results: list[GateResult],
    reports_dir: Path,
    junit_dir: Path,
    stress_summary_path: Path | None,
) -> dict[str, Any]:
    corpus = _read_json(reports_dir / "production_corpus_verification.json") or {}
    stress = _read_json(stress_summary_path) if stress_summary_path is not None else None
    commit = _git_output(repo_root, "rev-parse", "HEAD")
    status = _git_output(repo_root, "status", "--porcelain")
    warnings: list[str] = []
    if status:
        warnings.append("The release command ran from a working tree with uncommitted changes.")
    if not arguments.swift_tests:
        warnings.append("Swift tests were not requested; this is not a final release result.")
    if not arguments.generator_v3_stress:
        warnings.append("The production V3 release stress gate was not requested.")
    if not arguments.transaction_tests:
        warnings.append("The dedicated transaction gate was not requested.")

    config = {
        "python": arguments.python,
        "swiftTests": arguments.swift_tests,
        "destination": arguments.destination,
        "productionContent": arguments.production_content,
        "generatorV3Stress": arguments.generator_v3_stress,
        "transactionTests": arguments.transaction_tests,
        "stressCampaignCount": arguments.stress_campaign_count,
        "stressLevelsPerCampaign": arguments.stress_levels_per_campaign,
        "stressSeedRange": (
            arguments.stress_seed_range
            or (
                f"1-{arguments.stress_campaign_count}"
                if arguments.generator_v3_stress
                else None
            )
        ),
    }
    config_identity = hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    gate_pass_count = sum(result.passed for result in results)
    release_mode_requested = any(
        (
            arguments.production_content,
            arguments.generator_v3_stress,
            arguments.transaction_tests,
        )
    )
    required_release_flags = (
        arguments.swift_tests
        and arguments.production_content
        and arguments.generator_v3_stress
        and arguments.transaction_tests
    )
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "passed": bool(results)
        and all(result.passed for result in results)
        and (not release_mode_requested or required_release_flags),
        "releaseConfigurationComplete": required_release_flags,
        "commit": {
            "sha": commit,
            "workingTreeDirty": bool(status),
        },
        "configuration": config,
        "configurationIdentity": config_identity,
        "qualityProfile": _quality_profile(repo_root),
        "gateTotals": {
            "total": len(results),
            "passed": gate_pass_count,
            "failed": len(results) - gate_pass_count,
        },
        "testTotals": _junit_totals(junit_dir),
        "gates": [result.to_dict() for result in results],
        "stress": stress,
        "campaignCompletion": None
        if stress is None
        else {
            "campaignCount": stress.get("campaignCount"),
            "completeBatchCount": stress.get("completeBatchCount"),
            "requestedLevelCount": stress.get("requestedLevelCount"),
            "selectedLevelCount": stress.get("selectedLevelCount"),
        },
        "parity": {
            "swiftRequested": arguments.swift_tests,
            "swiftGatePassed": any(
                result.name == "swift_tests" and result.passed for result in results
            ),
            "stressParityErrorCount": None
            if stress is None
            else stress.get("parityErrorCount"),
        },
        "corpus": {
            "passed": corpus.get("passed"),
            "levelCount": corpus.get("levelCount"),
            "manifestSynchronized": corpus.get("manifestSynchronized"),
            "nonSwiftGatesPassed": corpus.get("nonSwiftGatesPassed"),
        },
        "knownNonBlockingWarnings": warnings,
    }


def _write_summary(payload: dict[str, Any], reports_dir: Path) -> tuple[Path, Path]:
    json_path = reports_dir / "release_summary.json"
    markdown_path = reports_dir / "release_summary.md"
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    gates = payload["gateTotals"]
    tests = payload["testTotals"]
    quality = payload["qualityProfile"]
    lines = [
        "# Tiny Routes Release Summary",
        "",
        f"- Passed: `{str(payload['passed']).lower()}`",
        f"- Commit: `{payload['commit']['sha'] or 'unavailable'}`",
        f"- Configuration identity: `{payload['configurationIdentity']}`",
        f"- Quality profile: `{quality['version'] or 'unavailable'}`",
        f"- Gates: `{gates['passed']}/{gates['total']}` passed",
        f"- Python/transaction tests: `{tests['tests']}` total, "
        f"`{tests['failures'] + tests['errors']}` failed, `{tests['skipped']}` skipped",
        "",
        "## Gates",
        "",
    ]
    lines.extend(
        f"- {'PASS' if gate['passed'] else 'FAIL'} — `{gate['name']}` "
        f"(exit {gate['exitCode']})"
        for gate in payload["gates"]
    )
    lines.extend(["", "## Known non-blocking warnings", ""])
    warnings = payload["knownNonBlockingWarnings"]
    lines.extend(f"- {warning}" for warning in warnings)
    if not warnings:
        lines.append("- None.")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, markdown_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="Python interpreter containing all Python dependencies.")
    parser.add_argument("--swift-tests", action="store_true", help="Also run the TinyRoutes Xcode test scheme (macOS only).")
    parser.add_argument(
        "--production-content",
        action="store_true",
        help="Assert that production corpus verification is part of this release run.",
    )
    parser.add_argument(
        "--generator-v3-stress",
        action="store_true",
        help="Run 100 complete 30-level campaigns through the exact production V3 path.",
    )
    parser.add_argument(
        "--transaction-tests",
        action="store_true",
        help="Run the dedicated staging, rollback, collision, and locking suite.",
    )
    parser.add_argument(
        "--stress-campaign-count",
        type=int,
        default=100,
        help="Campaign count used by --generator-v3-stress (default: 100).",
    )
    parser.add_argument(
        "--stress-levels-per-campaign",
        type=int,
        default=30,
        help="Level count per stress campaign (default: 30).",
    )
    parser.add_argument(
        "--stress-seed-range",
        help="Inclusive seed range; defaults to 1-N for N stress campaigns.",
    )
    parser.add_argument(
        "--destination",
        default="platform=iOS Simulator,name=iPhone 16 Pro,OS=18.5",
        help="xcodebuild destination used with --swift-tests.",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        help="Directory in which to retain release evidence and the final summary.",
    )
    args = parser.parse_args(argv)
    if args.stress_campaign_count < 1:
        parser.error("--stress-campaign-count must be positive")
    if args.stress_levels_per_campaign < 1:
        parser.error("--stress-levels-per-campaign must be positive")

    repo_root = Path(__file__).resolve().parents[1]
    scripts = repo_root / "scripts"
    python_path = Path(args.python)
    python = str(repo_root / python_path) if not python_path.is_absolute() and python_path.parent != Path(".") else args.python
    release_requested = any(
        (args.production_content, args.generator_v3_stress, args.transaction_tests)
    )

    temporary_reports: tempfile.TemporaryDirectory[str] | None = None
    if args.reports_dir is None and not release_requested:
        temporary_reports = tempfile.TemporaryDirectory(prefix="tiny-routes-checks-")
        reports_dir = Path(temporary_reports.name)
    elif args.reports_dir is None:
        reports_dir = repo_root / "artifacts" / "production-v3-release"
        reports_dir.mkdir(parents=True, exist_ok=True)
    else:
        reports_dir = args.reports_dir.expanduser()
        if not reports_dir.is_absolute():
            reports_dir = repo_root / reports_dir
        reports_dir.mkdir(parents=True, exist_ok=True)

    junit_dir = reports_dir / "junit"
    junit_dir.mkdir(parents=True, exist_ok=True)
    commands: list[tuple[str, list[str]]] = [
        (
            "python_suites",
            [
                python,
                str(scripts / "run_python_tests.py"),
                "--python",
                python,
                "--junit-dir",
                str(junit_dir),
            ],
        ),
        ("generator_smoke", [python, str(scripts / "run_generator_smoke.py"), "--python", python]),
        (
            "fixed_seed_regressions",
            [
                python,
                str(repo_root / "Tools/LevelGenerator/run_fixed_seed_regressions.py"),
                "--json-output",
                str(reports_dir / "fixed_seed_regressions.json"),
            ],
        ),
        (
            "production_content",
            [
                python,
                str(repo_root / "Tools/LevelGenerator/verify_production_corpus.py"),
                "--no-swift-tests",
                "--json-output",
                str(reports_dir / "production_corpus_verification.json"),
                "--markdown-output",
                str(reports_dir / "production_corpus_verification.md"),
            ],
        ),
    ]

    stress_summary_path: Path | None = None
    if args.generator_v3_stress:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        stress_dir = reports_dir / f"generator_v3_stress_{timestamp}"
        seed_range = args.stress_seed_range or f"1-{args.stress_campaign_count}"
        stress_summary_path = stress_dir / "stress_summary.json"
        commands.append(
            (
                "generator_v3_stress",
                [
                    python,
                    str(repo_root / "Tools/LevelGenerator/stress_test_generation.py"),
                    "--mode",
                    "production_v3",
                    "--campaign-count",
                    str(args.stress_campaign_count),
                    "--levels-per-campaign",
                    str(args.stress_levels_per_campaign),
                    "--seed-range",
                    seed_range,
                    "--require-complete-batches",
                    "--fail-on-one-tap",
                    "--fail-on-static-policy",
                    "--fail-on-parity-error",
                    "--output-dir",
                    str(stress_dir),
                ],
            )
        )
    if args.transaction_tests:
        commands.append(
            (
                "transaction_tests",
                [
                    python,
                    "-m",
                    "pytest",
                    "Tools/LevelGenerator/tests/test_transactional_generation.py",
                    "--junitxml",
                    str(junit_dir / "transaction_tests.xml"),
                ],
            )
        )
    if args.swift_tests:
        commands.append(
            (
                "swift_tests",
                [
                    python,
                    str(scripts / "run_swift_tests.py"),
                    "--destination",
                    args.destination,
                ],
            )
        )

    try:
        results = [run(name, command, repo_root) for name, command in commands]
        payload = _summary_payload(
            repo_root=repo_root,
            arguments=args,
            results=results,
            reports_dir=reports_dir,
            junit_dir=junit_dir,
            stress_summary_path=stress_summary_path,
        )
        json_path, markdown_path = _write_summary(payload, reports_dir)
        print(f"\nRelease summary: {json_path}", flush=True)
        print(f"Release summary (Markdown): {markdown_path}", flush=True)
        return 0 if payload["passed"] else 1
    finally:
        if temporary_reports is not None:
            temporary_reports.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
