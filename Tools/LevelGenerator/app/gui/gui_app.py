from __future__ import annotations

import threading
import tkinter as tk
import traceback
import subprocess
import sys
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from ..generation_config import (
    DEFAULT_CANDIDATE_POOL_SIZE,
    DEFAULT_LAYOUTS_PER_RECIPE,
    DEFAULT_LAYOUT_ORIENTATION_PREFERENCE,
    DEFAULT_LAYOUT_SIZE_PROFILE,
    DEFAULT_MAX_ATTEMPTS_PER_LEVEL,
    DEFAULT_RECIPE_POOL_SIZE,
    DEFAULT_ROAD_SHAPES_PER_LAYOUT,
    DEFAULT_VERTICAL_ROUTE_PROBABILITY,
    DEFAULT_GENERATOR_ARCHITECTURE,
    GENERATOR_ARCHITECTURES,
    LEGACY_GENERATOR_WARNING,
    LAYOUT_ORIENTATION_PREFERENCES,
    LAYOUT_SIZE_PROFILES,
)
from ..services.difficulty_service import DifficultyService
from ..recipes.recipe_family_registry import RecipeFamilyRegistry
from .gui_controller import (
    GuiController,
    format_generation_result,
    format_production_campaign_result,
    format_validation_result,
)
from .gui_paths import (
    open_path,
    try_get_default_debug_failures_directory,
    try_get_default_editor_drafts_directory,
    try_get_default_json_report_path,
    try_get_default_levels_directory,
    try_get_default_markdown_report_path,
    try_get_default_solutions_directory,
)
from .gui_state import GuiGenerationState, build_command_preview
from .gui_widgets import add_labeled_combobox, add_labeled_entry, add_path_picker


STATUS_COLORS = {
    "ready": "#333333",
    "running": "#8a5a00",
    "passed": "#146c2e",
    "failed": "#a61b1b",
}


def run_gui() -> None:
    root = tk.Tk()
    root.title("Tiny Routes Level Generator")
    width = min(950, max(760, root.winfo_screenwidth() - 80))
    height = min(700, max(500, root.winfo_screenheight() - 140))
    root.geometry(f"{width}x{height}")
    root.minsize(760, 500)
    LevelGeneratorGui(root)
    root.mainloop()


class LevelGeneratorGui:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.controller = GuiController()
        self.difficulty_names = [*DifficultyService().valid_names, "auto"]
        self.template_names = RecipeFamilyRegistry().valid_family_names()
        self.layout_orientation_preferences = list(LAYOUT_ORIENTATION_PREFERENCES)
        self.layout_size_profiles = list(LAYOUT_SIZE_PROFILES)
        self.generator_architectures = list(GENERATOR_ARCHITECTURES)
        self.latest_result = None
        self.latest_production_result = None
        self.approved_candidates = []
        self.cancel_requested = False

        self._create_variables()
        self._build_window()
        self._bind_preview_updates()
        self._update_command_preview()
        self._refresh_open_buttons()
        self.append_log("Ready.")
        self._log_default_path_warning_if_needed()

    def _create_variables(self) -> None:
        self.start_var = tk.StringVar(value="12")
        self.count_var = tk.StringVar(value="1")
        self.difficulty_var = tk.StringVar(value="easy")
        self.generator_architecture_var = tk.StringVar(value=DEFAULT_GENERATOR_ARCHITECTURE)
        self.template_var = tk.StringVar(value="mixed")
        self.recipe_pool_var = tk.StringVar(value=str(DEFAULT_RECIPE_POOL_SIZE))
        self.layouts_per_recipe_var = tk.StringVar(value=str(DEFAULT_LAYOUTS_PER_RECIPE))
        self.road_shapes_per_layout_var = tk.StringVar(value=str(DEFAULT_ROAD_SHAPES_PER_LAYOUT))
        self.layout_orientation_var = tk.StringVar(value=DEFAULT_LAYOUT_ORIENTATION_PREFERENCE)
        self.layout_size_profile_var = tk.StringVar(value=DEFAULT_LAYOUT_SIZE_PROFILE)
        self.vertical_route_probability_var = tk.StringVar(value=str(DEFAULT_VERTICAL_ROUTE_PROBABILITY))
        self.seed_var = tk.StringVar(value="")
        self.max_attempts_var = tk.StringVar(value=str(DEFAULT_MAX_ATTEMPTS_PER_LEVEL))
        self.candidate_pool_var = tk.StringVar(value=str(DEFAULT_CANDIDATE_POOL_SIZE))

        self.dry_run_var = tk.BooleanVar(value=True)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.swift_tests_var = tk.BooleanVar(value=False)
        self.compare_existing_var = tk.BooleanVar(value=True)
        self.prefer_vertical_for_long_routes_var = tk.BooleanVar(value=True)
        self.swift_timeout_var = tk.StringVar(value="180")

        self.levels_output_var = tk.StringVar(value=try_get_default_levels_directory())
        self.solutions_output_var = tk.StringVar(value=try_get_default_solutions_directory())
        self.report_path_var = tk.StringVar(value=try_get_default_markdown_report_path())
        self.json_report_path_var = tk.StringVar(value=try_get_default_json_report_path())
        self.map_seed_path_var = tk.StringVar(value="")
        self.debug_failures_var = tk.StringVar(value=try_get_default_debug_failures_directory())
        self.editor_drafts_var = tk.StringVar(value=try_get_default_editor_drafts_directory())

        self.validation_level_ids_var = tk.StringVar(value="")
        self.validation_difficulty_var = tk.StringVar(value="")
        self.validation_swift_tests_var = tk.BooleanVar(value=False)

        self.status_var = tk.StringVar(value="Status: Ready")
        self.accepted_var = tk.StringVar(value="Accepted: 0")
        self.rejected_var = tk.StringVar(value="Rejected: 0")
        self.swift_summary_var = tk.StringVar(value="Swift: Not run")
        self.command_preview_var = tk.StringVar(value="")

    def _build_window(self) -> None:
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        viewport = ttk.Frame(self.root)
        viewport.grid(row=0, column=0, sticky="nsew")
        viewport.grid_rowconfigure(0, weight=1)
        viewport.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(viewport, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(viewport, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        root_frame = ttk.Frame(canvas, padding=12)
        self._scroll_window_id = canvas.create_window((0, 0), window=root_frame, anchor="nw")
        self._scroll_canvas = canvas
        root_frame.bind("<Configure>", self._on_scroll_frame_configure)
        canvas.bind("<Configure>", self._on_scroll_canvas_configure)
        canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        root_frame.grid_columnconfigure(0, weight=1)
        root_frame.grid_rowconfigure(5, weight=1)

        header = ttk.Label(root_frame, text="Tiny Routes Level Generator", font=("TkDefaultFont", 16, "bold"))
        header.grid(row=0, column=0, sticky="w", pady=(0, 8))

        form_frame = ttk.Frame(root_frame)
        form_frame.grid(row=1, column=0, sticky="nsew")
        form_frame.grid_columnconfigure(0, weight=1)
        form_frame.grid_columnconfigure(1, weight=1)

        left_column = ttk.Frame(form_frame)
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left_column.grid_columnconfigure(0, weight=1)

        right_column = ttk.Frame(form_frame)
        right_column.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right_column.grid_columnconfigure(0, weight=1)

        self._build_generation_section(left_column)
        self._build_options_section(left_column)
        self._build_actions_section(left_column)
        self._build_output_section(right_column)
        self._build_validation_section(right_column)
        self._build_command_preview(root_frame)
        self._build_summary_section(root_frame)
        self._build_preview_section(root_frame)
        self._build_log_panel(root_frame)

    def _on_scroll_frame_configure(self, _event) -> None:
        self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox("all"))

    def _on_scroll_canvas_configure(self, event) -> None:
        self._scroll_canvas.itemconfigure(self._scroll_window_id, width=event.width)

    def _on_mousewheel(self, event) -> None:
        if self.root.focus_get() is self.log_text:
            return
        self._scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_generation_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Generation Settings", padding=8)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        frame.grid_columnconfigure(1, weight=1)

        add_labeled_entry(frame, "Start level number", self.start_var, 0)
        add_labeled_entry(frame, "Count", self.count_var, 1)
        add_labeled_combobox(frame, "Difficulty", self.difficulty_var, self.difficulty_names, 2)
        add_labeled_combobox(
            frame,
            "Generator architecture",
            self.generator_architecture_var,
            self.generator_architectures,
            3,
        )
        add_labeled_combobox(frame, "Template", self.template_var, self.template_names, 4)
        add_labeled_entry(frame, "Recipe pool size", self.recipe_pool_var, 5)
        add_labeled_entry(frame, "Layouts per recipe", self.layouts_per_recipe_var, 6)
        add_labeled_entry(frame, "Road shapes per layout", self.road_shapes_per_layout_var, 7)
        add_labeled_combobox(
            frame,
            "Layout orientation",
            self.layout_orientation_var,
            self.layout_orientation_preferences,
            8,
        )
        add_labeled_combobox(
            frame,
            "Layout size profile",
            self.layout_size_profile_var,
            self.layout_size_profiles,
            9,
        )
        add_labeled_entry(frame, "Vertical route probability", self.vertical_route_probability_var, 10)
        ttk.Checkbutton(
            frame,
            text="Prefer vertical for long routes",
            variable=self.prefer_vertical_for_long_routes_var,
        ).grid(row=11, column=0, columnspan=2, sticky="w", pady=3)
        add_labeled_entry(frame, "Seed", self.seed_var, 12)
        add_labeled_entry(frame, "Max attempts per level", self.max_attempts_var, 13)
        add_labeled_entry(frame, "Candidate pool size", self.candidate_pool_var, 14)

    def _build_options_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Options", padding=8)
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        frame.grid_columnconfigure(1, weight=1)

        ttk.Checkbutton(frame, text="Dry run", variable=self.dry_run_var).grid(row=0, column=0, sticky="w", pady=3)
        ttk.Checkbutton(frame, text="Overwrite", variable=self.overwrite_var).grid(row=1, column=0, sticky="w", pady=3)
        ttk.Checkbutton(frame, text="Run Swift tests", variable=self.swift_tests_var).grid(
            row=2,
            column=0,
            sticky="w",
            pady=3,
        )
        ttk.Checkbutton(frame, text="Avoid similar existing levels", variable=self.compare_existing_var).grid(
            row=3,
            column=0,
            sticky="w",
            pady=3,
        )
        add_labeled_entry(frame, "Swift timeout seconds", self.swift_timeout_var, 4)

    def _build_actions_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Actions", padding=8)
        frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        for column in range(2):
            frame.grid_columnconfigure(column, weight=1)

        self.generate_button = ttk.Button(frame, text="Generate Preview", command=self._on_generate)
        self.generate_button.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=3)
        self.production_generate_button = ttk.Button(
            frame,
            text="Generate Production Campaign",
            command=self._on_generate_production,
        )
        self.production_generate_button.grid(
            row=0, column=1, sticky="ew", padx=(4, 0), pady=3
        )

        self.open_report_button = ttk.Button(frame, text="Open Report", command=self._on_open_report)
        self.open_report_button.grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=3)
        ttk.Button(frame, text="Clear Log", command=self.clear_log).grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=3)

        self.open_levels_button = ttk.Button(frame, text="Open Levels Folder", command=self._on_open_levels_folder)
        self.open_levels_button.grid(row=2, column=0, sticky="ew", padx=(0, 4), pady=3)
        self.open_solutions_button = ttk.Button(frame, text="Open Solutions Folder", command=self._on_open_solutions_folder)
        self.open_solutions_button.grid(row=2, column=1, sticky="ew", padx=(4, 0), pady=3)

        self.cancel_button = ttk.Button(frame, text="Cancel", command=self._on_cancel)
        self.cancel_button.grid(row=3, column=0, sticky="ew", padx=(0, 4), pady=3)
        ttk.Button(frame, text="Open in Level Editor", command=self._on_open_level_editor).grid(
            row=3,
            column=1,
            sticky="ew",
            padx=(4, 0),
            pady=3,
        )
        ttk.Button(frame, text="Reset", command=self._reset_form).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=3
        )

    def _build_output_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Output Settings", padding=8)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        frame.grid_columnconfigure(1, weight=1)

        add_path_picker(frame, "Levels output directory", self.levels_output_var, 0, pick_directory=True)
        add_path_picker(frame, "Solutions output directory", self.solutions_output_var, 1, pick_directory=True)
        add_path_picker(frame, "Markdown report path", self.report_path_var, 2, pick_directory=False, file_extension=".md")
        add_path_picker(frame, "JSON report path", self.json_report_path_var, 3, pick_directory=False, file_extension=".json")
        add_path_picker(frame, "Map seed path", self.map_seed_path_var, 4, pick_directory=False, file_extension=".json")
        add_path_picker(frame, "Debug failures directory", self.debug_failures_var, 5, pick_directory=True)
        add_path_picker(frame, "Editor drafts directory", self.editor_drafts_var, 6, pick_directory=True)

    def _build_validation_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Validate Existing Levels", padding=8)
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        frame.grid_columnconfigure(1, weight=1)

        add_labeled_entry(frame, "Level IDs", self.validation_level_ids_var, 0)
        add_labeled_combobox(
            frame,
            "Difficulty",
            self.validation_difficulty_var,
            ["", *self.difficulty_names],
            1,
        )
        ttk.Checkbutton(frame, text="Run Swift tests", variable=self.validation_swift_tests_var).grid(
            row=2,
            column=0,
            sticky="w",
            pady=3,
        )
        self.validate_button = ttk.Button(frame, text="Validate", command=self._on_validate)
        self.validate_button.grid(row=2, column=1, sticky="e", pady=3)

    def _build_command_preview(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Command Preview", padding=8)
        frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        frame.grid_columnconfigure(0, weight=1)
        entry = ttk.Entry(frame, textvariable=self.command_preview_var, state="readonly")
        entry.grid(row=0, column=0, sticky="ew")

    def _build_summary_section(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent)
        frame.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        for column in range(4):
            frame.grid_columnconfigure(column, weight=1)

        self.status_label = ttk.Label(frame, textvariable=self.status_var, foreground=STATUS_COLORS["ready"])
        self.status_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Label(frame, textvariable=self.accepted_var).grid(row=0, column=1, sticky="w", padx=(0, 8))
        ttk.Label(frame, textvariable=self.rejected_var).grid(row=0, column=2, sticky="w", padx=(0, 8))
        ttk.Label(frame, textvariable=self.swift_summary_var).grid(row=0, column=3, sticky="w")

    def _build_preview_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Generation Preview", padding=8)
        frame.grid(row=4, column=0, sticky="nsew", pady=(0, 8))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        columns = ("difficulty", "template", "variant", "seed", "nodes", "quality")
        self.preview_tree = ttk.Treeview(frame, columns=columns, show="headings", height=6)
        self.preview_tree.heading("difficulty", text="Difficulty")
        self.preview_tree.heading("template", text="Template")
        self.preview_tree.heading("variant", text="Variant")
        self.preview_tree.heading("seed", text="Seed")
        self.preview_tree.heading("nodes", text="Nodes")
        self.preview_tree.heading("quality", text="Quality")
        self.preview_tree.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.preview_tree.bind("<<TreeviewSelect>>", lambda _event: self._draw_selected_preview())

        self.preview_canvas = tk.Canvas(frame, width=320, height=190, background="#f8fafc")
        self.preview_canvas.grid(row=0, column=1, sticky="nsew")
        self.preview_canvas.bind("<Configure>", lambda _event: self._draw_selected_preview())

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        for column in range(4):
            button_frame.grid_columnconfigure(column, weight=1)
        ttk.Button(button_frame, text="Approve Selected", command=self._on_approve_selected).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(button_frame, text="Reject Selected", command=self._on_reject_selected).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(button_frame, text="Regenerate Selected", command=self._on_regenerate_selected).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(button_frame, text="Write Approved", command=self._on_write_approved).grid(row=0, column=3, sticky="ew", padx=(4, 0))

    def _build_log_panel(self, parent: ttk.Frame) -> None:
        self.log_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=10)
        self.log_text.grid(row=5, column=0, sticky="nsew")
        parent.grid_rowconfigure(5, weight=1)

    def _bind_preview_updates(self) -> None:
        variables = [
            self.start_var,
            self.count_var,
            self.difficulty_var,
            self.generator_architecture_var,
            self.template_var,
            self.recipe_pool_var,
            self.layouts_per_recipe_var,
            self.road_shapes_per_layout_var,
            self.layout_orientation_var,
            self.layout_size_profile_var,
            self.vertical_route_probability_var,
            self.seed_var,
            self.max_attempts_var,
            self.candidate_pool_var,
            self.dry_run_var,
            self.overwrite_var,
            self.swift_tests_var,
            self.compare_existing_var,
            self.prefer_vertical_for_long_routes_var,
            self.swift_timeout_var,
            self.levels_output_var,
            self.solutions_output_var,
            self.report_path_var,
            self.json_report_path_var,
            self.map_seed_path_var,
            self.debug_failures_var,
            self.editor_drafts_var,
        ]
        for variable in variables:
            variable.trace_add("write", lambda *_args: self._update_command_preview())

        for variable in [self.report_path_var, self.json_report_path_var]:
            variable.trace_add("write", lambda *_args: self._refresh_open_buttons())

    def _current_state(self) -> GuiGenerationState:
        return GuiGenerationState(
            start_level_number=self.start_var.get(),
            count=self.count_var.get(),
            difficulty=self.difficulty_var.get(),
            generator_architecture=self.generator_architecture_var.get(),
            template_name=self.template_var.get(),
            recipe_pool_size=self.recipe_pool_var.get(),
            layouts_per_recipe=self.layouts_per_recipe_var.get(),
            road_shapes_per_layout=self.road_shapes_per_layout_var.get(),
            layout_orientation_preference=self.layout_orientation_var.get(),
            layout_size_profile=self.layout_size_profile_var.get(),
            vertical_route_probability=self.vertical_route_probability_var.get(),
            prefer_vertical_for_long_routes=self.prefer_vertical_for_long_routes_var.get(),
            seed=self.seed_var.get(),
            dry_run=self.dry_run_var.get(),
            overwrite=self.overwrite_var.get(),
            run_swift_tests=self.swift_tests_var.get(),
            compare_against_existing=self.compare_existing_var.get(),
            levels_output_dir=self.levels_output_var.get(),
            solutions_output_dir=self.solutions_output_var.get(),
            report_path=self.report_path_var.get(),
            json_report_path=self.json_report_path_var.get(),
            map_seed_path=self.map_seed_path_var.get(),
            debug_failures_dir=self.debug_failures_var.get(),
            max_attempts_per_level=self.max_attempts_var.get(),
            candidate_pool_size=self.candidate_pool_var.get(),
            swift_timeout_seconds=self.swift_timeout_var.get(),
        )

    def _on_generate(self) -> None:
        state = self._current_state()
        if state.generator_architecture == "v2_legacy":
            self.append_log(f"WARNING: {LEGACY_GENERATOR_WARNING}")
        self.cancel_requested = False
        self.generate_button.configure(state=tk.DISABLED)
        self._set_status("Running...", "running")
        self.append_log("Running generation...")

        def worker() -> None:
            try:
                result = self.controller.generate_from_state(state)
                summary = format_generation_result(result)
            except ValueError as exc:
                message = str(exc)
                self.root.after(0, lambda message=message: self._show_value_error(message))
                return
            except Exception as exc:
                message = exc
                details = traceback.format_exc()
                self.root.after(0, lambda message=message, details=details: self._show_unexpected_error(message, details))
                return
            self.root.after(0, lambda: self._finish_generation(result, summary))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_generation(self, result, summary: str) -> None:
        if self.cancel_requested:
            self.append_log("Generation finished after cancellation request; results were ignored.")
            self.generate_button.configure(state=tk.NORMAL)
            self._set_status("Ready", "ready")
            return
        self.latest_result = result
        self.approved_candidates = list(result.accepted)
        self.append_log(summary)
        self._set_status("Passed" if result.passed else "Failed", "passed" if result.passed else "failed")
        self.accepted_var.set(f"Accepted: {len(result.accepted)}")
        self.rejected_var.set(f"Rejected: {result.rejected_candidate_count}")
        self.swift_summary_var.set(self._summary_label_for_swift(result.swift_test_summary))
        self.generate_button.configure(state=tk.NORMAL)
        self._refresh_open_buttons()
        self._populate_preview_table(result.accepted)

    def _on_generate_production(self) -> None:
        state = self._current_state()
        self.production_generate_button.configure(state=tk.DISABLED)
        self.generate_button.configure(state=tk.DISABLED)
        self._set_status("Production: planning", "running")
        self.append_log(
            "Starting one-action production V3 generation. All files remain in "
            "staging until Python and Swift validation pass."
        )

        def progress(stage: str, message: str) -> None:
            self.root.after(0, lambda: self._show_production_progress(stage, message))

        def worker() -> None:
            try:
                result = self.controller.generate_production_from_state(
                    state,
                    progress=progress,
                )
                summary = format_production_campaign_result(result)
            except ValueError as exc:
                message = str(exc)
                self.root.after(
                    0,
                    lambda message=message: self._show_value_error(
                        message, button=self.production_generate_button
                    ),
                )
                return
            except Exception as exc:
                message = exc
                details = traceback.format_exc()
                self.root.after(
                    0,
                    lambda message=message, details=details: self._show_unexpected_error(
                        message,
                        details,
                        button=self.production_generate_button,
                    ),
                )
                return
            self.root.after(
                0, lambda: self._finish_production_generation(result, summary)
            )

        threading.Thread(target=worker, daemon=True).start()

    def _show_production_progress(self, stage: str, message: str) -> None:
        self._set_status(f"Production: {stage}", "running")
        self.append_log(f"[{stage}] {message}")

    def _finish_production_generation(self, result, summary: str) -> None:
        self.latest_production_result = result
        self.append_log(summary)
        color = "passed" if result.passed else "failed"
        self._set_status(result.status, color)
        self.accepted_var.set(f"Accepted: {result.selected_count}")
        self.swift_summary_var.set(
            "Swift: Passed" if result.passed else "Swift: Failed or not reached"
        )
        self.production_generate_button.configure(state=tk.NORMAL)
        self.generate_button.configure(state=tk.NORMAL)
        self._refresh_open_buttons()

    def _on_validate(self) -> None:
        self.validate_button.configure(state=tk.DISABLED)
        self._set_status("Running validation...", "running")
        self.append_log("Running validation...")

        level_ids_text = self.validation_level_ids_var.get()
        difficulty = self.validation_difficulty_var.get()
        run_swift_tests = self.validation_swift_tests_var.get()
        levels_output_dir = self.levels_output_var.get()
        solutions_output_dir = self.solutions_output_var.get()
        swift_timeout_seconds = self.swift_timeout_var.get()

        def worker() -> None:
            try:
                result = self.controller.validate_existing_levels(
                    level_ids_text=level_ids_text,
                    difficulty=difficulty,
                    run_swift_tests=run_swift_tests,
                    levels_output_dir=levels_output_dir,
                    solutions_output_dir=solutions_output_dir,
                    swift_timeout_seconds=swift_timeout_seconds,
                )
                summary = format_validation_result(result)
            except ValueError as exc:
                message = str(exc)
                self.root.after(
                    0,
                    lambda message=message: self._show_value_error(message, button=self.validate_button),
                )
                return
            except Exception as exc:
                message = exc
                details = traceback.format_exc()
                self.root.after(
                    0,
                    lambda message=message, details=details: self._show_unexpected_error(
                        message,
                        details,
                        button=self.validate_button,
                    ),
                )
                return
            self.root.after(0, lambda: self._finish_validation(result, summary))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_validation(self, result, summary: str) -> None:
        self.append_log(summary)
        self._set_status(
            "Validation Passed" if result.passed else "Validation Failed",
            "passed" if result.passed else "failed",
        )
        self.swift_summary_var.set(self._summary_label_for_swift(result.swift_summary))
        self.validate_button.configure(state=tk.NORMAL)

    def _show_value_error(self, message: str, *, button=None) -> None:
        messagebox.showerror("Invalid input", message)
        self.append_log(f"Invalid input: {message}")
        self._set_status("Failed", "failed")
        (button or self.generate_button).configure(state=tk.NORMAL)
        self.generate_button.configure(state=tk.NORMAL)

    def _show_unexpected_error(self, exc: Exception, details: str, *, button=None) -> None:
        messagebox.showerror("Unexpected error", str(exc))
        self.append_log(details)
        self._set_status("Failed", "failed")
        (button or self.generate_button).configure(state=tk.NORMAL)
        self.generate_button.configure(state=tk.NORMAL)

    def _on_open_report(self) -> None:
        production_report = (
            self.latest_production_result.report_path
            if self.latest_production_result is not None
            else None
        )
        if production_report is not None and Path(production_report).exists():
            self._open_path_with_error(Path(production_report))
            return
        markdown_path = Path(self.report_path_var.get()).expanduser() if self.report_path_var.get().strip() else None
        json_path = Path(self.json_report_path_var.get()).expanduser() if self.json_report_path_var.get().strip() else None
        target = None
        if markdown_path is not None and markdown_path.exists():
            target = markdown_path
        elif json_path is not None and json_path.exists():
            target = json_path
        if target is None:
            messagebox.showerror("Report not found", "No markdown or JSON report exists at the configured paths.")
            return
        self._open_path_with_error(target)

    def _on_open_levels_folder(self) -> None:
        self._open_configured_directory(self.levels_output_var.get(), "Levels output folder")

    def _on_open_solutions_folder(self) -> None:
        self._open_configured_directory(self.solutions_output_var.get(), "Solutions output folder")

    def _on_cancel(self) -> None:
        self.cancel_requested = True
        self._set_status("Cancel requested", "running")
        self.append_log("Cancel requested. The current worker result will be ignored when it finishes.")

    def _on_open_level_editor(self) -> None:
        candidate = self._selected_candidate()
        try:
            command = [sys.executable, "Tools/LevelEditor/run_level_editor.py"]
            if candidate is not None:
                handoff = self.controller.prepare_candidate_for_editor(
                    candidate,
                    draft_directory=self.editor_drafts_var.get(),
                )
                command.extend([
                    "--level", str(handoff.level_path),
                    "--solution", str(handoff.solution_path),
                    "--quality", str(handoff.quality_path),
                ])
                self.append_log(
                    f"Opened {candidate.level_id} and its solution as an editor draft."
                )
            subprocess.Popen(command, cwd=Path(__file__).resolve().parents[4])
        except Exception as exc:
            messagebox.showerror("Could not open Level Editor", str(exc))

    def _populate_preview_table(self, candidates) -> None:
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        for candidate in candidates:
            variant = next((note.split(":", 1)[1].strip() for note in candidate.generation_notes if note.startswith("Template variant:")), "")
            quality = f"{candidate.quality_score.total:.2f}" if candidate.quality_score is not None else ""
            self.preview_tree.insert(
                "",
                tk.END,
                iid=candidate.level_id,
                values=(
                    candidate.difficulty,
                    candidate.template_name,
                    variant,
                    candidate.seed,
                    f"{candidate.node_count}/{candidate.edge_count}",
                    quality,
                ),
            )
        children = self.preview_tree.get_children()
        if children:
            self.preview_tree.selection_set(children[0])
            self._draw_selected_preview()

    def _selected_candidate(self):
        if self.latest_result is None:
            return None
        selection = self.preview_tree.selection()
        if not selection:
            return None
        level_id = selection[0]
        return next((candidate for candidate in self.latest_result.accepted if candidate.level_id == level_id), None)

    def _draw_selected_preview(self) -> None:
        candidate = self._selected_candidate()
        self.preview_canvas.delete("all")
        if candidate is None:
            return
        level = candidate.level_document
        nodes = level.graph.nodes
        if not nodes:
            return
        width = max(self.preview_canvas.winfo_width(), int(self.preview_canvas["width"]))
        height = max(self.preview_canvas.winfo_height(), int(self.preview_canvas["height"]))
        margin = 18
        xs = [node.x for node in nodes]
        ys = [node.y for node in nodes]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1e-9)
        span_y = max(max_y - min_y, 1e-9)
        node_by_id = {node.id: node for node in nodes}

        def point(node_id: str) -> tuple[float, float]:
            node = node_by_id[node_id]
            x = margin + ((node.x - min_x) / span_x * (width - (2 * margin)))
            y = height - (margin + ((node.y - min_y) / span_y * (height - (2 * margin))))
            return x, y

        for edge in level.graph.edges:
            if edge.fromNodeID in node_by_id and edge.toNodeID in node_by_id:
                x1, y1 = point(edge.fromNodeID)
                x2, y2 = point(edge.toNodeID)
                self.preview_canvas.create_line(x1, y1, x2, y2, fill="#64748b", width=2)
        for node in nodes:
            x, y = point(node.id)
            fill = "#94a3b8"
            if node.id == level.startNodeID:
                fill = "#22c55e"
            elif node.id == level.packageNodeID:
                fill = "#f59e0b"
            elif node.id == level.destinationNodeID:
                fill = "#ef4444"
            elif len(node.outgoingEdgeIDs) > 1:
                fill = "#3b82f6"
            self.preview_canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill=fill, outline="#0f172a")
            self.preview_canvas.create_text(x + 8, y - 8, text=node.id, anchor="w", font=("TkDefaultFont", 8))

    def _on_approve_selected(self) -> None:
        candidate = self._selected_candidate()
        if candidate is not None and candidate not in self.approved_candidates:
            self.approved_candidates.append(candidate)
            self.append_log(f"Approved {candidate.level_id}.")

    def _on_reject_selected(self) -> None:
        candidate = self._selected_candidate()
        if candidate is None:
            return
        self.approved_candidates = [approved for approved in self.approved_candidates if approved.level_id != candidate.level_id]
        self.append_log(f"Rejected {candidate.level_id} from approved candidates.")

    def _on_regenerate_selected(self) -> None:
        candidate = self._selected_candidate()
        if candidate is None:
            return
        self.start_var.set(candidate.level_id.removeprefix("level_").lstrip("0") or "1")
        self.count_var.set("1")
        self._on_generate()

    def _on_write_approved(self) -> None:
        if not self.approved_candidates:
            messagebox.showerror("No approved candidates", "Approve at least one candidate before writing.")
            return
        try:
            written = self.controller.write_approved_levels(
                self.approved_candidates,
                levels_output_dir=self.levels_output_var.get(),
                solutions_output_dir=self.solutions_output_var.get(),
                overwrite=self.overwrite_var.get(),
            )
        except Exception as exc:
            messagebox.showerror("Write failed", str(exc))
            return
        self.append_log("Wrote approved files:\n" + "\n".join(f"  {path}" for path in written))

    def _open_configured_directory(self, value: str, label: str) -> None:
        if not value.strip():
            messagebox.showerror("Folder not configured", f"{label} is not configured.")
            return
        self._open_path_with_error(Path(value).expanduser())

    def _open_path_with_error(self, path: Path) -> None:
        try:
            open_path(path)
        except Exception as exc:
            messagebox.showerror("Could not open path", str(exc))

    def _reset_form(self) -> None:
        self.start_var.set("12")
        self.count_var.set("1")
        self.difficulty_var.set("easy")
        self.generator_architecture_var.set(DEFAULT_GENERATOR_ARCHITECTURE)
        self.template_var.set("mixed")
        self.recipe_pool_var.set(str(DEFAULT_RECIPE_POOL_SIZE))
        self.layouts_per_recipe_var.set(str(DEFAULT_LAYOUTS_PER_RECIPE))
        self.road_shapes_per_layout_var.set(str(DEFAULT_ROAD_SHAPES_PER_LAYOUT))
        self.layout_orientation_var.set(DEFAULT_LAYOUT_ORIENTATION_PREFERENCE)
        self.layout_size_profile_var.set(DEFAULT_LAYOUT_SIZE_PROFILE)
        self.vertical_route_probability_var.set(str(DEFAULT_VERTICAL_ROUTE_PROBABILITY))
        self.prefer_vertical_for_long_routes_var.set(True)
        self.seed_var.set("")
        self.max_attempts_var.set(str(DEFAULT_MAX_ATTEMPTS_PER_LEVEL))
        self.candidate_pool_var.set(str(DEFAULT_CANDIDATE_POOL_SIZE))
        self.dry_run_var.set(True)
        self.overwrite_var.set(False)
        self.swift_tests_var.set(False)
        self.compare_existing_var.set(True)
        self.swift_timeout_var.set("180")
        self.levels_output_var.set(try_get_default_levels_directory())
        self.solutions_output_var.set(try_get_default_solutions_directory())
        self.report_path_var.set(try_get_default_markdown_report_path())
        self.json_report_path_var.set(try_get_default_json_report_path())
        self.map_seed_path_var.set("")
        self.debug_failures_var.set(try_get_default_debug_failures_directory())
        self.editor_drafts_var.set(try_get_default_editor_drafts_directory())
        self.validation_level_ids_var.set("")
        self.validation_difficulty_var.set("")
        self.validation_swift_tests_var.set(False)
        self._set_status("Ready", "ready")
        self.accepted_var.set("Accepted: 0")
        self.rejected_var.set("Rejected: 0")
        self.swift_summary_var.set("Swift: Not run")
        self.latest_production_result = None
        self.append_log("Form reset.")
        self._log_default_path_warning_if_needed()

    def _update_command_preview(self) -> None:
        self.command_preview_var.set(build_command_preview(self._current_state()))

    def _refresh_open_buttons(self) -> None:
        report_configured = bool(
            self.report_path_var.get().strip()
            or self.json_report_path_var.get().strip()
            or (
                self.latest_production_result is not None
                and self.latest_production_result.report_path is not None
            )
        )
        self.open_report_button.configure(state=tk.NORMAL if report_configured else tk.DISABLED)

    def _set_status(self, value: str, color_key: str) -> None:
        self.status_var.set(f"Status: {value}")
        self.status_label.configure(foreground=STATUS_COLORS[color_key])

    def append_log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        if self.log_text.index("end-1c") != "1.0":
            self.log_text.insert(tk.END, "\n\n")
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.NORMAL)

    def clear_log(self) -> None:
        self.log_text.delete("1.0", tk.END)
        self.append_log("Ready.")

    def _log_default_path_warning_if_needed(self) -> None:
        missing = []
        if not self.levels_output_var.get().strip():
            missing.append("levels output directory")
        if not self.solutions_output_var.get().strip():
            missing.append("solutions output directory")
        if not self.report_path_var.get().strip():
            missing.append("markdown report path")
        if not self.json_report_path_var.get().strip():
            missing.append("JSON report path")
        if missing:
            self.append_log(
                "Default paths could not be resolved for "
                + ", ".join(missing)
                + ". Choose paths manually before generating."
            )

    def _summary_label_for_swift(self, summary) -> str:
        if summary.passed is None:
            return "Swift: Not run"
        return f"Swift: {'Passed' if summary.passed else 'Failed'}"
