from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ..level_numbering import format_level_id
from ..paths import find_repo_root


@dataclass
class LevelResourceSyncResult:
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    missing_project_references: list[str] = field(default_factory=list)
    stale_project_references: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


@dataclass
class DeleteLevelsResult:
    deleted_paths: list[Path] = field(default_factory=list)
    missing_paths: list[Path] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    xcodegen_message: str | None = None


class LevelResourceSyncService:
    LEVEL_PATTERN = re.compile(r"level_\d{3}(?:\.solution)?\.json")

    def check_project_references(
        self,
        levels_dir: Path,
        solutions_dir: Path,
        project_file: Path | None = None,
    ) -> LevelResourceSyncResult:
        result = LevelResourceSyncResult()
        repo_root = find_repo_root()
        project_path = project_file or repo_root / "TinyRoutes.xcodeproj" / "project.pbxproj"
        if not project_path.exists():
            result.errors.append(f"Project file not found: {project_path}")
            return result

        project_text = project_path.read_text(encoding="utf-8")
        existing_files = {
            path.name
            for directory in [Path(levels_dir), Path(solutions_dir)]
            if directory.exists()
            for path in directory.glob("level_*.json")
        }
        referenced_files = set(self.LEVEL_PATTERN.findall(project_text))

        result.missing_project_references = sorted(existing_files - referenced_files)
        result.stale_project_references = sorted(referenced_files - existing_files)
        if result.missing_project_references:
            result.warnings.append(
                "Files missing from TinyRoutes.xcodeproj: " + ", ".join(result.missing_project_references)
            )
        if result.stale_project_references:
            result.warnings.append(
                "Stale TinyRoutes.xcodeproj references: " + ", ".join(result.stale_project_references)
            )
        return result

    def delete_levels(
        self,
        level_ids: list[str],
        levels_dir: Path,
        solutions_dir: Path,
        *,
        dry_run: bool = False,
        run_xcodegen: bool = True,
    ) -> DeleteLevelsResult:
        result = DeleteLevelsResult()
        paths: list[Path] = []
        for level_id in level_ids:
            normalized = normalize_level_id_or_number(level_id)
            paths.extend(
                [
                    Path(levels_dir) / f"{normalized}.json",
                    Path(solutions_dir) / f"{normalized}.solution.json",
                ]
            )

        for path in paths:
            if not path.exists():
                result.missing_paths.append(path)
                continue
            if dry_run:
                result.messages.append(f"Would delete {path}")
            else:
                path.unlink()
                result.deleted_paths.append(path)

        if run_xcodegen and not dry_run:
            result.xcodegen_message = self.run_xcodegen()
        return result

    def run_xcodegen(self) -> str:
        repo_root = find_repo_root()
        if shutil.which("xcodegen") is None:
            return "Skipped xcodegen because the xcodegen command was not found."
        completed = subprocess.run(
            ["xcodegen", "generate"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            return "Regenerated TinyRoutes.xcodeproj with xcodegen."
        detail = completed.stderr.strip() or completed.stdout.strip() or f"exit code {completed.returncode}"
        return f"xcodegen generate failed: {detail}"


def parse_level_selectors(values: list[str]) -> list[str]:
    level_ids: list[str] = []
    for value in values:
        stripped = value.strip()
        if not stripped:
            continue
        if "-" in stripped and not stripped.startswith("level_"):
            start, end = stripped.split("-", 1)
            start_number = int(start)
            end_number = int(end)
            step = 1 if end_number >= start_number else -1
            for number in range(start_number, end_number + step, step):
                level_ids.append(format_level_id(number))
        else:
            level_ids.append(normalize_level_id_or_number(stripped))
    return list(dict.fromkeys(level_ids))


def normalize_level_id_or_number(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("level_"):
        return stripped
    return format_level_id(int(stripped))
