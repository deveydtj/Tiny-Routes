from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .abstract_puzzle_solution import AbstractPuzzleSolutionMetadata
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
    unique_solution_validation_result: Any | None = None
    layout_readability_validation_result: Any | None = None
    quality_score: GenerationQualityScore | None = None
    preview_path: Path | None = None
    warning_messages: list[str] = field(default_factory=list)
    recipe_family: str | None = None
    recipe_variant: str | None = None
    abstract_graph_signature: str | None = None
    selected_layout_variant: str | None = None
    selected_road_shape_strategy: str | None = None
    abstract_solution_metadata: AbstractPuzzleSolutionMetadata | None = None
    layout_metadata: dict[str, Any] | None = None
    road_shape_metadata: dict[str, Any] | None = None
    mechanic_tags: tuple[str, ...] = field(default_factory=tuple)
    primary_mechanic_tag: str = ""
    topology_class: str = ""
    unlock_requirement: str | None = None
    prior_mechanic_dependency: str | None = None
    mechanic_metadata: dict[str, Any] = field(default_factory=dict)

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
