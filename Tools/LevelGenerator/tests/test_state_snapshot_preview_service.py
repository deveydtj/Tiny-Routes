from app.random_source import RandomSource
from app.services.difficulty_service import DifficultyService
from app.services.state_snapshot_preview_service import StateSnapshotPreviewService
from app.templates.single_switch_template import SingleSwitchTemplate


def test_state_snapshot_previews_include_each_state_and_route_overlays(tmp_path) -> None:
    generated = SingleSwitchTemplate().generate(
        "level_012",
        12,
        DifficultyService().get_preset("easy"),
        RandomSource(2),
    )
    route = tuple(
        generated.solution._extra["metadata"]["solutionRoute"]
    )

    result = StateSnapshotPreviewService().write_generated_level_previews(
        generated,
        tmp_path,
        alternate_routes=((route[0], route[-1]),),
    )

    assert [artifact.kind for artifact in result.artifacts] == [
        "initial_state",
        "objective_completion_state",
        "objective_completion_state",
        "final_route_overlay",
        "optimal_alternate_overlay",
    ]
    assert generated.state_preview_paths == result.paths
    assert all(path.exists() for path in result.paths)
    assert "Active objective:" in result.paths[0].read_text(encoding="utf-8")
    assert "#16a34a" in result.paths[-1].read_text(encoding="utf-8")
    assert "#9333ea" in result.paths[-1].read_text(encoding="utf-8")


def test_same_candidate_writes_byte_identical_state_previews(tmp_path) -> None:
    generated = SingleSwitchTemplate().generate(
        "level_012",
        12,
        DifficultyService().get_preset("easy"),
        RandomSource(2),
    )
    service = StateSnapshotPreviewService()
    first = service.write_generated_level_previews(generated, tmp_path / "first")
    second = service.write_generated_level_previews(generated, tmp_path / "second")

    assert [path.read_bytes() for path in first.paths] == [
        path.read_bytes() for path in second.paths
    ]
