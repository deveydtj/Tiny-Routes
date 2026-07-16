import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.models import SolutionAction, Solution
from app.repositories import (
    InvalidSolutionJSONError,
    MissingSolutionFileError,
    SolutionFileIOError,
    SolutionFileRepository,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "valid_solution.json"


def test_load_solution_reads_valid_solution_file() -> None:
    repository = SolutionFileRepository()

    solution = repository.load_solution(FIXTURE_PATH)

    assert solution.levelID == "level_001"
    assert solution.expectedOutcome == "completed"
    assert solution.maxTaps == 0
    assert solution.actions == []


def test_save_solution_writes_round_trip_json(tmp_path: Path) -> None:
    repository = SolutionFileRepository()
    expected_solution = repository.load_solution(FIXTURE_PATH)
    output_path = tmp_path / "round_trip_solution.json"

    repository.save_solution(output_path, expected_solution)
    reloaded_solution = repository.load_solution(output_path)

    assert reloaded_solution.to_dict() == expected_solution.to_dict()


def test_find_solution_path_uses_matching_level_id_in_solution_resources() -> None:
    repository = SolutionFileRepository()
    level_path = LEVEL_EDITOR_ROOT.parent.parent / "TinyRoutes" / "Resources" / "Levels" / "level_010.json"

    solution_path = repository.find_solution_path(level_path)

    assert solution_path == (
        LEVEL_EDITOR_ROOT.parent.parent
        / "TinyRoutesTests"
        / "Resources"
        / "LevelSolutions"
        / "level_010.solution.json"
    )


def test_solution_path_for_level_id_uses_normalized_padded_id() -> None:
    repository = SolutionFileRepository()

    solution_path = repository.solution_path_for_level_id("level_021")

    assert solution_path == (
        LEVEL_EDITOR_ROOT.parent.parent
        / "TinyRoutesTests"
        / "Resources"
        / "LevelSolutions"
        / "level_021.solution.json"
    )


def test_solution_path_for_level_id_normalizes_non_padded_id() -> None:
    repository = SolutionFileRepository()

    solution_path = repository.solution_path_for_level_id("level_21")

    assert solution_path.name == "level_021.solution.json"


def test_find_solution_path_keeps_legacy_filename_behavior() -> None:
    repository = SolutionFileRepository()
    level_path = LEVEL_EDITOR_ROOT.parent.parent / "TinyRoutes" / "Resources" / "Levels" / "level_21.json"

    solution_path = repository.find_solution_path(level_path)

    assert solution_path.name == "level_21.solution.json"


def test_find_solution_path_prefers_sibling_draft_sidecar(tmp_path: Path) -> None:
    repository = SolutionFileRepository()
    level_path = tmp_path / "candidate.json"
    sibling = tmp_path / "candidate.solution.json"
    sibling.write_text("{}", encoding="utf-8")

    assert repository.find_solution_path(level_path) == sibling


def test_load_solution_raises_structured_error_for_missing_file(tmp_path: Path) -> None:
    repository = SolutionFileRepository()
    missing_path = tmp_path / "does_not_exist.solution.json"

    with pytest.raises(MissingSolutionFileError) as exc_info:
        repository.load_solution(missing_path)

    assert exc_info.value.error_code == "missing_file"
    assert exc_info.value.path == missing_path


def test_load_solution_raises_structured_error_for_invalid_json(tmp_path: Path) -> None:
    repository = SolutionFileRepository()
    invalid_path = tmp_path / "invalid_solution.json"
    invalid_path.write_text("{not-valid-json", encoding="utf-8")

    with pytest.raises(InvalidSolutionJSONError) as exc_info:
        repository.load_solution(invalid_path)

    assert exc_info.value.error_code == "invalid_json"
    assert exc_info.value.path == invalid_path


def test_load_solution_raises_structured_error_for_invalid_shape(tmp_path: Path) -> None:
    repository = SolutionFileRepository()
    invalid_shape_path = tmp_path / "invalid_shape_solution.json"
    invalid_shape_path.write_text(json.dumps({"levelID": "level_999"}), encoding="utf-8")

    with pytest.raises(InvalidSolutionJSONError) as exc_info:
        repository.load_solution(invalid_shape_path)

    assert exc_info.value.error_code == "invalid_json"
    assert exc_info.value.path == invalid_shape_path


def test_load_solution_wraps_os_error_as_solution_file_io_error(tmp_path: Path) -> None:
    repository = SolutionFileRepository()
    some_path = tmp_path / "solution.json"

    with patch.object(Path, "read_text", side_effect=OSError("Disk I/O error")):
        with pytest.raises(SolutionFileIOError) as exc_info:
            repository.load_solution(some_path)

    assert exc_info.value.error_code == "io_error"
    assert exc_info.value.path == some_path
    assert str(some_path) in exc_info.value.message


def test_save_solution_wraps_os_error_as_solution_file_io_error(tmp_path: Path) -> None:
    repository = SolutionFileRepository()
    solution = Solution(
        levelID="level_999",
        description="Test solution",
        expectedOutcome="completed",
        maxTaps=0,
        requiresWithinTimeLimit=True,
        actions=[SolutionAction(timeSeconds=0.0, tapNodeID="start")],
    )
    some_path = tmp_path / "solution.json"

    with patch.object(Path, "write_text", side_effect=OSError("Disk I/O error")):
        with pytest.raises(SolutionFileIOError) as exc_info:
            repository.save_solution(some_path, solution)

    assert exc_info.value.error_code == "io_error"
    assert exc_info.value.path == some_path
    assert str(some_path) in exc_info.value.message
