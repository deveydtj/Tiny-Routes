from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QFileDialog, QGraphicsView, QMessageBox
except ImportError as exc:
    pytest.skip(f"PySide6 unavailable in this environment: {exc}", allow_module_level=True)

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

import app.main_window as main_window_module
from app.main import _parse_arguments
from app.main_window import LevelEditorMainWindow
from app.models import (
    LevelDocument,
    RouteGraphModel,
    RouteNodeModel,
    SolutionModel,
)
from app.repositories import LevelFileRepository, SolutionFileRepository
from app.ui import LevelCanvasScene, LevelCanvasView


@pytest.fixture
def qapplication() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def no_modal_message_boxes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Discard,
    )


def _document() -> LevelDocument:
    return LevelDocument(
        id="candidate",
        name="Candidate",
        graph=RouteGraphModel(nodes=[
            RouteNodeModel(id="a", x=0.0, y=0.0),
            RouteNodeModel(id="b", x=1.0, y=2.0),
            RouteNodeModel(id="c", x=6.0, y=5.0),
        ]),
        startNodeID="a",
        packageNodeID="b",
        destinationNodeID="c",
        timeLimitSeconds=30,
        parTaps=0,
    )


def _solution() -> SolutionModel:
    return SolutionModel(
        levelID="candidate",
        description="Candidate solution",
        expectedOutcome="completed",
        maxTaps=0,
        requiresWithinTimeLimit=True,
        actions=[],
    )


def test_startup_arguments_accept_complete_candidate_bundle(tmp_path: Path) -> None:
    arguments = _parse_arguments([
        "--level", str(tmp_path / "candidate.json"),
        "--solution", str(tmp_path / "candidate.solution.json"),
        "--quality", str(tmp_path / "candidate.quality.json"),
    ])

    assert arguments.level == tmp_path / "candidate.json"
    assert arguments.solution == tmp_path / "candidate.solution.json"
    assert arguments.quality == tmp_path / "candidate.quality.json"


def test_open_level_bundle_loads_explicit_solution_and_generator_quality(
    qapplication: QApplication,
    tmp_path: Path,
) -> None:
    level_path = tmp_path / "candidate.json"
    solution_path = tmp_path / "candidate.solution.json"
    quality_path = tmp_path / "candidate.quality.json"
    LevelFileRepository().save_level(level_path, _document())
    SolutionFileRepository().save_solution(solution_path, _solution())
    quality_path.write_text(json.dumps({
        "levelID": "candidate",
        "difficulty": "hard",
        "template": "return_loop",
        "seed": 41,
        "quality": {
            "totalScore": 88.25,
            "topPositiveFactors": ["measured revisit dependency"],
        },
    }), encoding="utf-8")
    window = LevelEditorMainWindow()
    try:
        assert window.open_level_bundle(
            level_path,
            solution_path=solution_path,
            quality_path=quality_path,
        )
        assert window._current_document.id == "candidate"
        assert window._current_solution.levelID == "candidate"
        assert "hard · return_loop · seed 41 · score 88.25" == (
            window._puzzle_analysis_panel._imported_summary.text()
        )
        assert "measured revisit dependency" in (
            window._puzzle_analysis_panel._imported_factors.item(0).text()
        )
    finally:
        window.close()


def test_save_draft_keeps_level_solution_and_quality_together(
    qapplication: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = LevelEditorMainWindow()
    target = tmp_path / "drafts" / "candidate.json"
    window._current_candidate_quality = {"levelID": "candidate", "quality": {}}
    window._document_controller.open(_document(), _solution(), saved=False)
    monkeypatch.setattr(main_window_module, "get_default_drafts_directory", lambda: tmp_path / "drafts")
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(target), ""),
    )
    try:
        assert window._save_draft()
        assert target.exists()
        assert (tmp_path / "drafts" / "candidate.solution.json").exists()
        assert (tmp_path / "drafts" / "candidate.quality.json").exists()
    finally:
        window.close()


def test_save_draft_cannot_bypass_production_promotion(
    qapplication: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = LevelEditorMainWindow()
    production_dir = tmp_path / "production"
    production_dir.mkdir()
    target = production_dir / "level_012.json"
    window._document_controller.open(_document(), _solution(), saved=False)
    monkeypatch.setattr(main_window_module, "get_default_drafts_directory", lambda: tmp_path / "drafts")
    monkeypatch.setattr(window, "_resolve_default_levels_dir", lambda: production_dir)
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(target), ""),
    )
    try:
        assert window._save_draft() is False
        assert not target.exists()
    finally:
        window._document_controller.mark_saved()
        window.close()


def test_alignment_and_distribution_are_single_undoable_edits(
    qapplication: QApplication,
) -> None:
    window = LevelEditorMainWindow()
    document = _document()
    window._document_controller.open(document, _solution(), saved=True)
    scene = window._canvas_view.scene()
    try:
        scene.select_nodes_by_ids({"a", "b", "c"})
        window._arrange_selected_nodes("horizontal")
        assert {node.id: node.x for node in document.graph.nodes} == {
            "a": 0.0,
            "b": 3.0,
            "c": 6.0,
        }
        assert window._document_controller.undo_stack.count() == 1

        window._document_controller.undo_stack.undo()
        assert {node.id: node.x for node in document.graph.nodes} == {
            "a": 0.0,
            "b": 1.0,
            "c": 6.0,
        }
    finally:
        window.close()


def test_arrow_keys_request_normal_and_larger_nudges(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    scene.display_level(_document())
    scene.select_nodes_by_ids({"a", "b"})
    requested: list[tuple[float, float]] = []
    scene.nudge_selected_requested.connect(lambda dx, dy: requested.append((dx, dy)))

    scene.keyPressEvent(QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_Right,
        Qt.KeyboardModifier.NoModifier,
    ))
    scene.keyPressEvent(QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_Up,
        Qt.KeyboardModifier.ShiftModifier,
    ))

    assert requested == [(0.05, 0.0), (0.0, 0.25)]


def test_select_mode_supports_shift_multi_select_and_marquee(
    qapplication: QApplication,
) -> None:
    view = LevelCanvasView()
    view.resize(800, 600)
    view.scene().display_level(_document())
    view.show()
    qapplication.processEvents()
    try:
        assert view.dragMode() == QGraphicsView.DragMode.RubberBandDrag
        first = view.scene()._node_items_by_id["a"]
        second = view.scene()._node_items_by_id["b"]
        QTest.mouseClick(
            view.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            view.mapFromScene(first.pos()),
        )
        QTest.mouseClick(
            view.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ShiftModifier,
            view.mapFromScene(second.pos()),
        )
        assert {item.node_id for item in view.scene().selectedItems()} == {"a", "b"}
    finally:
        view.close()
