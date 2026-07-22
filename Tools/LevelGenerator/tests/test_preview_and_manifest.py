from __future__ import annotations

import json

from app.random_source import RandomSource
from app.repositories.generated_level_repository import GeneratedLevelRepository
from app.services.difficulty_service import DifficultyService
from app.services.preview_image_service import PreviewImageService
from app.services.production_manifest_service import ProductionManifestService
from app.templates.single_switch_template import SingleSwitchTemplate


def test_preview_image_service_writes_svg(tmp_path) -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(2))

    path = PreviewImageService().write_preview(generated, tmp_path)

    assert path.exists()
    assert "<svg" in path.read_text(encoding="utf-8")
    assert generated.preview_path == path


def test_production_manifest_rebuilds_from_level_files(tmp_path) -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(2))
    writer = GeneratedLevelRepository()
    writer.write_level(generated.level_document, tmp_path / "levels" / "level_012.json")
    writer.write_solution(generated.solution, tmp_path / "solutions" / "level_012.solution.json")

    output = ProductionManifestService().rebuild(
        tmp_path / "levels",
        tmp_path / "solutions",
        tmp_path / "manifest.json",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["levels"][0]["levelID"] == "level_012"
    assert payload["levels"][0]["difficultyEstimate"] == "easy"
    assert payload["levels"][0]["topologyHash"]
    assert payload["levels"][0]["structuralBehaviorSignature"]
