from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QKeySequence
from PySide6.QtWidgets import QDockWidget, QFileDialog, QMainWindow, QMessageBox

from app.config import get_default_levels_directory
from app.models import LevelDocument, RouteEdgeModel, RouteNodeModel
from app.repositories import LevelFileRepository, LevelFileRepositoryError
from app.services import LevelValidationService, create_default_level_document
from app.ui import LevelCanvasView, PiecePalette, PropertiesPanel, ValidationPanel


class LevelEditorMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(1024, 768)

        self._current_document: LevelDocument | None = None
        self._current_file_path: Path | None = None
        self._is_dirty = False
        self._repository = LevelFileRepository()
        self._validation_service = LevelValidationService()
        self._canvas_view = LevelCanvasView()
        self._piece_palette = PiecePalette()
        self._properties_panel = PropertiesPanel()
        self._validation_panel = ValidationPanel()

        self.setCentralWidget(self._canvas_view)

        # Add a dockable properties panel on the right side
        self._properties_dock = QDockWidget("Properties", self)
        self._properties_dock.setWidget(self._properties_panel)
        self._properties_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable,
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._properties_dock)

        self._validation_dock = QDockWidget("Validation", self)
        self._validation_dock.setWidget(self._validation_panel)
        self._validation_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable,
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._validation_dock)

        self._palette_dock = QDockWidget("Palette", self)
        self._palette_dock.setWidget(self._piece_palette)
        self._palette_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable,
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._palette_dock)

        # Wire canvas scene selection signals to the properties panel
        scene = self._canvas_view.scene()
        scene.node_item_selected.connect(self._properties_panel.show_node)
        scene.edge_item_selected.connect(self._properties_panel.show_edge)
        scene.selection_cleared.connect(self._properties_panel.clear)
        scene.node_item_moved.connect(self._on_node_item_moved)
        scene.edge_creation_requested.connect(self._on_edge_creation_requested)
        scene.level_items_deleted.connect(self._on_level_items_deleted)
        self._validation_panel.validate_requested.connect(self._validate_current_level)
        self._piece_palette.node_type_activated.connect(self._add_node_from_palette)

        self._build_menu_bar()
        self._update_window_title()

    def _build_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        new_action = file_menu.addAction("New Level")
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_level)

        open_action = file_menu.addAction("Open Level...")
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_level)

        save_action = file_menu.addAction("Save Level")
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_level)

        save_as_action = file_menu.addAction("Save Level As...")
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._save_level_as)

    def _open_level(self) -> None:
        if not self._prompt_to_save_unsaved_changes():
            return

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
        self._current_file_path = Path(file_path)
        self._canvas_view.scene().display_level(document)
        self._properties_panel.clear()
        self._validation_panel.clear()
        self._set_dirty(False)

    def _new_level(self) -> None:
        if not self._prompt_to_save_unsaved_changes():
            return

        self._current_document = create_default_level_document()
        self._current_file_path = None
        self._canvas_view.scene().display_level(self._current_document)
        self._properties_panel.clear()
        self._validation_panel.clear()
        self._set_dirty(True)

    def _save_level(self) -> bool:
        if self._current_document is None:
            return False

        if self._current_file_path is None:
            return self._save_level_as()

        try:
            self._repository.save_level(self._current_file_path, self._current_document)
        except LevelFileRepositoryError as exc:
            QMessageBox.critical(self, "Failed to Save Level", exc.message)
            return False

        self._set_dirty(False)
        return True

    def _save_level_as(self) -> bool:
        if self._current_document is None:
            return False

        initial_path = self._current_file_path
        if initial_path is None:
            initial_path = self._resolve_default_levels_dir() / f"{self._current_document.id}.json"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Level As",
            str(initial_path),
            "Level JSON Files (*.json);;All Files (*)",
        )

        if not file_path:
            return False

        self._current_file_path = Path(file_path)
        return self._save_level()

    def _validate_current_level(self) -> None:
        if self._current_document is None:
            self._validation_panel.clear()
            return

        result = self._validation_service.validate(self._current_document)
        self._validation_panel.show_result(result)

    def _resolve_default_levels_dir(self) -> Path:
        try:
            return get_default_levels_directory()
        except FileNotFoundError:
            return Path.home()

    def _mark_document_dirty(self) -> None:
        if self._current_document is None:
            return
        self._set_dirty(True)

    def _on_node_item_moved(self, node_id: str, model_x: float, model_y: float) -> None:
        if self._current_document is None:
            return

        for node in self._current_document.graph.nodes:
            if node.id != node_id:
                continue
            if node.x == model_x and node.y == model_y:
                return
            node.x = model_x
            node.y = model_y
            self._validation_panel.clear()
            self._set_dirty(True)
            return

    def _add_node_from_palette(self, node_type: str) -> None:
        if self._current_document is None:
            return

        node_id = self._generate_unique_default_node_id(node_type)
        center_scene_position = self._canvas_view.mapToScene(
            self._canvas_view.viewport().rect().center()
        )
        model_x, model_y = self._canvas_view.scene().scene_to_model_coordinates(center_scene_position)
        new_node = RouteNodeModel(
            id=node_id,
            x=model_x,
            y=model_y,
            outgoingEdgeIDs=[],
        )

        self._current_document.graph.nodes.append(new_node)
        if node_type == "start":
            self._current_document.startNodeID = node_id
        elif node_type == "package":
            self._current_document.packageNodeID = node_id
        elif node_type == "destination":
            self._current_document.destinationNodeID = node_id

        self._canvas_view.scene().display_level(self._current_document)
        self._properties_panel.clear()
        self._validation_panel.clear()
        self._set_dirty(True)

    def _on_edge_creation_requested(self, edge_id: str, from_node_id: str, to_node_id: str) -> None:
        if self._current_document is None:
            return

        if any(edge.id == edge_id for edge in self._current_document.graph.edges):
            return

        source_node = next(
            (node for node in self._current_document.graph.nodes if node.id == from_node_id),
            None,
        )
        if source_node is None:
            return

        source_node.outgoingEdgeIDs.append(edge_id)
        self._current_document.graph.edges.append(
            RouteEdgeModel(
                id=edge_id,
                fromNodeID=from_node_id,
                toNodeID=to_node_id,
            )
        )

        self._canvas_view.scene().display_level(self._current_document)
        self._validation_panel.clear()
        self._set_dirty(True)

    def _on_level_items_deleted(self) -> None:
        if self._current_document is None:
            return
        self._validation_panel.clear()
        self._set_dirty(True)

    def _generate_unique_default_node_id(self, node_type: str) -> str:
        if self._current_document is None:
            return "node"

        base_id_lookup = {
            "start": "start",
            "route": "node",
            "switch": "switch",
            "package": "package",
            "destination": "destination",
        }
        base_id = base_id_lookup.get(node_type, "node")
        existing_node_ids = {node.id for node in self._current_document.graph.nodes}

        if base_id not in existing_node_ids:
            return base_id

        suffix = 1
        while f"{base_id}_{suffix}" in existing_node_ids:
            suffix += 1
        return f"{base_id}_{suffix}"

    def _set_dirty(self, is_dirty: bool) -> None:
        self._is_dirty = is_dirty
        self._update_window_title()

    def _update_window_title(self) -> None:
        base_title = "Tiny Routes Level Editor"
        if self._current_document is None:
            self.setWindowTitle(base_title)
            return
        dirty_suffix = " *" if self._is_dirty else ""
        self.setWindowTitle(f"{base_title} — {self._current_document.id}{dirty_suffix}")

    def _prompt_to_save_unsaved_changes(self) -> bool:
        if not self._is_dirty or self._current_document is None:
            return True

        selection = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved changes. Save before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

        if selection == QMessageBox.StandardButton.Cancel:
            return False
        if selection == QMessageBox.StandardButton.Save:
            return self._save_level()
        return True

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if not self._prompt_to_save_unsaved_changes():
            event.ignore()
            return
        event.accept()
