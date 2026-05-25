from __future__ import annotations

import json

import pytest

from app.random_source import RandomSource
from app.repositories.generated_level_repository import GeneratedLevelRepository
from app.services.difficulty_service import DifficultyService
from app.templates.straight_delivery_template import StraightDeliveryTemplate


def test_generated_level_repository_writes_json_with_trailing_newline(tmp_path) -> None:
    preset = DifficultyService().get_preset("tutorial")
    generated = StraightDeliveryTemplate().generate("level_012", 12, preset, RandomSource(11))
    repository = GeneratedLevelRepository()
    path = repository.write_level(generated.level_document, tmp_path / "level_012.json")

    content = path.read_text(encoding="utf-8")
    assert content.endswith("\n")
    assert json.loads(content)["id"] == "level_012"


def test_generated_level_repository_refuses_overwrite(tmp_path) -> None:
    repository = GeneratedLevelRepository()
    path = tmp_path / "level_012.json"
    path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        repository.write_level(type("Level", (), {"to_dict": lambda self: {}})(), path, overwrite=False)
