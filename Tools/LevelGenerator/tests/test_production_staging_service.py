from __future__ import annotations

import json

import pytest

from app.services.production_staging_service import ProductionStagingService


def test_create_workspace_allocates_complete_isolated_tree(tmp_path) -> None:
    production_levels = tmp_path / "production" / "levels"
    production_levels.mkdir(parents=True)
    sentinel = production_levels / "level_001.json"
    sentinel.write_text("production stays unchanged\n", encoding="utf-8")
    service = ProductionStagingService(tmp_path / "staging")

    workspace = service.create_workspace(
        "run-20260721-001",
        seed=451,
        config_snapshot={"count": 5, "mode": "production_v3"},
    )

    assert workspace.root == (tmp_path / "staging" / "run-20260721-001").resolve()
    assert all(
        path.is_dir()
        for path in (
            workspace.levels_dir,
            workspace.solutions_dir,
            workspace.previews_dir,
            workspace.reports_dir,
            workspace.validation_logs_dir,
        )
    )
    assert workspace.proposed_manifest_path.parent == workspace.root
    assert workspace.proposed_manifest_path.exists() is False
    assert json.loads(workspace.seed_config_snapshot_path.read_text(encoding="utf-8")) == {
        "configuration": {"count": 5, "mode": "production_v3"},
        "runID": "run-20260721-001",
        "seed": 451,
    }
    assert sentinel.read_text(encoding="utf-8") == "production stays unchanged\n"
    assert workspace.contains(workspace.levels_dir / "level_001.json")
    assert not workspace.contains(sentinel)


def test_workspace_refuses_traversal_and_duplicate_run_ids(tmp_path) -> None:
    service = ProductionStagingService(tmp_path / "staging")

    with pytest.raises(ValueError, match="run_id"):
        service.create_workspace("../escape", seed=1, config_snapshot={})

    service.create_workspace("safe-run", seed=1, config_snapshot={})
    with pytest.raises(FileExistsError, match="already exists"):
        service.create_workspace("safe-run", seed=2, config_snapshot={})


def test_snapshot_serialization_failure_leaves_no_partial_workspace(tmp_path) -> None:
    staging_root = tmp_path / "staging"
    service = ProductionStagingService(staging_root)

    with pytest.raises(TypeError):
        service.create_workspace(
            "bad-snapshot",
            seed=1,
            config_snapshot={"notJSON": object()},
        )

    assert not staging_root.exists()


def test_open_workspace_verifies_required_paths(tmp_path) -> None:
    service = ProductionStagingService(tmp_path / "staging")
    created = service.create_workspace("open-me", seed=1, config_snapshot={})

    assert service.open_workspace("open-me") == created
    created.validation_logs_dir.rmdir()
    with pytest.raises(FileNotFoundError, match="missing required paths"):
        service.open_workspace("open-me")


def test_workspace_require_path_rejects_non_staging_target(tmp_path) -> None:
    workspace = ProductionStagingService(tmp_path / "staging").create_workspace(
        "safe-run",
        seed=1,
        config_snapshot={},
    )

    assert workspace.require_path(workspace.reports_dir / "report.json").parent == workspace.reports_dir
    with pytest.raises(ValueError, match="outside production staging"):
        workspace.require_path(tmp_path / "production" / "manifest.json")
