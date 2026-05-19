import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QFileDialog
except ImportError as exc:
    pytest.skip(f"PySide6 unavailable in this environment: {exc}", allow_module_level=True)

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.main_window import LevelEditorMainWindow
from app.models import LevelDocument, RouteGraphModel
from app.ui import LevelCanvasScene, LevelCanvasView


@pytest.fixture
def qapplication() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_level_canvas_scene_has_empty_state_message(qapplication: QApplication) -> None:
    scene = LevelCanvasScene()
    text_items = [item.text() for item in scene.items() if hasattr(item, "text")]

    assert "Open a level to begin" in text_items


def test_main_window_uses_canvas_view_as_central_widget(qapplication: QApplication) -> None:
    window = LevelEditorMainWindow()
    try:
        assert isinstance(window.centralWidget(), LevelCanvasView)
    finally:
        window.close()


def test_level_canvas_view_starts_centered_on_origin(qapplication: QApplication) -> None:
    view = LevelCanvasView()
    try:
        view.resize(800, 600)
        view.show()
        qapplication.processEvents()

        center_point = view.mapToScene(view.viewport().rect().center())
        assert abs(center_point.x()) < 10
        assert abs(center_point.y()) < 10
    finally:
        view.close()


def test_open_level_still_loads_document_with_canvas_central_widget(
    qapplication: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = LevelEditorMainWindow()
    document = LevelDocument(
        id="level_123",
        name="Sample Level",
        graph=RouteGraphModel(),
        startNodeID="start",
        packageNodeID="package",
        destinationNodeID="destination",
        timeLimitSeconds=60,
        parTaps=3,
    )

    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: ("/tmp/level_123.json", ""))
    monkeypatch.setattr(window._repository, "load_level", lambda path: document)

    try:
        window._open_level()
        assert window.windowTitle() == "Tiny Routes Level Editor — level_123"
    finally:
        window.close()
