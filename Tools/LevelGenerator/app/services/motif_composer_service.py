from __future__ import annotations

from dataclasses import dataclass

from ..models.decision_profile import DecisionProfile
from ..models.difficulty_preset import DifficultyPreset
from ..models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from ..models.recipe_topology_rules import RecipeTopologyRules
from ..motifs.motif_registry import MotifRegistry
from ..motifs.seed_motifs import default_motif_registry
from ..random_source import RandomSource
from .decision_profile_service import DecisionProfileService
from .topology_solver_service import TopologySearchResult, TopologySolverService


class MotifCompositionError(ValueError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class ComposedMotifGraph:
    recipe: GraphRecipe
    motif_ids: tuple[str, ...]
    topology_search: TopologySearchResult
    decision_profile: DecisionProfile


class MotifComposerService:
    """Deterministically joins independently validated motif fragments."""

    _counts = {"tutorial": (1, 1), "easy": (1, 2), "medium": (2, 3), "hard": (2, 4), "expert": (3, 4)}

    def __init__(
        self,
        registry: MotifRegistry | None = None,
        topology_solver: TopologySolverService | None = None,
        decision_profiler: DecisionProfileService | None = None,
    ) -> None:
        self.registry = registry or default_motif_registry()
        self.topology_solver = topology_solver or TopologySolverService()
        self.decision_profiler = decision_profiler or DecisionProfileService()

    def compose(
        self,
        level_id: str,
        preset: DifficultyPreset,
        seed: int,
        motif_ids: tuple[str, ...] | None = None,
    ) -> ComposedMotifGraph:
        rng = RandomSource(seed)
        selected = self._select_motifs(preset, rng, motif_ids)
        self._validate_compatibility(selected, preset)

        nodes = [GraphRecipeNode("start", "start")]
        edges: list[GraphRecipeEdge] = []
        required_path = ["start"]
        previous = "start"
        declared_tags: list[str] = []
        cycle_count = 0
        allows_rejoin = False
        allows_revisit = False

        for index, factory in enumerate(selected):
            motif = factory.build()
            prefix = f"m{index + 1}_{motif.motif_id}"
            rename = {node.id: f"{prefix}_{node.id}" for node in motif.nodes}
            nodes.extend(GraphRecipeNode(rename[node.id], node.role) for node in motif.nodes)
            edges.append(GraphRecipeEdge(previous, rename[motif.entry_connector]))
            edges.extend(GraphRecipeEdge(rename[edge.from_node_id], rename[edge.to_node_id]) for edge in motif.edges)
            local_path = self._primary_path(motif)
            required_path.extend(rename[node_id] for node_id in local_path)
            previous = rename[motif.exit_connectors[0]]
            declared_tags.append(motif.motif_id)
            cycle_count += int(motif.may_introduce_cycle)
            allows_rejoin = allows_rejoin or motif.may_introduce_rejoin
            allows_revisit = allows_revisit or motif.may_introduce_revisit

        nodes.extend((GraphRecipeNode("package", "package"), GraphRecipeNode("destination", "destination")))
        edges.extend((GraphRecipeEdge(previous, "package"), GraphRecipeEdge("package", "destination")))
        required_path.extend(("package", "destination"))

        outgoing_counts: dict[str, int] = {}
        for edge in edges:
            outgoing_counts[edge.from_node_id] = outgoing_counts.get(edge.from_node_id, 0) + 1
        tap_node_ids = tuple(node_id for node_id in required_path if outgoing_counts.get(node_id, 0) > 1)
        rules = RecipeTopologyRules(
            allows_cycles=cycle_count > 0,
            allows_rejoin=allows_rejoin,
            allows_revisit=allows_revisit,
            allows_return_path=cycle_count > 0,
            allows_ring=any(item.motif_id == "ring_route" for item in selected),
            allowed_cycle_count=cycle_count,
            requires_package_gate=False,
            requires_unique_solution=False,
            requires_swift_runtime_validation=False,
        )
        topology_class = "composed_motifs"
        if "ring_route" in declared_tags:
            topology_class = "ring_route"
        elif cycle_count:
            topology_class = "return_loop"
        recipe = GraphRecipe(
            level_id=level_id,
            difficulty=preset.name,
            nodes=tuple(nodes),
            edges=tuple(edges),
            required_path=tuple(required_path),
            tap_node_ids=tap_node_ids,
            topology_rules=rules,
            family_name="motif_composition",
            variant_name="+".join(declared_tags),
            mechanic_tags=tuple(declared_tags),
            primary_mechanic_tag=declared_tags[0] if declared_tags else "",
            topology_class=topology_class,
            notes=(f"motif_seed:{seed}",),
            mechanic_metadata={
                "declaredMotifs": declared_tags,
                "topologyClass": topology_class,
                "topologyRules": rules.to_metadata(),
                "allowsRepeatedTaps": allows_revisit,
            },
        )
        issues = recipe.validate()
        if issues:
            raise MotifCompositionError(f"composed_recipe_invalid:{issues[0]}")
        search = self.topology_solver.search(recipe, preset)
        if not search.succeeded:
            reason = search.failure_reasons[0] if search.failure_reasons else "no_solution"
            raise MotifCompositionError(f"topology_solver_rejected:{reason}")
        profile = self.decision_profiler.analyze(recipe, search.solutions)
        return ComposedMotifGraph(recipe, tuple(item.motif_id for item in selected), search, profile)

    def compose_recipe(self, *args, **kwargs) -> GraphRecipe:
        return self.compose(*args, **kwargs).recipe

    def _select_motifs(self, preset, rng, requested):
        if requested is not None:
            if not requested:
                raise MotifCompositionError("motif_selection_empty")
            try:
                return tuple(self.registry.get(motif_id) for motif_id in requested)
            except KeyError as error:
                raise MotifCompositionError(str(error).strip("'")) from error
        eligible = tuple(
            factory for factory in self.registry.all()
            if preset.name in factory.build().allowed_difficulties
            and not factory.build().may_introduce_cycle
            and self._outgoing_max(factory.build()) <= preset.max_outgoing_edges_per_switch
        )
        if not eligible:
            raise MotifCompositionError(f"no_motifs_for_difficulty:{preset.name}")
        low, high = self._counts.get(preset.name, (1, 2))
        count = rng.randint(low, high)
        return tuple(rng.choice(eligible) for _ in range(count))

    def _validate_compatibility(self, selected, preset) -> None:
        ids = {factory.motif_id for factory in selected}
        for factory in selected:
            motif = factory.build()
            if preset.name not in motif.allowed_difficulties:
                raise MotifCompositionError(f"motif_difficulty_not_allowed:{motif.motif_id}:{preset.name}")
            incompatible = ids.intersection(motif.compatibility.incompatible_motif_ids)
            if incompatible:
                raise MotifCompositionError(f"incompatible_motifs:{motif.motif_id}:{sorted(incompatible)[0]}")
            if motif.may_introduce_cycle and not preset.allow_return_loops:
                raise MotifCompositionError(f"cycle_not_allowed:{motif.motif_id}:{preset.name}")
            if self._outgoing_max(motif) > preset.max_outgoing_edges_per_switch:
                raise MotifCompositionError(f"switch_degree_exceeds_preset:{motif.motif_id}")

    def _primary_path(self, motif) -> tuple[str, ...]:
        metadata = dict(motif.mechanic_metadata)
        path = tuple(item for item in metadata.get("primaryPath", "").split(",") if item)
        if not path or path[0] != motif.entry_connector or path[-1] not in motif.exit_connectors:
            raise MotifCompositionError(f"invalid_primary_path:{motif.motif_id}")
        edge_pairs = {(edge.from_node_id, edge.to_node_id) for edge in motif.edges}
        if any(pair not in edge_pairs for pair in zip(path, path[1:])):
            raise MotifCompositionError(f"invalid_primary_path_edge:{motif.motif_id}")
        return path

    def _outgoing_max(self, motif) -> int:
        counts: dict[str, int] = {}
        for edge in motif.edges:
            counts[edge.from_node_id] = counts.get(edge.from_node_id, 0) + 1
        return max(counts.values(), default=0)
