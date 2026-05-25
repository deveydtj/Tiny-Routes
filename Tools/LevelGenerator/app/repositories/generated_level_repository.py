from __future__ import annotations

import json
from pathlib import Path


class GeneratedLevelRepository:
    def level_path(self, level_id: str, directory: Path) -> Path:
        return Path(directory) / f"{level_id}.json"

    def solution_path(self, level_id: str, directory: Path) -> Path:
        return Path(directory) / f"{level_id}.solution.json"

    def write_level(self, level_document, path: Path, overwrite: bool = False) -> Path:
        return self._write_json(level_document.to_dict(), path, overwrite)

    def write_solution(self, solution, path: Path, overwrite: bool = False) -> Path:
        return self._write_json(solution.to_dict(), path, overwrite)

    def _write_json(self, payload: dict, path: Path, overwrite: bool) -> Path:
        output_path = Path(path)
        if output_path.exists() and not overwrite:
            raise FileExistsError(f"Refusing to overwrite existing file: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return output_path
