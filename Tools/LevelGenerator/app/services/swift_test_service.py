from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..models.generation_result import SwiftTestSummary


@dataclass(frozen=True)
class SwiftTestService:
    repo_root: Path
    timeout_seconds: int = 180
    level_ids: tuple[str, ...] = ()
    levels_output_dir: Path | None = None
    solutions_output_dir: Path | None = None

    def build_command(self) -> list[str]:
        command = [
            "xcodebuild",
            "test",
            "-project",
            "TinyRoutes.xcodeproj",
            "-scheme",
            "TinyRoutes",
            "-destination",
            "platform=iOS Simulator,name=iPhone 16,OS=18.5",
        ]
        if self.level_ids:
            return [
                *command,
                "-only-testing:TinyRoutesTests/LevelSolvabilityTests/testRequestedGeneratedLevelsCompleteFromEnvironmentDirectories",
            ]
        return [
            *command,
            "-only-testing:TinyRoutesTests/LevelSolvabilityTests",
            "-only-testing:TinyRoutesTests/LevelSimulationHarnessTests",
            "-only-testing:TinyRoutesTests/LevelSolutionScriptTests",
            "-only-testing:TinyRoutesTests/RouteEngineTests",
            "-only-testing:TinyRoutesTests/SwitchNodeViewTests",
        ]

    def build_environment(self) -> dict[str, str]:
        if not self.level_ids:
            return {}
        environment = {
            "TINY_ROUTES_VALIDATION_LEVEL_IDS": ",".join(self.level_ids),
        }
        if self.levels_output_dir is not None:
            environment["TINY_ROUTES_LEVELS_DIR"] = str(self.levels_output_dir)
        if self.solutions_output_dir is not None:
            environment["TINY_ROUTES_SOLUTIONS_DIR"] = str(self.solutions_output_dir)
        return environment

    def is_available(self) -> bool:
        return shutil.which("xcodebuild") is not None

    def run(self) -> SwiftTestSummary:
        command = self.build_command()
        environment = self.build_environment()
        if not self.is_available():
            return SwiftTestSummary(
                command=command,
                environment=environment,
                exit_code=127,
                passed=False,
                summary="Could not run Swift tests because xcodebuild was not found.",
            )
        try:
            completed = subprocess.run(
                command,
                cwd=self.repo_root,
                env={**os.environ, **environment},
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return SwiftTestSummary(
                command=command,
                environment=environment,
                exit_code=124,
                passed=False,
                summary=f"Swift solvability tests timed out after {self.timeout_seconds} seconds.",
                stdout_tail=_tail(exc.stdout),
                stderr_tail=_tail(exc.stderr),
                failure_details=_failure_details(exc.stdout, exc.stderr),
                failure_reasons=_failure_reasons(exc.stdout, exc.stderr),
            )
        except OSError as exc:
            return SwiftTestSummary(
                command=command,
                environment=environment,
                exit_code=1,
                passed=False,
                summary=f"Could not run Swift tests: {exc}",
            )

        passed = completed.returncode == 0
        toolchain_unavailable = (
            not passed
            and _xcode_toolchain_unavailable(completed.stdout, completed.stderr)
        )
        failure_details = [] if passed else _failure_details(completed.stdout, completed.stderr)
        failure_reasons = (
            []
            if passed
            else (
                ["xcode_toolchain_unavailable"]
                if toolchain_unavailable
                else _failure_reasons(completed.stdout, completed.stderr)
            )
        )
        return SwiftTestSummary(
            command=command,
            environment=environment,
            exit_code=completed.returncode,
            passed=passed,
            summary=(
                "Swift solvability tests passed."
                if passed
                else (
                    "Could not run Swift tests because the full Xcode developer "
                    "toolchain is not installed or selected."
                    if toolchain_unavailable
                    else (
                        "Swift solvability tests failed with exit code "
                        f"{completed.returncode}."
                    )
                )
            ),
            stdout_tail=_tail(completed.stdout),
            stderr_tail=_tail(completed.stderr),
            failure_details=failure_details,
            failure_reasons=failure_reasons,
        )


def _tail(value: object, limit: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    text = str(value)
    return text[-limit:]


def _failure_details(stdout: object, stderr: object, limit: int = 20) -> list[str]:
    text = "\n".join(part for part in [_tail(stdout, 12_000), _tail(stderr, 12_000)] if part)
    details = []
    interesting_prefixes = (
        "External generated level solvability failures:",
        "Level solvability failures:",
        "level id:",
        "script id:",
        "expected outcome:",
        "actual outcome:",
        "elapsed time:",
        "time remaining:",
        "tap count:",
        "final node:",
        "current edge:",
        "progress along edge:",
        "package collected:",
        "last executed action:",
        "harness error:",
    )
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if any(line.startswith(prefix) for prefix in interesting_prefixes):
            details.append(line)
        if len(details) >= limit:
            break
    return details


def _failure_reasons(stdout: object, stderr: object) -> list[str]:
    text = "\n".join(part for part in [_tail(stdout, 12_000), _tail(stderr, 12_000)] if part).lower()
    reasons: list[str] = []
    if "didrotate=false" in text or "invalid action node id" in text or "tap node ids must be non-empty" in text:
        reasons.append("switch_tap_runtime_mismatch")
    if (
        "package collected: false" in text
        or "didcollectpackage=false" in text
        or "reached_destination_without_package" in text
    ):
        reasons.append("package_order_runtime_mismatch")
    if "expected .completed" in text or "actual outcome:" in text or "external generated level harness threw" in text:
        reasons.append("solution_sidecar_runtime_mismatch")
    if not reasons:
        reasons.append("swift_runtime_parity_failed")
    return list(dict.fromkeys(reasons))


def _xcode_toolchain_unavailable(stdout: object, stderr: object) -> bool:
    text = "\n".join(
        part for part in [_tail(stdout, 12_000), _tail(stderr, 12_000)] if part
    ).lower()
    return (
        "xcodebuild requires xcode" in text
        or (
            "active developer directory" in text
            and "command line tools instance" in text
        )
    )
