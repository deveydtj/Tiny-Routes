from __future__ import annotations

from dataclasses import dataclass, replace

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
    _advanced_difficulties = frozenset({"medium", "hard", "expert"})
    _hard_preferred_motifs = frozenset({
        "return_loop", "revisited_switch", "ring_route", "three_way_hub", "four_way_hub",
    })

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
        embedded_package_motifs = tuple(
            factory for factory in selected
            if dict(factory.build().mechanic_metadata).get("embeddedPackageNode")
        )
        if len(embedded_package_motifs) > 1:
            raise MotifCompositionError("multiple_embedded_package_motifs")
        has_embedded_package = bool(embedded_package_motifs)
        decision_motif_count = sum(self._outgoing_max(item.build()) > 1 for item in selected)
        pre_package_decision_target = max(1, decision_motif_count // 2)

        nodes = [GraphRecipeNode("start", "start")]
        edges: list[GraphRecipeEdge] = []
        required_path = ["start"]
        previous = "start"
        declared_tags: list[str] = []
        package_inserted = False
        cycle_count = 0
        allows_rejoin = False
        allows_revisit = False

        for index, factory in enumerate(selected):
            # Splitting the route into pre/post-package phases gives medium+
            # compositions a measured state dependency instead of a chain of
            # unrelated switches. The package is inserted near the decision
            # midpoint so both phases contain a real decision.
            if (
                preset.name in self._advanced_difficulties
                and not has_embedded_package
                and not package_inserted
                and index > 0
                and sum(self._outgoing_max(item.build()) > 1 for item in selected[:index])
                    >= pre_package_decision_target
                and self._outgoing_max(factory.build()) > 1
            ):
                nodes.append(GraphRecipeNode("package", "package"))
                edges.append(GraphRecipeEdge(previous, "package"))
                required_path.append("package")
                previous = "package"
                package_inserted = True
            motif = factory.build()
            prefix = f"m{index + 1}_{motif.motif_id}"
            embedded_package_node = dict(motif.mechanic_metadata).get("embeddedPackageNode")
            rename = {
                node.id: "package" if node.id == embedded_package_node else f"{prefix}_{node.id}"
                for node in motif.nodes
            }
            if embedded_package_node:
                if package_inserted:
                    raise MotifCompositionError("embedded_package_after_package_insertion")
                package_inserted = True
            nodes.extend(
                GraphRecipeNode(rename[node.id], node.role)
                for node in motif.nodes
                if rename[node.id] != "package"
            )
            if embedded_package_node:
                nodes.append(GraphRecipeNode("package", "package"))
            edges.append(GraphRecipeEdge(previous, rename[motif.entry_connector]))
            edges.extend(
                GraphRecipeEdge(
                    rename[edge.from_node_id], rename[edge.to_node_id], edge.availability
                )
                for edge in motif.edges
            )
            local_path = self._primary_path(motif)
            required_path.extend(rename[node_id] for node_id in local_path)
            previous = rename[motif.exit_connectors[0]]
            declared_tags.append(motif.motif_id)
            cycle_count += int(motif.may_introduce_cycle)
            allows_rejoin = allows_rejoin or motif.may_introduce_rejoin
            allows_revisit = allows_revisit or motif.may_introduce_revisit

        if not package_inserted:
            nodes.append(GraphRecipeNode("package", "package"))
            edges.append(GraphRecipeEdge(previous, "package"))
            required_path.append("package")
            previous = "package"
        nodes.append(GraphRecipeNode("destination", "destination"))
        edges.append(GraphRecipeEdge(previous, "destination"))
        required_path.append("destination")

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
            requires_package_gate=any(edge.availability != "always" for edge in edges),
            requires_unique_solution=False,
            requires_swift_runtime_validation=False,
        )
        topology_class = "composed_motifs"
        if "ring_route" in declared_tags:
            topology_class = "ring_route"
        elif cycle_count:
            topology_class = "return_loop"
        elif any(edge.availability != "always" for edge in edges):
            topology_class = "two_phase"
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
        evidence = self._detected_mechanic_evidence(recipe, profile)
        discrepancies = self._mechanic_discrepancies(selected, evidence)
        metadata = dict(recipe.mechanic_metadata)
        metadata.update({
            "detectedMechanics": sorted(evidence),
            "mechanicDiscrepancies": list(discrepancies),
        })
        recipe = replace(recipe, mechanic_metadata=metadata)
        self._validate_measured_composition(recipe, selected, preset, profile)
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
            and (preset.allow_return_loops or not factory.build().may_introduce_cycle)
            and self._outgoing_max(factory.build()) <= preset.max_outgoing_edges_per_switch
        )
        if not eligible:
            raise MotifCompositionError(f"no_motifs_for_difficulty:{preset.name}")
        low, high = self._counts.get(preset.name, (1, 2))
        count = rng.randint(low, high)
        selected: list = []
        if preset.name in self._advanced_difficulties:
            by_id = {item.motif_id: item for item in eligible}
            strategic_ids = tuple(
                motif_id for motif_id in ("split_and_rejoin", "package_branch") if motif_id in by_id
            )
            if len(strategic_ids) < 2:
                raise MotifCompositionError(f"no_dependency_motif_for_difficulty:{preset.name}")
            if rng.randint(0, 1):
                strategic_ids = tuple(reversed(strategic_ids))
            selected.extend(by_id[motif_id] for motif_id in strategic_ids)
            filler = by_id.get("straight_segment")
            if filler is None:
                raise MotifCompositionError(f"no_readable_filler_motif_for_difficulty:{preset.name}")
            while len(selected) < count:
                selected.append(filler)
        while len(selected) < count:
            selected.append(rng.choice(eligible))
        return tuple(selected[:count])

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
        dead_end_count = sum(factory.build().may_introduce_dead_end for factory in selected)
        dead_end_cap = 1 if preset.name in {"tutorial", "easy", "medium"} else 2
        if dead_end_count > dead_end_cap:
            raise MotifCompositionError(f"dead_end_punishment_cap_exceeded:{dead_end_count}:{dead_end_cap}")
        for factory in selected:
            motif = factory.build()
            if motif.may_introduce_dead_end and not self._has_readable_decoy_path(motif):
                raise MotifCompositionError(f"unreadable_decoy_consequence:{motif.motif_id}")

    def _has_readable_decoy_path(self, motif) -> bool:
        dead_ends = {node.id for node in motif.nodes if node.role == "dead_end"}
        outgoing: dict[str, list[str]] = {}
        for edge in motif.edges:
            outgoing.setdefault(edge.from_node_id, []).append(edge.to_node_id)
        return bool(dead_ends) and any(
            target in dead_ends
            for targets in outgoing.values() if len(targets) > 1
            for target in targets
        )

    def _detected_mechanic_evidence(self, recipe, profile) -> set[str]:
        evidence: set[str] = set()
        if profile.ordered_dependency_count:
            evidence.add("ordered_dependency")
        if profile.package_phase_decisions_before and profile.package_phase_decisions_after:
            evidence.add("package_phase_split")
        if profile.package_phase_transition_count and profile.state_dependent_route_change_count:
            evidence.add("package_state_transition")
            evidence.add("state_dependent_route_change")
        if profile.roads_opened_after_package_count:
            evidence.add("road_opens_after_package")
        if profile.roads_closed_after_package_count:
            evidence.add("road_closes_after_package")
        if profile.route_revisit_count:
            evidence.add("route_revisit")
        if profile.switch_state_change_on_revisit_count:
            evidence.add("multi_state_switch")
        if profile.recoverable_mistake_count:
            evidence.add("recoverable_route")
        if profile.dead_end_choice_count:
            evidence.add("dead_end_consequence")
        if recipe.topology_rules and recipe.topology_rules.allows_rejoin:
            evidence.add("route_rejoin")
        if recipe.topology_rules and recipe.topology_rules.allows_cycles:
            evidence.add("cycle_route")
        if any(self._outgoing_count(recipe, node.id) >= 3 for node in recipe.nodes):
            evidence.add("multi_exit_hub")
        return evidence

    def _mechanic_discrepancies(self, selected, evidence: set[str]) -> tuple[str, ...]:
        expected_by_motif = {
            "return_loop": "cycle_route",
            "revisited_switch": "route_revisit",
            "ring_route": "cycle_route",
            "three_way_hub": "multi_exit_hub",
            "four_way_hub": "multi_exit_hub",
            "dead_end_decoy": "dead_end_consequence",
            "single_binary_choice": "dead_end_consequence",
            "road_opens_after_package": "road_opens_after_package",
            "shortcut_closes_after_package": "road_closes_after_package",
            "return_route_changes_after_package": "state_dependent_route_change",
            "package_state_revisited_switch": "multi_state_switch",
        }
        return tuple(
            f"declared_effect_not_detected:{factory.motif_id}:{expected_by_motif[factory.motif_id]}"
            for factory in selected
            if factory.motif_id in expected_by_motif and expected_by_motif[factory.motif_id] not in evidence
        )

    def _validate_measured_composition(self, recipe, selected, preset, profile) -> None:
        if preset.name in self._advanced_difficulties:
            if (
                profile.ordered_dependency_count < 1
                and profile.state_dependent_route_change_count < 1
            ):
                raise MotifCompositionError("required_motif_effect_lost:ordered_or_state_dependency")
            if (
                profile.state_dependent_route_change_count < 1
                and profile.independent_decision_ratio > preset.maximum_independent_decision_ratio
            ):
                raise MotifCompositionError(
                    f"independent_decision_ratio_above_preset_maximum:{profile.independent_decision_ratio}"
                )
        discrepancies = recipe.mechanic_metadata.get("mechanicDiscrepancies", ())
        required_ids = self._hard_preferred_motifs if preset.name in {"hard", "expert"} else frozenset()
        if required_ids.intersection(factory.motif_id for factory in selected) and discrepancies:
            raise MotifCompositionError(f"required_motif_effect_lost:{discrepancies[0]}")

    def _outgoing_count(self, recipe, node_id: str) -> int:
        return sum(edge.from_node_id == node_id for edge in recipe.edges)

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
