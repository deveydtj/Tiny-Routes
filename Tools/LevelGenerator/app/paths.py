from __future__ import annotations

from pathlib import Path


def find_repo_root(start_path: Path | None = None) -> Path:
    """Locate the Tiny Routes repository root."""

    search_start = (start_path or Path(__file__)).resolve()
    for candidate in [search_start, *search_start.parents]:
        if (candidate / "TinyRoutes").is_dir() and (candidate / "Tools" / "LevelEditor").is_dir():
            return candidate
        if (candidate / "project.yml").is_file() and (candidate / "TinyRoutes.xcodeproj").exists():
            return candidate
    raise FileNotFoundError("Unable to locate Tiny Routes repository root")


def get_default_levels_directory() -> Path:
    return find_repo_root() / "TinyRoutes" / "Resources" / "Levels"


def get_default_solutions_directory() -> Path:
    return find_repo_root() / "TinyRoutesTests" / "Resources" / "LevelSolutions"


def get_default_reports_directory() -> Path:
    return find_repo_root() / "docs" / "generated_levels"


def get_default_production_staging_directory() -> Path:
    return find_repo_root() / "Tools" / "LevelGenerator" / ".scratch" / "production_staging"
