from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.generation_config import GenerationConfig
from app.gui.gui_controller import (
    GuiController,
    format_generation_result,
    format_production_campaign_result,
    parse_level_ids,
)
from app.models.production_campaign import ProductionCampaignResult
from app.gui.gui_state import GuiGenerationState
from app.models.generated_level import GeneratedLevel
from app.models.generation_result import GenerationResult


class FakeGenerationService:
    def __init__(self) -> None:
        self.config = None

    def generate(self, config: GenerationConfig) -> GenerationResult:
        self.config = config
        return GenerationResult()


class FakeProductionCampaignService:
    def __init__(self) -> None:
        self.config = None
        self.call_count = 0

    def run(self, config, *, progress=None):
        self.call_count += 1
        self.config = config
        if progress:
            progress("planning", "ready")
        return SimpleNamespace(status="completed", passed=True)


def test_controller_passes_generation_config_to_service(tmp_path) -> None:
    service = FakeGenerationService()
    controller = GuiController(generation_service=service)

    result = controller.generate_from_state(_state_with_paths(tmp_path))

    assert isinstance(result, GenerationResult)
    assert isinstance(service.config, GenerationConfig)
    assert service.config.start_level_number == 12


def test_controller_invalid_state_raises_user_friendly_error(tmp_path) -> None:
    controller = GuiController(generation_service=FakeGenerationService())
    state = _state_with_paths(tmp_path, count="0")

    with pytest.raises(ValueError, match="Count must be greater than zero"):
        controller.generate_from_state(state)


def test_controller_uses_shared_production_campaign_service(tmp_path) -> None:
    service = FakeProductionCampaignService()
    controller = GuiController(
        generation_service=FakeGenerationService(),
        production_campaign_service=service,
    )
    stages = []
    state = _state_with_paths(
        tmp_path,
        start_level_number="31",
        difficulty="hard",
    )

    result = controller.generate_production_from_state(
        state, progress=lambda stage, message: stages.append(stage)
    )

    assert result.passed
    assert service.config.start_level_number == 31
    assert service.config.run_swift_tests is True
    assert service.call_count == 1
    assert stages == ["planning"]


def test_result_formatter_includes_accepted_level_id() -> None:
    result = GenerationResult(accepted=[_fake_generated_level()])

    formatted = format_generation_result(result)

    assert "level_012" in formatted
    assert "template=straight_delivery" in formatted


def test_production_result_formatter_surfaces_v3_evidence(tmp_path) -> None:
    result = ProductionCampaignResult(
        status="completed",
        run_id="production-42",
        seed=42,
        requested_count=2,
        selected_count=2,
        report_path=tmp_path / "report.json",
        reproducibility_bundle_path=tmp_path / "reproduce",
        health_report_path=tmp_path / "health.json",
        workspace_path=tmp_path / "workspace",
        quality_profile_version="1.0.0",
        quality_profile_fingerprint="1234567890abcdef",
        promoted_paths=(tmp_path / "level_031.json",),
    )

    formatted = format_production_campaign_result(result)

    assert "Production V3 status: completed" in formatted
    assert "Quality profile: 1.0.0 (1234567890ab)" in formatted
    assert "Reproduction bundle:" in formatted
    assert "Health metrics:" in formatted
    assert "Promoted files: 1" in formatted


def test_parse_level_ids_accepts_commas_spaces_and_suffixes() -> None:
    assert parse_level_ids("level_012, level_013.json path/level_014.solution.json") == [
        "level_012",
        "level_013",
        "level_014",
    ]


def _state_with_paths(tmp_path, **kwargs) -> GuiGenerationState:
    state = GuiGenerationState(
        levels_output_dir=str(tmp_path / "levels"),
        solutions_output_dir=str(tmp_path / "solutions"),
        report_path=str(tmp_path / "report.md"),
        json_report_path=str(tmp_path / "report.json"),
    )
    for key, value in kwargs.items():
        setattr(state, key, value)
    return state


def _fake_generated_level() -> GeneratedLevel:
    node = SimpleNamespace(outgoingEdgeIDs=["edge_1", "edge_2"])
    level_document = SimpleNamespace(
        id="level_012",
        graph=SimpleNamespace(nodes=[node], edges=[SimpleNamespace()]),
    )
    solution = SimpleNamespace(actions=[SimpleNamespace()])
    return GeneratedLevel(
        level_document=level_document,
        solution=solution,
        template_name="straight_delivery",
        difficulty="tutorial",
        seed=1,
    )
