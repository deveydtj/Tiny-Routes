import ast
import json
import sys
from pathlib import Path

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.models.level_document import LevelDocument
from app.services.level_validation_service import (
    ValidationMessage,
    ValidationResult,
    ValidationSeverity,
    validate,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


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


# ---------------------------------------------------------------------------
# Task 013: Core validation rules tests
# ---------------------------------------------------------------------------


def _load_fixture(filename: str) -> LevelDocument:
    data = json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))
    return LevelDocument.from_dict(data)


def test_validate_valid_fixture_produces_no_errors():
    level = _load_fixture("valid_level.json")
    result = validate(level)
    assert not result.has_errors, [m.message for m in result.messages if m.severity == ValidationSeverity.ERROR]


def test_validate_invalid_fixture_produces_errors():
    level = _load_fixture("invalid_missing_node_level.json")
    result = validate(level)
    assert result.has_errors


def test_validate_missing_level_id():
    level = _load_fixture("valid_level.json")
    level.id = ""
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "missing_level_id" in codes


def test_validate_missing_level_name():
    level = _load_fixture("valid_level.json")
    level.name = "   "
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "missing_level_name" in codes


def test_validate_non_positive_time_limit():
    level = _load_fixture("valid_level.json")
    level.timeLimitSeconds = 0
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "invalid_time_limit" in codes


def test_validate_negative_time_limit():
    level = _load_fixture("valid_level.json")
    level.timeLimitSeconds = -5
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "invalid_time_limit" in codes


def test_validate_start_node_not_in_graph():
    level = _load_fixture("valid_level.json")
    level.startNodeID = "nonexistent_start"
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "start_node_not_found" in codes


def test_validate_empty_start_node_id():
    level = _load_fixture("valid_level.json")
    level.startNodeID = ""
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "missing_start_node" in codes


def test_validate_whitespace_start_node_id():
    level = _load_fixture("valid_level.json")
    level.startNodeID = "   "
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "missing_start_node" in codes


def test_validate_destination_node_not_in_graph():
    level = _load_fixture("valid_level.json")
    level.destinationNodeID = "nonexistent_dest"
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "destination_node_not_found" in codes


def test_validate_empty_destination_node_id():
    level = _load_fixture("valid_level.json")
    level.destinationNodeID = ""
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "missing_destination_node" in codes


def test_validate_whitespace_destination_node_id():
    level = _load_fixture("valid_level.json")
    level.destinationNodeID = "   "
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "missing_destination_node" in codes


def test_validate_package_node_not_in_graph():
    level = _load_fixture("valid_level.json")
    level.packageNodeID = "nonexistent_package"
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "package_node_not_found" in codes


def test_validate_empty_package_node_id():
    level = _load_fixture("valid_level.json")
    level.packageNodeID = ""
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "missing_package_node" in codes


def test_validate_whitespace_package_node_id():
    level = _load_fixture("valid_level.json")
    level.packageNodeID = "   "
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "missing_package_node" in codes


def test_validate_duplicate_node_ids():
    level = _load_fixture("valid_level.json")
    # Duplicate the first node
    level.graph.nodes.append(level.graph.nodes[0])
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "duplicate_node_id" in codes


def test_validate_duplicate_edge_ids():
    level = _load_fixture("valid_level.json")
    # Duplicate the first edge
    level.graph.edges.append(level.graph.edges[0])
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "duplicate_edge_id" in codes


def test_validate_edge_references_missing_from_node():
    level = _load_fixture("valid_level.json")
    level.graph.edges[0].fromNodeID = "ghost_node"
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "edge_references_missing_node" in codes


def test_validate_edge_references_missing_to_node():
    level = _load_fixture("valid_level.json")
    level.graph.edges[0].toNodeID = "ghost_node"
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "edge_references_missing_node" in codes


def test_validate_invalid_fixture_has_edge_referencing_missing_node():
    level = _load_fixture("invalid_missing_node_level.json")
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "edge_references_missing_node" in codes


def test_validate_bool_time_limit():
    level = _load_fixture("valid_level.json")
    level.timeLimitSeconds = True
    result = validate(level)
    codes = [m.code for m in result.messages]
    assert "invalid_time_limit" in codes


def test_validate_no_qt_imports():
    """Ensure the validation service module imports no Qt modules."""
    service_path = LEVEL_EDITOR_ROOT / "app" / "services" / "level_validation_service.py"
    tree = ast.parse(service_path.read_text(encoding="utf-8"))
    qt_prefixes = ("PySide6", "PyQt5", "PyQt6")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(alias.name.startswith(p) for p in qt_prefixes), (
                    f"Unexpected Qt import: {alias.name}"
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not any(module.startswith(p) for p in qt_prefixes), (
                f"Unexpected Qt import from: {module}"
            )
