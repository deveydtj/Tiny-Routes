from pathlib import Path

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from app.config import get_default_levels_directory
from app.models import LevelDocument
from app.repositories import LevelFileRepository, LevelFileRepositoryError
from app.ui import LevelCanvasView


class LevelEditorMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Tiny Routes Level Editor")
        self.resize(1024, 768)

        self._current_document: LevelDocument | None = None
        self._repository = LevelFileRepository()
        self._canvas_view = LevelCanvasView()

        self.setCentralWidget(self._canvas_view)

        self._build_menu_bar()

    def _build_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        open_action = file_menu.addAction("Open Level...")
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_level)

    def _open_level(self) -> None:
        levels_dir = self._resolve_default_levels_dir()

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Level",
            str(levels_dir),
            "Level JSON Files (*.json);;All Files (*)",
        )

        if not file_path:
            return

        try:
            document = self._repository.load_level(Path(file_path))
        except LevelFileRepositoryError as exc:
            QMessageBox.critical(self, "Failed to Open Level", exc.message)
            return

        self._current_document = document
        self._canvas_view.scene().display_level(document)
        self.setWindowTitle(f"Tiny Routes Level Editor — {document.id}")

    def _resolve_default_levels_dir(self) -> Path:
        try:
            return get_default_levels_directory()
        except FileNotFoundError:
            return Path.home()
