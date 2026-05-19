from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QDockWidget, QFileDialog, QMainWindow, QMessageBox

from app.config import get_default_levels_directory
from app.models import LevelDocument
from app.repositories import LevelFileRepository, LevelFileRepositoryError
from app.ui import LevelCanvasView, PropertiesPanel


class LevelEditorMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Tiny Routes Level Editor")
        self.resize(1024, 768)

        self._current_document: LevelDocument | None = None
        self._repository = LevelFileRepository()
        self._canvas_view = LevelCanvasView()
        self._properties_panel = PropertiesPanel()

        self.setCentralWidget(self._canvas_view)

        # Add a dockable properties panel on the right side
        self._properties_dock = QDockWidget("Properties", self)
        self._properties_dock.setWidget(self._properties_panel)
        self._properties_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable,
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._properties_dock)

        # Wire canvas scene selection signals to the properties panel
        scene = self._canvas_view.scene()
        scene.node_item_selected.connect(self._properties_panel.show_node)
        scene.edge_item_selected.connect(self._properties_panel.show_edge)
        scene.selection_cleared.connect(self._properties_panel.clear)

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
        self._properties_panel.clear()
        self.setWindowTitle(f"Tiny Routes Level Editor — {document.id}")

    def _resolve_default_levels_dir(self) -> Path:
        try:
            return get_default_levels_directory()
        except FileNotFoundError:
            return Path.home()
