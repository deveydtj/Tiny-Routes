from __future__ import annotations

from app.controllers import DocumentController
from app.models import LevelDocument, RouteEdgeModel, RouteGraphModel, RouteNodeModel


def _document() -> LevelDocument:
    return LevelDocument(
        id="undo_level",
        name="Undo Level",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id="start", x=0, y=0, outgoingEdgeIDs=["first", "second"]),
                RouteNodeModel(id="middle", x=1, y=0, outgoingEdgeIDs=[]),
                RouteNodeModel(id="finish", x=2, y=0, outgoingEdgeIDs=[]),
            ],
            edges=[
                RouteEdgeModel(id="first", fromNodeID="start", toNodeID="middle"),
                RouteEdgeModel(id="second", fromNodeID="start", toNodeID="finish"),
            ],
        ),
        startNodeID="start",
        packageNodeID="middle",
        destinationNodeID="finish",
        timeLimitSeconds=30,
        parTaps=0,
    )


def test_delete_undo_restores_edge_ids_and_outgoing_order() -> None:
    controller = DocumentController()
    document = _document()
    controller.open(document, None, saved=True)

    controller.delete_items({"middle"}, set())
    assert [edge.id for edge in document.graph.edges] == ["second"]
    assert document.graph.nodes[0].outgoingEdgeIDs == ["second"]

    controller.undo_stack.undo()
    assert [edge.id for edge in document.graph.edges] == ["first", "second"]
    assert document.graph.nodes[0].outgoingEdgeIDs == ["first", "second"]

    controller.undo_stack.redo()
    assert [edge.id for edge in document.graph.edges] == ["second"]


def test_dirty_state_tracks_saved_undo_index() -> None:
    controller = DocumentController()
    controller.open(_document(), None, saved=True)
    assert controller.is_dirty is False

    controller.move_node("middle", 4.0, 5.0)
    assert controller.is_dirty is True

    controller.undo_stack.undo()
    assert controller.is_dirty is False


def test_open_clears_undo_history() -> None:
    controller = DocumentController()
    controller.open(_document(), None, saved=True)
    controller.move_node("middle", 4.0, 5.0)
    assert controller.undo_stack.canUndo()

    controller.open(_document(), None, saved=True)
    assert controller.undo_stack.canUndo() is False
