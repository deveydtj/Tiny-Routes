from __future__ import annotations

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import pytest

from app.controllers import ValidationController
from app.services import ValidationMessage, ValidationResult, ValidationSeverity, create_default_level_document


class _RecordingLevelService:
    def __init__(self) -> None:
        self.level_ids: list[str] = []

    def validate(self, document, file_path=None) -> ValidationResult:
        self.level_ids.append(document.id)
        return ValidationResult(messages=[ValidationMessage(
            ValidationSeverity.INFO, "checked", f"Checked {document.id}"
        )])


class _EmptySolutionService:
    def validate(self, document, solution, file_path=None) -> ValidationResult:
        return ValidationResult()


@pytest.fixture
def qapplication():
    app = QApplication.instance() or QApplication([])
    return app


def test_debounce_cancels_stale_pending_validation(qapplication) -> None:
    level_service = _RecordingLevelService()
    controller = ValidationController(
        debounce_ms=20,
        level_service=level_service,
        solution_service=_EmptySolutionService(),
    )
    results: list[ValidationResult] = []
    controller.result_ready.connect(results.append)
    first = create_default_level_document()
    second = create_default_level_document()
    first.id = "first"
    second.id = "second"

    controller.schedule(first, None)
    controller.schedule(second, None)
    QTest.qWait(30)
    qapplication.processEvents()

    assert level_service.level_ids == ["second"]
    assert [result.messages[0].message for result in results] == ["Checked second"]


def test_validate_now_cancels_pending_debounce(qapplication) -> None:
    level_service = _RecordingLevelService()
    controller = ValidationController(
        debounce_ms=20,
        level_service=level_service,
        solution_service=_EmptySolutionService(),
    )
    pending = create_default_level_document()
    immediate = create_default_level_document()
    pending.id = "pending"
    immediate.id = "immediate"

    controller.schedule(pending, None)
    controller.validate_now(immediate, None)
    QTest.qWait(30)
    qapplication.processEvents()

    assert level_service.level_ids == ["immediate"]
