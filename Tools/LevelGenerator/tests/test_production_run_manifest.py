from __future__ import annotations

import json

import pytest

from app.models.production_run_manifest import (
    ProductionArtifact,
    ProductionCandidateRecord,
    ProductionRunManifest,
    ProductionTargetSnapshot,
)


_DIGEST = "a" * 64


def _manifest() -> ProductionRunManifest:
    return ProductionRunManifest(
        run_id="run-001",
        status="staged",
        generator_architecture="production_v3",
        generator_architecture_version=3,
        seed=42,
        config_snapshot_sha256=_DIGEST,
        requested_level_ids=("level_031",),
        selected_candidates=(
            ProductionCandidateRecord(
                level_id="level_031",
                difficulty="hard",
                seed=4201,
                candidate_id="level_031:4201",
                topology_hash="topology",
                layout_hash="layout",
                solution_hash="solution",
                structural_behavior_signature="behavior",
            ),
        ),
        artifacts=(
            ProductionArtifact(
                kind="level",
                staged_path="levels/level_031.json",
                production_path="/production/levels/level_031.json",
                level_id="level_031",
                sha256=_DIGEST,
                byte_count=10,
            ),
            ProductionArtifact(
                kind="solution",
                staged_path="solutions/level_031.solution.json",
                production_path="/production/solutions/level_031.solution.json",
                level_id="level_031",
                sha256="b" * 64,
                byte_count=8,
            ),
        ),
        target_snapshots=(
            ProductionTargetSnapshot(
                path="/production/levels/level_031.json",
                existed=False,
            ),
        ),
    )


def test_production_run_manifest_round_trips_deterministically(tmp_path) -> None:
    manifest = _manifest()

    first = manifest.write(tmp_path / "first.json")
    second = manifest.write(tmp_path / "second.json")

    assert first.read_bytes() == second.read_bytes()
    assert ProductionRunManifest.read(first) == manifest
    payload = json.loads(first.read_text(encoding="utf-8"))
    assert payload["requestedLevelIDs"] == ["level_031"]
    assert payload["selectedCandidates"][0]["candidateID"] == "level_031:4201"


def test_production_run_manifest_requires_exact_selected_artifacts() -> None:
    manifest = _manifest()

    with pytest.raises(ValueError, match="exactly match requested"):
        ProductionRunManifest(
            **{
                **manifest.__dict__,
                "requested_level_ids": ("level_032",),
            }
        )

    with pytest.raises(ValueError, match="level and solution"):
        ProductionRunManifest(
            **{
                **manifest.__dict__,
                "artifacts": manifest.artifacts[:1],
            }
        )


def test_production_artifact_rejects_staging_escape() -> None:
    with pytest.raises(ValueError, match="inside the staging workspace"):
        ProductionArtifact(
            kind="level",
            staged_path="../production/level_031.json",
            sha256=_DIGEST,
            byte_count=1,
        )
