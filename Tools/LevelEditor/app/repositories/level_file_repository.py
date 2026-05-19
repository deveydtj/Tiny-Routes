from __future__ import annotations

import json
from pathlib import Path

from app.models import LevelDocument


class LevelFileRepositoryError(Exception):
    """Base error type for level file repository operations."""

    def __init__(self, path: Path, message: str, error_code: str) -> None:
        super().__init__(message)
        self.path = path
        self.message = message
        self.error_code = error_code


class MissingLevelFileError(LevelFileRepositoryError):
    """Raised when the requested level file cannot be found."""

    def __init__(self, path: Path) -> None:
        super().__init__(path=path, message=f"Level file was not found: {path}", error_code="missing_file")


class InvalidLevelJSONError(LevelFileRepositoryError):
    """Raised when level JSON cannot be decoded or validated."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(path=path, message=message, error_code="invalid_json")


class LevelFileRepository:
    """Handles level JSON file loading and saving."""

    def load_level(self, path: Path | str) -> LevelDocument:
        level_path = Path(path)
        try:
            raw_content = level_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise MissingLevelFileError(level_path) from exc

        try:
            raw_level = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            message = f"Invalid JSON in {level_path} at line {exc.lineno} column {exc.colno}."
            raise InvalidLevelJSONError(level_path, message) from exc

        if not isinstance(raw_level, dict):
            raise InvalidLevelJSONError(level_path, "Expected top-level JSON object.")

        try:
            return LevelDocument.from_dict(raw_level)
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidLevelJSONError(level_path, "Level JSON does not match expected level shape.") from exc

    def save_level(self, path: Path | str, level_document: LevelDocument) -> None:
        level_path = Path(path)
        payload = level_document.to_dict()
        serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        level_path.write_text(serialized, encoding="utf-8")
