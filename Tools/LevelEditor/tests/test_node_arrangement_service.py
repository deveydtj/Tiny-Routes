from __future__ import annotations

import pytest

from app.services import NodeArrangementService


def test_align_edges_and_centers() -> None:
    service = NodeArrangementService()
    positions = {"a": (0.0, 1.0), "b": (2.0, 3.0), "c": (4.0, 5.0)}

    assert {value[0] for value in service.arrange(positions, "left").values()} == {0.0}
    assert {value[0] for value in service.arrange(positions, "right").values()} == {4.0}
    assert {value[1] for value in service.arrange(positions, "top").values()} == {5.0}
    assert {value[1] for value in service.arrange(positions, "bottom").values()} == {1.0}
    assert {
        value[0] for value in service.arrange(positions, "horizontal_centers").values()
    } == {2.0}
    assert {
        value[1] for value in service.arrange(positions, "vertical_centers").values()
    } == {3.0}


def test_distribute_uses_outer_nodes_as_fixed_endpoints() -> None:
    service = NodeArrangementService()
    positions = {"left": (0.0, 0.0), "middle": (1.0, 2.0), "right": (6.0, 5.0)}

    horizontal = service.arrange(positions, "horizontal")
    vertical = service.arrange(positions, "vertical")

    assert horizontal == {
        "left": (0.0, 0.0),
        "middle": (3.0, 2.0),
        "right": (6.0, 5.0),
    }
    assert vertical == {
        "left": (0.0, 0.0),
        "middle": (1.0, 2.5),
        "right": (6.0, 5.0),
    }


def test_nudge_preserves_relative_spacing() -> None:
    service = NodeArrangementService()

    assert service.nudge({"a": (1.0, 2.0), "b": (3.0, 4.0)}, 0.25, -0.5) == {
        "a": (1.25, 1.5),
        "b": (3.25, 3.5),
    }


def test_unknown_arrangement_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown arrangement operation"):
        NodeArrangementService().arrange({"a": (0.0, 0.0)}, "diagonal")
