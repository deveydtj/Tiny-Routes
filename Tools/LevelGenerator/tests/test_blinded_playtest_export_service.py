from __future__ import annotations

import json

import pytest

from app.models.playtest_export import PlaytestSample
from app.services.blinded_playtest_export_service import (
    BlindedPlaytestExportService,
)


def _samples() -> tuple[PlaytestSample, ...]:
    difficulties = ("easy", "medium", "hard", "expert", "hard", "expert")
    archetypes = BlindedPlaytestExportService.required_archetypes
    return tuple(
        PlaytestSample(
            source_id=f"secret-source-{index}",
            level_payload={
                "schemaVersion": 3,
                "id": f"source-{index}",
                "name": f"Secret Level {index}",
                "difficulty": difficulty,
                "seed": 1000 + index,
                "metadata": {"qualityScore": 0.8, "safeGameplay": "retained"},
                "objectives": [{"id": "objective"}],
                "graph": {"nodes": [], "edges": []},
            },
            difficulty=difficulty,
            blueprint_archetype=archetypes[index],
            objective_count=2 + index,
            recovery_pattern="loop" if index % 2 else "detour",
            failure_pattern="fatal" if index % 2 else "recoverable",
            layout_profile="wide" if index % 2 else "tall",
            known_weak=index == 2,
            automated_metrics={"meaningfulDecisions": index + 2},
        )
        for index, difficulty in enumerate(difficulties)
    )


def test_export_separates_blinded_tester_material_from_researcher_key(tmp_path) -> None:
    samples = _samples()
    service = BlindedPlaytestExportService()

    result = service.export(
        samples,
        tmp_path / "export",
        seed=7521,
        expected_archetypes=BlindedPlaytestExportService.required_archetypes,
    )

    tester_bytes = b"\n".join(
        path.read_bytes()
        for path in sorted(result.tester_directory.rglob("*"))
        if path.is_file()
    )
    assert b"secret-source" not in tester_bytes
    assert b"Secret Level" not in tester_bytes
    assert b"knownWeak" not in tester_bytes
    assert b"qualityScore" not in tester_bytes
    assert b"safeGameplay" in tester_bytes
    level_bytes = b"\n".join(
        path.read_bytes()
        for path in sorted((result.tester_directory / "levels").glob("*.json"))
    )
    assert b"difficulty" not in level_bytes.lower()

    manifest = json.loads(
        (result.tester_directory / "manifest.json").read_text(encoding="utf-8")
    )
    assert [item["blindID"] for item in manifest["entries"]] == [
        "TRP-001",
        "TRP-002",
        "TRP-003",
        "TRP-004",
        "TRP-005",
        "TRP-006",
    ]
    assert all("solutionPath" not in item for item in manifest["entries"])
    assert not tuple(result.tester_directory.rglob("*solution*"))
    rubric = json.loads(
        (result.tester_directory / "rubric.json").read_text(encoding="utf-8")
    )
    assert {item["field"] for item in rubric["questions"]} == {
        "goalUnderstandable",
        "routePlanning",
        "routeChangedAfterObjective",
        "wrongRoutesFair",
        "recoveryExperience",
        "overallImpression",
        "perceivedDifficulty",
        "replayDesire",
        "notes",
    }
    answer_key = json.loads(
        (result.researcher_directory / "answer_key.json").read_text(encoding="utf-8")
    )
    assert {item["sourceID"] for item in answer_key["entries"]} == {
        sample.source_id for sample in samples
    }
    assert answer_key["coverage"]["knownWeakCount"] == 1


def test_export_is_deterministic_for_same_samples_and_seed(tmp_path) -> None:
    service = BlindedPlaytestExportService()
    first = service.export(
        _samples(),
        tmp_path / "first",
        seed=44,
        expected_archetypes=BlindedPlaytestExportService.required_archetypes,
    )
    second = service.export(
        reversed(_samples()),
        tmp_path / "second",
        seed=44,
        expected_archetypes=BlindedPlaytestExportService.required_archetypes,
    )

    assert first.fingerprint == second.fingerprint
    assert (first.tester_directory / "manifest.json").read_bytes() == (
        second.tester_directory / "manifest.json"
    ).read_bytes()


def test_export_rejects_incomplete_or_unvaried_corpus(tmp_path) -> None:
    with pytest.raises(ValueError, match="missing difficulties"):
        BlindedPlaytestExportService().export(
            _samples()[:2],
            tmp_path / "incomplete",
            seed=1,
            expected_archetypes=BlindedPlaytestExportService.required_archetypes,
        )
