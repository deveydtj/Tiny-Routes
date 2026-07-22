from __future__ import annotations

import os
import shutil
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.random_source import RandomSource
from app.repositories.generated_level_repository import GeneratedLevelRepository
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
from app.services.production_generation_lock_service import (
    ProductionGenerationLockService,
)
import app.services.production_staged_corpus_validation_service as validation_module
from app.services.production_staged_corpus_validation_service import (
    ProductionStagedCorpusValidationService,
)
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


def _workspace(tmp_path, *, validated: bool = True):
    production = tmp_path / "production"
    levels = production / "levels"
    solutions = production / "solutions"
    manifest_path = production / "production_manifest.json"
    project_file = production / "project.pbxproj"
    project_file.parent.mkdir(parents=True, exist_ok=True)
    project_file.write_text("original project\n", encoding="utf-8")

    existing = _candidate("level_001", 1, 1)
    repository = GeneratedLevelRepository()
    repository.write_level(existing.level_document, levels / "level_001.json")
    repository.write_solution(existing.solution, solutions / "level_001.solution.json")
    manifest_path.write_text("original manifest\n", encoding="utf-8")

    workspace = ProductionStagingService(tmp_path / "staging").create_workspace(
        "rollback-run",
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
    if validated:
        replace(staged, status="validated").write(workspace.run_manifest_path)
    return workspace, levels, solutions, manifest_path, project_file


def _production_snapshot(levels, solutions, manifest_path, project_file):
    return {
        "level": (levels / "level_001.json").read_bytes(),
        "solution": (solutions / "level_001.solution.json").read_bytes(),
        "manifest": manifest_path.read_bytes(),
        "project": project_file.read_bytes(),
    }


def _assert_production_restored(
    snapshot,
    levels,
    solutions,
    manifest_path,
    project_file,
) -> None:
    assert (levels / "level_001.json").read_bytes() == snapshot["level"]
    assert (solutions / "level_001.solution.json").read_bytes() == snapshot["solution"]
    assert manifest_path.read_bytes() == snapshot["manifest"]
    assert project_file.read_bytes() == snapshot["project"]
    assert not (levels / "level_002.json").exists()
    assert not (solutions / "level_002.solution.json").exists()


def test_python_validation_failure_never_reaches_production(tmp_path) -> None:
    workspace, levels, solutions, manifest_path, project_file = _workspace(
        tmp_path,
        validated=False,
    )
    before = _production_snapshot(levels, solutions, manifest_path, project_file)
    (workspace.levels_dir / "level_002.json").write_text("{}\n", encoding="utf-8")

    validation = ProductionStagedCorpusValidationService().validate(
        workspace,
        (),
        repo_root=tmp_path,
        project_file=project_file,
        run_swift_tests=False,
    )

    assert validation.passed is False
    assert "staged_artifact_hash_mismatch" in {
        issue.code for issue in validation.issues
    }
    assert '"status": "staged"' in workspace.run_manifest_path.read_text(
        encoding="utf-8"
    )
    _assert_production_restored(
        before, levels, solutions, manifest_path, project_file
    )


def test_swift_validation_failure_never_reaches_production(
    tmp_path,
    monkeypatch,
) -> None:
    workspace, levels, solutions, manifest_path, project_file = _workspace(
        tmp_path,
        validated=False,
    )
    before = _production_snapshot(levels, solutions, manifest_path, project_file)

    class FailingSwiftTestService:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def run(self):
            return SimpleNamespace(
                passed=False,
                exit_code=65,
                summary="simulated Swift parity failure",
                command=("xcodebuild", "test"),
                environment={},
                failure_reasons=("simulated Swift parity failure",),
            )

    monkeypatch.setattr(
        validation_module,
        "SwiftTestService",
        FailingSwiftTestService,
    )
    validation = ProductionStagedCorpusValidationService().validate(
        workspace,
        (),
        repo_root=tmp_path,
        project_file=project_file,
        run_swift_tests=True,
    )

    assert "swift_staged_parity_failed" in {
        issue.code for issue in validation.issues
    }
    assert '"status": "staged"' in workspace.run_manifest_path.read_text(
        encoding="utf-8"
    )
    _assert_production_restored(
        before, levels, solutions, manifest_path, project_file
    )


def test_manifest_collision_fails_before_any_production_write(tmp_path) -> None:
    workspace, levels, solutions, manifest_path, project_file = _workspace(tmp_path)
    before = _production_snapshot(levels, solutions, manifest_path, project_file)
    collision = levels / "level_002.json"
    collision.write_text("external writer won\n", encoding="utf-8")

    result = TransactionalPromotionService(resource_updater=lambda: True).promote(
        workspace,
        lock_path=tmp_path / "production" / ".generation.lock",
        project_file=project_file,
    )

    assert result.status == "failed_no_changes"
    assert "appeared after preflight" in result.failure_reason
    assert collision.read_text(encoding="utf-8") == "external writer won\n"
    assert (levels / "level_001.json").read_bytes() == before["level"]
    assert (solutions / "level_001.solution.json").read_bytes() == before["solution"]
    assert manifest_path.read_bytes() == before["manifest"]
    assert project_file.read_bytes() == before["project"]


def test_file_write_failure_after_partial_promotion_rolls_back_every_target(
    tmp_path,
) -> None:
    workspace, levels, solutions, manifest_path, project_file = _workspace(tmp_path)
    before = _production_snapshot(levels, solutions, manifest_path, project_file)
    replacements = 0

    def fail_second_replacement(source, target):
        nonlocal replacements
        replacements += 1
        if replacements == 2:
            raise OSError("simulated file write failure")
        os.replace(source, target)

    result = TransactionalPromotionService(
        resource_updater=lambda: True,
        lightweight_validator=lambda manifest: True,
        file_replacer=fail_second_replacement,
    ).promote(
        workspace,
        lock_path=tmp_path / "production" / ".generation.lock",
        project_file=project_file,
    )

    assert result.status == "rolled_back"
    assert "simulated file write failure" in result.failure_reason
    assert result.promoted_paths
    _assert_production_restored(
        before, levels, solutions, manifest_path, project_file
    )
    assert not (workspace.root / "promotion_backup").exists()


def test_promotion_interrupt_restores_files_before_propagating_interrupt(
    tmp_path,
) -> None:
    workspace, levels, solutions, manifest_path, project_file = _workspace(tmp_path)
    before = _production_snapshot(levels, solutions, manifest_path, project_file)
    replacements = 0

    def interrupt_second_replacement(source, target):
        nonlocal replacements
        replacements += 1
        if replacements == 2:
            raise KeyboardInterrupt("simulated promotion interruption")
        os.replace(source, target)

    service = TransactionalPromotionService(
        resource_updater=lambda: True,
        file_replacer=interrupt_second_replacement,
    )
    lock_path = tmp_path / "production" / ".generation.lock"

    with pytest.raises(KeyboardInterrupt, match="promotion interruption"):
        service.promote(
            workspace,
            lock_path=lock_path,
            project_file=project_file,
        )

    _assert_production_restored(
        before, levels, solutions, manifest_path, project_file
    )
    assert '"status": "rolled_back"' in workspace.run_manifest_path.read_text(
        encoding="utf-8"
    )
    assert not lock_path.exists()


def test_staging_copy_failure_leaves_production_unchanged(tmp_path) -> None:
    workspace, levels, solutions, manifest_path, project_file = _workspace(tmp_path)
    before = _production_snapshot(levels, solutions, manifest_path, project_file)

    def fail_staged_copy(source, target):
        if str(target).endswith(".promoting"):
            target.write_bytes(b"partial")
            raise OSError("simulated staging copy failure")
        return shutil.copy2(source, target)

    result = TransactionalPromotionService(
        resource_updater=lambda: True,
        file_copier=fail_staged_copy,
    ).promote(
        workspace,
        lock_path=tmp_path / "production" / ".generation.lock",
        project_file=project_file,
    )

    assert result.status == "rolled_back"
    _assert_production_restored(
        before, levels, solutions, manifest_path, project_file
    )
    assert not tuple((tmp_path / "production").rglob("*.promoting"))


def test_project_resource_failure_restores_project_and_promoted_artifacts(
    tmp_path,
) -> None:
    workspace, levels, solutions, manifest_path, project_file = _workspace(tmp_path)
    before = _production_snapshot(levels, solutions, manifest_path, project_file)

    def fail_project_update():
        project_file.write_text("partially regenerated project\n", encoding="utf-8")
        raise RuntimeError("simulated project resource failure")

    result = TransactionalPromotionService(
        resource_updater=fail_project_update,
    ).promote(
        workspace,
        lock_path=tmp_path / "production" / ".generation.lock",
        project_file=project_file,
    )

    assert result.status == "rolled_back"
    assert "project resource failure" in result.failure_reason
    _assert_production_restored(
        before, levels, solutions, manifest_path, project_file
    )


def test_concurrent_generation_lock_fails_without_touching_production(tmp_path) -> None:
    workspace, levels, solutions, manifest_path, project_file = _workspace(tmp_path)
    before = _production_snapshot(levels, solutions, manifest_path, project_file)
    lock_path = tmp_path / "production" / ".generation.lock"
    held_lock = ProductionGenerationLockService().acquire(lock_path, "other-run")
    try:
        result = TransactionalPromotionService(resource_updater=lambda: True).promote(
            workspace,
            lock_path=lock_path,
            project_file=project_file,
        )
    finally:
        held_lock.release()

    assert result.status == "failed_no_changes"
    assert "already locked" in result.failure_reason
    _assert_production_restored(
        before, levels, solutions, manifest_path, project_file
    )
