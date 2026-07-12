import math
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
)

from app.config import find_repo_root, get_default_levels_directory
from app.controllers import DocumentController
from app.models import EditorTool, LevelDocument, RouteEdgeModel, RouteNodeModel, SolutionModel
from app.repositories import (
    LevelFileRepository,
    LevelFileRepositoryError,
    MissingSolutionFileError,
    SolutionFileRepository,
    SolutionFileRepositoryError,
)
from app.services import (
    LevelIdentity,
    LevelIdentityService,
    LevelValidationService,
    SolutionValidationService,
    SwitchClassificationService,
    TestRunnerService,
    ValidationMessage,
    ValidationResult,
    ValidationSeverity,
    create_default_level_document,
)
from app.ui import (
    LevelCanvasView,
    LevelMetadataDialog,
    LevelMetadataResult,
    PiecePalette,
    PropertiesPanel,
    SolutionPanel,
    ValidationPanel,
)
from app.ui.window_builders import build_main_toolbar, build_menu_bar, build_tools_toolbar


class LevelEditorMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.resize(1024, 768)

        self._current_document: LevelDocument | None = None
        self._current_solution: SolutionModel | None = None
        self._current_file_path: Path | None = None
        self._is_dirty = False
        self._active_tool = EditorTool.SELECT
        self._repository = LevelFileRepository()
        self._solution_repository = SolutionFileRepository()
        self._identity_service = LevelIdentityService()
        self._validation_service = LevelValidationService()
        self._solution_validation_service = SolutionValidationService()
        self._switch_classification_service = SwitchClassificationService()
        self._test_runner_service = TestRunnerService(self._resolve_repo_root())
        self._canvas_view = LevelCanvasView()
        self._piece_palette = PiecePalette()
        self._properties_panel = PropertiesPanel()
        self._solution_panel = SolutionPanel()
        self._validation_panel = ValidationPanel()
        self._document_controller = DocumentController(self)
        self._document_controller.document_changed.connect(self._on_controller_document_changed)
        self._document_controller.dirty_changed.connect(self._set_dirty)

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
        scene.node_item_selected.connect(self._on_node_item_selected)
        scene.edge_item_selected.connect(self._properties_panel.show_edge)
        scene.selection_cleared.connect(self._properties_panel.clear)
        scene.node_item_moved.connect(self._on_node_item_moved)
        scene.edge_creation_requested.connect(self._on_edge_creation_requested)
        scene.node_placement_requested.connect(self._place_node_at)
        scene.set_delete_items_handler(self._delete_items_with_controller)
        scene.placement_message_changed.connect(self.statusBar().showMessage)
        self._validation_panel.validate_requested.connect(self._validate_current_level)
        self._validation_panel.validation_message_activated.connect(
            self._focus_validation_message
        )
        self._piece_palette.node_type_activated.connect(self._add_node_from_palette)
        self._properties_panel.outgoing_edge_order_changed.connect(
            self._on_outgoing_edge_order_changed
        )
        self._solution_panel.solution_changed.connect(self._on_solution_changed)

        self._build_menu_bar()
        self._build_main_toolbar()
        self._build_tools_toolbar()
        scene.road_shape_changed.connect(self._sync_road_shape_actions)
        self._set_active_tool(EditorTool.SELECT)
        self._update_window_title()

    @property
    def active_tool(self) -> EditorTool:
        return self._active_tool

    def _build_menu_bar(self) -> None:
        build_menu_bar(self)

    def _build_main_toolbar(self) -> None:
        build_main_toolbar(self)

    def _build_tools_toolbar(self) -> None:
        build_tools_toolbar(self)

    def _set_active_tool(self, tool: EditorTool) -> None:
        self._active_tool = tool
        self._tool_actions[tool].setChecked(True)
        self._canvas_view.set_editor_tool(tool)
        editing_enabled = tool is not EditorTool.PLAYTEST
        self._piece_palette.setEnabled(editing_enabled)
        self._properties_panel.setEnabled(editing_enabled)
        for action in getattr(self, "_road_shape_actions", {}).values():
            action.setEnabled(tool is EditorTool.CONNECT)
        self.statusBar().showMessage(tool.status_message)

    def _set_grid_snapping_enabled(self, enabled: bool) -> None:
        self._canvas_view.scene().set_grid_snapping(enabled, self._grid_size_spinbox.value())

    def _set_grid_size(self, spacing: float) -> None:
        self._canvas_view.scene().set_grid_snapping(
            self._snap_toggle_action.isChecked(), spacing
        )

    def _set_pending_road_shape(self, road_shape: str) -> None:
        self._canvas_view.scene().set_pending_road_shape(road_shape)
        self.statusBar().showMessage(
            f"Road bends set to {'Vertical First' if road_shape == 'verticalFirst' else 'Horizontal First'}."
        )

    def _sync_road_shape_actions(self, road_shape: str) -> None:
        action = self._road_shape_actions.get(road_shape)
        if action is not None:
            action.setChecked(True)

    def _snap_selected_to_grid(self) -> None:
        moved = self._canvas_view.scene().snap_selected_to_grid()
        self.statusBar().showMessage(
            f"Snapped {moved} selected node{'s' if moved != 1 else ''} to the grid."
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            if self._active_tool is EditorTool.SELECT:
                self._canvas_view.scene().cancel_current_operation()
            else:
                self._set_active_tool(EditorTool.SELECT)
            event.accept()
            return
        super().keyPressEvent(event)

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

        self._current_file_path = Path(file_path)
        solution = self._load_solution_for_level(self._current_file_path, document)
        self._document_controller.open(document, solution, saved=True)
        self._properties_panel.clear()
        self._solution_panel.set_level(self._current_document)
        self._solution_panel.set_solution(self._current_solution)
        self._validation_panel.clear()
        self._update_run_tests_action_states()

    def _new_level(self) -> None:
        if not self._prompt_to_save_unsaved_changes():
            return

        document = create_default_level_document()
        self._current_file_path = None
        solution = self._build_default_solution(document)
        self._document_controller.open(document, solution, saved=False)
        self._properties_panel.clear()
        self._solution_panel.set_level(self._current_document)
        self._solution_panel.set_solution(self._current_solution)
        self._validation_panel.clear()
        self._update_run_tests_action_states()

    def _save_level(self) -> bool:
        if self._current_document is None:
            return False

        if self._current_file_path is None:
            return self._save_level_as()

        if not self._can_save_current_path():
            return False

        try:
            self._repository.save_level(self._current_file_path, self._current_document)
        except LevelFileRepositoryError as exc:
            QMessageBox.critical(self, "Failed to Save Level", exc.message)
            return False

        if self._current_solution is not None:
            solution_path = self._solution_path_for_current_save()
            try:
                self._solution_repository.save_solution(solution_path, self._current_solution)
            except SolutionFileRepositoryError as exc:
                QMessageBox.critical(self, "Failed to Save Solution", exc.message)
                return False

        self._document_controller.mark_saved()
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

        selected_path = Path(file_path)
        previous_path = self._current_file_path

        production_number = self._identity_service.try_parse_number_from_level_filename(
            selected_path
        )
        if production_number is not None:
            identity = self._identity_service.build_from_number(production_number)
            target_path = selected_path.with_name(identity.level_filename)
            target_solution_path = self._solution_repository.solution_path_for_level_id(
                identity.level_id
            )

            if selected_path.name != identity.level_filename:
                QMessageBox.information(
                    self,
                    "Production Filename Normalized",
                    (
                        "Tiny Routes production levels use three digits. This will "
                        f"be saved as {identity.level_filename} instead."
                    ),
                )

            if self._is_path_in_default_levels_dir(target_path):
                if not self._confirm_production_overwrite(target_path, target_solution_path):
                    return False

            self._ensure_controller_state()
            self._document_controller.edit_metadata(
                lambda document, solution: self._identity_service.apply_identity(
                    document, solution, identity
                )
            )
            self._current_file_path = target_path
            return self._save_level()

        if self._is_path_in_default_levels_dir(selected_path):
            QMessageBox.warning(
                self,
                "Production Filename Required",
                "Production levels must use a filename like level_021.json.",
            )
            self._current_file_path = previous_path
            return False

        self._current_file_path = selected_path
        return self._save_level()

    def _validate_current_level(self) -> None:
        if self._current_document is None:
            self._validation_panel.clear()
            return

        level_result = self._validation_service.validate(
            self._current_document,
            self._current_file_path,
        )
        solution_result = self._solution_validation_service.validate(
            self._current_document,
            self._current_solution,
            self._current_file_path,
        )
        messages = [*level_result.messages, *solution_result.messages]
        consistency_message = self._build_production_metadata_consistency_message(messages)
        if consistency_message is not None:
            messages.append(consistency_message)
        combined_result = ValidationResult(
            messages=messages
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

    def _edit_level_metadata(self) -> None:
        if self._current_document is None:
            return

        result = self._show_metadata_dialog(
            title="Edit Level Metadata",
            suggested_level_number=self._suggested_level_number_for_current_document(),
        )
        if result is None:
            return

        self._apply_metadata_result(result)

    def _promote_draft_to_production_level(self) -> None:
        if self._current_document is None:
            return

        result = self._show_metadata_dialog(
            title="Promote Draft to Production Level",
            suggested_level_number=self._suggested_level_number_for_current_document(),
        )
        if result is None:
            return

        target_level_path = self._level_path_for_identity(result.identity)
        target_solution_path = self._solution_repository.solution_path_for_level_id(
            result.identity.level_id
        )
        if not self._confirm_production_overwrite(target_level_path, target_solution_path):
            return

        self._apply_metadata_result(result)
        self._current_file_path = target_level_path
        self._update_window_title()

    def _repair_current_level_metadata(self) -> None:
        if self._current_document is None:
            return

        suggested_number = self._suggested_level_number_for_repair()
        result = self._show_metadata_dialog(
            title="Repair Current Level Metadata",
            suggested_level_number=suggested_number,
        )
        if result is None:
            return

        target_level_path = self._level_path_for_identity(result.identity)
        target_solution_path = self._solution_repository.solution_path_for_level_id(
            result.identity.level_id
        )
        if not self._confirm_production_overwrite(target_level_path, target_solution_path):
            return

        if not self._confirm_metadata_repair(result):
            return

        old_paths = self._old_paths_for_repair(target_level_path, target_solution_path)
        self._apply_metadata_result(result)
        self._current_file_path = target_level_path
        self._set_dirty(True)

        if not self._save_level():
            return

        if old_paths:
            old_path_list = "\n".join(str(path) for path in old_paths)
            QMessageBox.information(
                self,
                "Repair Complete",
                (
                    "Repaired files were saved to normalized production paths.\n\n"
                    "After verifying the new files, these old files can be deleted manually:\n"
                    f"{old_path_list}"
                ),
            )

    def _show_metadata_dialog(
        self,
        *,
        title: str,
        suggested_level_number: int,
    ) -> LevelMetadataResult | None:
        if self._current_document is None:
            return None

        dialog = LevelMetadataDialog(
            self._current_document,
            suggested_level_number=suggested_level_number,
            title=title,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.metadata_result()

    def _apply_metadata_result(self, result: LevelMetadataResult) -> None:
        if self._current_document is None:
            return
        self._ensure_controller_state()

        def mutation(document, solution):
            self._identity_service.apply_identity(document, solution, result.identity)
            document.name = result.level_name or result.identity.level_name
            document.timeLimitSeconds = result.timeLimitSeconds
            document.parTaps = result.parTaps

        self._document_controller.edit_metadata(mutation)

    def _suggested_level_number_for_current_document(self) -> int:
        if self._current_document is not None:
            parsed_document_number = self._identity_service.try_parse_number_from_level_id(
                self._current_document.id
            )
            if parsed_document_number is not None:
                return parsed_document_number

        if self._current_file_path is not None:
            parsed_file_number = self._identity_service.try_parse_number_from_level_filename(
                self._current_file_path
            )
            if parsed_file_number is not None:
                return parsed_file_number

        return self._find_next_available_level_number()

    def _suggested_level_number_for_repair(self) -> int:
        if self._current_file_path is not None:
            parsed_file_number = self._identity_service.try_parse_number_from_level_filename(
                self._current_file_path
            )
            if parsed_file_number is not None:
                return parsed_file_number
        return self._suggested_level_number_for_current_document()

    def _find_next_available_level_number(self) -> int:
        levels_dir = self._resolve_default_levels_dir()
        if not levels_dir.is_dir():
            return 1

        highest_level_number = 0
        for level_path in levels_dir.iterdir():
            if not level_path.is_file():
                continue
            if not self._is_strict_production_level_filename(level_path.name):
                continue
            level_number = self._identity_service.try_parse_number_from_level_filename(level_path)
            if level_number is not None:
                highest_level_number = max(highest_level_number, level_number)

        return highest_level_number + 1 if highest_level_number else 1

    def _level_path_for_identity(self, identity: LevelIdentity) -> Path:
        return self._resolve_default_levels_dir() / identity.level_filename

    def _solution_path_for_current_save(self) -> Path:
        if self._current_document is None or self._current_file_path is None:
            raise ValueError("No current level path is available.")

        if (
            self._is_path_in_default_levels_dir(self._current_file_path)
            and self._identity_service.is_padded_production_level_id(self._current_document.id)
            and self._current_file_path.name == f"{self._current_document.id}.json"
        ):
            return self._solution_repository.solution_path_for_level_id(
                self._current_document.id
            )

        return self._solution_repository.find_solution_path(self._current_file_path)

    def _confirm_production_overwrite(
        self,
        target_level_path: Path,
        target_solution_path: Path,
    ) -> bool:
        current_level_path = self._current_file_path
        if target_level_path.exists() and not self._same_path(
            target_level_path,
            current_level_path,
        ):
            selection = QMessageBox.question(
                self,
                "Overwrite Production Level?",
                f"The level file already exists:\n{target_level_path}\n\nOverwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if selection != QMessageBox.StandardButton.Yes:
                return False

        current_solution_path = (
            self._solution_repository.find_solution_path(current_level_path)
            if current_level_path is not None
            else None
        )
        if target_solution_path.exists() and not self._same_path(
            target_solution_path,
            current_solution_path,
        ):
            selection = QMessageBox.question(
                self,
                "Overwrite Production Solution?",
                (
                    "The solution sidecar already exists:\n"
                    f"{target_solution_path}\n\nOverwrite it?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if selection != QMessageBox.StandardButton.Yes:
                return False

        return True

    def _confirm_metadata_repair(self, result: LevelMetadataResult) -> bool:
        if self._current_document is None:
            return False

        current_solution_id = (
            self._current_solution.levelID if self._current_solution is not None else "(none)"
        )
        message = (
            "Repair current level metadata?\n\n"
            f"Current ID: {self._current_document.id}\n"
            f"Current Name: {self._current_document.name}\n"
            f"Current Solution levelID: {current_solution_id}\n\n"
            f"Repaired ID: {result.identity.level_id}\n"
            f"Repaired Name: {result.level_name or result.identity.level_name}\n"
            f"Repaired Solution levelID: {result.identity.level_id}"
        )
        selection = QMessageBox.question(
            self,
            "Repair Level Metadata",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return selection == QMessageBox.StandardButton.Yes

    def _old_paths_for_repair(
        self,
        target_level_path: Path,
        target_solution_path: Path,
    ) -> list[Path]:
        old_paths: list[Path] = []
        if self._current_file_path is not None and not self._same_path(
            self._current_file_path,
            target_level_path,
        ):
            old_paths.append(self._current_file_path)

            old_solution_path = self._solution_repository.find_solution_path(
                self._current_file_path
            )
            if not self._same_path(old_solution_path, target_solution_path):
                old_paths.append(old_solution_path)

        return old_paths

    def _build_production_metadata_consistency_message(
        self,
        existing_messages: list[ValidationMessage],
    ) -> ValidationMessage | None:
        if (
            self._current_document is None
            or self._current_solution is None
            or self._current_file_path is None
        ):
            return None
        if any(message.severity is ValidationSeverity.ERROR for message in existing_messages):
            return None

        level_number = self._identity_service.try_parse_number_from_level_filename(
            self._current_file_path
        )
        if level_number is None:
            return None

        identity = self._identity_service.build_from_number(level_number)
        if self._current_file_path.name != identity.level_filename:
            return None
        if self._current_document.id != identity.level_id:
            return None
        if self._current_solution.levelID != identity.level_id:
            return None

        return ValidationMessage(
            severity=ValidationSeverity.INFO,
            code="production_metadata_consistent",
            message=(
                "Production metadata is consistent: "
                f"{identity.level_filename}, id {identity.level_id}, "
                f"solution levelID {identity.level_id}."
            ),
        )

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
        self._document_controller.edit_solution(updated_solution)

    def _on_node_item_selected(self, node_id: str, node_type: str, model_x: float, model_y: float) -> None:
        if self._current_document is None:
            self._properties_panel.show_node(node_id, node_type, model_x, model_y)
            return

        node = next((node for node in self._current_document.graph.nodes if node.id == node_id), None)
        if node is None:
            self._properties_panel.show_node(node_id, node_type, model_x, model_y)
            return

        edge_by_id = {edge.id: edge for edge in self._current_document.graph.edges}
        classification = self._switch_classification_service.classify_node(node, edge_by_id)
        self._properties_panel.show_node(
            node_id,
            node_type,
            model_x,
            model_y,
            switch_classification=classification.display_name,
            outgoing_edge_order=self._outgoing_edge_order_rows(node),
        )

    def _on_node_item_moved(self, node_id: str, model_x: float, model_y: float) -> None:
        if self._current_document is None:
            return

        for node in self._current_document.graph.nodes:
            if node.id != node_id:
                continue
            if node.x == model_x and node.y == model_y:
                return
            self._ensure_controller_state()
            self._document_controller.move_node(node_id, model_x, model_y)
            return

    def _on_outgoing_edge_order_changed(self, node_id: str, ordered_edge_ids: list[str]) -> None:
        if self._current_document is None:
            return

        node = next((node for node in self._current_document.graph.nodes if node.id == node_id), None)
        if node is None:
            return

        edge_by_id = {edge.id: edge for edge in self._current_document.graph.edges}
        classification = self._switch_classification_service.classify_node(node, edge_by_id)
        current_valid_edge_ids = list(classification.valid_outgoing_edge_ids)
        if sorted(ordered_edge_ids) != sorted(current_valid_edge_ids):
            return

        self._ensure_controller_state()
        self._document_controller.reorder_edges(node_id, ordered_edge_ids, current_valid_edge_ids)
        self._canvas_view.scene().select_node_by_id(node_id)

    def _add_node_from_palette(self, node_type: str) -> None:
        if self._current_document is None:
            self.statusBar().showMessage("Create or open a level before placing nodes.")
            return

        self._set_active_tool(EditorTool.PLACE_NODE)
        self._canvas_view.scene().begin_node_placement(node_type)

    def _place_node_at(self, node_type: str, model_x: float, model_y: float) -> None:
        if self._current_document is None:
            return

        node_id = self._generate_unique_default_node_id(node_type)
        new_node = RouteNodeModel(
            id=node_id,
            x=model_x,
            y=model_y,
            outgoingEdgeIDs=[],
        )

        self._ensure_controller_state()
        self._document_controller.add_node(new_node, node_type)
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

        self._ensure_controller_state()
        self._document_controller.add_edge(
            RouteEdgeModel(
                id=edge_id,
                fromNodeID=from_node_id,
                toNodeID=to_node_id,
                roadShape=road_shape,
            )
        )


    def _outgoing_edge_order_rows(self, node) -> list[dict[str, object]]:
        if self._current_document is None:
            return []

        node_by_id = {node.id: node for node in self._current_document.graph.nodes}
        edge_by_id = {edge.id: edge for edge in self._current_document.graph.edges}
        classification = self._switch_classification_service.classify_node(node, edge_by_id)
        rows: list[dict[str, object]] = []
        for index, edge_id in enumerate(classification.valid_outgoing_edge_ids):
            edge = edge_by_id[edge_id]
            target_node = node_by_id.get(edge.toNodeID)
            direction_label, clockwise_sort_key = self._direction_label_and_clockwise_sort_key(
                node,
                target_node,
            )
            rows.append(
                {
                    "edge_id": edge_id,
                    "target_node_id": edge.toNodeID,
                    "direction_label": direction_label,
                    "clockwise_sort_key": clockwise_sort_key,
                    "is_default": index == 0,
                }
            )
        return rows

    def _direction_label_and_clockwise_sort_key(self, source_node, target_node) -> tuple[str, float]:
        if target_node is None:
            return "Unknown", 99.0

        dx = float(target_node.x) - float(source_node.x)
        dy = float(target_node.y) - float(source_node.y)
        if math.isclose(dx, 0.0, abs_tol=1e-9) and math.isclose(dy, 0.0, abs_tol=1e-9):
            return "Same", 99.0

        labels = [
            "Up",
            "Up-Right",
            "Right",
            "Down-Right",
            "Down",
            "Down-Left",
            "Left",
            "Up-Left",
        ]
        clockwise_from_up = math.atan2(dx, dy)
        if clockwise_from_up < 0:
            clockwise_from_up += math.tau
        label_index = int(round(clockwise_from_up / (math.tau / len(labels)))) % len(labels)
        return labels[label_index], clockwise_from_up

    def _on_level_items_deleted(self) -> None:
        if self._current_document is None:
            return
        self._validation_panel.clear()
        self._solution_panel.set_level(self._current_document)
        self._set_dirty(True)

    def _on_controller_document_changed(self, document, solution) -> None:
        self._current_document = document
        self._current_solution = solution
        self._set_dirty(True)
        self._canvas_view.scene().display_level(document)
        self._properties_panel.clear()
        self._solution_panel.set_level(document)
        self._solution_panel.set_solution(solution)
        self._validation_panel.clear()
        self._update_run_tests_action_states()
        self._update_window_title()

    def _ensure_controller_state(self) -> None:
        if self._current_document is None:
            return
        if self._document_controller.document is not self._current_document:
            self._document_controller.open(
                self._current_document,
                self._current_solution,
                saved=not self._is_dirty,
            )

    def _delete_items_with_controller(self, node_ids: set[str], edge_ids: set[str]) -> None:
        self._ensure_controller_state()
        self._document_controller.delete_items(node_ids, edge_ids)

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

        for action_name in (
            "_edit_metadata_action",
            "_promote_draft_action",
            "_repair_metadata_action",
        ):
            action = getattr(self, action_name, None)
            if action is not None:
                action.setEnabled(is_enabled)

    def _can_save_current_path(self) -> bool:
        if self._current_document is None or self._current_file_path is None:
            return False

        if not self._is_path_in_default_levels_dir(self._current_file_path):
            return True

        if not self._is_strict_production_level_filename(self._current_file_path.name):
            QMessageBox.warning(
                self,
                "Production Filename Required",
                "Production levels must use a filename like level_021.json.",
            )
            return False

        if self._identity_service.is_draft_level_id(self._current_document.id):
            QMessageBox.warning(
                self,
                "Production Metadata Required",
                (
                    "Draft level ID 'new_level' cannot be saved in the production "
                    "Levels directory. Use Edit Level Metadata or Promote Draft first."
                ),
            )
            return False

        return True

    def _is_path_in_default_levels_dir(self, path: Path) -> bool:
        return self._same_path(path.parent, self._resolve_default_levels_dir())

    def _is_strict_production_level_filename(self, filename: str) -> bool:
        level_number = self._identity_service.try_parse_number_from_level_filename(
            Path(filename)
        )
        if level_number is None:
            return False
        identity = self._identity_service.build_from_number(level_number)
        return filename == identity.level_filename

    @staticmethod
    def _same_path(left: Path | None, right: Path | None) -> bool:
        if left is None or right is None:
            return False
        return left.resolve(strict=False) == right.resolve(strict=False)

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
