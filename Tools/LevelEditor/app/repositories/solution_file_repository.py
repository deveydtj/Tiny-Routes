from __future__ import annotations

import json
from pathlib import Path

from app.config import find_repo_root
from app.models import SolutionModel


class SolutionFileRepositoryError(Exception):
    """Base error type for solution file repository operations."""

    def __init__(self, path: Path, message: str, error_code: str) -> None:
        super().__init__(message)
        self.path = path
        self.message = message
        self.error_code = error_code


class MissingSolutionFileError(SolutionFileRepositoryError):
    """Raised when the requested solution file cannot be found."""

    def __init__(self, path: Path) -> None:
        super().__init__(path=path, message=f"Solution file was not found: {path}", error_code="missing_file")


class InvalidSolutionJSONError(SolutionFileRepositoryError):
    """Raised when solution JSON cannot be decoded or validated."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(path=path, message=message, error_code="invalid_json")


class SolutionFileIOError(SolutionFileRepositoryError):
    """Raised when an OS-level I/O error prevents reading or writing a solution file."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(path=path, message=message, error_code="io_error")


class SolutionFileRepository:
    """Handles solution sidecar JSON loading, saving, and path resolution."""

    def load_solution(self, path: Path | str) -> SolutionModel:
        solution_path = Path(path)
        try:
            raw_content = solution_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise MissingSolutionFileError(solution_path) from exc
        except OSError as exc:
            raise SolutionFileIOError(solution_path, f"Could not read solution file {solution_path}: {exc}") from exc

        try:
            raw_solution = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            message = f"Invalid JSON in {solution_path} at line {exc.lineno} column {exc.colno}."
            raise InvalidSolutionJSONError(solution_path, message) from exc

        if not isinstance(raw_solution, dict):
            raise InvalidSolutionJSONError(solution_path, "Expected top-level JSON object.")

        try:
            return SolutionModel.from_dict(raw_solution)
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidSolutionJSONError(
                solution_path,
                "Solution JSON does not match expected solution shape.",
            ) from exc

    def save_solution(self, path: Path | str, solution: SolutionModel) -> None:
        solution_path = Path(path)
        payload = solution.to_dict()
        serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        try:
            solution_path.write_text(serialized, encoding="utf-8")
        except OSError as exc:
            raise SolutionFileIOError(
                solution_path,
                f"Could not write solution file {solution_path}: {exc}",
            ) from exc

    def find_solution_path(self, level_path: Path | str) -> Path:
        level_file_path = Path(level_path)
        filename = f"{level_file_path.stem}.solution.json"
        return find_repo_root() / "TinyRoutesTests" / "Resources" / "LevelSolutions" / filename
