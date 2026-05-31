from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..models.difficulty_preset import DifficultyPreset
from ..models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from ..models.recipe_variant_spec import RecipeVariantSpec
from ..random_source import RandomSource
from ..templates.four_way_intersection_template import FourWayIntersectionTemplate
from ..templates.four_way_intersection_template import _variant_spec as four_way_variant_spec
from ..templates.multi_switch_chain_template import MultiSwitchChainTemplate
from ..templates.package_gate_template import PackageGateTemplate
from ..templates.package_gate_template import _variant_spec as package_gate_variant_spec
from ..templates.return_loop_template import ReturnLoopTemplate
from ..templates.return_loop_template import _variant_spec as return_loop_variant_spec
from ..templates.ring_route_template import RingRouteTemplate
from ..templates.single_switch_template import SingleSwitchTemplate
from ..templates.single_switch_template import _variant_spec as single_switch_variant_spec
from ..templates.straight_delivery_template import StraightDeliveryTemplate
from .base_recipe import RecipeFamily


RecipeSpecBuilder = Callable[
    [str, DifficultyPreset, RandomSource],
    tuple[tuple[str, ...], tuple[GraphRecipeEdge, ...], tuple[str, ...], tuple[str, ...]],
]


@dataclass(frozen=True)
class TemplateRecipeFamilyDefinition:
    name: str
    variants: tuple[RecipeVariantSpec, ...]
    build_spec: RecipeSpecBuilder
    requires_swift_validation: bool = False


class TemplateRecipeFamily(RecipeFamily):
    def __init__(self, definition: TemplateRecipeFamilyDefinition) -> None:
        self.name = definition.name
        self.legacy_template_name = definition.name
        self.requires_swift_validation = definition.requires_swift_validation
        self._variants = definition.variants
        self._build_spec = definition.build_spec

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
        supported_variants = self.variants_for_difficulty(preset)
        if not supported_variants:
            raise ValueError(f"Recipe family '{self.name}' does not support difficulty '{preset.name}'")
        selected_variant = variant or rng.choice(list(supported_variants))
        if not selected_variant.supports_difficulty(preset.name):
            raise ValueError(f"Recipe variant '{selected_variant.name}' does not support difficulty '{preset.name}'")

        node_ids, edges, tap_node_ids, required_path = self._build_spec(selected_variant.name, preset, rng)
        nodes = tuple(GraphRecipeNode(node_id, _role_for_node(node_id)) for node_id in node_ids)
        recipe = GraphRecipe(
            level_id=level_id,
            difficulty=preset.name,
            nodes=nodes,
            edges=edges,
            required_path=required_path,
            tap_node_ids=tap_node_ids,
            notes=(f"Recipe family: {self.name}", f"Recipe variant: {selected_variant.name}"),
            family_name=self.name,
            variant_name=selected_variant.name,
        )
        issues = recipe.validate()
        if issues:
            raise ValueError(f"Invalid graph recipe: {', '.join(issues)}")
        return recipe


def template_recipe_family_definitions() -> list[TemplateRecipeFamilyDefinition]:
    return [
        TemplateRecipeFamilyDefinition(
            name=StraightDeliveryTemplate.name,
            variants=tuple(
                RecipeVariantSpec(
                    name=f"straight_delivery_{count}_intermediate",
                    family_name=StraightDeliveryTemplate.name,
                    difficulty_names=("tutorial",),
                    legacy_template_name=StraightDeliveryTemplate.name,
                )
                for count in range(3)
            ),
            build_spec=_straight_delivery_spec,
        ),
        TemplateRecipeFamilyDefinition(
            name=SingleSwitchTemplate.name,
            variants=_variants_from_template(SingleSwitchTemplate),
            build_spec=_single_switch_spec,
        ),
        TemplateRecipeFamilyDefinition(
            name=PackageGateTemplate.name,
            variants=_variants_from_template(PackageGateTemplate),
            build_spec=_package_gate_spec,
        ),
        TemplateRecipeFamilyDefinition(
            name=ReturnLoopTemplate.name,
            variants=_variants_from_template(ReturnLoopTemplate),
            build_spec=_return_loop_spec,
        ),
        TemplateRecipeFamilyDefinition(
            name=MultiSwitchChainTemplate.name,
            variants=_variants_from_template(MultiSwitchChainTemplate),
            build_spec=_multi_switch_chain_spec,
        ),
        TemplateRecipeFamilyDefinition(
            name=RingRouteTemplate.name,
            variants=_variants_from_template(RingRouteTemplate),
            build_spec=_ring_route_spec,
            requires_swift_validation=True,
        ),
        TemplateRecipeFamilyDefinition(
            name=FourWayIntersectionTemplate.name,
            variants=_variants_from_template(FourWayIntersectionTemplate),
            build_spec=_four_way_intersection_spec,
        ),
    ]


def _variants_from_template(template_class) -> tuple[RecipeVariantSpec, ...]:
    return tuple(
        RecipeVariantSpec(
            name=spec.name,
            family_name=spec.template_name,
            difficulty_names=spec.difficulty_names,
            legacy_template_name=spec.template_name,
            requires_swift_validation=spec.requires_swift_validation,
            notes=spec.notes,
        )
        for spec in template_class.variant_specs
    )


def _straight_delivery_spec(
    variant_name: str,
    preset: DifficultyPreset,
    rng: RandomSource,
) -> tuple[tuple[str, ...], tuple[GraphRecipeEdge, ...], tuple[str, ...], tuple[str, ...]]:
    count_by_variant = {
        "straight_delivery_0_intermediate": 0,
        "straight_delivery_1_intermediate": 1,
        "straight_delivery_2_intermediate": 2,
    }
    intermediate_count = count_by_variant.get(variant_name, 0)
    route = ("start",) + tuple(f"node_{chr(ord('a') + index)}" for index in range(intermediate_count)) + (
        "package",
        "destination",
    )
    return route, _edges_from_pairs(zip(route, route[1:])), (), route


def _single_switch_spec(
    variant_name: str,
    preset: DifficultyPreset,
    rng: RandomSource,
) -> tuple[tuple[str, ...], tuple[GraphRecipeEdge, ...], tuple[str, ...], tuple[str, ...]]:
    include_approach = preset.name != "tutorial"
    positions, switch_id, dead_end_id, route = single_switch_variant_spec(variant_name, include_approach)
    if not include_approach:
        positions = {node_id: position for node_id, position in positions.items() if node_id != "approach"}
    pairs = []
    if include_approach:
        pairs.extend([("start", "approach"), ("approach", switch_id)])
    else:
        pairs.append(("start", switch_id))
    pairs.extend([(switch_id, dead_end_id), (switch_id, "package"), ("package", "destination")])
    return tuple(positions), _edges_from_pairs(pairs), (switch_id,), tuple(route)


def _package_gate_spec(
    variant_name: str,
    preset: DifficultyPreset,
    rng: RandomSource,
) -> tuple[tuple[str, ...], tuple[GraphRecipeEdge, ...], tuple[str, ...], tuple[str, ...]]:
    positions, pairs, tap_node_ids, route = package_gate_variant_spec(variant_name)
    return tuple(positions), _edges_from_pairs(pairs), tuple(tap_node_ids), tuple(route)


def _return_loop_spec(
    variant_name: str,
    preset: DifficultyPreset,
    rng: RandomSource,
) -> tuple[tuple[str, ...], tuple[GraphRecipeEdge, ...], tuple[str, ...], tuple[str, ...]]:
    positions, pairs, tap_node_ids, route = return_loop_variant_spec(variant_name)
    return tuple(positions), _edges_from_pairs(pairs), tuple(tap_node_ids), tuple(route)


def _multi_switch_chain_spec(
    variant_name: str,
    preset: DifficultyPreset,
    rng: RandomSource,
) -> tuple[tuple[str, ...], tuple[GraphRecipeEdge, ...], tuple[str, ...], tuple[str, ...]]:
    if variant_name in {"multi_switch_chain_four_switch", "multi_switch_chain_double_gate"}:
        required_switch_count = 4
    else:
        required_switch_count = rng.randint(2, 3) if preset.name == "medium" else rng.randint(3, 4)
    switch_ids = tuple(f"{variant_name}_switch_{chr(ord('a') + index)}" for index in range(required_switch_count))
    route = ("start", switch_ids[0], "package", *switch_ids[1:], "destination")
    dead_end_ids = tuple(f"{variant_name}_dead_end_{chr(ord('a') + index)}" for index in range(required_switch_count))
    pairs: list[tuple[str, str]] = [("start", switch_ids[0])]
    for index, switch_id in enumerate(switch_ids):
        pairs.append((switch_id, dead_end_ids[index]))
        if index == 0:
            pairs.append((switch_id, "package"))
        else:
            next_node = switch_ids[index + 1] if index + 1 < len(switch_ids) else "destination"
            pairs.append((switch_id, next_node))
        if index == 0 and len(switch_ids) > 1:
            pairs.append(("package", switch_ids[1]))
    node_ids = tuple(dict.fromkeys((*route, *dead_end_ids)))
    return node_ids, _edges_from_pairs(pairs), switch_ids, route


def _ring_route_spec(
    variant_name: str,
    preset: DifficultyPreset,
    rng: RandomSource,
) -> tuple[tuple[str, ...], tuple[GraphRecipeEdge, ...], tuple[str, ...], tuple[str, ...]]:
    node_ids = ("start", "hub", "ring_a", "ring_b", "package", "gate", "destination", "dead_end_a", "dead_end_b")
    pairs = (
        ("start", "hub"),
        ("hub", "ring_a"),
        ("hub", "package"),
        ("ring_a", "ring_b"),
        ("ring_b", "ring_a"),
        ("ring_b", "gate"),
        ("ring_b", "dead_end_a"),
        ("package", "ring_b"),
        ("gate", "dead_end_b"),
        ("gate", "destination"),
        ("gate", "ring_a"),
    )
    route = ("start", "hub", "package", "ring_b", "gate", "destination")
    return node_ids, _edges_from_pairs(pairs), ("hub", "ring_b", "gate"), route


def _four_way_intersection_spec(
    variant_name: str,
    preset: DifficultyPreset,
    rng: RandomSource,
) -> tuple[tuple[str, ...], tuple[GraphRecipeEdge, ...], tuple[str, ...], tuple[str, ...]]:
    positions, pairs, tap_node_ids, route = four_way_variant_spec(variant_name)
    return tuple(positions), _edges_from_pairs(pairs), tuple(tap_node_ids), tuple(route)


def _edges_from_pairs(pairs) -> tuple[GraphRecipeEdge, ...]:
    return tuple(GraphRecipeEdge(from_node_id, to_node_id) for from_node_id, to_node_id in pairs)


def _role_for_node(node_id: str) -> str:
    if node_id == "start":
        return "start"
    if node_id == "package":
        return "package"
    if node_id == "destination":
        return "destination"
    if "dead_end" in node_id or node_id.endswith("_bypass") or node_id == "bypass":
        return "dead_end"
    if "switch" in node_id or node_id in {"choice", "hub", "gate"}:
        return "switch"
    return "route"
