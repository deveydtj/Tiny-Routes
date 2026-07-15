from pathlib import Path


_LEVEL_EDITOR_FOLDER_NAME = "LevelEditor"
_TOOLS_FOLDER_NAME = "Tools"


def find_repo_root(start_path: Path | None = None) -> Path:
    """Locate the Tiny Routes repository root from the Tools/LevelEditor tree."""

    search_start = (start_path or Path(__file__)).resolve()

    for candidate in [search_start, *search_start.parents]:
        level_editor_path = candidate / _TOOLS_FOLDER_NAME / _LEVEL_EDITOR_FOLDER_NAME
        if level_editor_path.is_dir():
            return candidate

    raise FileNotFoundError("Unable to locate repository root from LevelEditor path")


def get_default_levels_directory() -> Path:
    """Return the default Tiny Routes levels directory path."""

    return find_repo_root() / "TinyRoutes" / "Resources" / "Levels"


def get_default_docs_directory() -> Path:
    """Return the default Tiny Routes docs directory path."""

    return find_repo_root() / "docs"


def get_default_drafts_directory() -> Path:
    """Return the non-production workspace used for candidate review drafts."""

    return find_repo_root() / "docs" / "generated_levels" / "editor_drafts"
