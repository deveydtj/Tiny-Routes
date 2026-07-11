from __future__ import annotations

from app.level_editor_imports import SolutionModel
from app.models.abstract_puzzle_solution import AbstractPuzzleSolutionMetadata
from app.models.generated_level import GeneratedLevel
from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.generated_level_validation_service import GeneratedLevelValidationService
from app.services.graph_builder_service import GraphBuilderService
from app.services.road_geometry_validation_service import RoadGeometryValidationService
from app.templates.package_gate_template import PackageGateTemplate
from app.templates.return_loop_template import ReturnLoopTemplate, _variant_spec
from app.templates.single_switch_template import SingleSwitchTemplate
from app.templates.straight_delivery_template import StraightDeliveryTemplate


def test_level_7_like_visual_loop_is_rejected_by_generated_validation() -> None:
    generated = _generated_for_geometry_fixture(
        "level_007_loop",
        {
            "start": (-1.15, 0.0),
            "alpha_switch": (-0.25, 0.0),
            "package": (0.08, 0.64),
            "beta_switch": (0.62, 0.52),
            "return_a": (0.9, -0.62),
            "destination": (-0.75, -1.05),
            "dead_end_a": (1.08, 0.12),
        },
        [
            ("start", "alpha_switch"),
            ("alpha_switch", "destination"),
            ("alpha_switch", "package"),
            ("package", "beta_switch"),
            ("beta_switch", "dead_end_a"),
            ("beta_switch", "return_a"),
            ("return_a", "alpha_switch"),
        ],
        ["start", "alpha_switch", "package", "beta_switch", "return_a", "alpha_switch", "destination"],
    )

    result = GeneratedLevelValidationService().validate(
        generated,
        preset=DifficultyService().get_preset("medium"),
        overwrite=True,
        enforce_difficulty=False,
    )

    assert "road_visually_circles_back_on_itself" in result.error_codes


def test_revisited_switch_return_corridor_too_tight_is_rejected() -> None:
    report = _geometry_report(
        {
            "start": (-1.0, 0.0),
            "alpha_switch": (0.0, 0.0),
            "package": (0.0, 0.9),
            "beta_switch": (0.82, 0.9),
            "return_a": (0.16, 0.32),
            "destination": (0.0, -0.9),
        },
        [
            ("start", "alpha_switch"),
            ("alpha_switch", "package"),
            ("package", "beta_switch"),
            ("beta_switch", "return_a"),
            ("return_a", "alpha_switch"),
            ("alpha_switch", "destination"),
        ],
        ["start", "alpha_switch", "package", "beta_switch", "return_a", "alpha_switch", "destination"],
    )

    assert "revisited_switch_corridor_too_tight" in _issue_codes(report)


def test_return_branch_close_to_destination_branch_is_rejected() -> None:
    report = _geometry_report(
        {
            "start": (-1.0, 0.0),
            "alpha_switch": (0.0, 0.0),
            "package": (0.0, 0.78),
            "beta_switch": (0.95, 0.78),
            "return_a": (0.95, -0.18),
            "destination": (1.05, -0.04),
        },
        [
            ("start", "alpha_switch"),
            ("alpha_switch", "package"),
            ("package", "beta_switch"),
            ("beta_switch", "return_a"),
            ("return_a", "alpha_switch"),
            ("alpha_switch", "destination"),
        ],
        ["start", "alpha_switch", "package", "beta_switch", "return_a", "alpha_switch", "destination"],
    )

    assert "return_path_too_close_to_destination_branch" in _issue_codes(report)


def test_non_adjacent_road_corridors_too_close_are_rejected() -> None:
    report = _geometry_report(
        {
            "start": (-1.0, 0.0),
            "package": (0.0, 0.0),
            "detour_a": (-1.0, 0.14),
            "destination": (0.0, 0.14),
        },
        [
            ("start", "package"),
            ("detour_a", "destination"),
        ],
        ["start", "package"],
    )

    assert "non_adjacent_roads_too_close" in _issue_codes(report)


def test_clean_return_loop_layout_passes_road_geometry_validation() -> None:
    report = _geometry_report(
        {
            "start": (-1.15, -0.28),
            "alpha_switch": (-0.82, -0.28),
            "package": (-0.52, 0.58),
            "beta_switch": (0.7, 0.58),
            "return_a": (1.02, -0.28),
            "destination": (-0.82, -1.08),
            "dead_end_a": (1.04, 0.18),
        },
        [
            ("start", "alpha_switch"),
            ("alpha_switch", "destination"),
            ("alpha_switch", "package"),
            ("package", "beta_switch"),
            ("beta_switch", "dead_end_a"),
            ("beta_switch", "return_a"),
            ("return_a", "alpha_switch"),
        ],
        ["start", "alpha_switch", "package", "beta_switch", "return_a", "alpha_switch", "destination"],
    )

    assert not report.has_errors


def test_return_loop_template_variants_pass_road_geometry_validation() -> None:
    preset = DifficultyService().get_preset("medium")
    service = RoadGeometryValidationService()

    for variant in ("return_loop_classic", "return_loop_upper", "return_loop_lower"):
        positions, edges, _, route = _variant_spec(variant)
        level = _level_for_geometry_fixture(
            f"level_{variant}",
            positions,
            edges,
            destination_shape="verticalFirst",
            return_to_alpha_shape="verticalFirst",
        )
        report = service.report_for_level(level, required_path=tuple(route), preset=preset)

        assert not report.has_errors, f"{variant} geometry errors: {sorted(_issue_codes(report))}"


def test_existing_normal_templates_pass_generated_validation_with_geometry_checks() -> None:
    validator = GeneratedLevelValidationService()
    cases = [
        (StraightDeliveryTemplate(), "tutorial", 1),
        (SingleSwitchTemplate(), "easy", 2),
        (PackageGateTemplate(), "medium", 3),
        (ReturnLoopTemplate(), "medium", 4),
    ]

    for template, difficulty, seed in cases:
        preset = DifficultyService().get_preset(difficulty)
        generated = template.generate("level_012", 12, preset, RandomSource(seed))
        result = validator.validate(generated, preset=preset, overwrite=True)

        assert not result.has_errors, f"{template.name} errors: {result.error_codes}"


def _geometry_report(
    positions: dict[str, tuple[float, float]],
    edges: list[tuple[str, str]],
    route: list[str],
):
    return RoadGeometryValidationService().report_for_level(
        _level_for_geometry_fixture("level_geometry", positions, edges),
        required_path=tuple(route),
        preset=DifficultyService().get_preset("medium"),
    )


def _generated_for_geometry_fixture(
    level_id: str,
    positions: dict[str, tuple[float, float]],
    edges: list[tuple[str, str]],
    route: list[str],
) -> GeneratedLevel:
    level = _level_for_geometry_fixture(level_id, positions, edges)
    generated = GeneratedLevel(
        level_document=level,
        solution=SolutionModel(
            levelID=level.id,
            description="Geometry fixture.",
            expectedOutcome="completed",
            maxTaps=0,
            requiresWithinTimeLimit=True,
            actions=[],
            isPlaceholder=None,
            _extra={"metadata": {"solutionRoute": list(route), "requiredTapOrder": []}},
        ),
        template_name="geometry_fixture",
        difficulty="medium",
        seed=1,
    )
    generated.abstract_solution_metadata = AbstractPuzzleSolutionMetadata(
        decision_node_ids=(),
        solution_switch_states=(),
        required_path=tuple(route),
        alternate_path_count=0,
        dead_end_count=0,
        failure_path_count=0,
        false_route_count=0,
        loop_count=1,
        minimum_required_decisions=0,
        optional_tap_count=0,
        repeated_switch_usage=True,
        package_before_destination=True,
    )
    return generated


def _level_for_geometry_fixture(
    level_id: str,
    positions: dict[str, tuple[float, float]],
    edges: list[tuple[str, str]],
    *,
    destination_shape: str = "horizontalFirst",
    return_to_alpha_shape: str | None = None,
):
    builder = GraphBuilderService()
    for node_id, position in positions.items():
        builder.add_node(node_id, *position)
    for from_node_id, to_node_id in edges:
        road_shape = destination_shape if to_node_id == "destination" else None
        if return_to_alpha_shape is not None and "return" in from_node_id and "alpha_switch" in to_node_id:
            road_shape = return_to_alpha_shape
        builder.add_edge(from_node_id, to_node_id, road_shape=road_shape)
    return builder.build_level_document(
        level_id=level_id,
        name=level_id,
        start_node_id="start",
        package_node_id="package",
        destination_node_id="destination",
        time_limit_seconds=30,
        par_taps=3,
    )


def _issue_codes(report) -> set[str]:
    return {issue.code for issue in report.issues}
