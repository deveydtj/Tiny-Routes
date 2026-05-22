from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import QDockWidget, QFileDialog, QMainWindow, QMessageBox, QToolBar

from app.config import find_repo_root, get_default_levels_directory
from app.models import LevelDocument, RouteEdgeModel, RouteNodeModel, SolutionModel
from app.repositories import (
    LevelFileRepository,
    LevelFileRepositoryError,
    MissingSolutionFileError,
    SolutionFileRepository,
    SolutionFileRepositoryError,
)
from app.services import (
    LevelValidationService,
    SolutionValidationService,
    TestRunnerService,
    ValidationMessage,
    ValidationResult,
    ValidationSeverity,
    create_default_level_document,
)
from app.ui import LevelCanvasView, PiecePalette, PropertiesPanel, SolutionPanel, ValidationPanel


class LevelEditorMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(1024, 768)

        self._current_document: LevelDocument | None = None
        self._current_solution: SolutionModel | None = None
        self._current_file_path: Path | None = None
        self._is_dirty = False
        self._repository = LevelFileRepository()
        self._solution_repository = SolutionFileRepository()
        self._validation_service = LevelValidationService()
        self._solution_validation_service = SolutionValidationService()
        self._test_runner_service = TestRunnerService(self._resolve_repo_root())
        self._canvas_view = LevelCanvasView()
        self._piece_palette = PiecePalette()
        self._properties_panel = PropertiesPanel()
        self._solution_panel = SolutionPanel()
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

        self._solution_dock = QDockWidget("Solution", self)
        self._solution_dock.setWidget(self._solution_panel)
        self._solution_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable,
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._solution_dock)

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
        scene.placement_message_changed.connect(self.statusBar().showMessage)
        self._validation_panel.validate_requested.connect(self._validate_current_level)
        self._validation_panel.validation_message_activated.connect(
            self._focus_validation_message
        )
        self._piece_palette.node_type_activated.connect(self._add_node_from_palette)
        self._solution_panel.solution_changed.connect(self._on_solution_changed)

        self._build_menu_bar()
        self._build_main_toolbar()
        self._update_window_title()

    def _build_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        self._file_menu = menu_bar.addMenu("File")

        new_action = self._file_menu.addAction("New Level")
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_level)

        open_action = self._file_menu.addAction("Open Level...")
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_level)

        save_action = self._file_menu.addAction("Save Level")
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_level)

        save_as_action = self._file_menu.addAction("Save Level As...")
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._save_level_as)

        self._view_menu = menu_bar.addMenu("View")

        fit_view_action = self._view_menu.addAction("Fit View")
        fit_view_action.triggered.connect(self._canvas_view.fit_level_to_view)

        reset_zoom_action = self._view_menu.addAction("Reset Zoom")
        reset_zoom_action.triggered.connect(self._canvas_view.reset_zoom)

        self._tools_menu = menu_bar.addMenu("Tools")

        validate_action = self._tools_menu.addAction("Validate")
        validate_action.setToolTip("Validate Level + Solution References")
        validate_action.triggered.connect(self._validate_current_level)

        self._run_tests_menu_action = self._tools_menu.addAction("Run Tests")
        self._run_tests_menu_action.setToolTip("Run Swift Solvability Tests")
        self._run_tests_menu_action.triggered.connect(self._run_level_tests)
        self._run_tests_menu_action.setEnabled(False)

    def _build_main_toolbar(self) -> None:
        self._main_toolbar = QToolBar("Main Toolbar", self)
        self._main_toolbar.setObjectName("mainToolbar")
        self.addToolBar(self._main_toolbar)

        new_action = QAction("New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_level)
        self._main_toolbar.addAction(new_action)

        open_action = QAction("Open", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_level)
        self._main_toolbar.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_level)
        self._main_toolbar.addAction(save_action)

        self._main_toolbar.addSeparator()

        validate_action = QAction("Validate", self)
        validate_action.setToolTip("Validate Level + Solution References")
        validate_action.triggered.connect(self._validate_current_level)
        self._main_toolbar.addAction(validate_action)

        fit_view_action = QAction("Fit View", self)
        fit_view_action.triggered.connect(self._canvas_view.fit_level_to_view)
        self._main_toolbar.addAction(fit_view_action)

        reset_zoom_action = QAction("Reset Zoom", self)
        reset_zoom_action.triggered.connect(self._canvas_view.reset_zoom)
        self._main_toolbar.addAction(reset_zoom_action)

        self._main_toolbar.addSeparator()

        self._run_tests_action = QAction("Run Tests", self)
        self._run_tests_action.setToolTip("Run Swift Solvability Tests")
        self._run_tests_action.triggered.connect(self._run_level_tests)
        self._run_tests_action.setEnabled(False)
        self._main_toolbar.addAction(self._run_tests_action)

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
        self._current_solution = self._load_solution_for_level(self._current_file_path, document)
        self._canvas_view.scene().display_level(document)
        self._properties_panel.clear()
        self._solution_panel.set_solution(self._current_solution)
        self._validation_panel.clear()
        self._update_run_tests_action_states()
        self._set_dirty(False)

    def _new_level(self) -> None:
        if not self._prompt_to_save_unsaved_changes():
            return

        self._current_document = create_default_level_document()
        self._current_file_path = None
        self._current_solution = self._build_default_solution(self._current_document)
        self._canvas_view.scene().display_level(self._current_document)
        self._properties_panel.clear()
        self._solution_panel.set_solution(self._current_solution)
        self._validation_panel.clear()
        self._update_run_tests_action_states()
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

        if self._current_solution is not None:
            solution_path = self._solution_repository.find_solution_path(self._current_file_path)
            try:
                self._solution_repository.save_solution(solution_path, self._current_solution)
            except SolutionFileRepositoryError as exc:
                QMessageBox.critical(self, "Failed to Save Solution", exc.message)
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

        level_result = self._validation_service.validate(self._current_document)
        solution_result = self._solution_validation_service.validate(
            self._current_document,
            self._current_solution,
        )
        combined_result = ValidationResult(
            messages=[*level_result.messages, *solution_result.messages]
        )
        self._validation_panel.show_result(combined_result)

    def _run_level_tests(self) -> None:
        if self._current_document is None:
            self._validation_panel.clear()
            return

        if not self._prompt_to_save_unsaved_changes():
            return

        result = self._test_runner_service.run_tests()
        detail = self._summarize_test_runner_output(result.stdout, result.stderr)
        message_text = result.summary if not detail else f"{result.summary}\n\n{detail}"
        severity = ValidationSeverity.INFO if result.passed else ValidationSeverity.ERROR
        validation_result = ValidationResult(
            messages=[
                ValidationMessage(
                    severity=severity,
                    code="swift_tests_passed" if result.passed else "swift_tests_failed",
                    message=message_text,
                )
            ]
        )
        self._validation_panel.show_result(validation_result)

    def _focus_validation_message(self, message: object) -> None:
        scene = self._canvas_view.scene()
        related_node_id = getattr(message, "related_node_id", None)
        related_edge_id = getattr(message, "related_edge_id", None)

        if isinstance(related_node_id, str) and related_node_id:
            if scene.select_node_by_id(related_node_id):
                self._canvas_view.center_on_selected_item()
                self.statusBar().showMessage(f"Selected node '{related_node_id}'.")
                return

        if isinstance(related_edge_id, str) and related_edge_id:
            if scene.select_edge_by_id(related_edge_id):
                self._canvas_view.center_on_selected_item()
                self.statusBar().showMessage(f"Selected edge '{related_edge_id}'.")
                return

        self.statusBar().showMessage("Related validation item was not found on the canvas.")

    def _resolve_default_levels_dir(self) -> Path:
        try:
            return get_default_levels_directory()
        except FileNotFoundError:
            return Path.home()

    def _resolve_repo_root(self) -> Path:
        try:
            return find_repo_root()
        except FileNotFoundError:
            return Path.cwd()

    def _mark_document_dirty(self) -> None:
        if self._current_document is None:
            return
        self._set_dirty(True)

    def _on_solution_changed(self, updated_solution: SolutionModel) -> None:
        if self._current_document is None:
            return

        # Load-time normalization would hide bad sidecar metadata from Validate.
        # Edit-time normalization is intentional: once the designer changes the
        # solution in this editor, the sidecar belongs to the open level and
        # maxTaps tracks the scripted tap count.
        updated_solution.levelID = self._current_document.id
        updated_solution.maxTaps = len(updated_solution.actions)
        self._current_solution = updated_solution
        self._validation_panel.clear()
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

    def _on_edge_creation_requested(
        self,
        edge_id: str,
        from_node_id: str,
        to_node_id: str,
        road_shape: str,
    ) -> None:
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
                roadShape=road_shape,
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

    def _build_default_solution(
        self,
        document: LevelDocument,
        *,
        is_placeholder: bool = False,
    ) -> SolutionModel:
        return SolutionModel(
            levelID=document.id,
            description=f"Solution for {document.name}",
            expectedOutcome="completed",
            maxTaps=0,
            requiresWithinTimeLimit=True,
            actions=[],
            isPlaceholder=is_placeholder or None,
        )

    def _load_solution_for_level(self, level_path: Path, document: LevelDocument) -> SolutionModel:
        solution_path = self._solution_repository.find_solution_path(level_path)
        try:
            solution = self._solution_repository.load_solution(solution_path)
        except MissingSolutionFileError:
            return self._build_default_solution(document, is_placeholder=True)
        except SolutionFileRepositoryError as exc:
            QMessageBox.warning(
                self,
                "Failed to Load Solution",
                f"{exc.message}\n\nA blank solution will be used until the file is saved.",
            )
            return self._build_default_solution(document, is_placeholder=True)

        if solution.description is None:
            solution.description = f"Solution for {document.name}"
        return solution

    def _update_window_title(self) -> None:
        base_title = "Tiny Routes Level Editor"
        if self._current_document is None:
            self.setWindowTitle(base_title)
            return
        dirty_suffix = " *" if self._is_dirty else ""
        self.setWindowTitle(f"{base_title} — {self._current_document.id}{dirty_suffix}")

    def _update_run_tests_action_states(self) -> None:
        is_enabled = self._current_document is not None
        for action_name in ("_run_tests_menu_action", "_run_tests_action"):
            action = getattr(self, action_name, None)
            if action is not None:
                action.setEnabled(is_enabled)

    @staticmethod
    def _summarize_test_runner_output(stdout: str, stderr: str) -> str:
        combined_lines = [
            line.strip()
            for line in [*stdout.splitlines(), *stderr.splitlines()]
            if line.strip()
        ]
        if not combined_lines:
            return ""

        tail = combined_lines[-12:]
        return "\n".join(tail)

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
