from __future__ import annotations

from app.paths import (
    find_repo_root,
    get_default_levels_directory,
    get_default_reports_directory,
    get_default_solutions_directory,
)


def test_find_repo_root_from_generator_tree() -> None:
    repo_root = find_repo_root()
    assert (repo_root / "TinyRoutes").is_dir()
    assert (repo_root / "Tools" / "LevelGenerator").is_dir()


def test_default_directories() -> None:
    repo_root = find_repo_root()
    assert get_default_levels_directory() == repo_root / "TinyRoutes" / "Resources" / "Levels"
    assert get_default_solutions_directory() == repo_root / "TinyRoutesTests" / "Resources" / "LevelSolutions"
    assert get_default_reports_directory() == repo_root / "docs" / "generated_levels"
