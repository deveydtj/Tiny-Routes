from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from app.models import LevelDocument, SolutionModel


class AutosaveRecoveryError(Exception):
    """Raised when recovery data cannot be safely read or written."""


@dataclass(frozen=True)
class AutosaveRecovery:
    document: LevelDocument
    solution: SolutionModel | None
    source_path: Path | None
    candidate_quality: dict | None
    saved_at_utc: str


class AutosaveRecoveryService:
    """Stores one crash-recovery bundle without touching an authored level file."""

    FORMAT_VERSION = 1
    FILE_NAME = "level_editor_recovery.json"

    def __init__(self, recovery_path: Path | None = None) -> None:
        if recovery_path is None:
            data_root = Path(
                QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.AppLocalDataLocation
                )
            )
            recovery_path = data_root / "TinyRoutesLevelEditor" / self.FILE_NAME
        self.recovery_path = Path(recovery_path)

    def exists(self) -> bool:
        return self.recovery_path.is_file()

    def write(
        self,
        document: LevelDocument,
        solution: SolutionModel | None,
        *,
        source_path: Path | None,
        candidate_quality: dict | None = None,
    ) -> None:
        resolved_source = None if source_path is None else Path(source_path).resolve()
        if resolved_source is not None and self.recovery_path.resolve() == resolved_source:
            raise AutosaveRecoveryError("Recovery data cannot overwrite the source level file.")

        payload = {
            "formatVersion": self.FORMAT_VERSION,
            "savedAtUTC": datetime.now(timezone.utc).isoformat(),
            "sourcePath": None if source_path is None else str(source_path),
            "level": document.to_dict(),
            "solution": None if solution is None else solution.to_dict(),
            "candidateQuality": candidate_quality,
        }
        temporary_path = self.recovery_path.with_suffix(
            f"{self.recovery_path.suffix}.tmp"
        )
        try:
            self.recovery_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary_path.replace(self.recovery_path)
        except (OSError, TypeError, ValueError) as exc:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise AutosaveRecoveryError(f"Could not write recovery data: {exc}") from exc

    def load(self) -> AutosaveRecovery:
        try:
            payload = json.loads(self.recovery_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object.")
            if payload.get("formatVersion") != self.FORMAT_VERSION:
                raise ValueError("Unsupported recovery format version.")
            level_payload = payload["level"]
            solution_payload = payload.get("solution")
            quality_payload = payload.get("candidateQuality")
            if quality_payload is not None and not isinstance(quality_payload, dict):
                raise ValueError("Candidate quality must be an object or null.")
            document = LevelDocument.from_dict(level_payload)
            solution = (
                None
                if solution_payload is None
                else SolutionModel.from_dict(solution_payload)
            )
            source_value = payload.get("sourcePath")
            source_path = None if source_value is None else Path(source_value)
            saved_at_utc = str(payload["savedAtUTC"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AutosaveRecoveryError(f"Could not read recovery data: {exc}") from exc

        return AutosaveRecovery(
            document=document,
            solution=solution,
            source_path=source_path,
            candidate_quality=quality_payload,
            saved_at_utc=saved_at_utc,
        )

    def delete(self) -> None:
        try:
            self.recovery_path.unlink(missing_ok=True)
        except OSError as exc:
            raise AutosaveRecoveryError(f"Could not delete recovery data: {exc}") from exc
