import math
import json
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCloseEvent, QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
)

from app.config import (
    find_repo_root,
    get_default_drafts_directory,
    get_default_levels_directory,
)
from app.controllers import (
    DocumentController,
    PlaytestController,
    PuzzleAnalysisController,
    ValidationController,
)
from app.models import EditorTool, LevelDocument, RouteEdge, RouteNode, Solution
from app.repositories import (
    LevelFileRepository,
    LevelFileRepositoryError,
    MissingSolutionFileError,
    SolutionFileRepository,
    SolutionFileRepositoryError,
)
from app.services import (
    AutomatedChecksService,
    AutosaveRecoveryError,
    AutosaveRecoveryService,
    LevelIdentity,
    LevelIdentityService,
    LevelValidationService,
    NodeArrangementService,
    SolutionValidationService,
    RuntimeSolutionService,
    PuzzleAnalysisService,
    SwitchClassificationService,
    TestRunnerService,
    ValidationMessage,
    ValidationResult,
    ValidationSeverity,
    create_default_level_document,
)
from app.ui import (
    LevelCanvasView,
    KeyboardShortcutsDialog,
    LevelMetadataDialog,
    LevelMetadataResult,
    LevelRulesDialog,
    PiecePalette,
    PropertiesPanel,
    PuzzleAnalysisPanel,
    SolutionPanel,
    ValidationPanel,
)
from app.ui.window_builders import build_main_toolbar, build_menu_bar, build_tools_toolbar
from tiny_routes_core.simulation import LevelOutcome, TapResultCode


class LevelEditorMainWindow(QMainWindow):
    AUTOSAVE_INTERVAL_MS = 30_000

    def __init__(self) -> None:
        super().__init__()
        self.resize(1024, 768)

        self._current_document: LevelDocument | None = None
        self._current_solution: Solution | None = None
        self._current_file_path: Path | None = None
        self._is_dirty = False
        self._current_candidate_quality: dict | None = None
        self._active_tool = EditorTool.SELECT
        self._repository = LevelFileRepository()
        self._solution_repository = SolutionFileRepository()
        self._identity_service = LevelIdentityService()
        self._validation_service = LevelValidationService()
        self._solution_validation_service = SolutionValidationService()
        self._runtime_solution_service = RuntimeSolutionService()
        self._puzzle_analysis_service = PuzzleAnalysisService(
            self._runtime_solution_service
        )
        self._switch_classification_service = SwitchClassificationService()
        self._node_arrangement_service = NodeArrangementService()
        self._autosave_recovery_service = AutosaveRecoveryService()
        self._test_runner_service = TestRunnerService(self._resolve_repo_root())
        self._automated_checks_service = AutomatedChecksService(
            self._resolve_repo_root(),
            level_validation=self._validation_service,
            runtime=self._runtime_solution_service,
            analysis=self._puzzle_analysis_service,
            swift_tests=self._test_runner_service,
        )
        self._canvas_view = LevelCanvasView()
        self._piece_palette = PiecePalette()
        self._properties_panel = PropertiesPanel()
        self._solution_panel = SolutionPanel()
        self._validation_panel = ValidationPanel()
        self._puzzle_analysis_panel = PuzzleAnalysisPanel()
        self._document_controller = DocumentController(self)
        self._validation_controller = ValidationController(
            self,
            level_service=self._validation_service,
            solution_service=self._solution_validation_service,
        )
        self._puzzle_analysis_controller = PuzzleAnalysisController(
            self,
            service=self._puzzle_analysis_service,
        )
        self._playtest_controller = PlaytestController(self)
        self._playtest_controller.state_changed.connect(
            self._canvas_view.scene().update_playtest_overlay
        )
        self._playtest_controller.state_changed.connect(self._on_playtest_state_changed)
        self._document_controller.document_changed.connect(self._on_controller_document_changed)
        self._document_controller.dirty_changed.connect(self._set_dirty)
        self._validation_controller.result_ready.connect(self._show_validation_result)
        self._puzzle_analysis_controller.result_ready.connect(
            self._puzzle_analysis_panel.show_analysis
        )
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(self.AUTOSAVE_INTERVAL_MS)
        self._autosave_timer.timeout.connect(self._write_autosave_recovery)
        self._autosave_timer.start()

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

        self._puzzle_analysis_dock = QDockWidget("Puzzle Analysis", self)
        self._puzzle_analysis_dock.setWidget(self._puzzle_analysis_panel)
        self._puzzle_analysis_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable,
        )
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self._puzzle_analysis_dock
        )

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
        scene.edge_item_selected.connect(self._on_edge_item_selected)
        scene.selection_cleared.connect(self._properties_panel.clear)
        scene.node_item_moved.connect(self._on_node_item_moved)
        scene.edge_creation_requested.connect(self._on_edge_creation_requested)
        scene.node_placement_requested.connect(self._place_node_at)
        scene.set_delete_items_handler(self._delete_items_with_controller)
        scene.placement_message_changed.connect(self.statusBar().showMessage)
        scene.playtest_tap_requested.connect(self._on_playtest_tap_requested)
        scene.nudge_selected_requested.connect(self._nudge_selected_nodes)
        self._validation_panel.validate_requested.connect(self._validate_current_level)
        self._validation_panel.validation_message_activated.connect(
            self._focus_validation_message
        )
        self._puzzle_analysis_panel.analyze_requested.connect(self._analyze_puzzle)
        self._puzzle_analysis_panel.run_all_checks_requested.connect(
            self._run_all_automated_checks
        )
        self._puzzle_analysis_panel.recommendation_activated.connect(
            self._focus_validation_message
        )
        self._piece_palette.node_type_activated.connect(self._add_node_from_palette)
        self._properties_panel.outgoing_edge_order_changed.connect(
            self._on_outgoing_edge_order_changed
        )
        self._properties_panel.node_id_changed.connect(self._on_node_id_changed)
        self._properties_panel.node_role_changed.connect(self._on_node_role_changed)
        self._properties_panel.node_position_changed.connect(self._on_node_position_changed)
        self._properties_panel.initial_route_changed.connect(self._on_initial_route_changed)
        self._properties_panel.edge_id_changed.connect(self._on_edge_id_changed)
        self._properties_panel.edge_properties_changed.connect(self._on_edge_properties_changed)
        self._solution_panel.solution_changed.connect(self._on_solution_changed)
        self._solution_panel.replay_requested.connect(self._replay_solution)
        self._solution_panel.find_verified_requested.connect(self._find_verified_solution)
        self._solution_panel.analyze_margins_requested.connect(self._analyze_solution_margins)
        self._solution_panel.timeline_time_requested.connect(self._playtest_controller.scrub_to)
        self._solution_panel.timeline_step_requested.connect(self._playtest_controller.step_event)
        self._solution_panel.timeline_reset_requested.connect(lambda: self._playtest_controller.scrub_to(0.0))
        self._solution_panel.timeline_play_pause_requested.connect(self._pause_or_resume_playtest)

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

    def _show_keyboard_shortcuts(self) -> None:
        KeyboardShortcutsDialog(self).exec()

    def _set_active_tool(self, tool: EditorTool) -> None:
        if tool is EditorTool.PLAYTEST:
            if self._current_document is None:
                self.statusBar().showMessage("Open or create a level before playtesting.")
            elif not self._playtest_controller.state.running:
                self._playtest_controller.start(self._current_document)
        elif self._playtest_controller.state.running:
            self._playtest_controller.stop()
        self._active_tool = tool
        self._tool_actions[tool].setChecked(True)
        self._canvas_view.set_editor_tool(tool)
        editing_enabled = tool is not EditorTool.PLAYTEST
        self._piece_palette.setEnabled(editing_enabled)
        self._properties_panel.setEnabled(editing_enabled)
        for action in getattr(self, "_road_shape_actions", {}).values():
            action.setEnabled(tool is EditorTool.CONNECT)
        self._bidirectional_road_action.setEnabled(tool is EditorTool.CONNECT)
        self.statusBar().showMessage(tool.status_message)
        self._sync_playtest_actions()

    def _pause_or_resume_playtest(self) -> None:
        if self._playtest_controller.state.paused:
            self._playtest_controller.resume()
        else:
            self._playtest_controller.pause()
        self._sync_playtest_actions()

    def _reset_playtest(self) -> None:
        self._playtest_controller.reset()
        self._sync_playtest_actions()

    def _stop_playtest(self) -> None:
        self._set_active_tool(EditorTool.SELECT)

    def _on_playtest_tap_requested(self, node_id: str) -> None:
        record = self._playtest_controller.tap(node_id)
        if record is None:
            self.statusBar().showMessage("Playtest taps are unavailable while paused.", 2500)
        elif record.code == TapResultCode.ACCEPTED:
            self.statusBar().showMessage(f"Tap accepted at '{node_id}'.", 1500)
        else:
            reason = record.code.value.removeprefix("tap_").replace("_", " ")
            self.statusBar().showMessage(f"Tap rejected: {reason}.", 3000)

    def _on_playtest_state_changed(self, state) -> None:
        self._solution_panel.set_playhead(state.elapsed_time)
        if hasattr(self, "_use_playtest_solution_action"):
            self._use_playtest_solution_action.setEnabled(
                state.running and state.outcome == LevelOutcome.COMPLETED
            )
        self._sync_playtest_actions()

    def _replay_solution(self) -> None:
        if self._current_document is None or self._current_solution is None:
            return
        self._set_active_tool(EditorTool.PLAYTEST)
        self._playtest_controller.load_replay(self._current_document, self._current_solution)
        self.statusBar().showMessage("Solution loaded on the deterministic timeline.", 2500)

    def _find_verified_solution(self) -> None:
        if self._current_document is None:
            return
        solution = self._runtime_solution_service.find_verified(self._current_document)
        if solution is None:
            self.statusBar().showMessage("No verified runtime solution was found within the search limit.", 4000)
            return
        self._ensure_controller_state()
        self._document_controller.edit_solution(solution)
        self._solution_panel.set_action_timings(
            self._runtime_solution_service.analyze(self._current_document, solution)
        )
        self._validate_current_level()
        self.statusBar().showMessage("Found and installed a verified runtime solution.", 3000)

    def _analyze_solution_margins(self) -> None:
        if self._current_document is None or self._current_solution is None:
            return
        timings = self._runtime_solution_service.analyze(self._current_document, self._current_solution)
        self._solution_panel.set_action_timings(timings)
        margins = [min(item.early_margin_seconds, item.late_margin_seconds)
                   for item in timings
                   if item.early_margin_seconds is not None and item.late_margin_seconds is not None]
        message = "No eligible timing windows found."
        if margins:
            message = f"Tightest early/late safety margin: {min(margins):.2f}s."
        self.statusBar().showMessage(message, 4000)

    def _analyze_puzzle(self) -> None:
        if self._current_document is None:
            self._puzzle_analysis_panel.clear()
            return
        self._puzzle_analysis_controller.analyze_now(
            self._current_document, self._current_solution
        )
        self.statusBar().showMessage("Puzzle analysis updated.", 2500)

    def _run_all_automated_checks(self) -> None:
        if self._current_document is None:
            self._puzzle_analysis_panel.clear()
            return
        self._puzzle_analysis_panel.set_checks_running(True)
        self.statusBar().showMessage(
            "Running structural, runtime, quality, and Swift parity checks…"
        )
        try:
            report = self._automated_checks_service.run(
                self._current_document,
                self._current_solution,
                self._current_file_path,
            )
        finally:
            self._puzzle_analysis_panel.set_checks_running(False)
        self._puzzle_analysis_panel.show_checks(report)
        passed_count = sum(
            check.status.value == "passed" for check in report.checks
        )
        self.statusBar().showMessage(
            f"Automated checks finished: {passed_count}/{len(report.checks)} passed.",
            5000,
        )

    def _use_playtest_run_as_solution(self) -> None:
        solution = self._playtest_controller.recorded_solution()
        if solution is None:
            self.statusBar().showMessage(
                "Only a successfully completed, replayable run can replace the solution.", 4000
            )
            return
        self._ensure_controller_state()
        self._document_controller.edit_solution(solution)
        self._validate_current_level()
        self.statusBar().showMessage("Recorded run is now the validated solution.", 3000)

    def _sync_playtest_actions(self) -> None:
        if not hasattr(self, "_playtest_pause_action"):
            return
        running = self._playtest_controller.state.running
        self._playtest_pause_action.setEnabled(running)
        self._playtest_reset_action.setEnabled(running)
        self._playtest_stop_action.setEnabled(running)
        self._use_playtest_solution_action.setEnabled(
            running and self._playtest_controller.state.outcome == LevelOutcome.COMPLETED
        )
        self._playtest_pause_action.setText(
            "Resume" if self._playtest_controller.state.paused else "Pause"
        )

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

    def _set_bidirectional_roads_enabled(self, enabled: bool) -> None:
        self._canvas_view.scene().set_bidirectional_roads_enabled(enabled)
        self.statusBar().showMessage(
            "Two-way road creation enabled." if enabled else "Directed road creation enabled."
        )

    def _snap_selected_to_grid(self) -> None:
        moved = self._canvas_view.scene().snap_selected_to_grid()
        self.statusBar().showMessage(
            f"Snapped {moved} selected node{'s' if moved != 1 else ''} to the grid."
        )

    def _arrange_selected_nodes(self, operation: str) -> None:
        scene = self._canvas_view.scene()
        positions = scene.selected_node_positions()
        minimum = 3 if operation in {"horizontal", "vertical"} else 2
        if len(positions) < minimum:
            self.statusBar().showMessage(
                f"Select at least {minimum} nodes for this arrangement.", 2500
            )
            return
        arranged = self._node_arrangement_service.arrange(positions, operation)
        self._ensure_controller_state()
        self._document_controller.move_nodes(
            arranged,
            command_text=operation.replace("_", " ").title(),
        )
        scene.select_nodes_by_ids(set(arranged))
        self.statusBar().showMessage(
            f"Arranged {len(arranged)} selected nodes.", 2000
        )

    def _nudge_selected_nodes(self, dx: float, dy: float) -> None:
        scene = self._canvas_view.scene()
        positions = scene.selected_node_positions()
        if not positions:
            return
        nudged = self._node_arrangement_service.nudge(positions, dx, dy)
        self._ensure_controller_state()
        self._document_controller.move_nodes(
            nudged,
            command_text="Nudge selected nodes",
        )
        scene.select_nodes_by_ids(set(nudged))

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

        if not self._load_level_bundle(Path(file_path)):
            return
        self._properties_panel.clear()
        self._solution_panel.set_level(self._current_document)
        self._solution_panel.set_solution(self._current_solution)
        self._validation_panel.clear()
        self._update_run_tests_action_states()

    def open_level_bundle(
        self,
        level_path: Path,
        *,
        solution_path: Path | None = None,
        quality_path: Path | None = None,
    ) -> bool:
        """Open a level, its solution, and optional generator analysis together."""

        if not self._prompt_to_save_unsaved_changes():
            return False
        return self._load_level_bundle(
            Path(level_path),
            solution_path=solution_path,
            quality_path=quality_path,
        )

    def _load_level_bundle(
        self,
        level_path: Path,
        *,
        solution_path: Path | None = None,
        quality_path: Path | None = None,
    ) -> bool:
        try:
            document = self._repository.load_level(level_path)
        except LevelFileRepositoryError as exc:
            QMessageBox.critical(self, "Failed to Open Level", exc.message)
            return False

        if solution_path is None:
            solution = self._load_solution_for_level(level_path, document)
        else:
            try:
                solution = self._solution_repository.load_solution(solution_path)
            except SolutionFileRepositoryError as exc:
                QMessageBox.warning(self, "Failed to Load Solution", exc.message)
                solution = self._build_default_solution(document, is_placeholder=True)

        quality = None
        if quality_path is not None:
            try:
                payload = json.loads(Path(quality_path).read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("Expected a JSON object.")
                if payload.get("levelID") not in (None, document.id):
                    raise ValueError("Quality data belongs to a different level.")
                quality = payload
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                QMessageBox.warning(
                    self,
                    "Failed to Load Candidate Quality",
                    f"Could not import {quality_path}: {exc}",
                )

        self._current_file_path = level_path
        self._current_candidate_quality = quality
        self._document_controller.open(document, solution, saved=True)
        if quality is not None:
            self._puzzle_analysis_panel.show_imported_quality(quality)
        return True

    def _new_level(self) -> None:
        if not self._prompt_to_save_unsaved_changes():
            return

        document = create_default_level_document()
        self._current_file_path = None
        self._current_candidate_quality = None
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

        if (
            self._current_candidate_quality is not None
            and not self._is_path_in_default_levels_dir(self._current_file_path)
        ):
            quality_path = self._current_file_path.with_name(
                f"{self._current_file_path.stem}.quality.json"
            )
            try:
                quality_path.write_text(
                    json.dumps(
                        self._current_candidate_quality,
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
            except OSError as exc:
                QMessageBox.critical(
                    self, "Failed to Save Candidate Quality", str(exc)
                )
                return False

        self._document_controller.mark_saved()
        self._clear_autosave_recovery()
        self._set_dirty(False)
        return True

    def _write_autosave_recovery(self) -> None:
        if not self._is_dirty or self._current_document is None:
            return
        try:
            self._autosave_recovery_service.write(
                self._current_document,
                self._current_solution,
                source_path=self._current_file_path,
                candidate_quality=self._current_candidate_quality,
            )
        except AutosaveRecoveryError as exc:
            self.statusBar().showMessage(str(exc), 10_000)

    def _clear_autosave_recovery(self) -> None:
        try:
            self._autosave_recovery_service.delete()
        except AutosaveRecoveryError as exc:
            self.statusBar().showMessage(str(exc), 10_000)

    def offer_recovery_if_available(self) -> bool:
        """Offer to restore a bundle left behind by an unclean shutdown."""
        if not self._autosave_recovery_service.exists():
            return False
        try:
            recovery = self._autosave_recovery_service.load()
        except AutosaveRecoveryError as exc:
            QMessageBox.warning(self, "Recovery Unavailable", str(exc))
            return False

        choice = self._ask_recovery_action(recovery.saved_at_utc)
        if choice == "discard":
            self._clear_autosave_recovery()
            return False
        if choice != "recover":
            return False

        self._current_file_path = recovery.source_path
        self._current_candidate_quality = recovery.candidate_quality
        self._document_controller.open(
            recovery.document,
            recovery.solution,
            saved=False,
        )
        if recovery.candidate_quality is not None:
            self._puzzle_analysis_panel.show_imported_quality(
                recovery.candidate_quality
            )
        self.statusBar().showMessage(
            "Recovered autosaved changes. Save the level to keep them.",
            10_000,
        )
        return True

    def _ask_recovery_action(self, saved_at_utc: str) -> str:
        message_box = QMessageBox(self)
        message_box.setWindowTitle("Recover Unsaved Level")
        message_box.setIcon(QMessageBox.Icon.Question)
        message_box.setText("Unsaved level changes were found from an unclean shutdown.")
        message_box.setInformativeText(
            f"Recovery snapshot: {saved_at_utc}\n\nRecover these changes?"
        )
        recover_button = message_box.addButton(
            "Recover", QMessageBox.ButtonRole.AcceptRole
        )
        discard_button = message_box.addButton(
            "Discard", QMessageBox.ButtonRole.DestructiveRole
        )
        message_box.addButton(QMessageBox.StandardButton.Cancel)
        message_box.setDefaultButton(recover_button)
        message_box.exec()
        if message_box.clickedButton() is recover_button:
            return "recover"
        if message_box.clickedButton() is discard_button:
            return "discard"
        return "cancel"

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

    def _save_draft(self) -> bool:
        if self._current_document is None:
            return False
        draft_dir = get_default_drafts_directory()
        draft_dir.mkdir(parents=True, exist_ok=True)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Level Draft",
            str(draft_dir / f"{self._current_document.id}.json"),
            "Level JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return False
        selected_path = Path(file_path)
        if self._is_path_in_default_levels_dir(selected_path):
            QMessageBox.warning(
                self,
                "Use Production Promotion",
                (
                    "Drafts cannot be saved directly into the production Levels "
                    "directory. Save here first, then use Promote Draft to "
                    "Production Level so overwrite checks are applied."
                ),
            )
            return False
        previous_path = self._current_file_path
        self._current_file_path = selected_path
        self._current_file_path.parent.mkdir(parents=True, exist_ok=True)
        if self._save_level():
            return True
        self._current_file_path = previous_path
        return False

    def _validate_current_level(self) -> None:
        if self._current_document is None:
            self._validation_panel.clear()
            return

        self._validation_controller.validate_now(
            self._current_document,
            self._current_solution,
            self._current_file_path,
        )

    def _show_validation_result(self, result: ValidationResult) -> None:
        messages = list(result.messages)
        consistency_message = self._build_production_metadata_consistency_message(messages)
        if consistency_message is not None:
            messages.append(consistency_message)
        combined_result = ValidationResult(
            messages=messages
        )
        self._validation_panel.show_result(combined_result)
        self._canvas_view.scene().apply_validation_result(combined_result)

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

    def _edit_level_rules(self) -> None:
        if self._current_document is None:
            return
        schema_version = self._current_document._extra.get("schemaVersion", 1)
        dialog = LevelRulesDialog(self._current_document.rules, schema_version, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        result = dialog.result_value()
        self._ensure_controller_state()
        self._document_controller.edit_rules(result.rules, result.schema_version)

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

        return self._current_file_path.with_name(
            f"{self._current_file_path.stem}.solution.json"
        )

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

    def _on_solution_changed(self, updated_solution: Solution) -> None:
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
            available_node_ids=[item.id for item in self._current_document.graph.nodes],
        )

    def _on_edge_item_selected(
        self,
        edge_id: str,
        from_node_id: str,
        to_node_id: str,
        road_shape: str,
        availability: str,
    ) -> None:
        node_ids = [] if self._current_document is None else [
            node.id for node in self._current_document.graph.nodes
        ]
        self._properties_panel.show_edge(
            edge_id,
            from_node_id,
            to_node_id,
            road_shape,
            availability,
            available_node_ids=node_ids,
        )

    def _run_property_edit(self, mutation, *, select_node: str | None = None, select_edge: str | None = None) -> None:
        try:
            self._ensure_controller_state()
            mutation()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Property", str(exc))
            if select_node:
                self._canvas_view.scene().select_node_by_id(select_node)
            elif select_edge:
                self._canvas_view.scene().select_edge_by_id(select_edge)
            return
        if select_node:
            self._canvas_view.scene().select_node_by_id(select_node)
        elif select_edge:
            self._canvas_view.scene().select_edge_by_id(select_edge)

    def _on_node_id_changed(self, old_id: str, new_id: str) -> None:
        if new_id == old_id:
            return
        self._run_property_edit(
            lambda: self._document_controller.rename_node(old_id, new_id), select_node=new_id
        )

    def _on_node_role_changed(self, node_id: str, role: str) -> None:
        self._run_property_edit(
            lambda: self._document_controller.set_node_role(node_id, role), select_node=node_id
        )

    def _on_node_position_changed(self, node_id: str, x: float, y: float) -> None:
        self._run_property_edit(
            lambda: self._document_controller.edit_node_position(node_id, x, y), select_node=node_id
        )

    def _on_initial_route_changed(self, node_id: str, edge_id: str) -> None:
        node = next((item for item in self._current_document.graph.nodes if item.id == node_id), None) if self._current_document else None
        if node is None or edge_id not in node.outgoingEdgeIDs:
            return
        ordered = [edge_id, *[item for item in node.outgoingEdgeIDs if item != edge_id]]
        self._on_outgoing_edge_order_changed(node_id, ordered)

    def _on_edge_id_changed(self, old_id: str, new_id: str) -> None:
        if new_id == old_id:
            return
        self._run_property_edit(
            lambda: self._document_controller.rename_edge(old_id, new_id), select_edge=new_id
        )

    def _on_edge_properties_changed(
        self,
        edge_id: str,
        from_node_id: str,
        to_node_id: str,
        road_shape: str,
        availability: str,
    ) -> None:
        self._run_property_edit(
            lambda: self._document_controller.edit_edge(
                edge_id, from_node_id, to_node_id, road_shape, availability
            ),
            select_edge=edge_id,
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
        new_node = RouteNode(
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
        bidirectional: bool = False,
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
        edges = [RouteEdge(
                id=edge_id,
                fromNodeID=from_node_id,
                toNodeID=to_node_id,
                roadShape=road_shape,
            )]
        if bidirectional:
            existing_ids = {edge.id for edge in self._current_document.graph.edges} | {edge_id}
            reverse_edge_id = self._unique_edge_id(existing_ids)
            edges.append(RouteEdge(
                id=reverse_edge_id,
                fromNodeID=to_node_id,
                toNodeID=from_node_id,
                roadShape=road_shape,
            ))
        self._document_controller.add_edges(edges)

    @staticmethod
    def _unique_edge_id(existing_ids: set[str]) -> str:
        if "edge" not in existing_ids:
            return "edge"
        suffix = 1
        while f"edge_{suffix}" in existing_ids:
            suffix += 1
        return f"edge_{suffix}"


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
                    "road_shape": edge.roadShape,
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
        preserve_viewport = self._current_document is document
        viewport_state = (
            self._canvas_view.capture_viewport() if preserve_viewport else None
        )
        self._current_document = document
        self._current_solution = solution
        self._set_dirty(True)
        self._canvas_view.scene().display_level(document)
        if viewport_state is not None:
            self._canvas_view.restore_viewport(viewport_state)
        self._properties_panel.clear()
        self._solution_panel.set_level(document)
        self._solution_panel.set_solution(solution)
        self._validation_panel.clear()
        self._puzzle_analysis_panel.clear()
        if self._current_candidate_quality is not None:
            self._puzzle_analysis_panel.show_imported_quality(
                self._current_candidate_quality
            )
        self._canvas_view.scene().clear_validation_overlays()
        if document is not None:
            self._validation_controller.schedule(document, solution, self._current_file_path)
            # A document change can affect graph topology, geometry-derived
            # timing, rules, or the saved solution, so refresh both analysis
            # layers after the shared debounce.
            self._puzzle_analysis_controller.schedule(document, solution)
        else:
            self._puzzle_analysis_controller.cancel()
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
    ) -> Solution:
        return Solution(
            levelID=document.id,
            description=f"Solution for {document.name}",
            expectedOutcome="completed",
            maxTaps=0,
            requiresWithinTimeLimit=True,
            actions=[],
            isPlaceholder=is_placeholder or None,
        )

    def _load_solution_for_level(self, level_path: Path, document: LevelDocument) -> Solution:
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

        for action_name in ("_analyze_puzzle_action", "_run_all_checks_action"):
            action = getattr(self, action_name, None)
            if action is not None:
                action.setEnabled(is_enabled)

        for action_name in (
            "_edit_metadata_action",
            "_promote_draft_action",
            "_repair_metadata_action",
            "_edit_rules_action",
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
        self._clear_autosave_recovery()
        return True

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if not self._prompt_to_save_unsaved_changes():
            event.ignore()
            return
        self._validation_controller.cancel()
        self._puzzle_analysis_controller.cancel()
        self._autosave_timer.stop()
        self._clear_autosave_recovery()
        event.accept()
