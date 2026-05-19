import sys
from pathlib import Path

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.services.level_validation_service import ValidationMessage, ValidationResult, ValidationSeverity


def test_validation_severity_includes_error_warning_and_info():
    assert ValidationSeverity.ERROR.value == "error"
    assert ValidationSeverity.WARNING.value == "warning"
    assert ValidationSeverity.INFO.value == "info"


def test_validation_message_supports_optional_related_node_and_edge_ids():
    message = ValidationMessage(
        severity=ValidationSeverity.ERROR,
        code="missing_start_node",
        message="Exactly one start node is required.",
        related_node_id="start",
        related_edge_id="edge_001",
    )

    assert message.severity is ValidationSeverity.ERROR
    assert message.code == "missing_start_node"
    assert message.message == "Exactly one start node is required."
    assert message.related_node_id == "start"
    assert message.related_edge_id == "edge_001"


def test_validation_message_defaults_related_ids_to_none():
    message = ValidationMessage(
        severity=ValidationSeverity.INFO,
        code="ok",
        message="No issues found.",
    )

    assert message.related_node_id is None
    assert message.related_edge_id is None


def test_validation_result_has_errors_and_has_warnings():
    result = ValidationResult(
        messages=[
            ValidationMessage(
                severity=ValidationSeverity.INFO,
                code="ok",
                message="Info only.",
            ),
            ValidationMessage(
                severity=ValidationSeverity.WARNING,
                code="unreachable_optional_node",
                message="A non-critical node is unreachable.",
            ),
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                code="missing_destination",
                message="A destination node is required.",
            ),
        ]
    )

    assert result.has_warnings is True
    assert result.has_errors is True


def test_validation_result_without_errors_or_warnings():
    result = ValidationResult(
        messages=[
            ValidationMessage(
                severity=ValidationSeverity.INFO,
                code="ok",
                message="Info only.",
            )
        ]
    )

    assert result.has_warnings is False
    assert result.has_errors is False
