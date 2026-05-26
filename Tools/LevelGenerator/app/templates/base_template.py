from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.difficulty_preset import DifficultyPreset
from ..models.generated_level import GeneratedLevel
from ..random_source import RandomSource
from ..services.graph_builder_service import GraphBuilderService
from ..services.layout_variant_service import LayoutVariantResult, LayoutVariantService
from ..services.level_naming_service import LevelNamingService
from ..services.solution_builder_service import SolutionBuilderService


class LevelTemplate(ABC):
    name: str
    requires_swift_validation: bool = False

    def __init__(self) -> None:
        self.solution_builder = SolutionBuilderService()
        self.naming = LevelNamingService()
        self.layout_variants = LayoutVariantService()

    @abstractmethod
    def supports_difficulty(self, preset: DifficultyPreset) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        level_id: str,
        level_number: int,
        preset: DifficultyPreset,
        rng: RandomSource,
    ) -> GeneratedLevel:
        raise NotImplementedError

    def builder(self) -> GraphBuilderService:
        return GraphBuilderService()

    def apply_layout_variant(
        self,
        positions: dict[str, tuple[float, float]],
        preset: DifficultyPreset,
        rng: RandomSource,
    ) -> LayoutVariantResult:
        return self.layout_variants.apply_random_variant(positions, rng, preset)

    def calculate_time_limit(self, route_positions: list[tuple[float, float]], preset: DifficultyPreset) -> int:
        if len(route_positions) < 2:
            return 30
        distance = 0.0
        for first, second in zip(route_positions, route_positions[1:]):
            distance += abs(first[0] - second[0]) + abs(first[1] - second[1])
        return max(30, int(round(distance + preset.time_limit_padding_seconds + 6)))

    def generated(
        self,
        level_document,
        solution,
        preset: DifficultyPreset,
        seed: int,
        notes: list[str] | None = None,
    ) -> GeneratedLevel:
        return GeneratedLevel(
            level_document=level_document,
            solution=solution,
            template_name=self.name,
            difficulty=preset.name,
            seed=seed,
            generation_notes=notes or [],
            requires_swift_validation=self.requires_swift_validation,
        )
