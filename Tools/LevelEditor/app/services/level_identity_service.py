from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.models import LevelDocument, Solution


@dataclass(frozen=True)
class LevelIdentity:
    level_number: int
    level_id: str
    level_name: str
    level_filename: str
    solution_filename: str


class LevelIdentityService:
    """Centralizes production level identity parsing and formatting rules."""

    _PRODUCTION_LEVEL_ID_RE = re.compile(r"^level_(\d+)$")
    _PADDED_PRODUCTION_LEVEL_ID_RE = re.compile(r"^level_\d{3}$")
    _PRODUCTION_LEVEL_FILENAME_RE = re.compile(r"^level_(\d+)\.json$")

    def build_from_number(self, level_number: int) -> LevelIdentity:
        if (
            not isinstance(level_number, int)
            or isinstance(level_number, bool)
            or level_number <= 0
        ):
            raise ValueError("Level number must be a positive integer")

        level_id = f"level_{level_number:03d}"
        return LevelIdentity(
            level_number=level_number,
            level_id=level_id,
            level_name=f"Level {level_number:03d}",
            level_filename=f"{level_id}.json",
            solution_filename=f"{level_id}.solution.json",
        )

    def try_parse_number_from_level_id(self, level_id: str) -> int | None:
        if not isinstance(level_id, str) or not level_id:
            return None

        match = self._PRODUCTION_LEVEL_ID_RE.fullmatch(level_id)
        if match is None:
            return None

        level_number = int(match.group(1))
        return level_number if level_number > 0 else None

    def try_parse_number_from_level_filename(self, path: Path) -> int | None:
        filename = Path(path).name
        if filename.endswith(".solution.json"):
            return None

        match = self._PRODUCTION_LEVEL_FILENAME_RE.fullmatch(filename)
        if match is None:
            return None

        level_number = int(match.group(1))
        return level_number if level_number > 0 else None

    def is_padded_production_level_id(self, level_id: str) -> bool:
        return bool(
            isinstance(level_id, str)
            and self._PADDED_PRODUCTION_LEVEL_ID_RE.fullmatch(level_id)
            and self.try_parse_number_from_level_id(level_id) is not None
        )

    def is_draft_level_id(self, level_id: str) -> bool:
        return level_id == "new_level"

    def apply_identity(
        self,
        document: LevelDocument,
        solution: Solution | None,
        identity: LevelIdentity,
    ) -> None:
        document.id = identity.level_id
        document.name = identity.level_name
        if solution is not None:
            solution.levelID = identity.level_id
