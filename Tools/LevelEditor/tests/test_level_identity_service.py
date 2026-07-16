import sys
from pathlib import Path

import pytest

LEVEL_EDITOR_ROOT = Path(__file__).resolve().parents[1]
if str(LEVEL_EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(LEVEL_EDITOR_ROOT))

from app.models import RouteGraph, SolutionAction, Solution
from app.services import LevelIdentityService, create_default_level_document


def test_build_from_number_formats_level_021_identity() -> None:
    identity = LevelIdentityService().build_from_number(21)

    assert identity.level_number == 21
    assert identity.level_id == "level_021"
    assert identity.level_name == "Level 021"
    assert identity.level_filename == "level_021.json"
    assert identity.solution_filename == "level_021.solution.json"


def test_build_from_number_formats_level_001_identity() -> None:
    assert LevelIdentityService().build_from_number(1).level_id == "level_001"


@pytest.mark.parametrize("bad_number", [0, -1, True])
def test_build_from_number_rejects_invalid_values(bad_number: int) -> None:
    with pytest.raises(ValueError):
        LevelIdentityService().build_from_number(bad_number)


@pytest.mark.parametrize(
    ("level_id", "expected_number"),
    [
        ("level_021", 21),
        ("level_21", 21),
        ("new_level", None),
        ("", None),
        ("not_a_level", None),
    ],
)
def test_try_parse_number_from_level_id(
    level_id: str,
    expected_number: int | None,
) -> None:
    assert LevelIdentityService().try_parse_number_from_level_id(level_id) == expected_number


@pytest.mark.parametrize(
    ("filename", "expected_number"),
    [
        ("level_021.json", 21),
        ("level_21.json", 21),
        ("new_level.json", None),
        ("level_021.solution.json", None),
        ("unrelated.json", None),
    ],
)
def test_try_parse_number_from_level_filename(
    filename: str,
    expected_number: int | None,
) -> None:
    assert (
        LevelIdentityService().try_parse_number_from_level_filename(Path(filename))
        == expected_number
    )


def test_apply_identity_updates_document_and_solution_metadata() -> None:
    service = LevelIdentityService()
    identity = service.build_from_number(21)
    document = create_default_level_document()
    document.graph = RouteGraph()
    solution = Solution(
        levelID="new_level",
        description="Draft",
        expectedOutcome="completed",
        maxTaps=1,
        requiresWithinTimeLimit=True,
        actions=[SolutionAction(timeSeconds=1.0, tapNodeID="switch")],
    )

    service.apply_identity(document, solution, identity)

    assert document.id == "level_021"
    assert document.name == "Level 021"
    assert solution.levelID == "level_021"
    assert solution.actions[0].tapNodeID == "switch"
    assert solution.expectedOutcome == "completed"
    assert solution.requiresWithinTimeLimit is True
