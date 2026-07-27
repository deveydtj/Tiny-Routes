from __future__ import annotations

import json

from app.random_source import RandomSource
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
from app.services.production_staged_corpus_validation_service import (
    ProductionStagedCorpusValidationService,
)
from app.services.production_staged_output_service import ProductionStagedOutputService
from app.services.production_staging_service import ProductionStagingService
from app.templates.single_switch_template import SingleSwitchTemplate


def test_staged_loader_allows_solution_sidecars_for_unshipped_levels(tmp_path) -> None:
    workspace = ProductionStagingService(tmp_path / "staging").create_workspace(
        "future-sidecar-run",
        seed=8,
        config_snapshot={"generatorArchitecture": "production_v3"},
    )
    candidate = SingleSwitchTemplate().generate(
        "level_008",
        8,
        DifficultyService().get_preset("easy"),
        RandomSource(8),
    )
    candidate.candidate_signature = CandidateSignatureService().signature_for(candidate)
    production_solutions = tmp_path / "production" / "solutions"
    production_solutions.mkdir(parents=True)
    future_solution = candidate.solution.to_dict()
    future_solution["levelID"] = "level_099"
    (production_solutions / "level_099.solution.json").write_text(
        json.dumps(future_solution),
        encoding="utf-8",
    )
    ProductionStagedOutputService().write_selected_candidates(
        workspace,
        [candidate],
        production_levels_dir=tmp_path / "production" / "levels",
        production_solutions_dir=production_solutions,
        production_manifest_path=tmp_path / "production" / "manifest.json",
        production_project_file=tmp_path / "project.pbxproj",
    )

    issues = []
    staged = ProductionStagedCorpusValidationService()._load_complete_corpus(
        workspace,
        issues,
    )

    assert set(staged) == {"level_008"}
    assert not any(
        issue.code == "staged_level_solution_pair_missing" for issue in issues
    )


def test_staged_validation_rejects_bytes_changed_after_selection(tmp_path) -> None:
    project_file = tmp_path / "project.pbxproj"
    project_file.write_text("level_009.json level_009.solution.json\n", encoding="utf-8")
    workspace = ProductionStagingService(tmp_path / "staging").create_workspace(
        "validation-run",
        seed=9,
        config_snapshot={"generatorArchitecture": "production_v3"},
    )
    candidate = SingleSwitchTemplate().generate(
        "level_009",
        9,
        DifficultyService().get_preset("easy"),
        RandomSource(9),
    )
    candidate.candidate_signature = CandidateSignatureService().signature_for(candidate)
    ProductionStagedOutputService().write_selected_candidates(
        workspace,
        [candidate],
        production_levels_dir=tmp_path / "production" / "levels",
        production_solutions_dir=tmp_path / "production" / "solutions",
        production_manifest_path=tmp_path / "production" / "manifest.json",
        production_project_file=project_file,
    )
    (workspace.levels_dir / "level_009.json").write_text("{}\n", encoding="utf-8")

    result = ProductionStagedCorpusValidationService().validate(
        workspace,
        (),
        repo_root=tmp_path,
        project_file=project_file,
        run_swift_tests=False,
    )

    assert result.passed is False
    assert "staged_artifact_hash_mismatch" in {issue.code for issue in result.issues}
    assert "staged_json_schema_invalid" in {issue.code for issue in result.issues}
    assert "selected_quality_evidence_missing" in {issue.code for issue in result.issues}
    assert "swift_staged_parity_not_run" in {issue.code for issue in result.issues}
    assert result.report_path.exists()
    assert '"status": "staged"' in workspace.run_manifest_path.read_text(encoding="utf-8")


def test_staged_validation_checks_valid_json_before_quality_evidence(tmp_path) -> None:
    project_file = tmp_path / "project.pbxproj"
    project_file.write_text("level_010.json level_010.solution.json\n", encoding="utf-8")
    workspace = ProductionStagingService(tmp_path / "staging").create_workspace(
        "valid-json-run",
        seed=10,
        config_snapshot={"generatorArchitecture": "production_v3"},
    )
    candidate = SingleSwitchTemplate().generate(
        "level_010",
        10,
        DifficultyService().get_preset("easy"),
        RandomSource(10),
    )
    candidate.candidate_signature = CandidateSignatureService().signature_for(candidate)
    ProductionStagedOutputService().write_selected_candidates(
        workspace,
        [candidate],
        production_levels_dir=tmp_path / "production" / "levels",
        production_solutions_dir=tmp_path / "production" / "solutions",
        production_manifest_path=tmp_path / "production" / "manifest.json",
        production_project_file=project_file,
    )

    result = ProductionStagedCorpusValidationService().validate(
        workspace,
        (),
        repo_root=tmp_path,
        project_file=project_file,
        run_swift_tests=False,
    )

    codes = {issue.code for issue in result.issues}
    assert "selected_quality_evidence_missing" in codes
    assert "swift_staged_parity_not_run" in codes
    assert not any(code.startswith("staged_validation:") for code in codes)
    assert "staged_runtime_solution_replay_failed" not in codes
    assert "proposed_manifest_invalid" not in codes
