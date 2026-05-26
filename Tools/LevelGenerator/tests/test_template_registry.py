from __future__ import annotations

from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.templates.template_registry import TemplateRegistry


def test_mixed_never_chooses_unsupported_templates_for_tutorial() -> None:
    registry = TemplateRegistry()
    preset = DifficultyService().get_preset("tutorial")

    chosen = {registry.choose("mixed", preset, RandomSource(seed)).name for seed in range(20)}
    assert chosen <= {"straight_delivery", "single_switch"}


def test_mixed_excludes_swift_required_templates_when_requested() -> None:
    registry = TemplateRegistry()
    preset = DifficultyService().get_preset("hard")
    chosen = {registry.choose("mixed", preset, RandomSource(seed), include_swift_required=False).name for seed in range(20)}

    assert "ring_route" not in chosen


def test_four_way_intersection_template_is_expert_only() -> None:
    registry = TemplateRegistry()

    assert registry.get("four_way_intersection").supports_difficulty(DifficultyService().get_preset("expert"))
    assert not registry.get("four_way_intersection").supports_difficulty(DifficultyService().get_preset("hard"))


def test_mixed_can_choose_four_way_intersection_for_expert() -> None:
    registry = TemplateRegistry()
    preset = DifficultyService().get_preset("expert")

    chosen = {registry.choose("mixed", preset, RandomSource(seed)).name for seed in range(30)}

    assert "four_way_intersection" in chosen
