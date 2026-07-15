from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.main_window import LevelEditorMainWindow
from app.models import (
    LevelDocument,
    RouteGraphModel,
    RouteNodeModel,
    SolutionActionModel,
    SolutionModel,
)
from app.services import AutosaveRecoveryError, AutosaveRecoveryService


@pytest.fixture
def qapplication() -> QApplication:
    return QApplication.instance() or QApplication([])


def _document(name: str = "Recovery Level") -> LevelDocument:
    return LevelDocument(
        id="recovery_level",
        name=name,
        graph=RouteGraphModel(
            nodes=[RouteNodeModel(id="start", x=0.0, y=0.0)]
        ),
        startNodeID="start",
        packageNodeID="start",
        destinationNodeID="start",
        timeLimitSeconds=30,
        parTaps=0,
    )


def _solution() -> SolutionModel:
    return SolutionModel(
        levelID="recovery_level",
        description="Recovered solution",
        expectedOutcome="completed",
        maxTaps=1,
        requiresWithinTimeLimit=True,
        actions=[SolutionActionModel(timeSeconds=0.5, tapNodeID="start")],
    )


def test_recovery_round_trip_keeps_source_file_untouched(tmp_path: Path) -> None:
    source_path = tmp_path / "source.json"
    source_path.write_text("original source contents\n", encoding="utf-8")
    recovery_path = tmp_path / "state" / "recovery.json"
    service = AutosaveRecoveryService(recovery_path)

    service.write(
        _document(),
        _solution(),
        source_path=source_path,
        candidate_quality={"score": 42},
    )
    recovered = service.load()

    assert source_path.read_text(encoding="utf-8") == "original source contents\n"
    assert recovery_path.is_file()
    assert recovered.document == _document()
    assert recovered.solution == _solution()
    assert recovered.source_path == source_path
    assert recovered.candidate_quality == {"score": 42}


def test_recovery_refuses_to_use_source_path_as_recovery_path(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.json"
    service = AutosaveRecoveryService(source_path)

    with pytest.raises(AutosaveRecoveryError, match="cannot overwrite"):
        service.write(_document(), None, source_path=source_path)


def test_successful_save_deletes_recovery_bundle(
    qapplication: QApplication,
    tmp_path: Path,
) -> None:
    window = LevelEditorMainWindow()
    recovery_service = AutosaveRecoveryService(tmp_path / "recovery.json")
    source_path = tmp_path / "draft.json"
    try:
        window._autosave_recovery_service = recovery_service
        window._current_file_path = source_path
        window._document_controller.open(_document(), _solution(), saved=False)
        window._write_autosave_recovery()
        assert recovery_service.exists()

        assert window._save_level() is True

        assert source_path.is_file()
        assert not recovery_service.exists()
        assert window._is_dirty is False
    finally:
        window._set_dirty(False)
        window.close()


def test_startup_offer_restores_dirty_document_and_keeps_snapshot_until_save(
    qapplication: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AutosaveRecoveryService(tmp_path / "recovery.json")
    source_path = tmp_path / "original.json"
    service.write(_document("Recovered Name"), _solution(), source_path=source_path)
    window = LevelEditorMainWindow()
    try:
        window._autosave_recovery_service = service
        monkeypatch.setattr(window, "_ask_recovery_action", lambda saved_at: "recover")

        assert window.offer_recovery_if_available() is True

        assert window._current_document is not None
        assert window._current_document.name == "Recovered Name"
        assert window._current_solution == _solution()
        assert window._current_file_path == source_path
        assert window._is_dirty is True
        assert service.exists()
    finally:
        window._set_dirty(False)
        window.close()


def test_discarding_recovery_deletes_snapshot(
    qapplication: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AutosaveRecoveryService(tmp_path / "recovery.json")
    service.write(_document(), None, source_path=None)
    window = LevelEditorMainWindow()
    try:
        window._autosave_recovery_service = service
        monkeypatch.setattr(window, "_ask_recovery_action", lambda saved_at: "discard")

        assert window.offer_recovery_if_available() is False
        assert window._current_document is None
        assert not service.exists()
    finally:
        window.close()
