from __future__ import annotations

import builtins

import pytest

from app.map_import.osm_seed_importer import MapImportDependencyError, OSMSeedImporter


def test_osm_importer_fails_nicely_when_optional_dependency_is_missing(monkeypatch) -> None:
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "osmnx":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(MapImportDependencyError):
        OSMSeedImporter().import_place("Imperial, Missouri, USA")
