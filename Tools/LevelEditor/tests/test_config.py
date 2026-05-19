import sys
from pathlib import Path


LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.config import find_repo_root, get_default_docs_directory, get_default_levels_directory


EXPECTED_REPO_ROOT = LEVEL_EDITOR_ROOT.parent.parent


def test_find_repo_root_returns_repo_root() -> None:
    assert find_repo_root() == EXPECTED_REPO_ROOT


def test_get_default_levels_directory_points_to_levels_folder() -> None:
    expected = EXPECTED_REPO_ROOT / "TinyRoutes" / "Resources" / "Levels"
    assert get_default_levels_directory() == expected


def test_get_default_docs_directory_points_to_docs_folder() -> None:
    expected = EXPECTED_REPO_ROOT / "docs"
    assert get_default_docs_directory() == expected
