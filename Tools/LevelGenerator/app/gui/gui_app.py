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
    LEGACY_GENERATOR_WARNING,
    LAYOUT_ORIENTATION_PREFERENCES,
    LAYOUT_SIZE_PROFILES,
)
from ..models.quality_profile import CURRENT_QUALITY_PROFILE_VERSION
from ..services.difficulty_service import DifficultyService
from ..services.quality_profile_service import QualityProfileService
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
    try_get_default_production_manifest_path,
    try_get_default_production_staging_directory,
    try_get_default_solutions_directory,
)
from .gui_state import (
    GuiGenerationState,
    build_command_preview,
    build_production_command_preview,
    to_production_campaign_config,
)
from .gui_widgets import add_labeled_combobox, add_labeled_entry, add_path_picker


APP_COLORS = {
    "background": "#f3f5f8",
    "surface": "#ffffff",
    "ink": "#172033",
    "muted": "#5f6b7c",
    "accent": "#3157d5",
    "accent_active": "#2747b0",
    "success": "#18864b",
    "warning": "#9a6100",
    "danger": "#b42318",
    "border": "#d8dee9",
}

STATUS_COLORS = {
    "ready": APP_COLORS["muted"],
    "running": APP_COLORS["warning"],
    "passed": APP_COLORS["success"],
    "failed": APP_COLORS["danger"],
}

PRODUCTION_STAGES = (
    ("planning", "Plan"),
    ("candidate_pool", "Candidates"),
    ("portfolio", "Portfolio"),
    ("staging", "Stage"),
    ("validation", "Validate"),
    ("promotion", "Promote"),
    ("completed", "Complete"),
)


def run_gui() -> None:
    root = tk.Tk()
    root.title("Tiny Routes Generator · Production V3")
    width = min(1120, max(940, root.winfo_screenwidth() - 100))
    height = min(800, max(680, root.winfo_screenheight() - 140))
    root.geometry(f"{width}x{height}")
    root.minsize(940, 680)
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
        self.quality_profile_versions = self._available_quality_profile_versions()
        self.latest_result = None
        self.latest_production_result = None
        self.approved_candidates = []
        self.cancel_requested = False
        self._production_stage_index = -1
        self._result_buttons: dict[str, ttk.Button] = {}

        self._create_variables()
        self._configure_styles()
        self._build_window()
        self._update_stage_list()
        self._bind_preview_updates()
        self._update_command_preview()
        self._refresh_result_buttons()
        self.append_log(
            "Ready for a Production V3 campaign. Configure the level range, then "
            "generate; the complete batch is staged and verified before promotion."
        )
        self._log_default_path_warning_if_needed()

    def _create_variables(self) -> None:
        self.start_var = tk.StringVar(value="1")
        self.count_var = tk.StringVar(value="1")
        self.difficulty_var = tk.StringVar(value="easy")
        self.generator_architecture_var = tk.StringVar(value="v2_legacy")
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
        self.candidate_workers_var = tk.StringVar(value="4")
        self.wave_size_var = tk.StringVar(value="1")
        self.global_attempt_budget_var = tk.StringVar(value="")
        self.quality_profile_var = tk.StringVar(
            value=CURRENT_QUALITY_PROFILE_VERSION
        )

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
        self.production_manifest_var = tk.StringVar(
            value=try_get_default_production_manifest_path()
        )
        self.staging_root_var = tk.StringVar(
            value=try_get_default_production_staging_directory()
        )

        self.validation_level_ids_var = tk.StringVar(value="")
        self.validation_difficulty_var = tk.StringVar(value="")
        self.validation_swift_tests_var = tk.BooleanVar(value=False)

        self.status_var = tk.StringVar(value="Status: Ready")
        self.accepted_var = tk.StringVar(value="Accepted: 0")
        self.rejected_var = tk.StringVar(value="Rejected: 0")
        self.swift_summary_var = tk.StringVar(value="Swift: Not run")
        self.command_preview_var = tk.StringVar(value="")
        self.legacy_command_preview_var = tk.StringVar(value="")
        self.production_plan_var = tk.StringVar(value="")
        self.production_stage_var = tk.StringVar(value="Ready")
        self.production_stage_detail_var = tk.StringVar(
            value="No production files change until every v3 gate passes."
        )
        self.production_stage_list_var = tk.StringVar(value="")

    def _configure_styles(self) -> None:
        self.root.configure(background=APP_COLORS["background"])
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure(
            ".",
            font=("Helvetica Neue", 11),
            background=APP_COLORS["background"],
            foreground=APP_COLORS["ink"],
        )
        style.configure(
            "TLabel",
            background=APP_COLORS["surface"],
            foreground=APP_COLORS["ink"],
        )
        style.configure(
            "TCheckbutton",
            background=APP_COLORS["surface"],
            foreground=APP_COLORS["ink"],
        )
        style.map(
            "TCheckbutton",
            background=[("active", APP_COLORS["surface"])],
        )
        style.configure(
            "Treeview",
            background=APP_COLORS["surface"],
            fieldbackground=APP_COLORS["surface"],
            foreground=APP_COLORS["ink"],
            rowheight=25,
        )
        style.configure(
            "Treeview.Heading",
            font=("Helvetica Neue", 10, "bold"),
            foreground=APP_COLORS["muted"],
        )
        style.configure("App.TFrame", background=APP_COLORS["background"])
        style.configure(
            "Surface.TFrame",
            background=APP_COLORS["surface"],
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Hero.TLabel",
            background=APP_COLORS["background"],
            foreground=APP_COLORS["ink"],
            font=("Helvetica Neue", 22, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=APP_COLORS["background"],
            foreground=APP_COLORS["muted"],
            font=("Helvetica Neue", 11),
        )
        style.configure(
            "CardTitle.TLabel",
            background=APP_COLORS["surface"],
            foreground=APP_COLORS["ink"],
            font=("Helvetica Neue", 13, "bold"),
        )
        style.configure(
            "CardText.TLabel",
            background=APP_COLORS["surface"],
            foreground=APP_COLORS["muted"],
        )
        style.configure(
            "Badge.TLabel",
            background="#e8edff",
            foreground=APP_COLORS["accent"],
            font=("Helvetica Neue", 10, "bold"),
            padding=(10, 5),
        )
        style.configure(
            "Warning.TLabel",
            background="#fff7e6",
            foreground=APP_COLORS["warning"],
            padding=(10, 8),
        )
        style.configure(
            "Accent.TButton",
            background=APP_COLORS["accent"],
            foreground="#ffffff",
            font=("Helvetica Neue", 12, "bold"),
            padding=(14, 10),
        )
        style.map(
            "Accent.TButton",
            background=[
                ("disabled", "#a9b5dc"),
                ("active", APP_COLORS["accent_active"]),
                ("!disabled", APP_COLORS["accent"]),
            ],
            foreground=[("disabled", "#eef1fb"), ("!disabled", "#ffffff")],
        )
        style.configure("Quiet.TButton", padding=(10, 7))
        style.configure("TNotebook", background=APP_COLORS["background"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            font=("Helvetica Neue", 11, "bold"),
            padding=(16, 9),
        )
        style.configure(
            "TLabelframe",
            background=APP_COLORS["surface"],
            bordercolor=APP_COLORS["border"],
            padding=10,
        )
        style.configure(
            "TLabelframe.Label",
            background=APP_COLORS["surface"],
            foreground=APP_COLORS["ink"],
            font=("Helvetica Neue", 11, "bold"),
        )
        style.configure(
            "Production.Horizontal.TProgressbar",
            troughcolor="#e7eaf0",
            background=APP_COLORS["accent"],
            lightcolor=APP_COLORS["accent"],
            darkcolor=APP_COLORS["accent"],
        )

    def _build_window(self) -> None:
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        header = ttk.Frame(self.root, style="App.TFrame", padding=(20, 16, 20, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ttk.Label(
            header, text="Tiny Routes Generator", style="Hero.TLabel"
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text=(
                "Build a complete campaign through the locked v3 strategy, "
                "quality, parity, and atomic-promotion pipeline."
            ),
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Label(header, text="PRODUCTION V3", style="Badge.TLabel").grid(
            row=0, column=1, rowspan=2, sticky="e"
        )

        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(
            row=1, column=0, sticky="nsew", padx=16, pady=(4, 8)
        )

        production_tab = ttk.Frame(
            self.notebook, style="App.TFrame"
        )
        advanced_tab = ttk.Frame(
            self.notebook, style="App.TFrame"
        )
        legacy_tab = ttk.Frame(
            self.notebook, style="App.TFrame"
        )
        validation_tab = ttk.Frame(
            self.notebook, style="App.TFrame", padding=(4, 12)
        )
        self.activity_tab = ttk.Frame(
            self.notebook, style="App.TFrame", padding=(4, 12)
        )
        self.notebook.add(production_tab, text="Generate")
        self.notebook.add(advanced_tab, text="Advanced")
        self.notebook.add(legacy_tab, text="Legacy preview")
        self.notebook.add(validation_tab, text="Validate existing")
        self.notebook.add(self.activity_tab, text="Activity")

        production_content = self._create_scrollable_content(production_tab)
        advanced_content = self._create_scrollable_content(advanced_tab)
        legacy_content = self._create_scrollable_content(legacy_tab)
        self._build_production_tab(production_content)
        self._build_advanced_tab(advanced_content)
        self._build_legacy_tab(legacy_content)
        self._build_validation_tab(validation_tab)
        self._build_activity_tab(self.activity_tab)
        self._build_summary_section(self.root)

    def _create_scrollable_content(self, parent: ttk.Frame) -> ttk.Frame:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        canvas = tk.Canvas(
            parent,
            borderwidth=0,
            highlightthickness=0,
            background=APP_COLORS["background"],
        )
        scrollbar = ttk.Scrollbar(
            parent, orient=tk.VERTICAL, command=canvas.yview
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        content = ttk.Frame(
            canvas, style="App.TFrame", padding=(4, 12)
        )
        window_id = canvas.create_window(
            (0, 0), window=content, anchor="nw"
        )
        content.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(window_id, width=event.width),
        )

        def scroll(event) -> None:
            target = self.root.winfo_containing(event.x_root, event.y_root)
            if target is None:
                return
            if target is canvas or str(target).startswith(str(content)):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", scroll, add="+")
        return content

    def _build_production_tab(self, parent: ttk.Frame) -> None:
        parent.grid_columnconfigure(0, weight=3, uniform="production")
        parent.grid_columnconfigure(1, weight=2, uniform="production")
        parent.grid_rowconfigure(0, weight=1)

        settings = ttk.Frame(parent, style="App.TFrame")
        settings.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        settings.grid_columnconfigure(0, weight=1)

        campaign = ttk.LabelFrame(
            settings, text="1 · Campaign", padding=(12, 10)
        )
        campaign.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        campaign.grid_columnconfigure(1, weight=1)
        campaign.grid_columnconfigure(3, weight=1)
        add_labeled_entry(
            campaign, "First level number", self.start_var, 0, column=0, width=12
        )
        add_labeled_entry(
            campaign, "Number of levels", self.count_var, 0, column=2, width=12
        )
        add_labeled_entry(
            campaign, "Seed (optional)", self.seed_var, 1, column=0
        )
        ttk.Label(
            campaign,
            text=(
                "Leave the seed blank for a fresh campaign. Enter one only when "
                "you want to reproduce the exact same mix."
            ),
            style="CardText.TLabel",
            wraplength=450,
        ).grid(
            row=2,
            column=0,
            columnspan=4,
            sticky="w",
            pady=(7, 0),
        )

        variety = ttk.Frame(
            settings, style="Surface.TFrame", padding=(16, 14)
        )
        variety.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        variety.grid_columnconfigure(0, weight=1)
        ttk.Label(
            variety, text="Progression and variety are automatic", style="CardTitle.TLabel"
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            variety,
            text=(
                "Difficulty rises with the level number from easy through "
                "expert. Within each difficulty, V3 varies the puzzle type, "
                "mechanics, route shape, and layout—there is nothing else you "
                "need to choose."
            ),
            style="CardText.TLabel",
            wraplength=500,
            justify=tk.LEFT,
        ).grid(row=1, column=0, sticky="ew", pady=(5, 10))
        ttk.Label(
            variety,
            text=(
                "The first ten production levels are easy, levels 11–25 are "
                "medium, 26–40 are hard, and level 41 onward is expert."
            ),
            style="CardText.TLabel",
            wraplength=500,
            justify=tk.LEFT,
        ).grid(row=2, column=0, sticky="ew")
        ttk.Button(
            variety,
            text="Review advanced settings",
            style="Quiet.TButton",
            command=lambda: self.notebook.select(1),
        ).grid(row=3, column=0, sticky="w", pady=(12, 0))

        run_card = ttk.Frame(
            parent, style="Surface.TFrame", padding=(18, 16)
        )
        run_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        run_card.grid_columnconfigure(0, weight=1)
        run_card.grid_rowconfigure(8, weight=1)
        ttk.Label(
            run_card, text="Ready to generate", style="CardTitle.TLabel"
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            run_card,
            textvariable=self.production_plan_var,
            style="CardText.TLabel",
            wraplength=360,
            justify=tk.LEFT,
        ).grid(row=1, column=0, sticky="ew", pady=(5, 12))
        ttk.Label(
            run_card,
            text=(
                "V3 builds candidates, selects a diverse complete campaign, "
                "verifies Python + Swift evidence, and promotes everything as "
                "one safe transaction."
            ),
            style="CardText.TLabel",
            wraplength=360,
            justify=tk.LEFT,
        ).grid(row=2, column=0, sticky="ew", pady=(0, 14))
        self.production_generate_button = ttk.Button(
            run_card,
            text="Generate campaign",
            style="Accent.TButton",
            command=self._on_generate_production,
        )
        self.production_generate_button.grid(row=3, column=0, sticky="ew")
        ttk.Label(
            run_card,
            text="Nothing is written unless the entire campaign passes.",
            style="CardText.TLabel",
            wraplength=360,
        ).grid(row=4, column=0, sticky="w", pady=(7, 18))

        ttk.Label(
            run_card, textvariable=self.production_stage_var, style="CardTitle.TLabel"
        ).grid(row=5, column=0, sticky="w")
        self.production_progress = ttk.Progressbar(
            run_card,
            mode="determinate",
            maximum=len(PRODUCTION_STAGES),
            style="Production.Horizontal.TProgressbar",
        )
        self.production_progress.grid(row=6, column=0, sticky="ew", pady=(8, 7))
        ttk.Label(
            run_card,
            textvariable=self.production_stage_detail_var,
            style="CardText.TLabel",
            wraplength=360,
            justify=tk.LEFT,
        ).grid(row=7, column=0, sticky="ew")
        ttk.Label(
            run_card,
            textvariable=self.production_stage_list_var,
            style="CardText.TLabel",
            justify=tk.LEFT,
        ).grid(row=8, column=0, sticky="nw", pady=(12, 10))

        evidence = ttk.LabelFrame(run_card, text="Run evidence")
        evidence.grid(row=9, column=0, sticky="ew", pady=(4, 0))
        for column in range(2):
            evidence.grid_columnconfigure(column, weight=1)
        for index, (key, label) in enumerate(
            (
                ("report", "Open report"),
                ("reproduction", "Reproduction bundle"),
                ("health", "Health metrics"),
                ("workspace", "Run workspace"),
            )
        ):
            button = ttk.Button(
                evidence,
                text=label,
                style="Quiet.TButton",
                command=lambda key=key: self._open_result_artifact(key),
            )
            button.grid(
                row=index // 2,
                column=index % 2,
                sticky="ew",
                padx=(0, 4) if index % 2 == 0 else (4, 0),
                pady=3,
            )
            self._result_buttons[key] = button

    def _build_advanced_tab(self, parent: ttk.Frame) -> None:
        parent.grid_columnconfigure(0, weight=1, uniform="advanced")
        parent.grid_columnconfigure(1, weight=1, uniform="advanced")

        destinations = ttk.LabelFrame(
            parent, text="Production destinations", padding=(12, 10)
        )
        destinations.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        add_path_picker(
            destinations, "Levels", self.levels_output_var, 0, pick_directory=True
        )
        add_path_picker(
            destinations, "Solutions", self.solutions_output_var, 1, pick_directory=True
        )
        add_path_picker(
            destinations,
            "Manifest",
            self.production_manifest_var,
            2,
            pick_directory=False,
            file_extension=".json",
        )
        add_path_picker(
            destinations,
            "Staging",
            self.staging_root_var,
            3,
            pick_directory=True,
        )

        advanced = ttk.LabelFrame(
            parent, text="Performance and quality", padding=(12, 10)
        )
        advanced.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))
        advanced.grid_columnconfigure(1, weight=1)
        advanced.grid_columnconfigure(3, weight=1)
        add_labeled_entry(
            advanced,
            "Candidates",
            self.candidate_pool_var,
            0,
            column=0,
            width=10,
        )
        add_labeled_entry(
            advanced,
            "Max attempts",
            self.max_attempts_var,
            0,
            column=2,
            width=10,
        )
        add_labeled_entry(
            advanced,
            "Workers",
            self.candidate_workers_var,
            1,
            column=0,
            width=10,
        )
        add_labeled_entry(
            advanced,
            "Wave size",
            self.wave_size_var,
            1,
            column=2,
            width=10,
        )
        add_labeled_entry(
            advanced,
            "Global budget",
            self.global_attempt_budget_var,
            2,
            column=0,
            width=10,
        )
        add_labeled_entry(
            advanced,
            "Swift timeout",
            self.swift_timeout_var,
            2,
            column=2,
            width=10,
        )
        add_labeled_combobox(
            advanced,
            "Quality profile",
            self.quality_profile_var,
            self.quality_profile_versions,
            3,
            column=0,
        )

        command = ttk.LabelFrame(
            parent, text="Reproduce this run", padding=(12, 9)
        )
        command.grid(row=1, column=0, columnspan=2, sticky="ew")
        command.grid_columnconfigure(0, weight=1)
        ttk.Entry(
            command, textvariable=self.command_preview_var, state="readonly"
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(
            command,
            text="Copy",
            style="Quiet.TButton",
            command=lambda: self._copy_to_clipboard(
                self.command_preview_var.get(), "Production command copied."
            ),
        ).grid(row=0, column=1)

    def _build_legacy_tab(self, parent: ttk.Frame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)
        ttk.Label(
            parent,
            text=(
                "Compatibility tooling only · v2 recipe output is not eligible "
                "for production promotion."
            ),
            style="Warning.TLabel",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 8))

        form = ttk.Frame(parent, style="App.TFrame")
        form.grid(row=1, column=0, sticky="ew")
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)
        left = ttk.Frame(form, style="App.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_columnconfigure(0, weight=1)
        right = ttk.Frame(form, style="App.TFrame")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.grid_columnconfigure(0, weight=1)
        self._build_generation_section(left)
        self._build_options_section(left)
        self._build_actions_section(left)
        self._build_output_section(right)
        self._build_legacy_command_preview(right)
        self._build_preview_section(parent)

    def _build_validation_tab(self, parent: ttk.Frame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        intro = ttk.Frame(parent, style="Surface.TFrame", padding=16)
        intro.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        intro.grid_columnconfigure(0, weight=1)
        ttk.Label(
            intro, text="Validate the levels already on disk", style="CardTitle.TLabel"
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            intro,
            text=(
                "Enter IDs separated by spaces or commas. Validation reads the "
                "configured production level and solution folders without "
                "generating or promoting content."
            ),
            style="CardText.TLabel",
            wraplength=760,
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        content = ttk.Frame(parent, style="App.TFrame")
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        self._build_validation_section(content)

    def _build_activity_tab(self, parent: ttk.Frame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        toolbar = ttk.Frame(parent, style="App.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.grid_columnconfigure(0, weight=1)
        ttk.Label(
            toolbar,
            text="Generation, validation, and failure details",
            style="Subtitle.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            toolbar, text="Clear activity", command=self.clear_log
        ).grid(row=0, column=1, sticky="e")
        self._build_log_panel(parent)

    def _build_generation_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Legacy recipe settings", padding=8)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(3, weight=1)

        add_labeled_entry(frame, "Start", self.start_var, 0, column=0, width=9)
        add_labeled_entry(frame, "Count", self.count_var, 0, column=2, width=9)
        add_labeled_combobox(
            frame, "Difficulty", self.difficulty_var, self.difficulty_names, 1, column=0, width=12
        )
        add_labeled_combobox(
            frame, "Recipe", self.template_var, self.template_names, 1, column=2, width=12
        )
        add_labeled_entry(
            frame, "Recipe pool", self.recipe_pool_var, 2, column=0, width=9
        )
        add_labeled_entry(
            frame, "Layouts", self.layouts_per_recipe_var, 2, column=2, width=9
        )
        add_labeled_entry(
            frame, "Road shapes", self.road_shapes_per_layout_var, 3, column=0, width=9
        )
        add_labeled_combobox(
            frame,
            "Orientation",
            self.layout_orientation_var,
            self.layout_orientation_preferences,
            3,
            column=2,
            width=12,
        )
        add_labeled_combobox(
            frame,
            "Layout size",
            self.layout_size_profile_var,
            self.layout_size_profiles,
            4,
            column=0,
            width=12,
        )
        add_labeled_entry(
            frame,
            "Vertical chance",
            self.vertical_route_probability_var,
            4,
            column=2,
            width=9,
        )
        ttk.Checkbutton(
            frame,
            text="Prefer vertical for long routes",
            variable=self.prefer_vertical_for_long_routes_var,
        ).grid(row=5, column=0, columnspan=4, sticky="w", pady=3)
        add_labeled_entry(frame, "Seed", self.seed_var, 6, column=0, width=9)
        add_labeled_entry(
            frame, "Max attempts", self.max_attempts_var, 6, column=2, width=9
        )
        add_labeled_entry(
            frame, "Candidates", self.candidate_pool_var, 7, column=0, width=9
        )

    def _build_options_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Legacy output policy", padding=8)
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        frame.grid_columnconfigure(1, weight=1)

        ttk.Checkbutton(frame, text="Dry run", variable=self.dry_run_var).grid(row=0, column=0, sticky="w", pady=3)
        ttk.Checkbutton(frame, text="Overwrite", variable=self.overwrite_var).grid(row=0, column=1, sticky="w", pady=3)
        ttk.Checkbutton(frame, text="Run Swift tests", variable=self.swift_tests_var).grid(
            row=1,
            column=0,
            sticky="w",
            pady=3,
        )
        ttk.Checkbutton(frame, text="Avoid similar existing levels", variable=self.compare_existing_var).grid(
            row=1,
            column=1,
            sticky="w",
            pady=3,
        )

    def _build_actions_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Legacy actions", padding=8)
        frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        for column in range(2):
            frame.grid_columnconfigure(column, weight=1)

        self.generate_button = ttk.Button(
            frame, text="Generate legacy preview", command=self._on_generate
        )
        self.generate_button.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=3)
        ttk.Button(
            frame, text="Open in Level Editor", command=self._on_open_level_editor
        ).grid(
            row=0, column=1, sticky="ew", padx=(4, 0), pady=3
        )

        self.open_report_button = ttk.Button(
            frame, text="Open legacy report", command=self._on_open_report
        )
        self.open_report_button.grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=3)
        ttk.Button(frame, text="Reset", command=self._reset_form).grid(
            row=1, column=1, sticky="ew", padx=(4, 0), pady=3
        )

    def _build_output_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Output Settings", padding=8)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        frame.grid_columnconfigure(1, weight=1)

        add_path_picker(frame, "Levels", self.levels_output_var, 0, pick_directory=True)
        add_path_picker(frame, "Solutions", self.solutions_output_var, 1, pick_directory=True)
        add_path_picker(frame, "Markdown report", self.report_path_var, 2, pick_directory=False, file_extension=".md")
        add_path_picker(frame, "JSON report", self.json_report_path_var, 3, pick_directory=False, file_extension=".json")
        add_path_picker(
            frame,
            "Map seed",
            self.map_seed_path_var,
            4,
            pick_directory=False,
            file_extension=".json",
            save_file=False,
        )
        add_path_picker(frame, "Debug failures", self.debug_failures_var, 5, pick_directory=True)
        add_path_picker(frame, "Editor drafts", self.editor_drafts_var, 6, pick_directory=True)

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
        self.validate_button.grid(row=2, column=1, sticky="ew", pady=3)
        add_path_picker(
            frame, "Levels folder", self.levels_output_var, 3, pick_directory=True
        )
        add_path_picker(
            frame,
            "Solutions folder",
            self.solutions_output_var,
            4,
            pick_directory=True,
        )

    def _build_legacy_command_preview(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Legacy command", padding=8)
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        frame.grid_columnconfigure(0, weight=1)
        ttk.Entry(
            frame, textvariable=self.legacy_command_preview_var, state="readonly"
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(
            frame,
            text="Copy",
            command=lambda: self._copy_to_clipboard(
                self.legacy_command_preview_var.get(), "Legacy command copied."
            ),
        ).grid(row=0, column=1)

    def _build_summary_section(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent, style="Surface.TFrame", padding=(16, 9))
        frame.grid(row=2, column=0, sticky="ew")
        for column in range(4):
            frame.grid_columnconfigure(column, weight=1)

        self.status_label = ttk.Label(frame, textvariable=self.status_var, foreground=STATUS_COLORS["ready"])
        self.status_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Label(frame, textvariable=self.accepted_var).grid(row=0, column=1, sticky="w", padx=(0, 8))
        ttk.Label(frame, textvariable=self.rejected_var).grid(row=0, column=2, sticky="w", padx=(0, 8))
        ttk.Label(frame, textvariable=self.swift_summary_var).grid(row=0, column=3, sticky="w")

    def _build_preview_section(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Generation Preview", padding=8)
        frame.grid(row=2, column=0, sticky="nsew", pady=(0, 8))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        columns = ("difficulty", "template", "variant", "seed", "nodes", "quality")
        self.preview_tree = ttk.Treeview(frame, columns=columns, show="headings", height=6)
        self.preview_tree.heading("difficulty", text="Difficulty")
        self.preview_tree.heading("template", text="Template")
        self.preview_tree.heading("variant", text="Variant")
        self.preview_tree.heading("seed", text="Seed")
        self.preview_tree.heading("nodes", text="Nodes")
        self.preview_tree.heading("quality", text="Quality")
        for column, width in {
            "difficulty": 85,
            "template": 130,
            "variant": 130,
            "seed": 90,
            "nodes": 75,
            "quality": 75,
        }.items():
            self.preview_tree.column(column, width=width, minwidth=60, stretch=True)
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
        ttk.Button(button_frame, text="Write legacy fixtures", command=self._on_write_approved).grid(row=0, column=3, sticky="ew", padx=(4, 0))

    def _build_log_panel(self, parent: ttk.Frame) -> None:
        self.log_text = scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            height=18,
            background="#101828",
            foreground="#e6eaf2",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=10,
            font=("SF Mono", 10),
        )
        self.log_text.grid(row=1, column=0, sticky="nsew")
        parent.grid_rowconfigure(1, weight=1)

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
            self.candidate_workers_var,
            self.wave_size_var,
            self.global_attempt_budget_var,
            self.quality_profile_var,
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
            self.production_manifest_var,
            self.staging_root_var,
        ]
        for variable in variables:
            variable.trace_add("write", lambda *_args: self._update_command_preview())

        for variable in [
            self.report_path_var,
            self.json_report_path_var,
            self.production_manifest_var,
        ]:
            variable.trace_add(
                "write", lambda *_args: self._refresh_result_buttons()
            )

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
            candidate_workers=self.candidate_workers_var.get(),
            wave_size=self.wave_size_var.get(),
            global_attempt_budget=self.global_attempt_budget_var.get(),
            quality_profile_version=self.quality_profile_var.get(),
            production_manifest_path=self.production_manifest_var.get(),
            staging_root=self.staging_root_var.get(),
        )

    def _on_generate(self) -> None:
        state = self._current_state()
        state.generator_architecture = "v2_legacy"
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
        self._refresh_result_buttons()
        self._populate_preview_table(result.accepted)

    def _on_generate_production(self) -> None:
        state = self._current_state()
        try:
            to_production_campaign_config(state)
        except ValueError as exc:
            self._show_value_error(
                str(exc), button=self.production_generate_button
            )
            return
        self.latest_production_result = None
        self._production_stage_index = -1
        self.production_progress.configure(value=0)
        self.production_stage_var.set("Planning")
        self.production_stage_detail_var.set(
            "Preparing a deterministic, all-or-nothing campaign request."
        )
        self._update_stage_list()
        self._refresh_result_buttons()
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
        stage_keys = [key for key, _label in PRODUCTION_STAGES]
        if stage in stage_keys:
            self._production_stage_index = max(
                self._production_stage_index, stage_keys.index(stage)
            )
            self.production_progress.configure(
                value=self._production_stage_index + 1
            )
            label = dict(PRODUCTION_STAGES)[stage]
            self.production_stage_var.set(label)
        else:
            self.production_stage_var.set(stage.replace("_", " ").title())
        self.production_stage_detail_var.set(message)
        self._update_stage_list()
        self._set_status(f"Production: {stage}", "running")
        self.append_log(f"[{stage}] {message}")

    def _finish_production_generation(self, result, summary: str) -> None:
        self.latest_production_result = result
        self.append_log(summary)
        color = "passed" if result.passed else "failed"
        self._set_status(result.status, color)
        if result.passed:
            self._production_stage_index = len(PRODUCTION_STAGES) - 1
            self.production_progress.configure(value=len(PRODUCTION_STAGES))
            self.production_stage_var.set("Campaign promoted")
            self.production_stage_detail_var.set(
                "Every requested level passed v3 strategy, quality, Python, "
                "and Swift validation before atomic promotion."
            )
        else:
            self.production_stage_var.set("No production changes")
            self.production_stage_detail_var.set(
                result.failure_reason or "The campaign did not pass every gate."
            )
        self._update_stage_list()
        self.accepted_var.set(f"Accepted: {result.selected_count}")
        self.rejected_var.set(
            f"Requested: {result.requested_count}"
        )
        self.swift_summary_var.set(
            "Swift: Passed" if result.passed else "Swift: Failed or not reached"
        )
        self.production_generate_button.configure(state=tk.NORMAL)
        self.generate_button.configure(state=tk.NORMAL)
        self._refresh_result_buttons()
        self.notebook.select(self.activity_tab)

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
        if button is self.production_generate_button:
            self.production_stage_var.set("Check campaign settings")
            self.production_stage_detail_var.set(message)
        (button or self.generate_button).configure(state=tk.NORMAL)
        self.generate_button.configure(state=tk.NORMAL)

    def _show_unexpected_error(self, exc: Exception, details: str, *, button=None) -> None:
        messagebox.showerror("Unexpected error", str(exc))
        self.append_log(details)
        self._set_status("Failed", "failed")
        if button is self.production_generate_button:
            self.production_stage_var.set("Run failed")
            self.production_stage_detail_var.set(str(exc))
        (button or self.generate_button).configure(state=tk.NORMAL)
        self.generate_button.configure(state=tk.NORMAL)

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
        self.start_var.set("1")
        self.count_var.set("1")
        self.difficulty_var.set("easy")
        self.generator_architecture_var.set("v2_legacy")
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
        self.candidate_workers_var.set("4")
        self.wave_size_var.set("1")
        self.global_attempt_budget_var.set("")
        self.quality_profile_var.set(CURRENT_QUALITY_PROFILE_VERSION)
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
        self.production_manifest_var.set(
            try_get_default_production_manifest_path()
        )
        self.staging_root_var.set(
            try_get_default_production_staging_directory()
        )
        self.validation_level_ids_var.set("")
        self.validation_difficulty_var.set("")
        self.validation_swift_tests_var.set(False)
        self._set_status("Ready", "ready")
        self.accepted_var.set("Accepted: 0")
        self.rejected_var.set("Rejected: 0")
        self.swift_summary_var.set("Swift: Not run")
        self.latest_production_result = None
        self._production_stage_index = -1
        self.production_progress.configure(value=0)
        self.production_stage_var.set("Ready")
        self.production_stage_detail_var.set(
            "No production files change until every v3 gate passes."
        )
        self._update_stage_list()
        self._refresh_result_buttons()
        self.append_log("Form reset.")
        self._log_default_path_warning_if_needed()

    def _update_command_preview(self) -> None:
        state = self._current_state()
        self.command_preview_var.set(build_production_command_preview(state))
        state.generator_architecture = "v2_legacy"
        self.legacy_command_preview_var.set(build_command_preview(state))
        try:
            start = int(state.start_level_number)
            count = int(state.count)
            end = start + count - 1
            level_text = (
                f"level_{start:03d}"
                if count == 1
                else f"level_{start:03d} through level_{end:03d}"
            )
        except ValueError:
            level_text = "Enter a valid level range"
        seed_text = state.seed.strip() or "chosen and reported automatically"
        budget_text = state.global_attempt_budget.strip() or (
            "automatic (count × attempts + portfolio allowance)"
        )
        self.production_plan_var.set(
            f"{level_text}\n"
            "Difficulty: progressive by level number (easy → expert)\n"
            "Puzzle type: varied automatically within each difficulty\n"
            f"Seed: {seed_text}\n"
            f"Quality: {state.quality_profile_version} · Attempt budget: {budget_text}"
        )

    def _refresh_result_buttons(self) -> None:
        report_configured = bool(
            self.report_path_var.get().strip()
            or self.json_report_path_var.get().strip()
        )
        self.open_report_button.configure(state=tk.NORMAL if report_configured else tk.DISABLED)
        result = self.latest_production_result
        paths = {
            "report": getattr(result, "report_path", None),
            "reproduction": getattr(result, "reproducibility_bundle_path", None),
            "health": getattr(result, "health_report_path", None),
            "workspace": getattr(result, "workspace_path", None),
        }
        for key, button in self._result_buttons.items():
            button.configure(
                state=tk.NORMAL if paths.get(key) is not None else tk.DISABLED
            )

    def _open_result_artifact(self, key: str) -> None:
        result = self.latest_production_result
        if result is None:
            messagebox.showerror("No run evidence", "Run a production campaign first.")
            return
        attributes = {
            "report": "report_path",
            "reproduction": "reproducibility_bundle_path",
            "health": "health_report_path",
            "workspace": "workspace_path",
        }
        path = getattr(result, attributes[key], None)
        if path is None:
            messagebox.showerror(
                "Evidence unavailable",
                "This run did not produce that evidence artifact.",
            )
            return
        self._open_path_with_error(Path(path))

    def _copy_to_clipboard(self, value: str, confirmation: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.root.update_idletasks()
        self.append_log(confirmation)

    def _update_stage_list(self) -> None:
        lines = []
        for index, (_key, label) in enumerate(PRODUCTION_STAGES):
            if index < self._production_stage_index:
                marker = "✓"
            elif index == self._production_stage_index:
                marker = "●"
            else:
                marker = "○"
            lines.append(f"{marker}  {label}")
        self.production_stage_list_var.set("\n".join(lines))

    @staticmethod
    def _available_quality_profile_versions() -> list[str]:
        directory = QualityProfileService().profiles_directory
        versions = [
            path.stem.removeprefix("production_v3_")
            for path in directory.glob("production_v3_*.json")
        ]
        if CURRENT_QUALITY_PROFILE_VERSION not in versions:
            versions.append(CURRENT_QUALITY_PROFILE_VERSION)
        return sorted(
            versions,
            key=lambda value: tuple(int(part) for part in value.split(".")),
            reverse=True,
        )

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
        if not self.production_manifest_var.get().strip():
            missing.append("production manifest path")
        if not self.staging_root_var.get().strip():
            missing.append("production staging workspace")
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
