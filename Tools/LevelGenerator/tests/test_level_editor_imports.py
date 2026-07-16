from __future__ import annotations

from app.level_editor_imports import LevelDocument, LevelValidationService, RouteGraph, RouteNode


def test_level_editor_import_shim_imports_core_symbols() -> None:
    level = LevelDocument(
        id="level_999",
        name="Level 999",
        graph=RouteGraph(nodes=[RouteNode(id="start", x=0, y=0, outgoingEdgeIDs=[])], edges=[]),
        startNodeID="start",
        packageNodeID="start",
        destinationNodeID="start",
        timeLimitSeconds=30,
        parTaps=0,
    )

    assert LevelValidationService().validate(level).has_errors is False
