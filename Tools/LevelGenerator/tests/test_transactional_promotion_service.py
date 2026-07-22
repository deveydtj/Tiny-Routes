from __future__ import annotations

from dataclasses import replace

from app.random_source import RandomSource
from app.repositories.generated_level_repository import GeneratedLevelRepository
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
from app.services.production_staged_output_service import ProductionStagedOutputService
from app.services.production_staging_service import ProductionStagingService
from app.services.transactional_promotion_service import TransactionalPromotionService
from app.templates.single_switch_template import SingleSwitchTemplate


def _candidate(level_id: str, number: int, seed: int):
    candidate = SingleSwitchTemplate().generate(
        level_id,
        number,
        DifficultyService().get_preset("easy"),
        RandomSource(seed),
    )
    candidate.candidate_signature = CandidateSignatureService().signature_for(candidate)
    return candidate


def _validated_workspace(tmp_path):
    levels = tmp_path / "production" / "levels"
    solutions = tmp_path / "production" / "solutions"
    manifest_path = tmp_path / "production" / "production_manifest.json"
    project_file = tmp_path / "production" / "project.pbxproj"
    project_file.parent.mkdir(parents=True, exist_ok=True)
    project_file.write_text("original project\n", encoding="utf-8")
    existing = _candidate("level_001", 1, 1)
    writer = GeneratedLevelRepository()
    writer.write_level(existing.level_document, levels / "level_001.json")
    writer.write_solution(existing.solution, solutions / "level_001.solution.json")
    manifest_path.write_text("original manifest\n", encoding="utf-8")

    workspace = ProductionStagingService(tmp_path / "staging").create_workspace(
        "promotion-run",
        seed=42,
        config_snapshot={"generatorArchitecture": "production_v3"},
    )
    selected = _candidate("level_002", 2, 2)
    staged = ProductionStagedOutputService().write_selected_candidates(
        workspace,
        [selected],
        production_levels_dir=levels,
        production_solutions_dir=solutions,
        production_manifest_path=manifest_path,
        production_project_file=project_file,
    )
    replace(staged, status="validated").write(workspace.run_manifest_path)
    return workspace, levels, solutions, manifest_path, project_file


def test_atomic_promotion_moves_every_selected_artifact(tmp_path) -> None:
    workspace, levels, solutions, manifest_path, project_file = _validated_workspace(tmp_path)
    service = TransactionalPromotionService(
        resource_updater=lambda: True,
        lightweight_validator=lambda manifest: True,
    )

    result = service.promote(
        workspace,
        lock_path=tmp_path / "production" / ".generation.lock",
        project_file=project_file,
    )

    assert result.status == "completed"
    assert (levels / "level_002.json").read_bytes() == (
        workspace.levels_dir / "level_002.json"
    ).read_bytes()
    assert (solutions / "level_002.solution.json").read_bytes() == (
        workspace.solutions_dir / "level_002.solution.json"
    ).read_bytes()
    assert manifest_path.read_bytes() == workspace.proposed_manifest_path.read_bytes()
    assert (
        workspace.run_manifest_path.read_text(encoding="utf-8").find(
            '"status": "completed"'
        )
        >= 0
    )
    assert not (workspace.root / "promotion_backup").exists()


def test_preflight_conflict_leaves_production_unchanged(tmp_path) -> None:
    workspace, levels, _, manifest_path, project_file = _validated_workspace(tmp_path)
    conflicting_level = levels / "level_002.json"
    conflicting_level.write_text("created outside the run\n", encoding="utf-8")
    conflict_bytes = conflicting_level.read_bytes()
    manifest_before = manifest_path.read_bytes()

    result = TransactionalPromotionService(resource_updater=lambda: True).promote(
        workspace,
        lock_path=tmp_path / "production" / ".generation.lock",
        project_file=project_file,
    )

    assert result.status == "failed_no_changes"
    assert conflicting_level.read_bytes() == conflict_bytes
    assert manifest_path.read_bytes() == manifest_before


def test_post_promotion_failure_restores_overwrites_and_removes_new_files(tmp_path) -> None:
    workspace, levels, solutions, manifest_path, project_file = _validated_workspace(tmp_path)
    original_level = (levels / "level_001.json").read_bytes()
    original_solution = (solutions / "level_001.solution.json").read_bytes()
    original_manifest = manifest_path.read_bytes()

    result = TransactionalPromotionService(
        resource_updater=lambda: True,
        lightweight_validator=lambda manifest: False,
    ).promote(
        workspace,
        lock_path=tmp_path / "production" / ".generation.lock",
        project_file=project_file,
    )

    assert result.status == "rolled_back"
    assert (levels / "level_001.json").read_bytes() == original_level
    assert (solutions / "level_001.solution.json").read_bytes() == original_solution
    assert manifest_path.read_bytes() == original_manifest
    assert not (levels / "level_002.json").exists()
    assert not (solutions / "level_002.solution.json").exists()
