from __future__ import annotations

import builtins

import pytest

from app.map_import.map_graph_simplifier import MapGraphSimplifier
from app.map_import.map_seed_to_template_adapter import MapSeedToTemplateAdapter
from app.map_import.osm_seed_importer import MapSeedEdge, MapSeedGraph, MapSeedNode
from app.map_import.osm_seed_importer import MapImportDependencyError, OSMSeedImporter
from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.templates.single_switch_template import SingleSwitchTemplate


def test_osm_importer_fails_nicely_when_optional_dependency_is_missing(monkeypatch) -> None:
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "osmnx":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(MapImportDependencyError):
        OSMSeedImporter().import_place("Imperial, Missouri, USA")


def test_map_seed_graph_round_trips_to_dict() -> None:
    graph = MapSeedGraph(
        nodes=[MapSeedNode("a", 1, 2, {"highway": "stop"})],
        edges=[MapSeedEdge("e1", "a", "a", {"name": "Main"})],
        attribution="test attribution",
    )

    assert MapSeedGraph.from_dict(graph.to_dict()) == graph


def test_map_graph_simplifier_removes_duplicates_and_normalizes() -> None:
    graph = MapSeedGraph(
        nodes=[
            MapSeedNode("a", 0, 0),
            MapSeedNode("b", 1, 0),
            MapSeedNode("c", 1, 1),
            MapSeedNode("isolated", 5, 5),
        ],
        edges=[
            MapSeedEdge("e1", "a", "b"),
            MapSeedEdge("e2", "a", "b"),
            MapSeedEdge("e3", "b", "c"),
        ],
    )

    simplified = MapGraphSimplifier().simplify(graph, max_nodes=3, seed=1)

    assert {node.id for node in simplified.nodes} == {"a", "b", "c"}
    assert len(simplified.edges) == 2
    assert all(-1.1 <= node.x <= 1.1 for node in simplified.nodes)


def test_map_seed_adapter_influences_generated_positions() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(2))
    original_positions = [(node.x, node.y) for node in generated.level_document.graph.nodes]
    seed_graph = MapSeedGraph(
        nodes=[
            MapSeedNode("a", 0, 0),
            MapSeedNode("b", 1, 0),
            MapSeedNode("c", 2, 1),
            MapSeedNode("d", 3, 1),
            MapSeedNode("e", 4, 0),
        ],
        edges=[
            MapSeedEdge("e1", "a", "b"),
            MapSeedEdge("e2", "b", "c"),
            MapSeedEdge("e3", "c", "d"),
            MapSeedEdge("e4", "d", "e"),
        ],
        attribution="map attribution",
    )

    adapted = MapSeedToTemplateAdapter().apply_to_generated_level(seed_graph, generated, RandomSource(4))

    assert [(node.x, node.y) for node in adapted.level_document.graph.nodes] != original_positions
    assert any("Map attribution" in note for note in adapted.generation_notes)
