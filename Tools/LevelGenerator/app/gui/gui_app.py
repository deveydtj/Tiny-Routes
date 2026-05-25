from __future__ import annotations

import threading
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from ..services.difficulty_service import DifficultyService
from ..templates.template_registry import TemplateRegistry
from .gui_controller import GuiController, format_generation_result, format_validation_result
from .gui_paths import (
    open_path,
    try_get_default_debug_failures_directory,
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
    root.geometry("950x700")
    root.minsize(850, 640)
    LevelGeneratorGui(root)
    root.mainloop()


class LevelGeneratorGui:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.controller = GuiController()
        self.difficulty_names = DifficultyService().valid_names
        self.template_names = TemplateRegistry().valid_names

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
        self.difficulty_var = tk.StringVar(value="tutorial")
        self.template_var = tk.StringVar(value="mixed")
        self.seed_var = tk.StringVar(value="")
        self.max_attempts_var = tk.StringVar(value="100")

        self.dry_run_var = tk.BooleanVar(value=True)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.swift_tests_var = tk.BooleanVar(value=False)
        self.swift_timeout_var = tk.StringVar(value="180")

        self.levels_output_var = tk.StringVar(value=try_get_default_levels_directory())
        self.solutions_output_var = tk.StringVar(value=try_get_default_solutions_directory())
        self.report_path_var = tk.StringVar(value=try_get_default_markdown_report_path())
        self.json_report_path_var = tk.StringVar(value=try_get_default_json_report_path())
        self.debug_failures_var = tk.StringVar(value=try_get_default_debug_failures_directory())

        self.validation_level_ids_var = tk.StringVar(value="")
        self.validation_difficulty_var = tk.StringVar(value="")
        self.validation_swift_tests_var = tk.BooleanVar(value=False)

        self.status_var = tk.StringVar(value="Status: Ready")
        self.accepted_var = tk.StringVar(value="Accepted: 0")
        self.rejected_var = tk.StringVar(value="Rejected: 0")
        self.swift_summary_var = tk.StringVar(value="Swift: Not run")
        self.command_preview_var = tk.StringVar(value="")

    def _build_window(self) -> None:
        root_frame = ttk.Frame(self.root, padding=12)
        root_frame.grid(row=0, column=0, sticky="nsew")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        root_frame.grid_columnconfigure(0, weight=1)

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
        self._build_log_panel(root_frame)

    def _build_generation_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Generation Settings", padding=8)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        frame.grid_columnconfigure(1, weight=1)

        add_labeled_entry(frame, "Start level number", self.start_var, 0)
        add_labeled_entry(frame, "Count", self.count_var, 1)
        add_labeled_combobox(frame, "Difficulty", self.difficulty_var, self.difficulty_names, 2)
        add_labeled_combobox(frame, "Template", self.template_var, self.template_names, 3)
        add_labeled_entry(frame, "Seed", self.seed_var, 4)
        add_labeled_entry(frame, "Max attempts per level", self.max_attempts_var, 5)

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
        add_labeled_entry(frame, "Swift timeout seconds", self.swift_timeout_var, 3)

    def _build_actions_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Actions", padding=8)
        frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        for column in range(2):
            frame.grid_columnconfigure(column, weight=1)

        self.generate_button = ttk.Button(frame, text="Generate", command=self._on_generate)
        self.generate_button.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=3)
        ttk.Button(frame, text="Clear Log", command=self.clear_log).grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=3)

        self.open_report_button = ttk.Button(frame, text="Open Report", command=self._on_open_report)
        self.open_report_button.grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=3)
        ttk.Button(frame, text="Reset", command=self._reset_form).grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=3)

        self.open_levels_button = ttk.Button(frame, text="Open Levels Folder", command=self._on_open_levels_folder)
        self.open_levels_button.grid(row=2, column=0, sticky="ew", padx=(0, 4), pady=3)
        self.open_solutions_button = ttk.Button(frame, text="Open Solutions Folder", command=self._on_open_solutions_folder)
        self.open_solutions_button.grid(row=2, column=1, sticky="ew", padx=(4, 0), pady=3)

    def _build_output_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Output Settings", padding=8)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        frame.grid_columnconfigure(1, weight=1)

        add_path_picker(frame, "Levels output directory", self.levels_output_var, 0, pick_directory=True)
        add_path_picker(frame, "Solutions output directory", self.solutions_output_var, 1, pick_directory=True)
        add_path_picker(frame, "Markdown report path", self.report_path_var, 2, pick_directory=False, file_extension=".md")
        add_path_picker(frame, "JSON report path", self.json_report_path_var, 3, pick_directory=False, file_extension=".json")
        add_path_picker(frame, "Debug failures directory", self.debug_failures_var, 4, pick_directory=True)

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

    def _build_log_panel(self, parent: ttk.Frame) -> None:
        self.log_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=14)
        self.log_text.grid(row=4, column=0, sticky="nsew")
        parent.grid_rowconfigure(4, weight=1)

    def _bind_preview_updates(self) -> None:
        variables = [
            self.start_var,
            self.count_var,
            self.difficulty_var,
            self.template_var,
            self.seed_var,
            self.max_attempts_var,
            self.dry_run_var,
            self.overwrite_var,
            self.swift_tests_var,
            self.swift_timeout_var,
            self.levels_output_var,
            self.solutions_output_var,
            self.report_path_var,
            self.json_report_path_var,
            self.debug_failures_var,
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
            template_name=self.template_var.get(),
            seed=self.seed_var.get(),
            dry_run=self.dry_run_var.get(),
            overwrite=self.overwrite_var.get(),
            run_swift_tests=self.swift_tests_var.get(),
            levels_output_dir=self.levels_output_var.get(),
            solutions_output_dir=self.solutions_output_var.get(),
            report_path=self.report_path_var.get(),
            json_report_path=self.json_report_path_var.get(),
            debug_failures_dir=self.debug_failures_var.get(),
            max_attempts_per_level=self.max_attempts_var.get(),
            swift_timeout_seconds=self.swift_timeout_var.get(),
        )

    def _on_generate(self) -> None:
        state = self._current_state()
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
        self.append_log(summary)
        self._set_status("Passed" if result.passed else "Failed", "passed" if result.passed else "failed")
        self.accepted_var.set(f"Accepted: {len(result.accepted)}")
        self.rejected_var.set(f"Rejected: {result.rejected_candidate_count}")
        self.swift_summary_var.set(self._summary_label_for_swift(result.swift_test_summary))
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

    def _show_unexpected_error(self, exc: Exception, details: str, *, button=None) -> None:
        messagebox.showerror("Unexpected error", str(exc))
        self.append_log(details)
        self._set_status("Failed", "failed")
        (button or self.generate_button).configure(state=tk.NORMAL)

    def _on_open_report(self) -> None:
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
        self.difficulty_var.set("tutorial")
        self.template_var.set("mixed")
        self.seed_var.set("")
        self.max_attempts_var.set("100")
        self.dry_run_var.set(True)
        self.overwrite_var.set(False)
        self.swift_tests_var.set(False)
        self.swift_timeout_var.set("180")
        self.levels_output_var.set(try_get_default_levels_directory())
        self.solutions_output_var.set(try_get_default_solutions_directory())
        self.report_path_var.set(try_get_default_markdown_report_path())
        self.json_report_path_var.set(try_get_default_json_report_path())
        self.debug_failures_var.set(try_get_default_debug_failures_directory())
        self.validation_level_ids_var.set("")
        self.validation_difficulty_var.set("")
        self.validation_swift_tests_var.set(False)
        self._set_status("Ready", "ready")
        self.accepted_var.set("Accepted: 0")
        self.rejected_var.set("Rejected: 0")
        self.swift_summary_var.set("Swift: Not run")
        self.append_log("Form reset.")
        self._log_default_path_warning_if_needed()

    def _update_command_preview(self) -> None:
        self.command_preview_var.set(build_command_preview(self._current_state()))

    def _refresh_open_buttons(self) -> None:
        report_configured = bool(self.report_path_var.get().strip() or self.json_report_path_var.get().strip())
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
