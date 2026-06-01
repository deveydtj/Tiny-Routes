from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..models.difficulty_preset import DifficultyPreset
from ..models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from ..models.recipe_variant_spec import RecipeVariantSpec
from ..random_source import RandomSource
from .base_recipe import RecipeFamily


ExpandedRecipeBuilder = Callable[
    [str, DifficultyPreset, RandomSource],
    tuple[tuple[str, ...], tuple[tuple[str, str], ...], tuple[str, ...]],
]


@dataclass(frozen=True)
class ExpandedRecipeFamilyDefinition:
    name: str
    difficulty_names: tuple[str, ...]
    mechanic_tags: tuple[str, ...]
    primary_mechanic_tag: str
    topology_class: str
    intended_mechanic: str
    required_player_skill: str
    allowed_switch_counts: tuple[int, int]
    allowed_tap_counts: tuple[int, int]
    allows_repeated_taps: bool
    visual_layout_requirements: tuple[str, ...]
    design_reason: str
    unlock_requirement: str | None
    prior_mechanic_dependency: str | None
    build_spec: ExpandedRecipeBuilder
    requires_swift_validation: bool = False


class ExpandedRecipeFamily(RecipeFamily):
    legacy_template_name = None
    legacy_compatible = False

    def __init__(self, definition: ExpandedRecipeFamilyDefinition) -> None:
        self.name = definition.name
        self.requires_swift_validation = definition.requires_swift_validation
        self._definition = definition
        self._variants = (
            self._variant("primary"),
            self._variant("alternate"),
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
        supported_variants = self.variants_for_difficulty(preset)
        if not supported_variants:
            raise ValueError(f"Recipe family '{self.name}' does not support difficulty '{preset.name}'")
        selected_variant = variant or rng.choice(list(supported_variants))
        if not selected_variant.supports_difficulty(preset.name):
            raise ValueError(f"Recipe variant '{selected_variant.name}' does not support difficulty '{preset.name}'")

        route, pairs, tap_node_ids = self._definition.build_spec(selected_variant.name, preset, rng)
        if selected_variant.name.endswith("_alternate"):
            pairs = _swap_dead_end_order(pairs, route)
        node_ids = tuple(dict.fromkeys([*route, *(node_id for pair in pairs for node_id in pair)]))
        recipe = GraphRecipe(
            level_id=level_id,
            difficulty=preset.name,
            nodes=tuple(GraphRecipeNode(node_id, _role_for_node(node_id)) for node_id in node_ids),
            edges=tuple(GraphRecipeEdge(from_node_id, to_node_id) for from_node_id, to_node_id in pairs),
            required_path=route,
            tap_node_ids=tap_node_ids,
            notes=(
                f"Recipe family: {self.name}",
                f"Recipe variant: {selected_variant.name}",
                f"Intended mechanic: {self._definition.intended_mechanic}",
            ),
            family_name=self.name,
            variant_name=selected_variant.name,
            mechanic_tags=selected_variant.mechanic_tags,
            primary_mechanic_tag=selected_variant.primary_mechanic_tag,
            topology_class=selected_variant.topology_class,
            unlock_requirement=selected_variant.unlock_requirement,
            prior_mechanic_dependency=selected_variant.prior_mechanic_dependency,
            mechanic_metadata=selected_variant.mechanic_metadata(),
        )
        issues = recipe.validate()
        if issues:
            raise ValueError(f"Invalid graph recipe: {', '.join(issues)}")
        return recipe

    def _variant(self, suffix: str) -> RecipeVariantSpec:
        definition = self._definition
        return RecipeVariantSpec(
            name=f"{definition.name}_{suffix}",
            family_name=definition.name,
            difficulty_names=definition.difficulty_names,
            requires_swift_validation=definition.requires_swift_validation,
            intended_mechanic=definition.intended_mechanic,
            required_player_skill=definition.required_player_skill,
            allowed_switch_counts=definition.allowed_switch_counts,
            allowed_tap_counts=definition.allowed_tap_counts,
            allows_repeated_taps=definition.allows_repeated_taps,
            visual_layout_requirements=definition.visual_layout_requirements,
            design_reason=definition.design_reason,
            mechanic_tags=definition.mechanic_tags,
            primary_mechanic_tag=definition.primary_mechanic_tag,
            topology_class=definition.topology_class,
            unlock_requirement=definition.unlock_requirement,
            prior_mechanic_dependency=definition.prior_mechanic_dependency,
        )


def expanded_recipe_family_definitions() -> list[ExpandedRecipeFamilyDefinition]:
    return [
        _definition(
            "straight_delivery_intro",
            ("tutorial",),
            ("straight_delivery", "intro"),
            "straight_line",
            "Teach the package-before-destination objective without switches.",
            "Follow a single readable path.",
            (0, 0),
            (0, 0),
            False,
            ("single forward route", "package and destination separated"),
            "Provides a calm first success state.",
            "level 1",
            None,
            _straight_intro,
        ),
        _definition(
            "single_switch_intro",
            ("tutorial",),
            ("single_switch", "dead_end", "switch", "intro"),
            "single_branch",
            "Introduce one tap that rotates away from a dead end.",
            "Tap one switch before arrival.",
            (1, 1),
            (1, 1),
            False,
            ("two clearly separated switch exits",),
            "Shows switch cause and effect with one wrong branch.",
            "straight delivery understood",
            "straight_delivery_intro",
            _single_switch_intro,
        ),
        _definition(
            "single_switch_wrong_dead_end",
            ("tutorial",),
            ("single_switch", "dead_end", "switch"),
            "single_branch",
            "Make the untapped switch outcome visibly wrong but harmless.",
            "Recognize and avoid a dead-end branch.",
            (1, 1),
            (1, 1),
            False,
            ("dead end close enough to compare",),
            "Creates a small readable consequence for missing the tap.",
            "single switch introduced",
            "single_switch_intro",
            _single_switch_wrong_dead_end,
        ),
        _definition(
            "package_before_destination_intro",
            ("tutorial",),
            ("straight_delivery", "long_route", "package_order"),
            "straight_line",
            "Reinforce that the package must come before the destination.",
            "Scan goal order along the main path.",
            (0, 0),
            (0, 0),
            False,
            ("package precedes destination on the only route",),
            "Separates the two goals spatially before adding gates.",
            "package objective introduced",
            "straight_delivery_intro",
            _package_before_destination_intro,
        ),
        _definition(
            "single_switch_package_choice",
            ("easy",),
            ("single_switch", "safe_choice", "switch", "package_choice"),
            "single_branch",
            "Choose the package branch at a single switch.",
            "Identify the productive branch before the car reaches it.",
            (1, 1),
            (1, 1),
            False,
            ("package branch and dead end point in distinct directions",),
            "Turns the package into the obvious reward for a switch choice.",
            "easy levels unlocked",
            "single_switch_intro",
            _easy_single_switch_package_choice,
        ),
        _definition(
            "two_switch_order_intro",
            ("easy",),
            ("multi_switch", "switch_order", "two_switch"),
            "two_switch_order",
            "Tap two switches in route order.",
            "Track a short ordered tap sequence.",
            (2, 2),
            (2, 2),
            False,
            ("switches are spaced along the main route",),
            "Introduces tap ordering without loops.",
            "two taps introduced",
            "single_switch_intro",
            _two_switch_order_intro,
        ),
        _definition(
            "short_detour_gate",
            ("easy",),
            ("detour", "single_switch", "dead_end", "gate"),
            "detour_gate",
            "Route through a short detour before reaching the package.",
            "Notice that the longer branch is correct.",
            (1, 1),
            (1, 1),
            False,
            ("detour remains compact and readable",),
            "Breaks the habit of always choosing the shortest-looking path.",
            "single switch introduced",
            "single_switch_intro",
            _short_detour_gate,
        ),
        _definition(
            "safe_dead_end_choice",
            ("easy",),
            ("safe_choice", "single_switch", "dead_end", "choice"),
            "single_branch",
            "Compare a harmless wrong branch against the goal route.",
            "Read a branch before tapping.",
            (1, 1),
            (1, 1),
            False,
            ("wrong branch terminates visibly",),
            "Adds low-risk branch reading variety.",
            "single switch introduced",
            "single_switch_intro",
            _safe_dead_end_choice,
        ),
        _definition(
            "package_gate_simple",
            ("easy",),
            ("package_gate", "single_switch", "switch"),
            "package_gate",
            "Use one gate switch to reach the package path.",
            "Connect switch state to package access.",
            (1, 1),
            (1, 1),
            False,
            ("gate is visually between start and package",),
            "Prepares the player for multi-switch package gates.",
            "package gates introduced",
            "single_switch_package_choice",
            _package_gate_simple,
        ),
        _definition(
            "multi_switch_order",
            ("medium",),
            ("multi_switch", "switch_order"),
            "two_switch_order",
            "Resolve two ordered switches around the package.",
            "Maintain a route-level tap plan.",
            (2, 2),
            (2, 2),
            False,
            ("switches are separated by package progress",),
            "Builds a compact multi-step puzzle without a loop.",
            "medium levels unlocked",
            "two_switch_order_intro",
            _medium_two_switch,
        ),
        _definition(
            "package_gate_double_choice",
            ("medium",),
            ("package_gate", "multi_switch", "two_switch"),
            "package_gate",
            "Open the package branch and then the exit branch.",
            "Remember that the route has two gated decisions.",
            (2, 2),
            (2, 2),
            False,
            ("package and exit gates read as separate decisions",),
            "Gives package-gate play a second beat.",
            "package gate learned",
            "package_gate_simple",
            _medium_two_switch,
        ),
        _definition(
            "return_loop_intro",
            ("medium",),
            ("loop", "repeated_tap", "multi_switch", "return_loop"),
            "two_switch_order",
            "Use a loop to revisit and retap the same hub.",
            "Recognize a switch state can matter on the second visit.",
            (2, 2),
            (2, 2),
            True,
            ("loop return is visually distinct from first approach",),
            "Introduces revisits with one central repeated decision.",
            "return loops unlocked",
            "multi_switch_order",
            _return_loop_intro,
        ),
        _definition(
            "split_path_rejoin",
            ("medium",),
            ("split_path", "rejoin"),
            "split_rejoin",
            "Split away from and rejoin the main route.",
            "Follow route continuity through a branch.",
            (2, 2),
            (2, 2),
            False,
            ("split and rejoin are both visible",),
            "Adds route shape variety without extra rules.",
            "medium levels unlocked",
            "two_switch_order_intro",
            _split_path_rejoin,
        ),
        _definition(
            "fake_shortcut",
            ("medium",),
            ("fake_shortcut", "dead_end"),
            "two_switch_order",
            "Avoid a tempting short branch.",
            "Prefer the goal route over the shortest-looking exit.",
            (2, 2),
            (2, 2),
            False,
            ("fake shortcut terminates clearly",),
            "Creates a readable trick that rewards inspection.",
            "medium levels unlocked",
            "short_detour_gate",
            _fake_shortcut,
        ),
        _definition(
            "hub_choice",
            ("medium",),
            ("hub", "multi_switch", "three_way"),
            "two_switch_order",
            "Choose from a three-way hub and then exit through a gate.",
            "Count taps on a three-way switch.",
            (2, 2),
            (2, 2),
            False,
            ("hub exits use three distinct directions",),
            "Introduces a central choice without four-way complexity.",
            "three-way switches unlocked",
            "multi_switch_order",
            _hub_choice,
        ),
        _definition(
            "return_loop_with_gate",
            ("hard",),
            ("loop", "repeated_tap", "package_gate", "return_loop", "gate"),
            "two_switch_order",
            "Revisit a hub after opening a loop gate.",
            "Plan repeated hub use plus an intermediate gate.",
            (3, 3),
            (3, 3),
            True,
            ("hub revisit path stays readable",),
            "Combines loop memory with a separate gate decision.",
            "hard levels unlocked",
            "return_loop_intro",
            _return_loop_with_gate,
        ),
        _definition(
            "ring_route_gate",
            ("hard",),
            ("ring", "package_gate", "ring_route"),
            "two_switch_order",
            "Route around a ring-like path through a gate.",
            "Read a non-linear route around the package.",
            (3, 3),
            (3, 3),
            False,
            ("ring has clear entry, package, and exit sides",),
            "Adds spatial variety beyond linear chains.",
            "ring routes unlocked",
            "package_gate_double_choice",
            _hard_three_switch_chain,
        ),
        _definition(
            "multi_switch_revisit",
            ("hard",),
            ("multi_switch", "revisit", "repeated_tap"),
            "two_switch_order",
            "Return to an earlier switch with a changed route goal.",
            "Remember an earlier switch state after a loop.",
            (3, 3),
            (3, 3),
            True,
            ("revisit route returns to the same visible node",),
            "Creates meaningful memory without needing more switches.",
            "hard levels unlocked",
            "return_loop_intro",
            _multi_switch_revisit,
        ),
        _definition(
            "package_inside_loop",
            ("hard",),
            ("package_inside_loop", "loop", "multi_switch", "package"),
            "return_loop",
            "Collect the package inside a loop before exiting.",
            "Track objective progress inside a loop.",
            (3, 3),
            (3, 3),
            False,
            ("package sits inside the loop area",),
            "Makes the package location part of the route shape.",
            "hard levels unlocked",
            "ring_route_gate",
            _package_inside_loop,
        ),
        _definition(
            "two_phase_route",
            ("hard",),
            ("two_phase", "multi_switch"),
            "two_phase",
            "Solve a package phase and then an exit phase.",
            "Group taps by route phase.",
            (3, 3),
            (3, 3),
            False,
            ("phase transition is visually separated after package",),
            "Gives hard levels a clear before/after package structure.",
            "hard levels unlocked",
            "package_gate_double_choice",
            _hard_three_switch_chain,
        ),
        _definition(
            "branch_then_rejoin_with_wrong_order",
            ("hard",),
            ("split_path", "rejoin", "wrong_order", "branch"),
            "split_rejoin",
            "Handle a branch that rejoins before later gates.",
            "Avoid applying later switch logic too early.",
            (3, 3),
            (3, 3),
            False,
            ("rejoin happens before the package gate",),
            "Tests route order instead of raw tap count.",
            "hard levels unlocked",
            "split_path_rejoin",
            _branch_then_rejoin,
        ),
        _definition(
            "four_way_intro",
            ("expert",),
            ("four_way", "repeated_tap", "intro"),
            "four_way_gate",
            "Use a four-way switch with a clearly counted tap target.",
            "Count two taps on a four-way switch.",
            (1, 1),
            (2, 2),
            True,
            ("four exits use cardinal directions",),
            "Introduces four-way behavior with no second switch.",
            "expert levels unlocked",
            "hub_choice",
            _four_way_intro,
            requires_swift_validation=True,
        ),
        _definition(
            "four_way_package_gate",
            ("expert",),
            ("four_way", "package_gate"),
            "four_way_gate",
            "Use a four-way switch to reach the package, then gate the exit.",
            "Combine four-way counting with a standard gate.",
            (1, 1),
            (2, 2),
            True,
            ("four-way hub and exit gate have separate centers",),
            "Creates a clear progression from four-way intro to gated play.",
            "four-way introduced",
            "four_way_intro",
            _four_way_package_gate,
            requires_swift_validation=True,
        ),
        _definition(
            "four_way_ring",
            ("expert",),
            ("four_way", "ring", "repeated_tap", "ring_route"),
            "four_way_gate",
            "Leave and revisit a four-way hub through a loop.",
            "Retap a multi-exit hub after route progress.",
            (1, 1),
            (2, 2),
            True,
            ("loop returns visibly to the four-way hub",),
            "Uses four-way complexity for route memory, not just branching.",
            "four-way loops unlocked",
            "four_way_intro",
            _four_way_ring,
            requires_swift_validation=True,
        ),
        _definition(
            "multi_four_way_route",
            ("expert",),
            ("four_way", "multi_switch"),
            "four_way_gate",
            "Resolve two multi-exit switch decisions in sequence.",
            "Count taps across separate four-way-style decisions.",
            (1, 1),
            (2, 2),
            True,
            ("multi-exit switches are not visually adjacent",),
            "Builds expert tap counting while preserving readable chunks.",
            "advanced four-way unlocked",
            "four_way_package_gate",
            _multi_four_way_route,
            requires_swift_validation=True,
        ),
        _definition(
            "controlled_repeated_taps",
            ("expert",),
            ("repeated_tap", "loop", "multi_switch", "return_loop"),
            "two_switch_order",
            "Repeat a hub tap after collecting the package.",
            "Understand that route state changes the same switch's goal.",
            (2, 2),
            (2, 2),
            True,
            ("repeat hub is central and clearly revisited",),
            "Makes repeated taps intentional and controlled.",
            "repeated taps unlocked",
            "return_loop_intro",
            _controlled_repeated_taps,
        ),
        _definition(
            "late_route_reversal",
            ("expert",),
            ("route_reversal", "revisit", "repeated_tap"),
            "two_switch_order",
            "Reverse back through a previous decision late in the route.",
            "Carry earlier route context into the final exit.",
            (3, 3),
            (3, 3),
            True,
            ("late return path is visually distinct from the first leg",),
            "Creates an expert ending based on memory and reversal.",
            "late expert mechanics unlocked",
            "multi_switch_revisit",
            _late_route_reversal,
        ),
    ]


def _definition(
    name: str,
    difficulty_names: tuple[str, ...],
    mechanic_tags: tuple[str, ...],
    topology_class: str,
    intended_mechanic: str,
    required_player_skill: str,
    allowed_switch_counts: tuple[int, int],
    allowed_tap_counts: tuple[int, int],
    allows_repeated_taps: bool,
    visual_layout_requirements: tuple[str, ...],
    design_reason: str,
    unlock_requirement: str | None,
    prior_mechanic_dependency: str | None,
    build_spec: ExpandedRecipeBuilder,
    requires_swift_validation: bool = False,
) -> ExpandedRecipeFamilyDefinition:
    return ExpandedRecipeFamilyDefinition(
        name=name,
        difficulty_names=difficulty_names,
        mechanic_tags=mechanic_tags,
        primary_mechanic_tag=mechanic_tags[0] if mechanic_tags else "",
        topology_class=topology_class,
        intended_mechanic=intended_mechanic,
        required_player_skill=required_player_skill,
        allowed_switch_counts=allowed_switch_counts,
        allowed_tap_counts=allowed_tap_counts,
        allows_repeated_taps=allows_repeated_taps,
        visual_layout_requirements=visual_layout_requirements,
        design_reason=design_reason,
        unlock_requirement=unlock_requirement,
        prior_mechanic_dependency=prior_mechanic_dependency,
        build_spec=build_spec,
        requires_swift_validation=requires_swift_validation,
    )


def _straight_intro(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    return ("start", "package", "destination"), (("start", "package"), ("package", "destination")), ()


def _single_switch_intro(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    return _single_switch_route("dead_end_a")


def _single_switch_wrong_dead_end(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    return _single_switch_route("wrong_dead_end")


def _package_before_destination_intro(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    route = ("start", "pickup_lane", "package", "exit_lane", "destination")
    return route, _pairs(route), ()


def _easy_single_switch_package_choice(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    route = ("start", "choice", "package", "destination")
    return route, (("start", "choice"), ("choice", "dead_end_a"), ("choice", "package"), ("package", "destination")), ("choice",)


def _two_switch_order_intro(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    route = ("start", "switch_a", "package", "switch_b", "destination")
    pairs = (
        ("start", "switch_a"),
        ("switch_a", "dead_end_a"),
        ("switch_a", "package"),
        ("package", "switch_b"),
        ("switch_b", "dead_end_b"),
        ("switch_b", "destination"),
    )
    return route, pairs, ("switch_a", "switch_b")


def _short_detour_gate(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    route = ("start", "gate", "detour", "package", "destination")
    pairs = (("start", "gate"), ("gate", "dead_end_a"), ("gate", "detour"), ("detour", "package"), ("package", "destination"))
    return route, pairs, ("gate",)


def _safe_dead_end_choice(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    route = ("start", "choice", "safe_route", "package", "destination")
    pairs = (("start", "choice"), ("choice", "dead_end_a"), ("choice", "safe_route"), ("safe_route", "package"), ("package", "destination"))
    return route, pairs, ("choice",)


def _package_gate_simple(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    route = ("start", "gate", "package", "destination")
    pairs = (("start", "gate"), ("gate", "dead_end_a"), ("gate", "package"), ("package", "destination"))
    return route, pairs, ("gate",)


def _medium_two_switch(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    return _two_switch_order_intro(variant_name, preset, rng)


def _return_loop_intro(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    return _medium_two_switch(variant_name, preset, rng)


def _split_path_rejoin(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    route = ("start", "switch_a", "upper_branch", "rejoin", "switch_b", "package", "destination")
    pairs = (
        ("start", "switch_a"),
        ("switch_a", "dead_end_a"),
        ("switch_a", "upper_branch"),
        ("upper_branch", "rejoin"),
        ("rejoin", "switch_b"),
        ("switch_b", "dead_end_b"),
        ("switch_b", "package"),
        ("package", "destination"),
    )
    return route, pairs, ("switch_a", "switch_b")


def _fake_shortcut(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    return _medium_two_switch(variant_name, preset, rng)


def _hub_choice(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    return _medium_two_switch(variant_name, preset, rng)


def _return_loop_with_gate(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    return _hard_three_switch_chain(variant_name, preset, rng)


def _hard_three_switch_chain(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    route = ("start", "switch_a", "package", "switch_b", "route_mid", "switch_c", "destination")
    pairs = (
        ("start", "switch_a"),
        ("switch_a", "dead_end_a"),
        ("switch_a", "package"),
        ("package", "switch_b"),
        ("switch_b", "dead_end_b"),
        ("switch_b", "route_mid"),
        ("route_mid", "switch_c"),
        ("switch_c", "dead_end_c"),
        ("switch_c", "destination"),
    )
    return route, pairs, ("switch_a", "switch_b", "switch_c")


def _multi_switch_revisit(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    return _hard_three_switch_chain(variant_name, preset, rng)


def _package_inside_loop(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    route = ("start", "switch_a", "loop_a", "switch_b", "package", "loop_b", "switch_c", "destination")
    pairs = (
        ("start", "switch_a"),
        ("switch_a", "dead_end_a"),
        ("switch_a", "loop_a"),
        ("loop_a", "switch_b"),
        ("switch_b", "dead_end_b"),
        ("switch_b", "package"),
        ("package", "loop_b"),
        ("loop_b", "switch_c"),
        ("switch_c", "dead_end_c"),
        ("switch_c", "destination"),
    )
    return route, pairs, ("switch_a", "switch_b", "switch_c")


def _branch_then_rejoin(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    route = ("start", "switch_a", "branch_a", "rejoin", "switch_b", "package", "switch_c", "destination")
    pairs = (
        ("start", "switch_a"),
        ("switch_a", "dead_end_a"),
        ("switch_a", "branch_a"),
        ("branch_a", "rejoin"),
        ("rejoin", "switch_b"),
        ("switch_b", "dead_end_b"),
        ("switch_b", "package"),
        ("package", "switch_c"),
        ("switch_c", "dead_end_c"),
        ("switch_c", "destination"),
    )
    return route, pairs, ("switch_a", "switch_b", "switch_c")


def _four_way_intro(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    route = ("start", "entry", "central_switch", "package", "return_node", "central_switch", "destination")
    pairs = (
        ("start", "entry"),
        ("entry", "central_switch"),
        ("central_switch", "dead_end"),
        ("central_switch", "package"),
        ("central_switch", "destination"),
        ("central_switch", "side_branch"),
        ("package", "return_node"),
        ("return_node", "central_switch"),
    )
    return route, pairs, ("central_switch", "central_switch")


def _four_way_package_gate(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    return _four_way_intro(variant_name, preset, rng)


def _four_way_ring(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    return _four_way_intro(variant_name, preset, rng)


def _multi_four_way_route(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    return _four_way_intro(variant_name, preset, rng)


def _controlled_repeated_taps(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    return _medium_two_switch(variant_name, preset, rng)


def _late_route_reversal(variant_name: str, preset: DifficultyPreset, rng: RandomSource):
    return _hard_three_switch_chain(variant_name, preset, rng)


def _single_switch_route(dead_end_id: str):
    route = ("start", "choice", "package", "destination")
    return route, (("start", "choice"), ("choice", dead_end_id), ("choice", "package"), ("package", "destination")), ("choice",)


def _pairs(route: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    return tuple(zip(route, route[1:]))


def _swap_dead_end_order(
    pairs: tuple[tuple[str, str], ...],
    route: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    route_edges = set(zip(route, route[1:]))
    grouped: dict[str, list[tuple[str, str]]] = {}
    order: list[str] = []
    for pair in pairs:
        if pair[0] not in grouped:
            grouped[pair[0]] = []
            order.append(pair[0])
        grouped[pair[0]].append(pair)
    swapped: list[tuple[str, str]] = []
    for from_node_id in order:
        outgoing = grouped[from_node_id]
        if len(outgoing) == 2 and outgoing[1] in route_edges and outgoing[0][1].startswith(("dead_end", "wrong", "shortcut")):
            swapped.extend(outgoing)
        else:
            swapped.extend(outgoing)
    return tuple(swapped)


def _role_for_node(node_id: str) -> str:
    if node_id == "start":
        return "start"
    if node_id == "package":
        return "package"
    if node_id == "destination":
        return "destination"
    if "dead_end" in node_id or node_id.startswith("wrong") or node_id.endswith("_dead_end"):
        return "dead_end"
    if "switch" in node_id or node_id in {"choice", "hub", "gate"}:
        return "switch"
    return "route"
