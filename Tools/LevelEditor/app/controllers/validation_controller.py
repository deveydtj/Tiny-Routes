from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from app.models import LevelDocument, Solution
from app.services import LevelValidationService, SolutionValidationService, ValidationResult, validate_layout


class ValidationController(QObject):
    """Debounce lightweight editor validation and discard superseded work."""

    result_ready = Signal(object)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        debounce_ms: int = 250,
        level_service: LevelValidationService | None = None,
        solution_service: SolutionValidationService | None = None,
    ) -> None:
        super().__init__(parent)
        self._level_service = level_service or LevelValidationService()
        self._solution_service = solution_service or SolutionValidationService()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(debounce_ms)
        self._timer.timeout.connect(self._run_pending)
        self._generation = 0
        self._pending: tuple[int, LevelDocument, Solution | None, Path | None] | None = None

    @property
    def is_pending(self) -> bool:
        return self._timer.isActive()

    def schedule(
        self,
        document: LevelDocument,
        solution: Solution | None,
        file_path: Path | None = None,
    ) -> None:
        self._generation += 1
        self._pending = (
            self._generation,
            deepcopy(document),
            deepcopy(solution),
            file_path,
        )
        # Restarting a single-shot timer cancels the stale pending timeout.
        self._timer.start()

    def validate_now(
        self,
        document: LevelDocument,
        solution: Solution | None,
        file_path: Path | None = None,
    ) -> ValidationResult:
        self._generation += 1
        self._timer.stop()
        self._pending = None
        result = self._validate(document, solution, file_path)
        self.result_ready.emit(result)
        return result

    def cancel(self) -> None:
        self._generation += 1
        self._timer.stop()
        self._pending = None

    def _run_pending(self) -> None:
        pending = self._pending
        self._pending = None
        if pending is None:
            return
        generation, document, solution, file_path = pending
        result = self._validate(document, solution, file_path)
        if generation == self._generation:
            self.result_ready.emit(result)

    def _validate(
        self,
        document: LevelDocument,
        solution: Solution | None,
        file_path: Path | None,
    ) -> ValidationResult:
        level_result = self._level_service.validate(document, file_path)
        solution_result = self._solution_service.validate(document, solution, file_path)
        layout_result = validate_layout(document)
        return ValidationResult(messages=[
            *level_result.messages,
            *solution_result.messages,
            *layout_result.messages,
        ])
