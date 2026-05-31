from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.difficulty_preset import DifficultyPreset
from ..models.graph_recipe import GraphRecipe
from ..models.recipe_variant_spec import RecipeVariantSpec
from ..random_source import RandomSource


class RecipeFamily(ABC):
    name: str
    legacy_template_name: str | None = None
    requires_swift_validation: bool = False
    legacy_compatible: bool = True

    @property
    @abstractmethod
    def variants(self) -> tuple[RecipeVariantSpec, ...]:
        raise NotImplementedError

    def supports_difficulty(self, preset: DifficultyPreset) -> bool:
        return any(variant.supports_difficulty(preset.name) for variant in self.variants)

    def variants_for_difficulty(self, preset: DifficultyPreset) -> tuple[RecipeVariantSpec, ...]:
        return tuple(variant for variant in self.variants if variant.supports_difficulty(preset.name))

    @abstractmethod
    def generate_recipe(
        self,
        level_id: str,
        preset: DifficultyPreset,
        rng: RandomSource,
        variant: RecipeVariantSpec | None = None,
    ) -> GraphRecipe:
        raise NotImplementedError


class MechanicRecipeGenerator(ABC):
    @abstractmethod
    def valid_family_names(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def get_family(self, name: str) -> RecipeFamily:
        raise NotImplementedError

    @abstractmethod
    def supported_families(self, preset: DifficultyPreset) -> list[RecipeFamily]:
        raise NotImplementedError

    @abstractmethod
    def choose_family(
        self,
        name: str,
        preset: DifficultyPreset,
        rng: RandomSource,
        include_swift_required: bool = True,
        weights_override: dict[str, int] | None = None,
    ) -> RecipeFamily:
        raise NotImplementedError
