from __future__ import annotations

import json

import pytest

from app.random_source import RandomSource
from app.repositories.generated_level_repository import GeneratedLevelRepository
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
from app.services.production_manifest_service import ProductionManifestService
from app.services.production_staged_output_service import ProductionStagedOutputService
from app.services.production_staging_service import ProductionStagingService
from app.templates.single_switch_template import SingleSwitchTemplate


def _candidate(level_id: str, level_number: int, seed: int):
    preset = DifficultyService().get_preset("easy")
    candidate = SingleSwitchTemplate().generate(
        level_id,
        level_number,
        preset,
        RandomSource(seed),
    )
    candidate.candidate_signature = CandidateSignatureService().signature_for(candidate)
    return candidate


def test_selected_candidates_overlay_complete_staged_corpus_only(tmp_path) -> None:
    levels = tmp_path / "production" / "levels"
    solutions = tmp_path / "production" / "solutions"
    reports = tmp_path / "production" / "reports"
    writer = GeneratedLevelRepository()
    existing = _candidate("level_001", 1, 1)
    selected = _candidate("level_002", 2, 2)
    writer.write_level(existing.level_document, levels / "level_001.json")
    writer.write_solution(existing.solution, solutions / "level_001.solution.json")
    writer.write_solution(
        _candidate("level_099", 99, 99).solution,
        solutions / "level_099.solution.json",
    )
    sentinel_level = (levels / "level_001.json").read_bytes()
    production_manifest = ProductionManifestService().rebuild(
        levels,
        solutions,
        reports / "production_manifest.json",
    )
    sentinel_manifest = production_manifest.read_bytes()
    workspace = ProductionStagingService(tmp_path / "staging").create_workspace(
        "run-002",
        seed=22,
        config_snapshot={"generatorArchitecture": "production_v3", "count": 1},
    )

    manifest = ProductionStagedOutputService().write_selected_candidates(
        workspace,
        [selected],
        production_levels_dir=levels,
        production_solutions_dir=solutions,
        production_manifest_path=production_manifest,
    )

    assert sorted(path.name for path in workspace.levels_dir.glob("*.json")) == [
        "level_001.json",
        "level_002.json",
    ]
    assert (workspace.solutions_dir / "level_002.solution.json").exists()
    assert (workspace.solutions_dir / "level_099.solution.json").exists()
    assert workspace.proposed_manifest_path.exists()
    assert workspace.run_manifest_path.exists()
    assert (workspace.previews_dir / "level_002.svg").exists()
    assert (levels / "level_002.json").exists() is False
    assert (solutions / "level_002.solution.json").exists() is False
    assert (levels / "level_001.json").read_bytes() == sentinel_level
    assert production_manifest.read_bytes() == sentinel_manifest
    assert manifest.requested_level_ids == ("level_002",)
    assert {artifact.kind for artifact in manifest.artifacts} == {
        "level",
        "solution",
        "preview",
        "proposed_manifest",
        "seed_config_snapshot",
    }
    assert manifest.config_snapshot_sha256
    assert manifest.target_snapshots
    proposed = json.loads(workspace.proposed_manifest_path.read_text(encoding="utf-8"))
    assert [item["levelID"] for item in proposed["levels"]] == [
        "level_001",
        "level_002",
    ]


def test_staged_output_rejects_unsigned_candidates_and_reuse(tmp_path) -> None:
    workspace = ProductionStagingService(tmp_path / "staging").create_workspace(
        "run-003",
        seed=3,
        config_snapshot={"mode": "production_v3"},
    )
    unsigned = _candidate("level_003", 3, 3)
    unsigned.candidate_signature = None
    service = ProductionStagedOutputService()

    with pytest.raises(ValueError, match="complete signature"):
        service.write_selected_candidates(
            workspace,
            [unsigned],
            production_levels_dir=tmp_path / "production" / "levels",
            production_solutions_dir=tmp_path / "production" / "solutions",
            production_manifest_path=tmp_path / "production" / "manifest.json",
        )

    signed = _candidate("level_003", 3, 3)
    service.write_selected_candidates(
        workspace,
        [signed],
        production_levels_dir=tmp_path / "production" / "levels",
        production_solutions_dir=tmp_path / "production" / "solutions",
        production_manifest_path=tmp_path / "production" / "manifest.json",
    )
    with pytest.raises(FileExistsError, match="already exists"):
        service.write_selected_candidates(
            workspace,
            [signed],
            production_levels_dir=tmp_path / "production" / "levels",
            production_solutions_dir=tmp_path / "production" / "solutions",
            production_manifest_path=tmp_path / "production" / "manifest.json",
        )


def test_report_and_validation_writes_cannot_escape_workspace(tmp_path) -> None:
    workspace = ProductionStagingService(tmp_path / "staging").create_workspace(
        "run-004",
        seed=4,
        config_snapshot={"mode": "production_v3"},
    )
    service = ProductionStagedOutputService()

    assert service.write_report(workspace, "report.json", "{}\n").parent == workspace.reports_dir
    validation_log = service.write_validation_log(
        workspace,
        "swift.log",
        b"passed\n",
    )
    assert validation_log.parent == workspace.validation_logs_dir
    with pytest.raises(ValueError, match="single path component"):
        service.write_report(workspace, "../production.json", "bad")


@pytest.mark.parametrize(
    "config_snapshot",
    [
        {},
        {"generatorArchitecture": "v2_legacy"},
        {"mode": "v2_legacy"},
    ],
)
def test_staged_output_rejects_missing_or_legacy_architecture(
    tmp_path, config_snapshot
) -> None:
    workspace = ProductionStagingService(tmp_path / "staging").create_workspace(
        "run-legacy",
        seed=5,
        config_snapshot=config_snapshot,
    )

    with pytest.raises(ValueError, match="requires production_v3"):
        ProductionStagedOutputService().write_selected_candidates(
            workspace,
            [_candidate("level_005", 5, 5)],
            production_levels_dir=tmp_path / "production" / "levels",
            production_solutions_dir=tmp_path / "production" / "solutions",
            production_manifest_path=tmp_path / "production" / "manifest.json",
        )
