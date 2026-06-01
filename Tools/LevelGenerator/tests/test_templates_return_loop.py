from __future__ import annotations

from collections import Counter

from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.services.graph_builder_service import GraphBuilderService
from app.services.layout_variant_service import LayoutVariantService
from app.services.visual_clarity_validation_service import VisualClarityValidationService
from app.templates.return_loop_template import ReturnLoopTemplate, _variant_spec


RETURN_LOOP_VARIANTS = ("return_loop_classic", "return_loop_upper", "return_loop_lower")


def test_return_loop_repeats_switch_tap_with_safe_spacing() -> None:
    preset = DifficultyService().get_preset("medium")
    generated = ReturnLoopTemplate().generate("level_012", 12, preset, RandomSource(4))
    tap_counts = Counter(action.tapNodeID for action in generated.solution.actions)
    times = [action.timeSeconds for action in generated.solution.actions]

    assert tap_counts["alpha_switch"] == 2
    assert min(b - a for a, b in zip(times, times[1:])) >= preset.min_tap_spacing_seconds
    assert generated.level_document.parTaps == len(generated.solution.actions)
    assert not GeneratedLevelValidationService().validate(generated, preset=preset, overwrite=True).has_errors


def test_return_loop_variants_pass_visual_clarity_validation() -> None:
    service = VisualClarityValidationService()

    for variant in RETURN_LOOP_VARIANTS:
        level, route, _ = _level_for_variant(variant)
        report = service.report_for_level(level, required_path=tuple(route))
        error_codes = {issue.code for issue in report.errors}

        assert not report.has_errors, f"{variant} visual clarity errors: {sorted(error_codes)}"
        assert "return_loop_false_shortcut" not in error_codes


def test_return_loop_layout_variants_pass_visual_clarity_validation() -> None:
    preset = DifficultyService().get_preset("medium")
    layout_variants = LayoutVariantService()
    visual_clarity = VisualClarityValidationService()

    for variant in RETURN_LOOP_VARIANTS:
        positions, _, _, _ = _variant_spec(variant)
        for layout_name in layout_variants.variant_names:
            for seed in range(1, 26):
                layout = layout_variants.apply_variant(layout_name, positions, RandomSource(seed), preset)
                level, route, _ = _level_for_variant(variant, positions=layout.positions)
                report = visual_clarity.report_for_level(level, required_path=tuple(route))
                error_codes = {issue.code for issue in report.errors}

                assert not report.has_errors, f"{variant}/{layout.name}/{seed} visual clarity errors: {sorted(error_codes)}"
                assert "return_loop_false_shortcut" not in error_codes


def test_return_loop_variants_keep_repeated_switch_required_path() -> None:
    for variant in RETURN_LOOP_VARIANTS:
        _, route, tap_node_ids = _level_for_variant(variant)
        route_counts = Counter(route)
        tap_counts = Counter(tap_node_ids)
        repeated_tap_node_ids = [node_id for node_id, count in tap_counts.items() if count > 1]

        assert repeated_tap_node_ids == [tap_node_ids[0]]
        assert route_counts[tap_node_ids[0]] == 2
        assert tap_node_ids == [tap_node_ids[0], tap_node_ids[1], tap_node_ids[0]]
        assert route.index("package") < route.index("destination")
        assert len(tap_node_ids) == 3


def _level_for_variant(variant: str, positions: dict[str, tuple[float, float]] | None = None):
    default_positions, edges, tap_node_ids, route = _variant_spec(variant)
    positions = positions or default_positions
    builder = GraphBuilderService()
    for node_id, position in positions.items():
        builder.add_node(node_id, *position)
    for from_node_id, to_node_id in edges:
        destination_shape = "horizontalFirst" if to_node_id == "destination" else None
        builder.add_edge(from_node_id, to_node_id, road_shape=destination_shape)
    return (
        builder.build_level_document(
            level_id=f"level_{variant}",
            name=variant,
            start_node_id="start",
            package_node_id="package",
            destination_node_id="destination",
            time_limit_seconds=30,
            par_taps=3,
        ),
        route,
        tap_node_ids,
    )
