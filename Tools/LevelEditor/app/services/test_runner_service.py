from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestRunnerResult:
    __test__ = False

    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    passed: bool
    summary: str


class TestRunnerService:
    """Run the Swift solvability test harness from the repository root."""

    __test__ = False

    def __init__(self, repo_root: Path | str, timeout_seconds: int = 120) -> None:
        self._repo_root = Path(repo_root)
        self._timeout_seconds = timeout_seconds

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
        ]

    def run_tests(self) -> TestRunnerResult:
        command = self.build_command()

        try:
            completed = subprocess.run(
                command,
                cwd=self._repo_root,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            return TestRunnerResult(
                command=command,
                exit_code=127,
                stdout="",
                stderr=str(exc),
                passed=False,
                summary="Could not run Swift tests because xcodebuild was not found.",
            )
        except subprocess.TimeoutExpired as exc:
            stdout = _coerce_output(exc.stdout)
            stderr = _coerce_output(exc.stderr)
            return TestRunnerResult(
                command=command,
                exit_code=124,
                stdout=stdout,
                stderr=stderr,
                passed=False,
                summary=f"Swift tests timed out after {self._timeout_seconds} seconds.",
            )
        except OSError as exc:
            return TestRunnerResult(
                command=command,
                exit_code=1,
                stdout="",
                stderr=str(exc),
                passed=False,
                summary=f"Could not run Swift tests: {exc}",
            )

        passed = completed.returncode == 0
        summary = (
            "Swift solvability tests passed."
            if passed
            else f"Swift solvability tests failed with exit code {completed.returncode}."
        )
        return TestRunnerResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            passed=passed,
            summary=summary,
        )


def _coerce_output(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return str(value)
