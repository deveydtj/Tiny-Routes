from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from app.models import LevelDocument, Solution

from .level_validation_service import LevelValidationService
from .puzzle_analysis_service import PuzzleAnalysis, PuzzleAnalysisService
from .runtime_solution_service import RuntimeSolutionService
from .test_runner_service import TestRunnerService


class AutomatedCheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


@dataclass(frozen=True)
class AutomatedCheckResult:
    key: str
    label: str
    status: AutomatedCheckStatus
    summary: str


@dataclass(frozen=True)
class AutomatedChecksReport:
    checks: tuple[AutomatedCheckResult, ...]
    analysis: PuzzleAnalysis
    verified_solution: Solution | None = None

    @property
    def passed(self) -> bool:
        return all(check.status is not AutomatedCheckStatus.FAILED for check in self.checks)


class AutomatedChecksService:
    """Run the editor's complete manual verification gate in one action."""

    def __init__(
        self,
        repo_root: Path | str,
        *,
        level_validation: LevelValidationService | None = None,
        runtime: RuntimeSolutionService | None = None,
        analysis: PuzzleAnalysisService | None = None,
        swift_tests: TestRunnerService | None = None,
    ) -> None:
        self._level_validation = level_validation or LevelValidationService()
        self._runtime = runtime or RuntimeSolutionService()
        self._analysis = analysis or PuzzleAnalysisService(self._runtime)
        self._swift_tests = swift_tests or TestRunnerService(repo_root)

    def run(
        self,
        level: LevelDocument,
        solution: Solution | None,
        file_path: Path | None = None,
    ) -> AutomatedChecksReport:
        checks: list[AutomatedCheckResult] = []

        structure = self._level_validation.validate(level, file_path)
        checks.append(AutomatedCheckResult(
            "structure",
            "Validate structure",
            AutomatedCheckStatus.FAILED if structure.has_errors else AutomatedCheckStatus.PASSED,
            (
                f"Found {sum(message.severity.value == 'error' for message in structure.messages)} structural error(s)."
                if structure.has_errors
                else "Structural validation passed."
            ),
        ))

        verified = self._safe_find_verified(level)
        checks.append(AutomatedCheckResult(
            "find_solution",
            "Find verified solution",
            AutomatedCheckStatus.PASSED if verified is not None else AutomatedCheckStatus.FAILED,
            (
                f"Found a verified solution with {len(verified.actions)} tap(s)."
                if verified is not None
                else "No verified solution was found within the search limit."
            ),
        ))

        replay = self._safe_replay(level, solution)
        checks.append(AutomatedCheckResult(
            "replay_solution",
            "Replay saved solution",
            AutomatedCheckStatus.PASSED if replay is not None and replay.passed else AutomatedCheckStatus.FAILED,
            (
                "The saved solution completed the level."
                if replay is not None and replay.passed
                else "The saved solution failed "
                f"({getattr(replay, 'failure_reason', None) or 'missing or invalid solution'})."
            ),
        ))

        analysis = self._analysis.analyze(level, solution)
        if solution is None or not solution.actions:
            front_status = AutomatedCheckStatus.WARNING
            front_summary = "No saved taps are available for the front-load diagnostic."
        elif analysis.legacy_front_load_possible:
            front_status = AutomatedCheckStatus.FAILED
            front_summary = "All taps at 0.0 complete the level in legacy-global diagnostic mode."
        else:
            front_status = AutomatedCheckStatus.PASSED
            front_summary = "Moving every tap to 0.0 does not complete the legacy diagnostic replay."
        checks.append(AutomatedCheckResult(
            "front_load",
            "Legacy front-load diagnostic",
            front_status,
            front_summary,
        ))

        quality_status = (
            AutomatedCheckStatus.WARNING
            if analysis.recommendations
            else AutomatedCheckStatus.PASSED
        )
        checks.append(AutomatedCheckResult(
            "decision_quality",
            "Analyze decision quality",
            quality_status,
            (
                f"Estimated {analysis.estimated_difficulty.lower()} difficulty; "
                f"{len(analysis.recommendations)} recommendation(s)."
            ),
        ))

        swift = self._swift_tests.run_tests()
        checks.append(AutomatedCheckResult(
            "swift_parity",
            "Run Swift parity tests",
            AutomatedCheckStatus.PASSED if swift.passed else AutomatedCheckStatus.FAILED,
            swift.summary,
        ))
        return AutomatedChecksReport(tuple(checks), analysis, verified)

    def _safe_find_verified(self, level: LevelDocument) -> Solution | None:
        try:
            return self._runtime.find_verified(level)
        except (KeyError, TypeError, ValueError):
            return None

    def _safe_replay(self, level: LevelDocument, solution: Solution | None):
        if solution is None:
            return None
        try:
            return self._runtime.replay(level, solution)
        except (KeyError, TypeError, ValueError):
            return None
