from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .candidate_signature import CandidateSignature
from .generation_quality import GenerationQualityScore
from .simulation import SimulationResult


@dataclass
class GeneratedLevel:
    level_document: Any
    solution: Any
    template_name: str
    difficulty: str
    seed: int
    rejection_messages: list[str] = field(default_factory=list)
    generation_notes: list[str] = field(default_factory=list)
    requires_swift_validation: bool = False
    candidate_signature: CandidateSignature | None = None
    simulation_result: SimulationResult | None = None
    quality_score: GenerationQualityScore | None = None
    preview_path: Path | None = None

    @property
    def level_id(self) -> str:
        return self.level_document.id

    @property
    def node_count(self) -> int:
        return len(self.level_document.graph.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.level_document.graph.edges)

    @property
    def switch_count(self) -> int:
        return sum(1 for node in self.level_document.graph.nodes if len(node.outgoingEdgeIDs) > 1)

    @property
    def required_tap_count(self) -> int:
        return len(self.solution.actions)
