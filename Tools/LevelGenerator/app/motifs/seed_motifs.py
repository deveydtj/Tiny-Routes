from __future__ import annotations

from dataclasses import dataclass

from ..models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from ..models.puzzle_motif import MotifCompatibilityConstraints, PuzzleMotif
from .base_motif import BaseMotif
from .motif_registry import MotifRegistry


ALL_DIFFICULTIES = ("tutorial", "easy", "medium", "hard", "expert")


@dataclass(frozen=True)
class SeedMotif(BaseMotif):
    motif: PuzzleMotif

    @property
    def motif_id(self) -> str:
        return self.motif.motif_id

    def build(self) -> PuzzleMotif:
        return self.motif


class RecipeSeedMotifAdapter(BaseMotif):
    """Keeps an existing recipe family usable as a composable seed fragment."""

    def __init__(self, recipe: GraphRecipe, motif_id: str | None = None) -> None:
        self.recipe = recipe
        self._motif_id = motif_id or f"legacy.{recipe.family_name}.{recipe.variant_name}"

    @property
    def motif_id(self) -> str:
        return self._motif_id

    def build(self) -> PuzzleMotif:
        entry = self.recipe.required_path[0]
        exits = (self.recipe.required_path[-1],)
        return PuzzleMotif(
            motif_id=self.motif_id,
            entry_connector=entry,
            exit_connectors=exits,
            nodes=self.recipe.nodes,
            edges=self.recipe.edges,
            intended_decision_effect="Legacy recipe topology preserved through an adapter.",
            allowed_difficulties=(self.recipe.difficulty,),
            may_introduce_cycle=bool(self.recipe.topology_rules and self.recipe.topology_rules.allows_cycles),
            may_introduce_rejoin=bool(self.recipe.topology_rules and self.recipe.topology_rules.allows_rejoin),
            may_introduce_revisit=bool(self.recipe.topology_rules and self.recipe.topology_rules.allows_revisit),
            mechanic_metadata=(("legacyFamily", self.recipe.family_name),),
        )


def _motif(
    motif_id: str,
    nodes: tuple[tuple[str, str], ...],
    edges: tuple[tuple[str, str] | tuple[str, str, str], ...],
    primary_path: tuple[str, ...],
    effect: str,
    *,
    difficulties: tuple[str, ...] = ALL_DIFFICULTIES,
    cycle: bool = False,
    rejoin: bool = False,
    revisit: bool = False,
    dead_end: bool = False,
    embedded_package: bool = False,
) -> SeedMotif:
    metadata = [("primaryPath", ",".join(primary_path)), ("category", motif_id)]
    if embedded_package:
        metadata.append(("embeddedPackageNode", "package"))
    return SeedMotif(PuzzleMotif(
        motif_id=motif_id,
        entry_connector=primary_path[0],
        exit_connectors=(primary_path[-1],),
        nodes=tuple(GraphRecipeNode(node_id, role) for node_id, role in nodes),
        edges=tuple(
            GraphRecipeEdge(edge[0], edge[1], edge[2] if len(edge) == 3 else "always")
            for edge in edges
        ),
        intended_decision_effect=effect,
        allowed_difficulties=difficulties,
        may_introduce_cycle=cycle,
        may_introduce_rejoin=rejoin,
        may_introduce_revisit=revisit,
        may_introduce_dead_end=dead_end,
        compatibility=MotifCompatibilityConstraints(),
        mechanic_metadata=tuple(metadata),
    ))


def seed_motif_factories() -> tuple[BaseMotif, ...]:
    advanced = ("medium", "hard", "expert")
    hard = ("hard", "expert")
    return (
        _motif("straight_segment", (("entry", "route"), ("exit", "route")), (("entry", "exit"),),
               ("entry", "exit"), "Adds readable travel spacing."),
        _motif("single_binary_choice", (("entry", "switch"), ("exit", "route"), ("decoy", "dead_end")),
               (("entry", "exit"), ("entry", "decoy")), ("entry", "exit"), "One binary routing decision.", dead_end=True),
        _motif("dead_end_decoy", (("entry", "switch"), ("exit", "route"), ("dead_end", "dead_end")),
               (("entry", "dead_end"), ("entry", "exit")), ("entry", "exit"), "A visibly punishable wrong branch.", dead_end=True),
        _motif("recoverable_detour", (("entry", "switch"), ("detour_a", "route"), ("detour_b", "route"), ("exit", "route")),
               (("entry", "exit"), ("entry", "detour_a"), ("detour_a", "detour_b"), ("detour_b", "exit")),
               ("entry", "detour_a", "detour_b", "exit"), "A longer choice that safely rejoins.", rejoin=True),
        _motif("split_and_rejoin", (("entry", "switch"), ("upper", "route"), ("lower", "route"), ("exit", "route")),
               (("entry", "upper"), ("entry", "lower"), ("upper", "exit"), ("lower", "exit")),
               ("entry", "upper", "exit"), "Alternative routes split and rejoin.", difficulties=advanced, rejoin=True),
        _motif("package_branch", (("entry", "switch"), ("package", "package"), ("bypass", "route"), ("exit", "route")),
               (("entry", "package"), ("entry", "bypass"), ("package", "exit"), ("bypass", "exit")),
               ("entry", "package", "exit"), "The correct branch collects the package.", rejoin=True),
        _motif("return_loop", (("entry", "switch"), ("loop", "route"), ("exit", "route")),
               (("entry", "loop"), ("loop", "entry"), ("entry", "exit")), ("entry", "exit"),
               "A wrong route returns to the decision.", difficulties=advanced, cycle=True, revisit=True),
        _motif("revisited_switch", (("entry", "switch"), ("phase", "route"), ("exit", "route")),
               (("entry", "phase"), ("phase", "entry"), ("entry", "exit")), ("entry", "phase", "entry", "exit"),
               "The same switch is encountered in two phases.", difficulties=hard, cycle=True, revisit=True),
        _motif("ring_route", (("entry", "switch"), ("ring_a", "route"), ("ring_b", "route"), ("exit", "route")),
               (("entry", "ring_a"), ("ring_a", "ring_b"), ("ring_b", "entry"), ("entry", "exit")),
               ("entry", "exit"), "A ring offers a looping alternate route.", difficulties=hard, cycle=True),
        _motif("three_way_hub", (("entry", "switch"), ("exit", "route"), ("spur_a", "dead_end"), ("spur_b", "dead_end")),
               (("entry", "spur_a"), ("entry", "exit"), ("entry", "spur_b")), ("entry", "exit"),
               "A three-way ordered switch.", difficulties=advanced, dead_end=True),
        _motif("four_way_hub", (("entry", "switch"), ("exit", "route"), ("spur_a", "dead_end"), ("spur_b", "dead_end"), ("spur_c", "dead_end")),
               (("entry", "spur_a"), ("entry", "spur_b"), ("entry", "exit"), ("entry", "spur_c")),
               ("entry", "exit"), "A four-way ordered switch.", difficulties=("expert",), dead_end=True),
        _motif(
            "road_opens_after_package",
            (("entry", "switch"), ("outbound", "route"), ("package", "package"), ("exit", "route")),
            (
                ("entry", "outbound"),
                ("entry", "exit", "afterPackage"),
                ("outbound", "package"),
                ("package", "entry"),
            ),
            ("entry", "outbound", "package", "entry", "exit"),
            "Collecting the package opens a new exit at a router visited in both phases.",
            difficulties=advanced,
            cycle=True,
            revisit=True,
            embedded_package=True,
        ),
        _motif(
            "shortcut_closes_after_package",
            (("entry", "switch"), ("shortcut", "route"), ("package", "package"), ("exit", "route")),
            (
                ("entry", "exit"),
                ("entry", "shortcut", "beforePackage"),
                ("shortcut", "package"),
                ("package", "entry"),
            ),
            ("entry", "shortcut", "package", "entry", "exit"),
            "The package shortcut closes on the return visit, leaving the destination road.",
            difficulties=advanced,
            cycle=True,
            revisit=True,
            embedded_package=True,
        ),
        _motif(
            "return_route_changes_after_package",
            (("entry", "route"), ("outbound", "route"), ("package", "package"), ("exit", "route")),
            (
                ("entry", "outbound", "beforePackage"),
                ("entry", "exit", "afterPackage"),
                ("outbound", "package"),
                ("package", "entry"),
            ),
            ("entry", "outbound", "package", "entry", "exit"),
            "The same router automatically selects a different return road after collection.",
            difficulties=advanced,
            cycle=True,
            revisit=True,
            embedded_package=True,
        ),
        _motif(
            "package_state_revisited_switch",
            (
                ("entry", "switch"),
                ("decoy", "dead_end"),
                ("outbound", "route"),
                ("package", "package"),
                ("exit", "route"),
            ),
            (
                ("entry", "decoy"),
                ("entry", "outbound", "beforePackage"),
                ("entry", "exit", "afterPackage"),
                ("outbound", "package"),
                ("package", "entry"),
            ),
            ("entry", "outbound", "package", "entry", "exit"),
            "A revisited switch requires a different correct authored road in each package phase.",
            difficulties=hard,
            cycle=True,
            revisit=True,
            dead_end=True,
            embedded_package=True,
        ),
    )


def default_motif_registry() -> MotifRegistry:
    return MotifRegistry(seed_motif_factories())
