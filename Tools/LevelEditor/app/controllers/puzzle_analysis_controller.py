from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import QObject, QTimer, Signal

from app.models import LevelDocument, SolutionModel
from app.services.puzzle_analysis_service import PuzzleAnalysisService


class PuzzleAnalysisController(QObject):
    """Debounce analysis so normal canvas edits remain responsive."""

    result_ready = Signal(object)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        debounce_ms: int = 300,
        service: PuzzleAnalysisService | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service or PuzzleAnalysisService()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(debounce_ms)
        self._timer.timeout.connect(self._run_pending)
        self._generation = 0
        self._pending: tuple[int, LevelDocument, SolutionModel | None] | None = None

    @property
    def is_pending(self) -> bool:
        return self._timer.isActive()

    def schedule(self, document: LevelDocument, solution: SolutionModel | None) -> None:
        self._generation += 1
        self._pending = (self._generation, deepcopy(document), deepcopy(solution))
        self._timer.start()

    def analyze_now(self, document: LevelDocument, solution: SolutionModel | None):
        self._generation += 1
        self._timer.stop()
        self._pending = None
        result = self._service.analyze(document, solution)
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
        generation, document, solution = pending
        result = self._service.analyze(document, solution)
        if generation == self._generation:
            self.result_ready.emit(result)
