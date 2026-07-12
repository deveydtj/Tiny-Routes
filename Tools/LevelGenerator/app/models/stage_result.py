from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StageResult(Mapping[str, Any]):
    """Typed result passed between generator stages.

    Mapping compatibility keeps older report and GUI consumers working while
    stage orchestration can rely on named, typed fields.
    """

    passed: bool
    stage: str
    code: str
    details: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    report_fields: dict[str, Any] = field(default_factory=dict)

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "stage": self.stage,
            "code": self.code,
            "details": self.details,
            "metrics": dict(self.metrics),
            **self.report_fields,
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_report_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_report_dict())

    def __len__(self) -> int:
        return len(self.to_report_dict())


@dataclass(frozen=True)
class CandidateStageResult(StageResult):
    candidate_id: str = ""
    level_id: str = ""
    seed: int = 0
    difficulty: str = ""
    status: str = ""

    def to_report_dict(self) -> dict[str, Any]:
        payload = super().to_report_dict()
        payload.update(
            {
                "candidateID": self.candidate_id,
                "levelID": self.level_id,
                "seed": self.seed,
                "difficulty": self.difficulty,
                "status": self.status,
            }
        )
        return payload
