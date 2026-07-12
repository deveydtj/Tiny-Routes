from __future__ import annotations

import pytest

from app.controllers import DocumentController
from app.models import (
    EmbeddedSolution,
    LevelDocument,
    RouteEdgeModel,
    RouteGraphModel,
    RouteNodeModel,
    SolutionActionModel,
    SolutionModel,
)


def _document() -> tuple[LevelDocument, SolutionModel]:
    document = LevelDocument(
        id="rename_level",
        name="Rename Level",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id="start", x=0, y=0, outgoingEdgeIDs=["road"]),
                RouteNodeModel(id="target", x=1, y=0, outgoingEdgeIDs=[]),
            ],
            edges=[RouteEdgeModel(id="road", fromNodeID="start", toNodeID="target")],
            _extra={"analysis": {"edgeIDs": ["road"], "nodeIDs": ["start", "target"]}},
        ),
        startNodeID="start",
        packageNodeID="target",
        destinationNodeID="target",
        timeLimitSeconds=20,
        parTaps=1,
        solution=EmbeddedSolution(tapNodeIDs=["start"]),
        _extra={"metadata": {"solutionRoute": ["start", "target"]}},
    )
    solution = SolutionModel(
        levelID=document.id,
        description=None,
        expectedOutcome="completed",
        maxTaps=1,
        requiresWithinTimeLimit=True,
        actions=[SolutionActionModel(1.0, "start", {"expectedEdgeAfterTap": "road"})],
    )
    return document, solution


def test_node_rename_updates_all_references_and_undo_restores_them() -> None:
    document, solution = _document()
    controller = DocumentController()
    controller.open(document, solution, saved=True)

    controller.rename_node("target", "delivery")

    assert document.packageNodeID == "delivery"
    assert document.destinationNodeID == "delivery"
    assert document.graph.edges[0].toNodeID == "delivery"
    assert document.graph._extra["analysis"]["nodeIDs"] == ["start", "delivery"]
    assert document._extra["metadata"]["solutionRoute"] == ["start", "delivery"]

    controller.undo_stack.undo()
    assert document.packageNodeID == "target"
    assert document.graph.edges[0].toNodeID == "target"
    assert document._extra["metadata"]["solutionRoute"] == ["start", "target"]


def test_edge_rename_updates_outgoing_and_solution_metadata() -> None:
    document, solution = _document()
    controller = DocumentController()
    controller.open(document, solution, saved=True)

    controller.rename_edge("road", "road_to_target")

    assert document.graph.edges[0].id == "road_to_target"
    assert document.graph.nodes[0].outgoingEdgeIDs == ["road_to_target"]
    assert document.graph._extra["analysis"]["edgeIDs"] == ["road_to_target"]
    assert solution.actions[0]._extra["expectedEdgeAfterTap"] == "road_to_target"


@pytest.mark.parametrize("kind", ["node", "edge"])
def test_duplicate_rename_is_rejected_before_mutation(kind: str) -> None:
    document, solution = _document()
    controller = DocumentController()
    controller.open(document, solution, saved=True)
    before = document.to_dict()

    with pytest.raises(ValueError, match="already exists"):
        if kind == "node":
            controller.rename_node("start", "target")
        else:
            document.graph.edges.append(RouteEdgeModel("other", "target", "start"))
            before = document.to_dict()
            controller.rename_edge("road", "other")

    assert document.to_dict() == before
    assert controller.undo_stack.canUndo() is False
