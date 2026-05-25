from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk


def add_labeled_entry(
    parent: tk.Widget,
    label_text: str,
    variable: tk.StringVar,
    row: int,
    *,
    width: int = 16,
    column: int = 0,
) -> ttk.Entry:
    label = ttk.Label(parent, text=label_text)
    label.grid(row=row, column=column, sticky="w", padx=(0, 8), pady=3)
    entry = ttk.Entry(parent, textvariable=variable, width=width)
    entry.grid(row=row, column=column + 1, sticky="ew", pady=3)
    parent.grid_columnconfigure(column + 1, weight=1)
    return entry


def add_labeled_combobox(
    parent: tk.Widget,
    label_text: str,
    variable: tk.StringVar,
    values: list[str],
    row: int,
    *,
    width: int = 18,
    column: int = 0,
) -> ttk.Combobox:
    label = ttk.Label(parent, text=label_text)
    label.grid(row=row, column=column, sticky="w", padx=(0, 8), pady=3)
    combobox = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=width)
    combobox.grid(row=row, column=column + 1, sticky="ew", pady=3)
    parent.grid_columnconfigure(column + 1, weight=1)
    return combobox


def add_path_picker(
    parent: tk.Widget,
    label_text: str,
    variable: tk.StringVar,
    row: int,
    *,
    pick_directory: bool,
    file_extension: str | None = None,
    column: int = 0,
) -> ttk.Entry:
    label = ttk.Label(parent, text=label_text)
    label.grid(row=row, column=column, sticky="w", padx=(0, 8), pady=3)
    entry = ttk.Entry(parent, textvariable=variable)
    entry.grid(row=row, column=column + 1, sticky="ew", pady=3)

    def browse() -> None:
        if pick_directory:
            selected = filedialog.askdirectory()
        else:
            filetypes = _filetypes_for_extension(file_extension)
            selected = filedialog.asksaveasfilename(defaultextension=file_extension or "", filetypes=filetypes)
        if selected:
            variable.set(selected)

    button = ttk.Button(parent, text="Browse", command=browse)
    button.grid(row=row, column=column + 2, sticky="ew", padx=(8, 0), pady=3)
    parent.grid_columnconfigure(column + 1, weight=1)
    return entry


def _filetypes_for_extension(file_extension: str | None) -> list[tuple[str, str]]:
    if file_extension == ".md":
        return [("Markdown files", "*.md"), ("All files", "*.*")]
    if file_extension == ".json":
        return [("JSON files", "*.json"), ("All files", "*.*")]
    return [("All files", "*.*")]
