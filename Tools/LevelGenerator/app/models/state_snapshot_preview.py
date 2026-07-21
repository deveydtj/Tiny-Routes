"""Typed debug artifacts for objective-state layout previews."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StateSnapshotPreviewArtifact:
    kind: str
    path: Path
    state_index: int | None = None
    active_objective_id: str | None = None

    def to_report_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "path": str(self.path),
            "stateIndex": self.state_index,
            "activeObjectiveID": self.active_objective_id,
        }


@dataclass(frozen=True)
class StateSnapshotPreviewResult:
    candidate_id: str
    artifacts: tuple[StateSnapshotPreviewArtifact, ...]

    @property
    def paths(self) -> tuple[Path, ...]:
        return tuple(artifact.path for artifact in self.artifacts)

    def to_report_dict(self) -> dict[str, object]:
        return {
            "candidateID": self.candidate_id,
            "artifacts": [artifact.to_report_dict() for artifact in self.artifacts],
        }
