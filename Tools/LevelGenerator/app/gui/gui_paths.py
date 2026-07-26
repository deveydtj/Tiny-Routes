from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ..paths import (
    get_default_levels_directory,
    get_default_production_staging_directory,
    get_default_reports_directory,
    get_default_solutions_directory,
)


def open_path(path: Path) -> None:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Path does not exist: {target}")

    if sys.platform == "darwin":
        subprocess.run(["open", str(target)], check=True)
    elif sys.platform.startswith("win"):
        os.startfile(str(target))  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(target)], check=True)


def try_get_default_levels_directory() -> str:
    return _try_default_path(get_default_levels_directory)


def try_get_default_solutions_directory() -> str:
    return _try_default_path(get_default_solutions_directory)


def try_get_default_markdown_report_path() -> str:
    return _try_default_path(lambda: get_default_reports_directory() / "last_generation_report.md")


def try_get_default_json_report_path() -> str:
    return _try_default_path(lambda: get_default_reports_directory() / "last_generation_report.json")


def try_get_default_production_manifest_path() -> str:
    return _try_default_path(
        lambda: get_default_reports_directory() / "production_manifest.json"
    )


def try_get_default_production_staging_directory() -> str:
    return _try_default_path(get_default_production_staging_directory)


def try_get_default_debug_failures_directory() -> str:
    return _try_default_path(lambda: get_default_reports_directory() / "debug_failures")


def try_get_default_editor_drafts_directory() -> str:
    return _try_default_path(
        lambda: get_default_reports_directory() / "editor_drafts"
    )


def _try_default_path(factory) -> str:
    try:
        return str(factory())
    except FileNotFoundError:
        return ""
