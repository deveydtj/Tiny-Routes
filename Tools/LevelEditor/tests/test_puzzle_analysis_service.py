import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LEVEL_EDITOR_ROOT.parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.repositories import LevelFileRepository, SolutionFileRepository
from app.services import (
    AutomatedCheckStatus,
    AutomatedChecksService,
    PuzzleAnalysisService,
    TestRunnerResult,
)

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
except ImportError as exc:
    pytest.skip(f"PySide6 unavailable in this environment: {exc}", allow_module_level=True)

from app.ui import PuzzleAnalysisPanel


def _level_and_solution():
    level = LevelFileRepository().load_level(
        REPO_ROOT / "TinyRoutes" / "Resources" / "Levels" / "level_002.json"
    )
    solution = SolutionFileRepository().load_solution(
        REPO_ROOT
        / "TinyRoutesTests"
        / "Resources"
        / "LevelSolutions"
        / "level_002.solution.json"
    )
    return level, solution


class _PassingSwiftTests:
    def run_tests(self):
        return TestRunnerResult(
            command=["xcodebuild", "test"],
            exit_code=0,
            stdout="passed",
            stderr="",
            passed=True,
            summary="Swift parity tests passed.",
        )


def test_analysis_reports_topology_runtime_and_front_load_metrics() -> None:
    level, solution = _level_and_solution()

    analysis = PuzzleAnalysisService().analyze(level, solution)

    assert analysis.decision_count == 1
    assert analysis.unique_switches_used == 1
    assert analysis.equivalent_solutions == 1
    assert analysis.failure_outcomes == (("dead end", 1),)
    assert analysis.activation_window_lengths
    assert analysis.estimated_difficulty == "Easy"
    assert analysis.legacy_front_load_possible is True
    assert analysis.recommendations[0].related_node_id == "choice"
    assert "front-loaded" in analysis.recommendations[0].message


def test_one_click_checks_run_all_six_actions() -> None:
    level, solution = _level_and_solution()
    service = AutomatedChecksService(REPO_ROOT, swift_tests=_PassingSwiftTests())

    report = service.run(level, solution)

    assert [check.key for check in report.checks] == [
        "structure",
        "find_solution",
        "replay_solution",
        "front_load",
        "decision_quality",
        "swift_parity",
    ]
    assert report.checks[-1].status is AutomatedCheckStatus.PASSED
    assert report.checks[3].status is AutomatedCheckStatus.FAILED
    assert report.verified_solution is not None


def test_panel_displays_metrics_and_links_recommendations() -> None:
    app = QApplication.instance() or QApplication([])
    level, solution = _level_and_solution()
    analysis = PuzzleAnalysisService().analyze(level, solution)
    panel = PuzzleAnalysisPanel()
    activated = []
    panel.recommendation_activated.connect(activated.append)
    try:
        panel.show_analysis(analysis)
        assert panel._metric_labels["decision_count"].text() == "1"
        assert panel._metric_labels["failure_outcomes"].text() == "dead end: 1"

        item = panel._recommendations.item(0)
        panel._recommendations.itemDoubleClicked.emit(item)
        app.processEvents()

        assert activated[0].related_node_id == "choice"
        assert item.data(Qt.ItemDataRole.UserRole) == activated[0]
    finally:
        panel.close()
