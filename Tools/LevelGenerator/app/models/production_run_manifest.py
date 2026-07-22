"""Deterministic integrity manifest for one transactional production run."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_RUN_STATUSES = {
    "staged",
    "validated",
    "completed",
    "failed_no_changes",
    "rolled_back",
}


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


def _sha256(value: str, field_name: str) -> str:
    normalized = _required_text(value, field_name).lower()
    if not _SHA256_PATTERN.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return normalized


def _relative_path(value: str, field_name: str) -> str:
    normalized = _required_text(value, field_name).replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or path == PurePosixPath("."):
        raise ValueError(f"{field_name} must stay inside the staging workspace")
    return path.as_posix()


@dataclass(frozen=True)
class ProductionArtifact:
    """One immutable staged file and its intended production destination."""

    kind: str
    staged_path: str
    sha256: str
    byte_count: int
    production_path: str | None = None
    level_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _required_text(self.kind, "kind"))
        object.__setattr__(
            self,
            "staged_path",
            _relative_path(self.staged_path, "staged_path"),
        )
        object.__setattr__(self, "sha256", _sha256(self.sha256, "sha256"))
        if (
            not isinstance(self.byte_count, int)
            or isinstance(self.byte_count, bool)
            or self.byte_count < 0
        ):
            raise ValueError("byte_count must be a non-negative integer")
        if self.production_path is not None:
            object.__setattr__(
                self,
                "production_path",
                _required_text(self.production_path, "production_path"),
            )
        if self.level_id is not None:
            object.__setattr__(
                self,
                "level_id",
                _required_text(self.level_id, "level_id"),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "stagedPath": self.staged_path,
            "productionPath": self.production_path,
            "levelID": self.level_id,
            "sha256": self.sha256,
            "byteCount": self.byte_count,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProductionArtifact:
        return cls(
            kind=payload["kind"],
            staged_path=payload["stagedPath"],
            production_path=payload.get("productionPath"),
            level_id=payload.get("levelID"),
            sha256=payload["sha256"],
            byte_count=payload["byteCount"],
        )


@dataclass(frozen=True)
class ProductionTargetSnapshot:
    """Preflight content state used to detect production changes before promotion."""

    path: str
    existed: bool
    sha256: str | None = None
    byte_count: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _required_text(self.path, "path"))
        if not isinstance(self.existed, bool):
            raise ValueError("existed must be a Boolean")
        if self.existed:
            if self.sha256 is None or self.byte_count is None:
                raise ValueError("existing targets require sha256 and byte_count")
            object.__setattr__(self, "sha256", _sha256(self.sha256, "sha256"))
            if (
                not isinstance(self.byte_count, int)
                or isinstance(self.byte_count, bool)
                or self.byte_count < 0
            ):
                raise ValueError("byte_count must be a non-negative integer")
        elif self.sha256 is not None or self.byte_count is not None:
            raise ValueError("missing targets cannot carry content metadata")

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "existed": self.existed,
            "sha256": self.sha256,
            "byteCount": self.byte_count,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProductionTargetSnapshot:
        return cls(
            path=payload["path"],
            existed=payload["existed"],
            sha256=payload.get("sha256"),
            byte_count=payload.get("byteCount"),
        )


@dataclass(frozen=True)
class ProductionCandidateRecord:
    """Reproducible identity and proof hashes for one selected candidate."""

    level_id: str
    difficulty: str
    seed: int
    candidate_id: str
    topology_hash: str
    layout_hash: str
    solution_hash: str
    structural_behavior_signature: str

    def __post_init__(self) -> None:
        for field_name in ("level_id", "difficulty", "candidate_id"):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(self, "difficulty", self.difficulty.lower())
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise ValueError("seed must be an integer")
        for field_name in (
            "topology_hash",
            "layout_hash",
            "solution_hash",
            "structural_behavior_signature",
        ):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "levelID": self.level_id,
            "difficulty": self.difficulty,
            "seed": self.seed,
            "candidateID": self.candidate_id,
            "topologyHash": self.topology_hash,
            "layoutHash": self.layout_hash,
            "solutionHash": self.solution_hash,
            "structuralBehaviorSignature": self.structural_behavior_signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProductionCandidateRecord:
        return cls(
            level_id=payload["levelID"],
            difficulty=payload["difficulty"],
            seed=payload["seed"],
            candidate_id=payload["candidateID"],
            topology_hash=payload["topologyHash"],
            layout_hash=payload["layoutHash"],
            solution_hash=payload["solutionHash"],
            structural_behavior_signature=payload["structuralBehaviorSignature"],
        )


@dataclass(frozen=True)
class ProductionRunManifest:
    """Complete deterministic record of the files selected for promotion."""

    run_id: str
    status: str
    generator_architecture: str
    generator_architecture_version: int
    seed: int
    config_snapshot_sha256: str
    requested_level_ids: tuple[str, ...]
    selected_candidates: tuple[ProductionCandidateRecord, ...]
    artifacts: tuple[ProductionArtifact, ...]
    target_snapshots: tuple[ProductionTargetSnapshot, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_text(self.run_id, "run_id"))
        status = _required_text(self.status, "status")
        if status not in _RUN_STATUSES:
            raise ValueError(f"unsupported production run status: {status}")
        object.__setattr__(self, "status", status)
        architecture = _required_text(
            self.generator_architecture,
            "generator_architecture",
        )
        if architecture != "production_v3":
            raise ValueError("production run manifests require production_v3")
        object.__setattr__(self, "generator_architecture", architecture)
        if self.generator_architecture_version != 3:
            raise ValueError("production_v3 run manifests require architecture version 3")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise ValueError("seed must be an integer")
        object.__setattr__(
            self,
            "config_snapshot_sha256",
            _sha256(self.config_snapshot_sha256, "config_snapshot_sha256"),
        )
        if self.schema_version != 1:
            raise ValueError("unsupported production run manifest schema version")

        requested = tuple(
            _required_text(value, "requested_level_ids")
            for value in self.requested_level_ids
        )
        candidates = tuple(self.selected_candidates)
        artifacts = tuple(self.artifacts)
        snapshots = tuple(self.target_snapshots)
        if not requested:
            raise ValueError("production run manifest requires requested levels")
        if len(requested) != len(set(requested)):
            raise ValueError("requested level IDs must be unique")
        if any(not isinstance(item, ProductionCandidateRecord) for item in candidates):
            raise TypeError("selected_candidates must contain ProductionCandidateRecord values")
        if tuple(item.level_id for item in candidates) != requested:
            raise ValueError("selected candidates must exactly match requested level order")
        if any(not isinstance(item, ProductionArtifact) for item in artifacts):
            raise TypeError("artifacts must contain ProductionArtifact values")
        if any(not isinstance(item, ProductionTargetSnapshot) for item in snapshots):
            raise TypeError("target_snapshots must contain ProductionTargetSnapshot values")
        staged_paths = tuple(item.staged_path for item in artifacts)
        target_paths = tuple(item.path for item in snapshots)
        if len(staged_paths) != len(set(staged_paths)):
            raise ValueError("staged artifact paths must be unique")
        if len(target_paths) != len(set(target_paths)):
            raise ValueError("production target snapshots must be unique")
        for level_id in requested:
            artifact_kinds = {
                item.kind for item in artifacts if item.level_id == level_id
            }
            if not {"level", "solution"}.issubset(artifact_kinds):
                raise ValueError(
                    f"selected level {level_id} requires staged level and solution artifacts"
                )
        object.__setattr__(self, "requested_level_ids", requested)
        object.__setattr__(self, "selected_candidates", candidates)
        object.__setattr__(self, "artifacts", artifacts)
        object.__setattr__(self, "target_snapshots", snapshots)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "runID": self.run_id,
            "status": self.status,
            "generatorArchitecture": self.generator_architecture,
            "generatorArchitectureVersion": self.generator_architecture_version,
            "seed": self.seed,
            "configSnapshotSHA256": self.config_snapshot_sha256,
            "requestedLevelIDs": list(self.requested_level_ids),
            "selectedCandidates": [item.to_dict() for item in self.selected_candidates],
            "artifacts": [item.to_dict() for item in self.artifacts],
            "targetSnapshots": [item.to_dict() for item in self.target_snapshots],
        }

    def write(self, path: Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return output_path

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> ProductionRunManifest:
        return cls(
            schema_version=payload["schemaVersion"],
            run_id=payload["runID"],
            status=payload["status"],
            generator_architecture=payload["generatorArchitecture"],
            generator_architecture_version=payload["generatorArchitectureVersion"],
            seed=payload["seed"],
            config_snapshot_sha256=payload["configSnapshotSHA256"],
            requested_level_ids=tuple(payload["requestedLevelIDs"]),
            selected_candidates=tuple(
                ProductionCandidateRecord.from_dict(item)
                for item in payload["selectedCandidates"]
            ),
            artifacts=tuple(
                ProductionArtifact.from_dict(item) for item in payload["artifacts"]
            ),
            target_snapshots=tuple(
                ProductionTargetSnapshot.from_dict(item)
                for item in payload["targetSnapshots"]
            ),
        )

    @classmethod
    def read(cls, path: Path) -> ProductionRunManifest:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("production run manifest must be a JSON object")
        return cls.from_dict(payload)
