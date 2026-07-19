"""Graph-derived topology contracts for legacy fixed recipe families."""

from __future__ import annotations

from collections import Counter, deque

from ..models.graph_recipe import GraphRecipe
from ..models.recipe_topology_evidence import RecipeTopologyEvidence


class RecipeTopologyContractService:
    """Compare recipe claims with graph evidence using stable reason codes."""

    _behavior_order = (
        "ring",
        "cycle",
        "rejoin",
        "revisit",
        "route_reversal",
        "objective_gate",
        "high_arity_switch",
        "recoverable_route",
        "unique_success",
        "unique_optimal",
    )

    def analyze(self, recipe: GraphRecipe) -> RecipeTopologyEvidence:
        claimed = self._claimed_behaviors(recipe)
        detected = self._detected_behaviors(recipe)
        reasons = [
            f"claimed_{behavior}_not_detected"
            for behavior in self._behavior_order
            if behavior in claimed and behavior not in detected
        ]
        reasons.extend(
            f"recipe_validation:{issue}"
            for issue in recipe.validate()
        )
        stable_reasons = tuple(dict.fromkeys(sorted(reasons)))
        return RecipeTopologyEvidence(
            family_name=recipe.family_name,
            variant_name=recipe.variant_name,
            claimed_behaviors=self._ordered(claimed),
            detected_behaviors=self._ordered(detected),
            status="failed" if stable_reasons else "passed",
            reasons=stable_reasons,
        )

    def audit_registry(self, registry=None, difficulty_service=None) -> tuple[RecipeTopologyEvidence, ...]:
        """Audit every family variant, including stable generation failures."""

        if registry is None:
            from ..recipes.recipe_family_registry import RecipeFamilyRegistry

            registry = RecipeFamilyRegistry()
        if difficulty_service is None:
            from .difficulty_service import DifficultyService

            difficulty_service = DifficultyService()
        from ..random_source import RandomSource

        results: list[RecipeTopologyEvidence] = []
        audit_index = 0
        for family_name in registry.valid_family_names():
            if family_name == "mixed":
                continue
            family = registry.get_family(family_name)
            for variant in family.variants:
                preset = difficulty_service.get_preset(variant.difficulty_names[0])
                try:
                    recipe = family.generate_recipe(
                        "level_topology_contract_audit",
                        preset,
                        RandomSource(43000 + audit_index),
                        variant,
                    )
                except Exception as error:  # Legacy generation failures are audit evidence.
                    results.append(
                        RecipeTopologyEvidence(
                            family_name=family_name,
                            variant_name=variant.name,
                            claimed_behaviors=(),
                            detected_behaviors=(),
                            status="failed",
                            reasons=(f"recipe_generation_failed:{type(error).__name__}",),
                        )
                    )
                else:
                    results.append(self.analyze(recipe))
                audit_index += 1
        return tuple(results)

    def _claimed_behaviors(self, recipe: GraphRecipe) -> set[str]:
        rules = recipe.topology_rules
        terms = self._claim_terms(recipe)
        claimed: set[str] = set()
        if (rules and rules.allows_ring) or self._matches(terms, "ring"):
            claimed.add("ring")
        if (rules and rules.allows_cycles) or self._matches(
            terms, "loop", "ring", "revisit", "route_reversal"
        ):
            claimed.add("cycle")
        if (rules and rules.allows_rejoin) or self._matches(terms, "rejoin"):
            claimed.add("rejoin")
        if (rules and rules.allows_revisit) or self._matches(
            terms, "revisit", "repeated_tap", "return_loop"
        ):
            claimed.add("revisit")
        if self._matches(terms, "route_reversal"):
            claimed.add("route_reversal")
        if (rules and rules.requires_package_gate) or self._matches(terms, "package_gate"):
            claimed.add("objective_gate")
        if self._matches(terms, "four_way", "high_arity"):
            claimed.add("high_arity_switch")
        if self._matches(terms, "recoverable", "recovery", "safe_choice"):
            claimed.add("recoverable_route")
        if rules and rules.requires_unique_solution:
            claimed.add("unique_success")
        if self._matches(terms, "unique_optimal"):
            claimed.add("unique_optimal")
        return claimed

    def _detected_behaviors(self, recipe: GraphRecipe) -> set[str]:
        detected: set[str] = set()
        cycles = recipe._detected_cycles()
        if cycles:
            detected.add("cycle")
        if any(len(cycle) >= 3 for cycle in cycles):
            detected.add("ring")
        if recipe._detected_rejoins():
            detected.add("rejoin")
        if any(count > 1 for count in Counter(recipe.required_path).values()):
            detected.add("revisit")
        if self._has_route_reversal(recipe.required_path):
            detected.add("route_reversal")
        if not self._destination_reachable_without_objective(recipe):
            detected.add("objective_gate")
        if self._maximum_out_degree(recipe) >= 4:
            detected.add("high_arity_switch")
        if self._has_recoverable_branch(recipe):
            detected.add("recoverable_route")

        success_costs = self._successful_route_costs(recipe)
        if len(success_costs) == 1:
            detected.add("unique_success")
        if success_costs and success_costs.count(min(success_costs)) == 1:
            detected.add("unique_optimal")
        return detected

    def _claim_terms(self, recipe: GraphRecipe) -> set[str]:
        raw_terms = {
            recipe.family_name,
            recipe.variant_name,
            recipe.topology_class,
            recipe.primary_mechanic_tag,
            *recipe.mechanic_tags,
        }
        for key in ("topologyClass", "primaryMechanicTag", "intendedMechanic"):
            value = recipe.mechanic_metadata.get(key)
            if isinstance(value, str):
                raw_terms.add(value)
        normalized: set[str] = set()
        for term in raw_terms:
            value = term.strip().lower().replace("-", "_").replace(" ", "_")
            if not value:
                continue
            normalized.add(value)
            normalized.update(part for part in value.split("_") if part)
        return normalized

    @staticmethod
    def _matches(terms: set[str], *needles: str) -> bool:
        return any(
            term == needle or term.startswith(f"{needle}_") or term.endswith(f"_{needle}")
            for term in terms
            for needle in needles
        )

    @staticmethod
    def _has_route_reversal(path: tuple[str, ...]) -> bool:
        traversed: set[tuple[str, str]] = set()
        for edge in zip(path, path[1:]):
            if (edge[1], edge[0]) in traversed:
                return True
            traversed.add(edge)
        return False

    @staticmethod
    def _maximum_out_degree(recipe: GraphRecipe) -> int:
        counts = Counter(edge.from_node_id for edge in recipe.edges)
        return max(counts.values(), default=0)

    @staticmethod
    def _destination_reachable_without_objective(recipe: GraphRecipe) -> bool:
        outgoing: dict[str, list[str]] = {}
        for edge in recipe.edges:
            outgoing.setdefault(edge.from_node_id, []).append(edge.to_node_id)
        queue = deque(["start"])
        visited = {recipe.package_node_id}
        while queue:
            node_id = queue.popleft()
            if node_id == recipe.destination_node_id:
                return True
            if node_id in visited:
                continue
            visited.add(node_id)
            queue.extend(outgoing.get(node_id, ()))
        return False

    def _has_recoverable_branch(self, recipe: GraphRecipe) -> bool:
        route_index = {node_id: index for index, node_id in enumerate(recipe.required_path)}
        required_edges = set(zip(recipe.required_path, recipe.required_path[1:]))
        outgoing: dict[str, list[str]] = {}
        for edge in recipe.edges:
            outgoing.setdefault(edge.from_node_id, []).append(edge.to_node_id)

        for edge in recipe.edges:
            if edge.from_node_id not in route_index or (
                edge.from_node_id, edge.to_node_id
            ) in required_edges:
                continue
            origin_index = route_index[edge.from_node_id]
            queue = deque([edge.to_node_id])
            visited: set[str] = set()
            while queue:
                node_id = queue.popleft()
                if node_id in visited:
                    continue
                visited.add(node_id)
                if route_index.get(node_id, -1) > origin_index:
                    return True
                queue.extend(outgoing.get(node_id, ()))
        return False

    def _successful_route_costs(self, recipe: GraphRecipe) -> tuple[int, ...]:
        """Enumerate bounded edge-simple success routes, including one revisit loop."""

        outgoing: dict[str, list[tuple[int, str]]] = {}
        for edge_index, edge in enumerate(recipe.edges):
            outgoing.setdefault(edge.from_node_id, []).append((edge_index, edge.to_node_id))
        maximum_steps = max(len(recipe.required_path), len(recipe.nodes) + 2)
        costs: list[int] = []
        stack = [("start", False, 0, frozenset())]
        while stack:
            node_id, collected, cost, used_edges = stack.pop()
            collected = collected or node_id == recipe.package_node_id
            if node_id == recipe.destination_node_id:
                if collected:
                    costs.append(cost)
                continue
            if cost >= maximum_steps:
                continue
            for edge_index, next_id in outgoing.get(node_id, ()):
                if edge_index in used_edges:
                    continue
                stack.append((next_id, collected, cost + 1, used_edges | {edge_index}))
        return tuple(sorted(costs))

    def _ordered(self, values: set[str]) -> tuple[str, ...]:
        return tuple(value for value in self._behavior_order if value in values)
