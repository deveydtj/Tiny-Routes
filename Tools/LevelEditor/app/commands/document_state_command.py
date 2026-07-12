from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from PySide6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from app.controllers.document_controller import DocumentController
    from app.models import LevelDocument, SolutionModel


class DocumentStateCommand(QUndoCommand):
    """Undo command that restores an exact level-and-solution snapshot."""

    def __init__(
        self,
        controller: "DocumentController",
        text: str,
        before_document: "LevelDocument",
        after_document: "LevelDocument",
        before_solution: "SolutionModel | None",
        after_solution: "SolutionModel | None",
    ) -> None:
        super().__init__(text)
        self._controller = controller
        self._before_document = deepcopy(before_document)
        self._after_document = deepcopy(after_document)
        self._before_solution = deepcopy(before_solution)
        self._after_solution = deepcopy(after_solution)

    def undo(self) -> None:
        self._controller._restore_state(self._before_document, self._before_solution)

    def redo(self) -> None:
        self._controller._restore_state(self._after_document, self._after_solution)
