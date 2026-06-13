from __future__ import annotations

from dataclasses import dataclass

from ..models.difficulty_preset import DifficultyPreset
from ..models.graph_recipe import GraphRecipe
from ..models.recipe_topology_rules import RecipeTopologyRules
from ..models.recipe_variant_spec import RecipeVariantSpec
from ..random_source import RandomSource
from .base_recipe import RecipeFamily


@dataclass(frozen=True)
class LegacyRecipeFamilySpec:
    name: str
    legacy_template_name: str
    difficulty_names: tuple[str, ...]
    requires_swift_validation: bool = False


class LegacyRecipeFamily(RecipeFamily):
    def __init__(self, spec: LegacyRecipeFamilySpec) -> None:
        self.name = spec.name
        self.legacy_template_name = spec.legacy_template_name
        self.requires_swift_validation = spec.requires_swift_validation
        self._variants = (
            RecipeVariantSpec(
                name="default",
                family_name=spec.name,
                difficulty_names=spec.difficulty_names,
                topology_rules=RecipeTopologyRules(
                    allows_cycles=False,
                    allows_rejoin=False,
                    allows_revisit=False,
                    allows_return_path=False,
                    allows_ring=False,
                    allowed_cycle_count=0,
                    requires_package_gate=False,
                    requires_unique_solution=True,
                    requires_swift_runtime_validation=spec.requires_swift_validation,
                ),
                legacy_template_name=spec.legacy_template_name,
                requires_swift_validation=spec.requires_swift_validation,
                notes=("legacy-compatible placeholder",),
            ),
        )

    @property
    def variants(self) -> tuple[RecipeVariantSpec, ...]:
        return self._variants

    def generate_recipe(
        self,
        level_id: str,
        preset: DifficultyPreset,
        rng: RandomSource,
        variant: RecipeVariantSpec | None = None,
    ) -> GraphRecipe:
        raise NotImplementedError(
            f"Recipe family '{self.name}' declares recipe-first architecture but has not "
            "implemented graph recipe production yet."
        )
