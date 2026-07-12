from __future__ import annotations

from enum import Enum


class EditorTool(Enum):
    SELECT = "select"
    PLACE_NODE = "place_node"
    CONNECT = "connect"
    PLAYTEST = "playtest"

    @property
    def label(self) -> str:
        return {
            EditorTool.SELECT: "Select",
            EditorTool.PLACE_NODE: "Place Node",
            EditorTool.CONNECT: "Connect",
            EditorTool.PLAYTEST: "Playtest",
        }[self]

    @property
    def status_message(self) -> str:
        return {
            EditorTool.SELECT: "Select and move level items.",
            EditorTool.PLACE_NODE: "Choose a node type, then click the canvas to place it.",
            EditorTool.CONNECT: "Choose a start node and destination node to connect them.",
            EditorTool.PLAYTEST: "Playtest mode: editing gestures are disabled.",
        }[self]
