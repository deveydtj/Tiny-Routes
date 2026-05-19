import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.repositories import InvalidLevelJSONError, LevelFileIOError, LevelFileRepository, MissingLevelFileError


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "valid_level.json"


def test_load_level_reads_valid_level_file() -> None:
    repository = LevelFileRepository()

    document = repository.load_level(FIXTURE_PATH)

    assert document.id == "level_001"
    assert document.name == "First Pickup"
    assert len(document.graph.nodes) == 3
    assert len(document.graph.edges) == 2


def test_save_level_writes_round_trip_json(tmp_path: Path) -> None:
    repository = LevelFileRepository()
    expected_document = repository.load_level(FIXTURE_PATH)
    output_path = tmp_path / "round_trip_level.json"

    repository.save_level(output_path, expected_document)
    reloaded_document = repository.load_level(output_path)

    assert reloaded_document.to_dict() == expected_document.to_dict()


def test_load_level_raises_structured_error_for_missing_file(tmp_path: Path) -> None:
    repository = LevelFileRepository()
    missing_path = tmp_path / "does_not_exist.json"

    with pytest.raises(MissingLevelFileError) as exc_info:
        repository.load_level(missing_path)

    assert exc_info.value.error_code == "missing_file"
    assert exc_info.value.path == missing_path


def test_load_level_raises_structured_error_for_invalid_json(tmp_path: Path) -> None:
    repository = LevelFileRepository()
    invalid_path = tmp_path / "invalid_level.json"
    invalid_path.write_text("{not-valid-json", encoding="utf-8")

    with pytest.raises(InvalidLevelJSONError) as exc_info:
        repository.load_level(invalid_path)

    assert exc_info.value.error_code == "invalid_json"
    assert exc_info.value.path == invalid_path


def test_load_level_raises_structured_error_for_invalid_shape(tmp_path: Path) -> None:
    repository = LevelFileRepository()
    invalid_shape_path = tmp_path / "invalid_shape_level.json"
    invalid_shape_path.write_text(json.dumps({"id": "level_999"}), encoding="utf-8")

    with pytest.raises(InvalidLevelJSONError) as exc_info:
        repository.load_level(invalid_shape_path)

    assert exc_info.value.error_code == "invalid_json"
    assert exc_info.value.path == invalid_shape_path


def test_load_level_wraps_permission_error_as_level_file_io_error(tmp_path: Path) -> None:
    repository = LevelFileRepository()
    some_path = tmp_path / "level.json"

    with patch.object(Path, "read_text", side_effect=PermissionError("Permission denied")):
        with pytest.raises(LevelFileIOError) as exc_info:
            repository.load_level(some_path)

    assert exc_info.value.error_code == "io_error"
    assert exc_info.value.path == some_path


def test_load_level_wraps_os_error_as_level_file_io_error(tmp_path: Path) -> None:
    repository = LevelFileRepository()
    some_path = tmp_path / "level.json"

    with patch.object(Path, "read_text", side_effect=OSError("Disk I/O error")):
        with pytest.raises(LevelFileIOError) as exc_info:
            repository.load_level(some_path)

    assert exc_info.value.error_code == "io_error"
    assert exc_info.value.path == some_path


def test_save_level_wraps_os_error_as_level_file_io_error(tmp_path: Path) -> None:
    repository = LevelFileRepository()
    document = repository.load_level(FIXTURE_PATH)
    some_path = tmp_path / "level.json"

    with patch.object(Path, "write_text", side_effect=PermissionError("Permission denied")):
        with pytest.raises(LevelFileIOError) as exc_info:
            repository.save_level(some_path, document)

    assert exc_info.value.error_code == "io_error"
    assert exc_info.value.path == some_path
