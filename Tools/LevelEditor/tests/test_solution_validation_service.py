import ast
import json
import sys
from pathlib import Path

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.models import LevelDocument, RouteEdgeModel, RouteNodeModel, SolutionActionModel, SolutionModel
from app.services import SolutionValidationService, ValidationSeverity

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_level_fixture(filename: str = "valid_level.json") -> LevelDocument:
    data = json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))
    return LevelDocument.from_dict(data)


def _load_solution_fixture(filename: str = "valid_solution.json") -> SolutionModel:
    data = json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))
    return SolutionModel.from_dict(data)


def _codes(result) -> list[str]:
    return [message.code for message in result.messages]


def test_valid_level_and_solution_pair_returns_no_messages() -> None:
    result = SolutionValidationService().validate(
        _load_level_fixture(),
        _load_solution_fixture(),
    )

    assert result.messages == []


def test_missing_solution_is_reported() -> None:
    result = SolutionValidationService().validate(_load_level_fixture(), None)

    assert "missing_solution" in _codes(result)
    assert result.has_errors is True


def test_solution_level_id_mismatch_is_reported() -> None:
    solution = _load_solution_fixture()
    solution.levelID = "wrong_level"

    result = SolutionValidationService().validate(_load_level_fixture(), solution)

    assert "solution_level_id_mismatch" in _codes(result)


def test_solution_level_id_filename_mismatch_is_reported() -> None:
    level = _load_level_fixture()
    level.id = "new_level"
    solution = _load_solution_fixture()
    solution.levelID = "new_level"

    result = SolutionValidationService().validate(
        level,
        solution,
        Path("level_21.json"),
    )

    assert "solution_level_id_filename_mismatch" in _codes(result)


def test_invalid_expected_outcome_is_reported() -> None:
    solution = _load_solution_fixture()
    solution.expectedOutcome = "failed"

    result = SolutionValidationService().validate(_load_level_fixture(), solution)

    assert "invalid_expected_outcome" in _codes(result)


def test_negative_max_taps_is_reported() -> None:
    solution = _load_solution_fixture()
    solution.maxTaps = -1

    result = SolutionValidationService().validate(_load_level_fixture(), solution)

    assert "invalid_max_taps" in _codes(result)


def test_max_taps_less_than_action_count_is_reported() -> None:
    solution = _load_solution_fixture()
    solution.actions.append(SolutionActionModel(timeSeconds=0.5, tapNodeID="start"))

    result = SolutionValidationService().validate(_load_level_fixture(), solution)

    assert "max_taps_less_than_action_count" in _codes(result)


def test_invalid_action_time_type_is_reported() -> None:
    solution = _load_solution_fixture()
    solution.maxTaps = 1
    solution.actions.append(SolutionActionModel(timeSeconds=True, tapNodeID="start"))

    result = SolutionValidationService().validate(_load_level_fixture(), solution)

    assert "solution_action_invalid_time" in _codes(result)


def test_negative_action_time_is_reported() -> None:
    solution = _load_solution_fixture()
    solution.maxTaps = 1
    solution.actions.append(SolutionActionModel(timeSeconds=-0.25, tapNodeID="start"))

    result = SolutionValidationService().validate(_load_level_fixture(), solution)

    assert "solution_action_negative_time" in _codes(result)


def test_unsorted_action_times_are_reported() -> None:
    solution = _load_solution_fixture()
    solution.maxTaps = 2
    solution.actions = [
        SolutionActionModel(timeSeconds=1.0, tapNodeID="start"),
        SolutionActionModel(timeSeconds=0.5, tapNodeID="package"),
    ]

    result = SolutionValidationService().validate(_load_level_fixture(), solution)

    assert "solution_actions_not_sorted" in _codes(result)


def test_unknown_tap_node_is_reported_with_related_node_id() -> None:
    solution = _load_solution_fixture()
    solution.maxTaps = 1
    solution.actions.append(SolutionActionModel(timeSeconds=0.5, tapNodeID="ghost"))

    result = SolutionValidationService().validate(_load_level_fixture(), solution)

    matching = [
        message
        for message in result.messages
        if message.code == "solution_action_unknown_tap_node"
    ]
    assert len(matching) == 1
    assert matching[0].related_node_id == "ghost"


def test_tap_node_with_fewer_than_two_outgoing_edges_is_reported() -> None:
    solution = _load_solution_fixture()
    solution.maxTaps = 1
    solution.actions.append(SolutionActionModel(timeSeconds=0.5, tapNodeID="start"))

    result = SolutionValidationService().validate(_load_level_fixture(), solution)

    warnings = [
        message
        for message in result.messages
        if message.severity is ValidationSeverity.WARNING
    ]
    assert "tap_node_is_not_switchable" in [message.code for message in warnings]


def test_switch_tap_includes_option_count_context() -> None:
    level = _load_level_fixture()
    level.graph.nodes.append(RouteNodeModel(id="dead", x=1.5, y=1.0, outgoingEdgeIDs=[]))
    package = next(node for node in level.graph.nodes if node.id == "package")
    package.outgoingEdgeIDs.append("e_package_dead")
    level.graph.edges.append(RouteEdgeModel(id="e_package_dead", fromNodeID="package", toNodeID="dead"))
    solution = _load_solution_fixture()
    solution.maxTaps = 1
    solution.actions.append(SolutionActionModel(timeSeconds=0.5, tapNodeID="package"))

    result = SolutionValidationService().validate(level, solution)

    info_messages = [message for message in result.messages if message.code == "tap_node_switch_context"]
    assert info_messages
    assert "2 option" in info_messages[0].message


def test_solution_validation_service_imports_no_qt_modules() -> None:
    service_path = LEVEL_EDITOR_ROOT / "app" / "services" / "solution_validation_service.py"
    tree = ast.parse(service_path.read_text(encoding="utf-8"))
    qt_prefixes = ("PySide6", "PyQt5", "PyQt6")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(alias.name.startswith(p) for p in qt_prefixes)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not any(module.startswith(p) for p in qt_prefixes)
