from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..models.generation_result import SwiftTestSummary


@dataclass(frozen=True)
class SwiftTestService:
    repo_root: Path
    timeout_seconds: int = 180

    def build_command(self) -> list[str]:
        return [
            "xcodebuild",
            "test",
            "-project",
            "TinyRoutes.xcodeproj",
            "-scheme",
            "TinyRoutes",
            "-destination",
            "platform=iOS Simulator,name=iPhone 16,OS=18.5",
            "-only-testing:TinyRoutesTests/LevelSolvabilityTests",
        ]

    def is_available(self) -> bool:
        return shutil.which("xcodebuild") is not None

    def run(self) -> SwiftTestSummary:
        command = self.build_command()
        if not self.is_available():
            return SwiftTestSummary(
                command=command,
                exit_code=127,
                passed=False,
                summary="Could not run Swift tests because xcodebuild was not found.",
            )
        try:
            completed = subprocess.run(
                command,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return SwiftTestSummary(
                command=command,
                exit_code=124,
                passed=False,
                summary=f"Swift solvability tests timed out after {self.timeout_seconds} seconds.",
                stdout_tail=_tail(exc.stdout),
                stderr_tail=_tail(exc.stderr),
            )
        except OSError as exc:
            return SwiftTestSummary(
                command=command,
                exit_code=1,
                passed=False,
                summary=f"Could not run Swift tests: {exc}",
            )

        passed = completed.returncode == 0
        return SwiftTestSummary(
            command=command,
            exit_code=completed.returncode,
            passed=passed,
            summary="Swift solvability tests passed." if passed else f"Swift solvability tests failed with exit code {completed.returncode}.",
            stdout_tail=_tail(completed.stdout),
            stderr_tail=_tail(completed.stderr),
        )


def _tail(value: object, limit: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    text = str(value)
    return text[-limit:]
