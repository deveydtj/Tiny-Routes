from __future__ import annotations

from dataclasses import dataclass, replace

from ..models.graph_recipe import GraphRecipe, GraphRecipeEdge, GraphRecipeNode
from ..models.motif_contract import (
    MotifDependencyEffect,
    MotifEdgeStateChange,
    MotifEdgeStateChangeKind,
    MotifEffectContract,
    MotifGameplayEffect,
    MotifIncomingObjectiveState,
    MotifPreconditionContract,
    MotifStructuralEffect,
)
from ..models.motif_port import MotifPort, MotifPortType
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
    edges: tuple[tuple[str, str] | tuple[str, str, str] | tuple[str, str, str, int], ...],
    primary_path: tuple[str, ...],
    effect: str,
    *,
    difficulties: tuple[str, ...] = ALL_DIFFICULTIES,
    cycle: bool = False,
    rejoin: bool = False,
    revisit: bool = False,
    dead_end: bool = False,
    embedded_package: bool = False,
    ports: tuple[MotifPort, ...] = (),
    preconditions: MotifPreconditionContract | None = None,
    effects: MotifEffectContract | None = None,
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
            GraphRecipeEdge(
                edge[0],
                edge[1],
                edge[2] if len(edge) >= 3 else "always",
                edge[3] if len(edge) == 4 else None,
            )
            for edge in edges
        ),
        intended_decision_effect=effect,
        allowed_difficulties=difficulties,
        ports=ports,
        preconditions=preconditions,
        effects=effects,
        may_introduce_cycle=cycle,
        may_introduce_rejoin=rejoin,
        may_introduce_revisit=revisit,
        may_introduce_dead_end=dead_end,
        compatibility=MotifCompatibilityConstraints(),
        mechanic_metadata=tuple(metadata),
    ))


def _main_route_ports(entry: str = "entry", exit: str = "exit") -> tuple[MotifPort, ...]:
    return (
        MotifPort("main_entry", entry, MotifPortType.MAIN_ROUTE_ENTRY),
        MotifPort("main_exit", exit, MotifPortType.MAIN_ROUTE_EXIT),
    )


def _package_state_ports() -> tuple[MotifPort, ...]:
    return (
        *_main_route_ports(),
        MotifPort("branch_insertion", "entry", MotifPortType.BRANCH_INSERTION_POINT),
        MotifPort("return_input", "entry", MotifPortType.RETURN_PATH_INPUT),
        MotifPort("objective", "package", MotifPortType.OBJECTIVE_ATTACHMENT),
        MotifPort("state_change", "package", MotifPortType.STATE_CHANGE_ATTACHMENT),
        MotifPort("return_output", "package", MotifPortType.RETURN_PATH_OUTPUT),
    )


def _package_state_contract(
    *edge_changes: tuple[str, str, MotifEdgeStateChangeKind],
    decision_node_ids: tuple[str, ...] = ("entry",),
) -> tuple[MotifPreconditionContract, MotifEffectContract]:
    return (
        MotifPreconditionContract(
            minimum_objective_phase_index=0,
            required_incoming_objective_state=(
                MotifIncomingObjectiveState.BEFORE_ACTIVE_OBJECTIVE
            ),
            forbidden_completed_objective_roles=("active_objective",),
        ),
        MotifEffectContract(
            completed_objective_node_ids=("package",),
            edge_state_changes=tuple(
                MotifEdgeStateChange(from_node, to_node, kind, "package")
                for from_node, to_node, kind in edge_changes
            ),
            decision_node_ids=decision_node_ids,
            expected_downstream_dependency=MotifDependencyEffect.OBJECTIVE_STATE,
            introduces_cycle=True,
            introduces_revisit=True,
            minimum_layout_footprint=(3, 2),
            incompatible_effects=("secondEmbeddedObjective",),
            maximum_instances_per_composition=1,
        ),
    )


def _split_rejoin_ports() -> tuple[MotifPort, ...]:
    return (
        *_main_route_ports(),
        MotifPort("branch_insertion", "entry", MotifPortType.BRANCH_INSERTION_POINT),
        MotifPort("upper_rejoin", "upper", MotifPortType.REJOIN_INPUT),
        MotifPort("lower_rejoin", "lower", MotifPortType.REJOIN_INPUT),
    )


def _recoverable_detour_ports() -> tuple[MotifPort, ...]:
    """Expose the direct route and the nonfatal branch before they rejoin."""

    return (
        *_main_route_ports(),
        MotifPort("branch_insertion", "entry", MotifPortType.BRANCH_INSERTION_POINT),
        MotifPort("direct_rejoin", "entry", MotifPortType.REJOIN_INPUT),
        MotifPort("detour_rejoin", "detour_b", MotifPortType.REJOIN_INPUT),
        MotifPort("recovery", "detour_b", MotifPortType.RECOVERY_EXIT),
    )


def _delayed_consequence_ports() -> tuple[MotifPort, ...]:
    """Expose an early commitment and its later success/failure decision."""

    return (
        *_main_route_ports(),
        MotifPort("early_branch", "entry", MotifPortType.BRANCH_INSERTION_POINT),
        MotifPort(
            "downstream_consequence",
            "consequence",
            MotifPortType.BRANCH_INSERTION_POINT,
        ),
        MotifPort("safe_rejoin", "safe", MotifPortType.REJOIN_INPUT),
        MotifPort("commit_rejoin", "consequence", MotifPortType.REJOIN_INPUT),
        MotifPort("failure", "failure", MotifPortType.FAILURE_EXIT),
    )


def _objective_gate_ports() -> tuple[MotifPort, ...]:
    return (
        *_main_route_ports(),
        MotifPort("branch_insertion", "entry", MotifPortType.BRANCH_INSERTION_POINT),
        MotifPort("objective_rejoin", "package", MotifPortType.REJOIN_INPUT),
        MotifPort("bypass_rejoin", "bypass", MotifPortType.REJOIN_INPUT),
        MotifPort("objective", "package", MotifPortType.OBJECTIVE_ATTACHMENT),
        MotifPort("state_change", "package", MotifPortType.STATE_CHANGE_ATTACHMENT),
        MotifPort("failure", "failure", MotifPortType.FAILURE_EXIT),
    )


def _objective_state_return_ports() -> tuple[MotifPort, ...]:
    """Typed ports shared by objective-driven outbound/return route changes."""

    return (
        *_main_route_ports(),
        MotifPort("branch_insertion", "entry", MotifPortType.BRANCH_INSERTION_POINT),
        MotifPort("return_input", "entry", MotifPortType.RETURN_PATH_INPUT),
        MotifPort("return_output", "package", MotifPortType.RETURN_PATH_OUTPUT),
        MotifPort("objective", "package", MotifPortType.OBJECTIVE_ATTACHMENT),
        MotifPort("state_change", "package", MotifPortType.STATE_CHANGE_ATTACHMENT),
    )


def _objective_state_return_contract(
    *edge_changes: tuple[str, str, MotifEdgeStateChangeKind],
    gameplay_effect: MotifGameplayEffect,
    minimum_layout_footprint: tuple[int, int],
) -> tuple[MotifPreconditionContract, MotifEffectContract]:
    """Build the explicit contract for one objective-state return motif."""

    return (
        MotifPreconditionContract(
            minimum_objective_phase_index=0,
            required_incoming_objective_state=(
                MotifIncomingObjectiveState.BEFORE_ACTIVE_OBJECTIVE
            ),
            forbidden_completed_objective_roles=("active_objective",),
        ),
        MotifEffectContract(
            completed_objective_node_ids=("package",),
            edge_state_changes=tuple(
                MotifEdgeStateChange(from_node, to_node, kind, "package")
                for from_node, to_node, kind in edge_changes
            ),
            decision_node_ids=("entry",),
            structural_effects=(
                MotifStructuralEffect.SEGMENT,
                MotifStructuralEffect.SPLIT,
                MotifStructuralEffect.RING,
                MotifStructuralEffect.RETURN_CORRIDOR,
                MotifStructuralEffect.CROSS_PHASE_CONNECTOR,
            ),
            gameplay_effects=(gameplay_effect,),
            expected_downstream_dependency=MotifDependencyEffect.OBJECTIVE_STATE,
            introduces_cycle=True,
            introduces_revisit=True,
            minimum_layout_footprint=minimum_layout_footprint,
            incompatible_effects=("secondEmbeddedObjective",),
            maximum_instances_per_composition=1,
        ),
    )


def _hub_revisit_ports() -> tuple[MotifPort, ...]:
    """Expose both outbound choices and the cross-phase return at a hub."""

    return (
        *_main_route_ports(),
        MotifPort("branch_insertion", "entry", MotifPortType.BRANCH_INSERTION_POINT),
        MotifPort("outbound_rejoin", "outbound", MotifPortType.REJOIN_INPUT),
        MotifPort("detour_rejoin", "detour", MotifPortType.REJOIN_INPUT),
        MotifPort("return_input", "entry", MotifPortType.RETURN_PATH_INPUT),
        MotifPort("return_output", "package", MotifPortType.RETURN_PATH_OUTPUT),
        MotifPort("objective", "package", MotifPortType.OBJECTIVE_ATTACHMENT),
        MotifPort("state_change", "package", MotifPortType.STATE_CHANGE_ATTACHMENT),
        MotifPort("recovery", "detour", MotifPortType.RECOVERY_EXIT),
    )


def _stateful_ring_ports() -> tuple[MotifPort, ...]:
    """Expose the ring, objective transition, and phase-specific failure exit."""

    return (
        *_main_route_ports(),
        MotifPort("branch_insertion", "entry", MotifPortType.BRANCH_INSERTION_POINT),
        MotifPort("return_input", "entry", MotifPortType.RETURN_PATH_INPUT),
        MotifPort("return_output", "ring_b", MotifPortType.RETURN_PATH_OUTPUT),
        MotifPort("objective", "package", MotifPortType.OBJECTIVE_ATTACHMENT),
        MotifPort("state_change", "package", MotifPortType.STATE_CHANGE_ATTACHMENT),
        MotifPort("failure", "failure", MotifPortType.FAILURE_EXIT),
    )


def _stateful_cycle_contract(
    *edge_changes: tuple[str, str, MotifEdgeStateChangeKind],
    structural_effects: tuple[MotifStructuralEffect, ...],
    gameplay_effects: tuple[MotifGameplayEffect, ...],
    introduces_rejoin: bool = False,
    introduces_failure_exit: bool = False,
    introduces_recovery_exit: bool = False,
) -> tuple[MotifPreconditionContract, MotifEffectContract]:
    """Build an explicit objective-state contract for a revisited cycle."""

    return (
        MotifPreconditionContract(
            minimum_objective_phase_index=0,
            required_incoming_objective_state=(
                MotifIncomingObjectiveState.BEFORE_ACTIVE_OBJECTIVE
            ),
            forbidden_completed_objective_roles=("active_objective",),
        ),
        MotifEffectContract(
            completed_objective_node_ids=("package",),
            edge_state_changes=tuple(
                MotifEdgeStateChange(from_node, to_node, kind, "package")
                for from_node, to_node, kind in edge_changes
            ),
            decision_node_ids=("entry",),
            structural_effects=structural_effects,
            gameplay_effects=gameplay_effects,
            expected_downstream_dependency=MotifDependencyEffect.OBJECTIVE_STATE,
            introduces_cycle=True,
            introduces_revisit=True,
            introduces_rejoin=introduces_rejoin,
            introduces_failure_exit=introduces_failure_exit,
            introduces_recovery_exit=introduces_recovery_exit,
            minimum_layout_footprint=(6, 3),
            incompatible_effects=("secondEmbeddedObjective",),
            maximum_instances_per_composition=1,
        ),
    )


def _complete_typed_contract(factory: SeedMotif) -> SeedMotif:
    """Migrate a seed fixture to the V3 contract without changing its graph."""

    motif = factory.build()
    if motif.ports and motif.preconditions is not None and motif.effects is not None:
        return factory

    outgoing: dict[str, list[GraphRecipeEdge]] = {node.id: [] for node in motif.nodes}
    incoming: dict[str, list[GraphRecipeEdge]] = {node.id: [] for node in motif.nodes}
    for edge in motif.edges:
        outgoing[edge.from_node_id].append(edge)
        incoming[edge.to_node_id].append(edge)

    ports: list[MotifPort] = list(_main_route_ports(motif.entry_connector, motif.exit_connectors[0]))
    for node_id, edges in outgoing.items():
        if len(edges) >= 2:
            ports.append(MotifPort(f"branch_{node_id}", node_id, MotifPortType.BRANCH_INSERTION_POINT))
    for node_id, edges in incoming.items():
        if len(edges) >= 2:
            for index, edge in enumerate(edges):
                ports.append(MotifPort(
                    f"rejoin_{node_id}_{index}", edge.from_node_id, MotifPortType.REJOIN_INPUT
                ))
    objective_nodes = tuple(
        node.id for node in motif.nodes
        if node.role in {"package", "pickup", "checkpoint", "delivery", "objective"}
    )
    for node_id in objective_nodes:
        ports.append(MotifPort(f"objective_{node_id}", node_id, MotifPortType.OBJECTIVE_ATTACHMENT))
    for node in motif.nodes:
        if node.role in {"dead_end", "failure"}:
            ports.append(MotifPort(f"failure_{node.id}", node.id, MotifPortType.FAILURE_EXIT))
        if node.role == "recovery":
            ports.append(MotifPort(f"recovery_{node.id}", node.id, MotifPortType.RECOVERY_EXIT))
    if motif.may_introduce_cycle or motif.may_introduce_revisit:
        ports.extend((
            MotifPort("return_input", motif.entry_connector, MotifPortType.RETURN_PATH_INPUT),
            MotifPort("return_output", motif.entry_connector, MotifPortType.RETURN_PATH_OUTPUT),
        ))

    changes: list[MotifEdgeStateChange] = []
    trigger = objective_nodes[0] if objective_nodes else None
    if trigger is not None:
        for edge in motif.edges:
            if edge.availability == "afterPackage":
                changes.append(MotifEdgeStateChange(
                    edge.from_node_id, edge.to_node_id, MotifEdgeStateChangeKind.OPEN, trigger
                ))
            elif edge.availability == "beforePackage":
                changes.append(MotifEdgeStateChange(
                    edge.from_node_id, edge.to_node_id, MotifEdgeStateChangeKind.CLOSE, trigger
                ))
            if edge.usage_limit == 1:
                changes.append(MotifEdgeStateChange(
                    edge.from_node_id, edge.to_node_id, MotifEdgeStateChangeKind.CONSUME
                ))
        if changes:
            ports.append(MotifPort("state_change", trigger, MotifPortType.STATE_CHANGE_ATTACHMENT))

    structural: list[MotifStructuralEffect] = [MotifStructuralEffect.SEGMENT]
    if any(len(edges) >= 2 for edges in outgoing.values()):
        structural.append(MotifStructuralEffect.SPLIT)
    if any(len(edges) >= 2 for edges in incoming.values()):
        structural.append(MotifStructuralEffect.REJOIN)
    if any(len(edges) >= 3 for edges in outgoing.values()):
        structural.append(MotifStructuralEffect.HUB)
    if motif.may_introduce_cycle:
        structural.append(MotifStructuralEffect.RETURN_CORRIDOR)
        if len(motif.nodes) >= 4:
            structural.append(MotifStructuralEffect.RING)
    if changes:
        structural.append(MotifStructuralEffect.CROSS_PHASE_CONNECTOR)
    if MotifStructuralEffect.SPLIT in structural and MotifStructuralEffect.REJOIN in structural:
        structural.append(MotifStructuralEffect.LANE_EXPANSION)

    gameplay_by_id = {
        "recoverable_detour": (MotifGameplayEffect.ALTERNATE_SUCCESSFUL_DETOUR,),
        "return_loop": (MotifGameplayEffect.RECOVERABLE_LOOP,),
        "revisited_switch": (MotifGameplayEffect.REQUIRED_HUB_REVISIT,),
        "ring_route": (MotifGameplayEffect.RECOVERABLE_LOOP,),
        "three_way_hub": (MotifGameplayEffect.DELAYED_CONSEQUENCE,),
        "four_way_hub": (MotifGameplayEffect.DELAYED_CONSEQUENCE,),
        "binary_delayed_consequence": (MotifGameplayEffect.DELAYED_CONSEQUENCE,),
        "phase_dependent_ring_exits": (
            MotifGameplayEffect.STATE_DEPENDENT_BRANCH,
            MotifGameplayEffect.REQUIRED_HUB_REVISIT,
        ),
        "destination_before_objectives_decoy": (MotifGameplayEffect.DESTINATION_DECOY,),
        "one_use_objective_connector": (
            MotifGameplayEffect.ONE_USE_CONNECTOR,
            MotifGameplayEffect.CLOSE_BEHIND_ROUTE,
        ),
        "objective_state_revisited_hub": (
            MotifGameplayEffect.REQUIRED_HUB_REVISIT,
            MotifGameplayEffect.STATE_DEPENDENT_BRANCH,
        ),
        "three_phase_relay": (MotifGameplayEffect.DELAYED_CONSEQUENCE,),
        "parallel_unique_optimum": (MotifGameplayEffect.ALTERNATE_SUCCESSFUL_DETOUR,),
        "objective_unlocked_shortcut": (MotifGameplayEffect.UNLOCK_SHORTCUT,),
        "objective_closed_return_road": (MotifGameplayEffect.CLOSE_BEHIND_ROUTE,),
    }
    gameplay = gameplay_by_id.get(motif.motif_id, ())
    decision_exclusions = {"split_and_rejoin", "straight_segment", "return_route_changes_after_package"}
    decision_nodes = () if motif.motif_id in decision_exclusions else tuple(
        node_id for node_id, edges in outgoing.items() if len(edges) >= 2
    )
    dependency = MotifDependencyEffect.NONE
    if changes:
        dependency = MotifDependencyEffect.OBJECTIVE_STATE
    elif motif.may_introduce_revisit and decision_nodes:
        dependency = MotifDependencyEffect.REVISIT
    elif MotifGameplayEffect.DELAYED_CONSEQUENCE in gameplay:
        dependency = MotifDependencyEffect.EARLIER_CHOICE

    introduces_recovery = motif.motif_id in {
        "recoverable_detour", "return_loop", "ring_route", "parallel_unique_optimum"
    } or any(node.role == "recovery" for node in motif.nodes)
    if introduces_recovery and not any(
        port.port_type is MotifPortType.RECOVERY_EXIT for port in ports
    ):
        ports.append(MotifPort("recovery_exit", motif.exit_connectors[0], MotifPortType.RECOVERY_EXIT))

    preconditions = MotifPreconditionContract(
        minimum_objective_phase_index=0,
        required_incoming_objective_state=(
            MotifIncomingObjectiveState.BEFORE_ACTIVE_OBJECTIVE
            if changes else MotifIncomingObjectiveState.ANY
        ),
        forbidden_completed_objective_roles=("active_objective",) if changes else (),
    )
    effects = MotifEffectContract(
        completed_objective_node_ids=objective_nodes,
        edge_state_changes=tuple(changes),
        decision_node_ids=decision_nodes,
        structural_effects=tuple(dict.fromkeys(structural)),
        gameplay_effects=gameplay,
        expected_downstream_dependency=dependency,
        introduces_cycle=motif.may_introduce_cycle,
        introduces_revisit=motif.may_introduce_revisit,
        introduces_rejoin=motif.may_introduce_rejoin,
        introduces_failure_exit=motif.may_introduce_dead_end,
        introduces_recovery_exit=introduces_recovery,
        minimum_layout_footprint=(
            max(2, min(6, len(motif.nodes))),
            2 if any(len(edges) >= 2 for edges in outgoing.values()) else 1,
        ),
        incompatible_effects=("secondEmbeddedObjective",) if changes else (),
        maximum_instances_per_composition=1 if changes else 2,
    )
    return SeedMotif(replace(
        motif,
        ports=tuple(ports),
        preconditions=preconditions,
        effects=effects,
    ))


def seed_motif_factories() -> tuple[BaseMotif, ...]:
    advanced = ("medium", "hard", "expert")
    hard = ("hard", "expert")
    opens_preconditions, opens_effects = _package_state_contract(
        ("entry", "exit", MotifEdgeStateChangeKind.OPEN)
    )
    closes_preconditions, closes_effects = _package_state_contract(
        ("entry", "shortcut", MotifEdgeStateChangeKind.CLOSE)
    )
    changes_preconditions, changes_effects = _package_state_contract(
        ("entry", "outbound", MotifEdgeStateChangeKind.CLOSE),
        ("entry", "exit", MotifEdgeStateChangeKind.OPEN),
        decision_node_ids=(),
    )
    revisited_preconditions, revisited_effects = _package_state_contract(
        ("entry", "outbound", MotifEdgeStateChangeKind.CLOSE),
        ("entry", "exit", MotifEdgeStateChangeKind.OPEN),
    )
    split_rejoin_effects = MotifEffectContract(
        structural_effects=(MotifStructuralEffect.SPLIT, MotifStructuralEffect.REJOIN),
        introduces_rejoin=True,
        minimum_layout_footprint=(3, 2),
    )
    recoverable_detour_effects = MotifEffectContract(
        decision_node_ids=("entry",),
        structural_effects=(
            MotifStructuralEffect.SEGMENT,
            MotifStructuralEffect.SPLIT,
            MotifStructuralEffect.REJOIN,
            MotifStructuralEffect.LANE_EXPANSION,
        ),
        gameplay_effects=(MotifGameplayEffect.ALTERNATE_SUCCESSFUL_DETOUR,),
        expected_downstream_dependency=MotifDependencyEffect.EARLIER_CHOICE,
        introduces_rejoin=True,
        introduces_recovery_exit=True,
        minimum_layout_footprint=(4, 2),
        maximum_instances_per_composition=2,
    )
    delayed_consequence_effects = MotifEffectContract(
        decision_node_ids=("entry", "consequence"),
        structural_effects=(
            MotifStructuralEffect.SEGMENT,
            MotifStructuralEffect.SPLIT,
            MotifStructuralEffect.REJOIN,
            MotifStructuralEffect.LANE_EXPANSION,
        ),
        gameplay_effects=(MotifGameplayEffect.DELAYED_CONSEQUENCE,),
        expected_downstream_dependency=MotifDependencyEffect.EARLIER_CHOICE,
        introduces_rejoin=True,
        introduces_failure_exit=True,
        minimum_layout_footprint=(6, 2),
        maximum_instances_per_composition=2,
    )
    objective_gate_preconditions = MotifPreconditionContract(
        minimum_objective_phase_index=0,
        required_incoming_objective_state=(
            MotifIncomingObjectiveState.BEFORE_ACTIVE_OBJECTIVE
        ),
        forbidden_completed_objective_roles=("active_objective",),
    )
    objective_gate_effects = MotifEffectContract(
        completed_objective_node_ids=("package",),
        edge_state_changes=(
            MotifEdgeStateChange(
                "gate", "exit", MotifEdgeStateChangeKind.OPEN, "package"
            ),
            MotifEdgeStateChange(
                "gate", "failure", MotifEdgeStateChangeKind.CLOSE, "package"
            ),
        ),
        decision_node_ids=("entry",),
        structural_effects=(MotifStructuralEffect.SPLIT, MotifStructuralEffect.REJOIN),
        gameplay_effects=(
            MotifGameplayEffect.OBJECTIVE_GATE,
            MotifGameplayEffect.STATE_DEPENDENT_BRANCH,
            MotifGameplayEffect.DELAYED_CONSEQUENCE,
        ),
        expected_downstream_dependency=MotifDependencyEffect.OBJECTIVE_STATE,
        introduces_rejoin=True,
        introduces_failure_exit=True,
        minimum_layout_footprint=(4, 2),
        incompatible_effects=("secondEmbeddedObjective",),
        maximum_instances_per_composition=1,
    )
    unlock_shortcut_preconditions, unlock_shortcut_effects = _objective_state_return_contract(
        ("entry", "shortcut", MotifEdgeStateChangeKind.OPEN),
        gameplay_effect=MotifGameplayEffect.UNLOCK_SHORTCUT,
        minimum_layout_footprint=(6, 2),
    )
    close_behind_preconditions, close_behind_effects = _objective_state_return_contract(
        ("entry", "return_road", MotifEdgeStateChangeKind.CLOSE),
        ("entry", "exit", MotifEdgeStateChangeKind.OPEN),
        gameplay_effect=MotifGameplayEffect.CLOSE_BEHIND_ROUTE,
        minimum_layout_footprint=(5, 2),
    )
    hub_revisit_preconditions, hub_revisit_effects = _stateful_cycle_contract(
        ("entry", "outbound", MotifEdgeStateChangeKind.CLOSE),
        ("entry", "detour", MotifEdgeStateChangeKind.CLOSE),
        ("entry", "exit", MotifEdgeStateChangeKind.OPEN),
        structural_effects=(
            MotifStructuralEffect.SEGMENT,
            MotifStructuralEffect.SPLIT,
            MotifStructuralEffect.REJOIN,
            MotifStructuralEffect.HUB,
            MotifStructuralEffect.RING,
            MotifStructuralEffect.RETURN_CORRIDOR,
            MotifStructuralEffect.CROSS_PHASE_CONNECTOR,
            MotifStructuralEffect.LANE_EXPANSION,
        ),
        gameplay_effects=(
            MotifGameplayEffect.REQUIRED_HUB_REVISIT,
            MotifGameplayEffect.STATE_DEPENDENT_BRANCH,
        ),
        introduces_rejoin=True,
        introduces_recovery_exit=True,
    )
    stateful_ring_preconditions, stateful_ring_effects = _stateful_cycle_contract(
        ("entry", "ring_a", MotifEdgeStateChangeKind.CLOSE),
        ("entry", "failure", MotifEdgeStateChangeKind.CLOSE),
        ("entry", "exit", MotifEdgeStateChangeKind.OPEN),
        structural_effects=(
            MotifStructuralEffect.SEGMENT,
            MotifStructuralEffect.SPLIT,
            MotifStructuralEffect.HUB,
            MotifStructuralEffect.RING,
            MotifStructuralEffect.RETURN_CORRIDOR,
            MotifStructuralEffect.CROSS_PHASE_CONNECTOR,
        ),
        gameplay_effects=(
            MotifGameplayEffect.STATE_DEPENDENT_BRANCH,
            MotifGameplayEffect.REQUIRED_HUB_REVISIT,
        ),
        introduces_failure_exit=True,
    )
    motifs = (
        _motif("straight_segment", (("entry", "route"), ("exit", "route")), (("entry", "exit"),),
               ("entry", "exit"), "Adds readable travel spacing.", ports=_main_route_ports()),
        _motif("single_binary_choice", (("entry", "switch"), ("exit", "route"), ("decoy", "dead_end")),
               (("entry", "exit"), ("entry", "decoy")), ("entry", "exit"), "One binary routing decision.", dead_end=True),
        _motif("dead_end_decoy", (("entry", "switch"), ("exit", "route"), ("dead_end", "dead_end")),
               (("entry", "dead_end"), ("entry", "exit")), ("entry", "exit"), "A visibly punishable wrong branch.", dead_end=True),
        _motif(
            "recoverable_detour",
            (("entry", "switch"), ("detour_a", "route"), ("detour_b", "route"), ("exit", "route")),
            (("entry", "exit"), ("entry", "detour_a"), ("detour_a", "detour_b"), ("detour_b", "exit")),
            ("entry", "detour_a", "detour_b", "exit"),
            "A longer choice that safely rejoins.",
            rejoin=True,
            ports=_recoverable_detour_ports(),
            preconditions=MotifPreconditionContract(),
            effects=recoverable_detour_effects,
        ),
        _motif("split_and_rejoin", (("entry", "switch"), ("upper", "route"), ("lower", "route"), ("exit", "route")),
               (("entry", "upper"), ("entry", "lower"), ("upper", "exit"), ("lower", "exit")),
               ("entry", "upper", "exit"),
               "Structural split/rejoin lanes for later gameplay-effect insertion.",
               difficulties=advanced, rejoin=True, ports=_split_rejoin_ports(),
               preconditions=MotifPreconditionContract(), effects=split_rejoin_effects),
        _motif(
            "objective_gate",
            (
                ("entry", "switch"),
                ("package", "package"),
                ("bypass", "route"),
                ("gate", "switch"),
                ("exit", "route"),
                ("failure", "dead_end"),
            ),
            (
                ("entry", "package"),
                ("entry", "bypass"),
                ("package", "gate"),
                ("bypass", "gate"),
                ("gate", "exit", "afterPackage"),
                ("gate", "failure", "beforePackage"),
            ),
            ("entry", "package", "gate", "exit"),
            "The earlier branch choice determines objective state at a downstream gate.",
            difficulties=advanced,
            rejoin=True,
            dead_end=True,
            embedded_package=True,
            ports=_objective_gate_ports(),
            preconditions=objective_gate_preconditions,
            effects=objective_gate_effects,
        ),
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
               ("entry", "exit"), "A ring offers a looping alternate route.",
               difficulties=hard, cycle=True, revisit=True),
        _motif(
            "three_way_hub",
            (("entry", "switch"), ("exit", "route"), ("failure", "dead_end"), ("detour", "recovery")),
            (("entry", "failure"), ("entry", "exit"), ("entry", "detour"), ("detour", "exit")),
            ("entry", "exit"),
            "A three-way hub with success, failure, and recoverable-detour outcomes.",
            difficulties=advanced, rejoin=True, dead_end=True,
        ),
        _motif(
            "four_way_hub",
            (
                ("entry", "switch"), ("exit", "route"), ("failure", "dead_end"),
                ("detour", "recovery"), ("package", "package"),
            ),
            (
                ("entry", "failure"), ("entry", "detour"), ("entry", "exit"),
                ("entry", "package"), ("detour", "exit"), ("package", "exit"),
            ),
            ("entry", "package", "exit"),
            "A four-way hub with optimal, objective, recoverable, and failure outcomes.",
            difficulties=("expert",), rejoin=True, dead_end=True, embedded_package=True,
        ),
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
            ports=_package_state_ports(),
            preconditions=opens_preconditions,
            effects=opens_effects,
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
            ports=_package_state_ports(),
            preconditions=closes_preconditions,
            effects=closes_effects,
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
            ports=_package_state_ports(),
            preconditions=changes_preconditions,
            effects=changes_effects,
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
            ports=(
                *_package_state_ports(),
                MotifPort("failure", "decoy", MotifPortType.FAILURE_EXIT),
            ),
            preconditions=revisited_preconditions,
            effects=replace(revisited_effects, introduces_failure_exit=True),
        ),
        _motif(
            "binary_delayed_consequence",
            (
                ("entry", "switch"), ("commit", "route"), ("safe", "route"),
                ("consequence", "switch"), ("exit", "route"), ("failure", "dead_end"),
            ),
            (
                ("entry", "commit"), ("entry", "safe"), ("commit", "consequence"),
                ("safe", "exit"), ("consequence", "exit"), ("consequence", "failure"),
            ),
            ("entry", "commit", "consequence", "exit"),
            "An early commitment changes the later consequence reached by the player.",
            difficulties=advanced, rejoin=True, dead_end=True,
            ports=_delayed_consequence_ports(),
            preconditions=MotifPreconditionContract(),
            effects=delayed_consequence_effects,
        ),
        _motif(
            "phase_dependent_ring_exits",
            (
                ("entry", "switch"), ("ring_a", "route"), ("package", "package"),
                ("ring_b", "route"), ("exit", "route"), ("failure", "dead_end"),
            ),
            (
                ("entry", "ring_a", "beforePackage"), ("entry", "exit", "afterPackage"),
                ("entry", "failure", "beforePackage"), ("ring_a", "package"),
                ("package", "ring_b"), ("ring_b", "entry"),
            ),
            ("entry", "ring_a", "package", "ring_b", "entry", "exit"),
            "The useful ring exit changes after the objective is collected.",
            difficulties=hard, cycle=True, revisit=True, dead_end=True, embedded_package=True,
            ports=_stateful_ring_ports(),
            preconditions=stateful_ring_preconditions,
            effects=stateful_ring_effects,
        ),
        _motif(
            "destination_before_objectives_decoy",
            (
                ("entry", "switch"), ("destination_decoy", "destination"),
                ("package", "package"), ("return", "route"), ("exit", "route"),
            ),
            (
                ("entry", "destination_decoy", "beforePackage"),
                ("entry", "package"), ("package", "return"), ("return", "entry"),
                ("entry", "exit", "afterPackage"),
            ),
            ("entry", "package", "return", "entry", "exit"),
            "A visible terminal is a premature decoy until prior objectives are complete.",
            difficulties=advanced, cycle=True, revisit=True, embedded_package=True,
        ),
        _motif(
            "one_use_objective_connector",
            (
                ("entry", "switch"), ("connector", "route"), ("package", "package"),
                ("return", "route"), ("exit", "route"),
            ),
            (
                ("entry", "connector"), ("connector", "package", "always", 1),
                ("package", "return"), ("return", "entry"),
                ("entry", "exit", "afterPackage"),
            ),
            ("entry", "connector", "package", "return", "entry", "exit"),
            "The objective connector closes after its single useful phase.",
            difficulties=advanced, cycle=True, revisit=True, embedded_package=True,
        ),
        _motif(
            "objective_state_revisited_hub",
            (
                ("entry", "switch"), ("outbound", "route"), ("package", "package"),
                ("return", "route"), ("exit", "route"), ("detour", "recovery"),
            ),
            (
                ("entry", "outbound", "beforePackage"), ("entry", "detour", "beforePackage"),
                ("outbound", "package"), ("detour", "package"), ("package", "return"),
                ("return", "entry"), ("entry", "exit", "afterPackage"),
            ),
            ("entry", "outbound", "package", "return", "entry", "exit"),
            "A three-way hub is revisited with a newly required exit.",
            difficulties=hard, cycle=True, rejoin=True, revisit=True, embedded_package=True,
            ports=_hub_revisit_ports(),
            preconditions=hub_revisit_preconditions,
            effects=hub_revisit_effects,
        ),
        _motif(
            "three_phase_relay",
            (
                ("entry", "route"), ("pickup", "pickup"), ("relay", "switch"),
                ("checkpoint", "checkpoint"), ("return", "route"),
                ("delivery", "delivery"), ("exit", "route"),
            ),
            (
                ("entry", "pickup"), ("pickup", "relay"), ("relay", "checkpoint"),
                ("relay", "delivery"), ("checkpoint", "return"), ("return", "relay"),
                ("delivery", "exit"),
            ),
            ("entry", "pickup", "relay", "checkpoint", "return", "relay", "delivery", "exit"),
            "Three ordered objectives form a relay through a revisited decision.",
            difficulties=("expert",), cycle=True, rejoin=True, revisit=True,
        ),
        _motif(
            "parallel_unique_optimum",
            (
                ("entry", "switch"), ("fast", "route"), ("slow_a", "route"),
                ("slow_b", "recovery"), ("exit", "route"),
            ),
            (
                ("entry", "fast"), ("fast", "exit"), ("entry", "slow_a"),
                ("slow_a", "slow_b"), ("slow_b", "exit"),
            ),
            ("entry", "fast", "exit"),
            "Two successful parallel routes have unequal proven edge cost.",
            difficulties=advanced, rejoin=True,
        ),
        _motif(
            "objective_unlocked_shortcut",
            (
                ("entry", "switch"), ("outbound", "route"), ("package", "package"),
                ("return", "route"), ("shortcut", "route"), ("exit", "route"),
            ),
            (
                ("entry", "outbound"), ("outbound", "package"), ("package", "return"),
                ("return", "entry"), ("entry", "shortcut", "afterPackage"),
                ("shortcut", "exit"),
            ),
            ("entry", "outbound", "package", "return", "entry", "shortcut", "exit"),
            "Completing the objective unlocks a shorter return route.",
            difficulties=advanced, cycle=True, revisit=True, embedded_package=True,
            ports=_objective_state_return_ports(),
            preconditions=unlock_shortcut_preconditions,
            effects=unlock_shortcut_effects,
        ),
        _motif(
            "objective_closed_return_road",
            (
                ("entry", "switch"), ("return_road", "route"), ("package", "package"),
                ("loop", "route"), ("exit", "route"),
            ),
            (
                ("entry", "return_road", "beforePackage"), ("return_road", "package"),
                ("package", "loop"), ("loop", "entry"), ("entry", "exit", "afterPackage"),
            ),
            ("entry", "return_road", "package", "loop", "entry", "exit"),
            "The outbound return road closes behind the completed objective.",
            difficulties=advanced, cycle=True, revisit=True, embedded_package=True,
            ports=_objective_state_return_ports(),
            preconditions=close_behind_preconditions,
            effects=close_behind_effects,
        ),
    )
    return tuple(_complete_typed_contract(factory) for factory in motifs)


def default_motif_registry() -> MotifRegistry:
    return MotifRegistry(seed_motif_factories())
