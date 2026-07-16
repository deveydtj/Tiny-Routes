#!/usr/bin/env python3
"""Verify every shipped level against the Phase 16 production gates."""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

_SHARED_CORE_ROOT = Path(__file__).resolve().parents[1] / "TinyRoutesCore"
if str(_SHARED_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SHARED_CORE_ROOT))

from app.level_editor_imports import (
    LevelDocument,
    LevelFileRepository,
    LevelValidationService,
    SolutionFileRepository,
    SolutionModel,
    SolutionValidationService,
    ValidationSeverity,
)
from app.models.generated_level import GeneratedLevel
from app.paths import (
    find_repo_root,
    get_default_levels_directory,
    get_default_reports_directory,
    get_default_solutions_directory,
)
from app.services.production_manifest_service import ProductionManifestService
from app.services.python_solution_simulator_service import PythonSolutionSimulatorService
from app.services.swift_test_service import SwiftTestService
from app.services.visual_clarity_validation_service import VisualClarityValidationService
from migrate_levels_to_live_routing import analyze_level


_DEBUG_RESOURCE_DIRECTORY_NAMES = {
    "candidate_debug",
    "candidate_failures",
    "debug",
    "debug_candidates",
    "failed_candidates",
}


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def _error_codes(validation_result) -> list[str]:
    return sorted(
        message.code
        for message in validation_result.messages
        if message.severity is ValidationSeverity.ERROR
    )


def _representative_ids(level_ids: list[str]) -> list[str]:
    if not level_ids:
        return []
    return sorted({level_ids[0], level_ids[len(level_ids) // 2], level_ids[-1]})


def _duplicate_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def _debug_candidate_directories(resources_dir: Path) -> list[str]:
    if not resources_dir.exists():
        return []
    matches = []
    for path in resources_dir.rglob("*"):
        if not path.is_dir():
            continue
        normalized = path.name.strip().lower().replace("-", "_").replace(" ", "_")
        if (
            normalized in _DEBUG_RESOURCE_DIRECTORY_NAMES
            or normalized.startswith("debug_candidate")
            or normalized.startswith("failed_candidate")
        ):
            matches.append(str(path.relative_to(resources_dir)))
    return sorted(matches)


def _disk_round_trip(
    level_id: str,
    level: LevelDocument,
    solution: SolutionModel,
) -> bool:
    with tempfile.TemporaryDirectory(prefix="tiny-routes-editor-roundtrip-") as root:
        root_path = Path(root)
        level_path = root_path / f"{level_id}.json"
        solution_path = root_path / f"{level_id}.solution.json"
        level_repository = LevelFileRepository()
        solution_repository = SolutionFileRepository()
        level_repository.save_level(level_path, level)
        solution_repository.save_solution(solution_path, solution)
        reopened_level = level_repository.load_level(level_path)
        reopened_solution = solution_repository.load_solution(solution_path)
        return (
            reopened_level.to_dict() == level.to_dict()
            and reopened_solution.to_dict() == solution.to_dict()
        )


def verify(
    levels_dir: Path,
    solutions_dir: Path,
    manifest_path: Path,
    *,
    run_swift_tests: bool,
    swift_timeout_seconds: int = 600,
    app_resources_dir: Path | None = None,
) -> dict[str, Any]:
    levels_dir = Path(levels_dir)
    solutions_dir = Path(solutions_dir)
    manifest_path = Path(manifest_path)
    app_resources_dir = Path(app_resources_dir) if app_resources_dir is not None else levels_dir.parent
    level_paths = sorted(
        path for path in levels_dir.glob("level_*.json")
        if not path.name.endswith(".solution.json")
    )
    level_ids = [path.stem for path in level_paths]
    solution_ids = sorted(
        path.name.removesuffix(".solution.json")
        for path in solutions_dir.glob("level_*.solution.json")
    )
    missing_solution_ids = sorted(set(level_ids) - set(solution_ids))
    # The Swift test bundle intentionally retains sidecars for later campaign
    # levels that are not yet shipped in TinyRoutes/Resources/Levels.
    unshipped_solution_ids = sorted(set(solution_ids) - set(level_ids))
    corpus_set_synchronized = not missing_solution_ids
    representative_ids = _representative_ids(level_ids)

    level_validation = LevelValidationService()
    solution_validation = SolutionValidationService()
    simulator = PythonSolutionSimulatorService()
    visual_validation = VisualClarityValidationService()
    records: list[dict[str, Any]] = []

    for level_path in level_paths:
        level_id = level_path.stem
        solution_path = solutions_dir / f"{level_id}.solution.json"
        record: dict[str, Any] = {"levelID": level_id, "issues": []}
        try:
            raw_level = _read_object(level_path)
            raw_solution = _read_object(solution_path)
            level = LevelDocument.from_dict(raw_level)
            solution = SolutionModel.from_dict(raw_solution)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            record.update({
                "passed": False,
                "issues": [f"load_failed:{error}"],
            })
            records.append(record)
            continue

        sidecar_level_id_matches = raw_solution.get("levelID") == level_id
        duplicate_node_ids = _duplicate_values(
            [str(node.get("id", "")) for node in raw_level.get("graph", {}).get("nodes", [])]
        )
        duplicate_edge_ids = _duplicate_values(
            [str(edge.get("id", "")) for edge in raw_level.get("graph", {}).get("edges", [])]
        )

        structural_errors = _error_codes(level_validation.validate(level, level_path))
        structural_errors.extend(
            _error_codes(solution_validation.validate(level, solution, solution_path))
        )
        structural_errors = sorted(set(structural_errors))
        explicit_live_rules = (
            raw_level.get("schemaVersion") == 2
            and isinstance(raw_level.get("rules"), dict)
            and raw_level["rules"].get("switchInteractionMode") == "liveLookahead"
        )
        generated = GeneratedLevel(level, solution, "production", "campaign", 0)
        replay = simulator.simulate(generated)
        zero_time_solution = copy.deepcopy(solution)
        for action in zero_time_solution.actions:
            action.timeSeconds = 0.0
        zero_time_replay = simulator.simulate(
            GeneratedLevel(level, zero_time_solution, "production", "campaign", 0)
        )
        zero_time_gate = not solution.actions or not zero_time_replay.passed
        try:
            migration_analysis = analyze_level(raw_level, raw_solution)
        except (KeyError, TypeError, ValueError) as error:
            migration_analysis = {
                "decisionQuality": {
                    "passed": False,
                    "issues": [f"analysis_failed:{error}"],
                }
            }
        decision_fit = bool(migration_analysis["decisionQuality"]["passed"])
        visual_report = visual_validation.report_for_level(level, solution)
        model_round_trip = (
            level.to_dict() == raw_level
            and solution.to_dict() == raw_solution
        )
        disk_round_trip = (
            _disk_round_trip(level_id, level, solution)
            if level_id in representative_ids
            else None
        )

        issues = []
        issues.extend(f"structural:{code}" for code in structural_errors)
        if not sidecar_level_id_matches:
            issues.append("sidecar:level_id_mismatch")
        issues.extend(f"graph:duplicate_node_id:{node_id}" for node_id in duplicate_node_ids)
        issues.extend(f"graph:duplicate_edge_id:{edge_id}" for edge_id in duplicate_edge_ids)
        if not explicit_live_rules:
            issues.append("rules:not_explicit_schema_v2_live_lookahead")
        if not replay.passed:
            issues.append(f"python_replay:{replay.failure_reason or replay.outcome}")
        if not zero_time_gate:
            issues.append("zero_time:complete_solution_was_accepted")
        if not decision_fit:
            issues.extend(
                f"decision_fit:{issue}"
                for issue in migration_analysis["decisionQuality"]["issues"]
            )
        issues.extend(f"visual:{issue.code}" for issue in visual_report.errors)
        if not model_round_trip:
            issues.append("editor_round_trip:model_changed_payload")
        if disk_round_trip is False:
            issues.append("editor_round_trip:save_reopen_changed_payload")

        record.update({
            "passed": not issues,
            "issues": issues,
            "structuralValidationPassed": not structural_errors,
            "sidecarLevelIDMatches": sidecar_level_id_matches,
            "duplicateNodeIDs": duplicate_node_ids,
            "duplicateEdgeIDs": duplicate_edge_ids,
            "graphIDsUnique": not duplicate_node_ids and not duplicate_edge_ids,
            "explicitSchemaV2LiveRules": explicit_live_rules,
            "pythonReplayPassed": replay.passed,
            "zeroTimeSolutionRejected": zero_time_gate,
            "decisionProfilePassed": decision_fit,
            "decisionProfileIssues": migration_analysis["decisionQuality"]["issues"],
            "visualReadabilityPassed": not visual_report.errors,
            "visualReadabilityScore": visual_report.score,
            "visualWarnings": sorted(issue.code for issue in visual_report.warnings),
            "modelRoundTripPassed": model_round_trip,
            "representativeDiskRoundTripPassed": disk_round_trip,
        })
        records.append(record)

    with tempfile.TemporaryDirectory(prefix="tiny-routes-manifest-check-") as root:
        rebuilt_manifest_path = Path(root) / "production_manifest.json"
        ProductionManifestService().rebuild(
            levels_dir,
            solutions_dir,
            rebuilt_manifest_path,
        )
        rebuilt_manifest = _read_object(rebuilt_manifest_path)
    try:
        committed_manifest = _read_object(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError):
        committed_manifest = None
    manifest_synchronized = committed_manifest == rebuilt_manifest
    manifest_level_ids = [
        str(item.get("levelID", ""))
        for item in (committed_manifest or {}).get("levels", [])
        if isinstance(item, dict)
    ]
    duplicate_manifest_level_ids = _duplicate_values(manifest_level_ids)
    missing_manifest_level_ids = sorted(set(level_ids) - set(manifest_level_ids))
    extra_manifest_level_ids = sorted(set(manifest_level_ids) - set(level_ids))
    manifest_exactly_once = (
        not duplicate_manifest_level_ids
        and not missing_manifest_level_ids
        and not extra_manifest_level_ids
        and len(manifest_level_ids) == len(level_ids)
    )
    debug_candidate_directories = _debug_candidate_directories(app_resources_dir)

    swift_payload: dict[str, Any]
    if run_swift_tests:
        swift_result = SwiftTestService(
            find_repo_root(),
            timeout_seconds=swift_timeout_seconds,
            level_ids=tuple(level_ids),
            levels_output_dir=levels_dir,
            solutions_output_dir=solutions_dir,
        ).run()
        swift_payload = {
            "requested": True,
            "passed": swift_result.passed is True,
            "summary": swift_result.summary,
            "command": swift_result.command,
            "failureReasons": swift_result.failure_reasons,
            "failureDetails": swift_result.failure_details,
        }
    else:
        swift_payload = {
            "requested": False,
            "passed": None,
            "summary": "Swift replay was not requested.",
            "command": [],
            "failureReasons": [],
            "failureDetails": [],
        }

    non_swift_passed = (
        bool(records)
        and corpus_set_synchronized
        and manifest_synchronized
        and manifest_exactly_once
        and not debug_candidate_directories
        and all(record["passed"] for record in records)
    )
    overall_passed = non_swift_passed and (
        swift_payload["passed"] is True if run_swift_tests else True
    )
    return {
        "schemaVersion": 1,
        "passed": overall_passed,
        "levelCount": len(records),
        "corpusSetSynchronized": corpus_set_synchronized,
        "missingSolutionIDs": missing_solution_ids,
        "unshippedSolutionIDs": unshipped_solution_ids,
        "manifestSynchronized": manifest_synchronized,
        "manifestExactlyOnce": manifest_exactly_once,
        "duplicateManifestLevelIDs": duplicate_manifest_level_ids,
        "missingManifestLevelIDs": missing_manifest_level_ids,
        "extraManifestLevelIDs": extra_manifest_level_ids,
        "debugCandidateDirectories": debug_candidate_directories,
        "appResourcesClean": not debug_candidate_directories,
        "everyLevelHasSidecar": not missing_solution_ids,
        "everySidecarLevelIDMatches": all(
            record.get("sidecarLevelIDMatches", False) for record in records
        ),
        "allGraphIDsUnique": all(record.get("graphIDsUnique", False) for record in records),
        "allProductionRulesLiveLookahead": all(
            record.get("explicitSchemaV2LiveRules", False) for record in records
        ),
        "allPythonSolutionsComplete": all(
            record.get("pythonReplayPassed", False) for record in records
        ),
        "allSwiftSolutionsComplete": swift_payload["passed"] if run_swift_tests else None,
        "representativeEditorRoundTripLevelIDs": representative_ids,
        "nonSwiftGatesPassed": non_swift_passed,
        "swiftReplay": swift_payload,
        "levels": records,
    }


def render_markdown(report: dict[str, Any]) -> str:
    swift = report["swiftReplay"]
    lines = [
        "# Production Corpus Verification",
        "",
        "Generated by `Tools/LevelGenerator/verify_production_corpus.py`.",
        "",
        f"- Overall: **{'PASS' if report['passed'] else 'FAIL'}**",
        f"- Levels: {report['levelCount']}",
        f"- Level/sidecar sets synchronized: {'yes' if report['corpusSetSynchronized'] else 'no'}",
        f"- Manifest synchronized: {'yes' if report['manifestSynchronized'] else 'no'}",
        f"- Manifest contains every level exactly once: {'yes' if report['manifestExactlyOnce'] else 'no'}",
        f"- Sidecar IDs match level IDs: {'yes' if report['everySidecarLevelIDMatches'] else 'no'}",
        f"- Node and edge IDs are unique: {'yes' if report['allGraphIDsUnique'] else 'no'}",
        f"- Production rules are live-lookahead: {'yes' if report['allProductionRulesLiveLookahead'] else 'no'}",
        f"- App resources contain no debug candidate directories: {'yes' if report['appResourcesClean'] else 'no'}",
        f"- Non-Swift gates: {'pass' if report['nonSwiftGatesPassed'] else 'fail'}",
        f"- Swift replay: {('pass' if swift['passed'] else 'fail') if swift['requested'] else 'not requested'}",
        "",
        "| Level | Structure | Sidecar ID | Unique IDs | v2 live | Python | Zero-time | Decision fit | Visual | Model RT | Disk RT | Result |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in report["levels"]:
        mark = lambda value: "pass" if value else "fail"
        disk = item.get("representativeDiskRoundTripPassed")
        lines.append(
            f"| {item['levelID']} | {mark(item.get('structuralValidationPassed'))} | "
            f"{mark(item.get('sidecarLevelIDMatches'))} | {mark(item.get('graphIDsUnique'))} | "
            f"{mark(item.get('explicitSchemaV2LiveRules'))} | {mark(item.get('pythonReplayPassed'))} | "
            f"{mark(item.get('zeroTimeSolutionRejected'))} | {mark(item.get('decisionProfilePassed'))} | "
            f"{mark(item.get('visualReadabilityPassed'))} | {mark(item.get('modelRoundTripPassed'))} | "
            f"{mark(disk) if disk is not None else 'n/a'} | {mark(item['passed'])} |"
        )
    if swift["requested"]:
        lines.extend(["", "## Swift replay", "", swift["summary"]])
        lines.extend(f"- {detail}" for detail in swift["failureDetails"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    root = find_repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--levels-dir", type=Path, default=get_default_levels_directory())
    parser.add_argument("--solutions-dir", type=Path, default=get_default_solutions_directory())
    parser.add_argument(
        "--manifest",
        type=Path,
        default=get_default_reports_directory() / "production_manifest.json",
    )
    parser.add_argument("--swift-tests", dest="swift_tests", action="store_true", default=True)
    parser.add_argument("--no-swift-tests", dest="swift_tests", action="store_false")
    parser.add_argument("--swift-timeout-seconds", type=int, default=600)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=root / "docs/quality/production_corpus_verification.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=root / "docs/quality/production_corpus_verification.md",
    )
    args = parser.parse_args(argv)
    report = verify(
        args.levels_dir,
        args.solutions_dir,
        args.manifest,
        run_swift_tests=args.swift_tests,
        swift_timeout_seconds=args.swift_timeout_seconds,
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(f"Verified {report['levelCount']} production levels: {'PASS' if report['passed'] else 'FAIL'}")
    if args.swift_tests:
        print(report["swiftReplay"]["summary"])
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
