from app.models.motif_contract import (
    MotifDependencyEffect,
    MotifEdgeStateChangeKind,
    MotifGameplayEffect,
    MotifIncomingObjectiveState,
    MotifStructuralEffect,
)
from app.models.motif_port import MotifPortType
from app.motifs.seed_motifs import default_motif_registry, seed_motif_factories


EXPECTED = {
    "straight_segment", "single_binary_choice", "dead_end_decoy", "recoverable_detour",
    "split_and_rejoin", "objective_gate", "package_branch", "return_loop", "revisited_switch", "ring_route",
    "three_way_hub", "four_way_hub",
    "road_opens_after_package", "shortcut_closes_after_package",
    "return_route_changes_after_package", "package_state_revisited_switch",
    "binary_delayed_consequence", "phase_dependent_ring_exits",
    "destination_before_objectives_decoy", "one_use_objective_connector",
    "objective_state_revisited_hub", "three_phase_relay",
    "parallel_unique_optimum", "objective_unlocked_shortcut",
    "objective_closed_return_road",
}

PACKAGE_STATE_MOTIFS = {
    "road_opens_after_package",
    "shortcut_closes_after_package",
    "return_route_changes_after_package",
    "package_state_revisited_switch",
}


def test_split_and_rejoin_is_a_typed_structural_motif() -> None:
    motif = default_motif_registry().get("split_and_rejoin").build()

    assert motif.validate() == ()
    assert {port.port_type for port in motif.ports} == {
        MotifPortType.MAIN_ROUTE_ENTRY,
        MotifPortType.MAIN_ROUTE_EXIT,
        MotifPortType.BRANCH_INSERTION_POINT,
        MotifPortType.REJOIN_INPUT,
    }
    assert motif.effects is not None
    assert motif.effects.structural_effects == (
        MotifStructuralEffect.SPLIT,
        MotifStructuralEffect.REJOIN,
    )
    assert motif.effects.gameplay_effects == ()
    assert motif.effects.decision_node_ids == ()
    assert motif.effects.introduces_rejoin is True


def test_objective_gate_has_stateful_gameplay_contract_and_real_gate_edges() -> None:
    motif = default_motif_registry().get("objective_gate").build()

    assert motif.validate() == ()
    assert motif.preconditions is not None
    assert motif.effects is not None
    assert motif.effects.completed_objective_node_ids == ("package",)
    assert motif.effects.expected_downstream_dependency is MotifDependencyEffect.OBJECTIVE_STATE
    assert motif.effects.structural_effects == (
        MotifStructuralEffect.SPLIT,
        MotifStructuralEffect.REJOIN,
    )
    assert motif.effects.gameplay_effects == (
        MotifGameplayEffect.OBJECTIVE_GATE,
        MotifGameplayEffect.STATE_DEPENDENT_BRANCH,
        MotifGameplayEffect.DELAYED_CONSEQUENCE,
    )
    assert {change.kind for change in motif.effects.edge_state_changes} == {
        MotifEdgeStateChangeKind.OPEN,
        MotifEdgeStateChangeKind.CLOSE,
    }
    assert {
        (edge.from_node_id, edge.to_node_id, edge.availability)
        for edge in motif.edges
        if edge.from_node_id == "gate"
    } == {
        ("gate", "exit", "afterPackage"),
        ("gate", "failure", "beforePackage"),
    }
    assert {port.port_type for port in motif.ports}.issuperset({
        MotifPortType.OBJECTIVE_ATTACHMENT,
        MotifPortType.STATE_CHANGE_ATTACHMENT,
        MotifPortType.FAILURE_EXIT,
    })


def test_unlock_shortcut_motif_opens_a_real_post_objective_route() -> None:
    motif = default_motif_registry().get("objective_unlocked_shortcut").build()

    assert motif.validate() == ()
    assert motif.preconditions is not None
    assert motif.effects is not None
    assert motif.preconditions.required_incoming_objective_state is (
        MotifIncomingObjectiveState.BEFORE_ACTIVE_OBJECTIVE
    )
    assert motif.effects.completed_objective_node_ids == ("package",)
    assert len(motif.effects.edge_state_changes) == 1
    change = motif.effects.edge_state_changes[0]
    assert (change.from_node_id, change.to_node_id, change.kind) == (
        "entry", "shortcut", MotifEdgeStateChangeKind.OPEN,
    )
    assert motif.effects.gameplay_effects == (MotifGameplayEffect.UNLOCK_SHORTCUT,)
    assert motif.effects.expected_downstream_dependency is MotifDependencyEffect.OBJECTIVE_STATE
    assert {
        (edge.from_node_id, edge.to_node_id, edge.availability)
        for edge in motif.edges
        if edge.from_node_id == "entry"
    } == {
        ("entry", "outbound", "always"),
        ("entry", "shortcut", "afterPackage"),
    }
    assert {port.port_type for port in motif.ports}.issuperset({
        MotifPortType.BRANCH_INSERTION_POINT,
        MotifPortType.OBJECTIVE_ATTACHMENT,
        MotifPortType.STATE_CHANGE_ATTACHMENT,
        MotifPortType.RETURN_PATH_INPUT,
        MotifPortType.RETURN_PATH_OUTPUT,
    })


def test_close_behind_motif_closes_outbound_road_and_opens_return_exit() -> None:
    motif = default_motif_registry().get("objective_closed_return_road").build()

    assert motif.validate() == ()
    assert motif.preconditions is not None
    assert motif.effects is not None
    assert motif.preconditions.required_incoming_objective_state is (
        MotifIncomingObjectiveState.BEFORE_ACTIVE_OBJECTIVE
    )
    assert motif.effects.completed_objective_node_ids == ("package",)
    assert {
        (change.from_node_id, change.to_node_id, change.kind)
        for change in motif.effects.edge_state_changes
    } == {
        ("entry", "return_road", MotifEdgeStateChangeKind.CLOSE),
        ("entry", "exit", MotifEdgeStateChangeKind.OPEN),
    }
    assert motif.effects.gameplay_effects == (MotifGameplayEffect.CLOSE_BEHIND_ROUTE,)
    assert motif.effects.expected_downstream_dependency is MotifDependencyEffect.OBJECTIVE_STATE
    assert {
        (edge.from_node_id, edge.to_node_id, edge.availability)
        for edge in motif.edges
        if edge.from_node_id == "entry"
    } == {
        ("entry", "return_road", "beforePackage"),
        ("entry", "exit", "afterPackage"),
    }
    assert motif.effects.introduces_cycle is True
    assert motif.effects.introduces_revisit is True


def test_hub_revisit_motif_changes_the_required_exit_after_objective() -> None:
    motif = default_motif_registry().get("objective_state_revisited_hub").build()

    assert motif.validate() == ()
    assert motif.preconditions is not None
    assert motif.effects is not None
    assert motif.preconditions.required_incoming_objective_state is (
        MotifIncomingObjectiveState.BEFORE_ACTIVE_OBJECTIVE
    )
    assert motif.effects.completed_objective_node_ids == ("package",)
    assert {
        (change.from_node_id, change.to_node_id, change.kind)
        for change in motif.effects.edge_state_changes
    } == {
        ("entry", "outbound", MotifEdgeStateChangeKind.CLOSE),
        ("entry", "detour", MotifEdgeStateChangeKind.CLOSE),
        ("entry", "exit", MotifEdgeStateChangeKind.OPEN),
    }
    assert motif.effects.gameplay_effects == (
        MotifGameplayEffect.REQUIRED_HUB_REVISIT,
        MotifGameplayEffect.STATE_DEPENDENT_BRANCH,
    )
    assert motif.effects.expected_downstream_dependency is MotifDependencyEffect.OBJECTIVE_STATE
    assert motif.effects.introduces_cycle is True
    assert motif.effects.introduces_revisit is True
    assert motif.effects.introduces_rejoin is True
    assert motif.effects.introduces_recovery_exit is True
    assert {
        (edge.to_node_id, edge.availability)
        for edge in motif.edges
        if edge.from_node_id == "entry"
    } == {
        ("outbound", "beforePackage"),
        ("detour", "beforePackage"),
        ("exit", "afterPackage"),
    }
    assert {port.port_type for port in motif.ports}.issuperset({
        MotifPortType.BRANCH_INSERTION_POINT,
        MotifPortType.REJOIN_INPUT,
        MotifPortType.RETURN_PATH_INPUT,
        MotifPortType.RETURN_PATH_OUTPUT,
        MotifPortType.OBJECTIVE_ATTACHMENT,
        MotifPortType.STATE_CHANGE_ATTACHMENT,
        MotifPortType.RECOVERY_EXIT,
    })


def test_stateful_ring_changes_available_exit_between_objective_phases() -> None:
    motif = default_motif_registry().get("phase_dependent_ring_exits").build()

    assert motif.validate() == ()
    assert motif.preconditions is not None
    assert motif.effects is not None
    assert motif.preconditions.required_incoming_objective_state is (
        MotifIncomingObjectiveState.BEFORE_ACTIVE_OBJECTIVE
    )
    assert motif.effects.completed_objective_node_ids == ("package",)
    assert {
        (change.from_node_id, change.to_node_id, change.kind)
        for change in motif.effects.edge_state_changes
    } == {
        ("entry", "ring_a", MotifEdgeStateChangeKind.CLOSE),
        ("entry", "failure", MotifEdgeStateChangeKind.CLOSE),
        ("entry", "exit", MotifEdgeStateChangeKind.OPEN),
    }
    assert motif.effects.structural_effects == (
        MotifStructuralEffect.SEGMENT,
        MotifStructuralEffect.SPLIT,
        MotifStructuralEffect.HUB,
        MotifStructuralEffect.RING,
        MotifStructuralEffect.RETURN_CORRIDOR,
        MotifStructuralEffect.CROSS_PHASE_CONNECTOR,
    )
    assert motif.effects.gameplay_effects == (
        MotifGameplayEffect.STATE_DEPENDENT_BRANCH,
        MotifGameplayEffect.REQUIRED_HUB_REVISIT,
    )
    assert motif.effects.expected_downstream_dependency is MotifDependencyEffect.OBJECTIVE_STATE
    assert motif.effects.introduces_cycle is True
    assert motif.effects.introduces_revisit is True
    assert motif.effects.introduces_failure_exit is True
    assert {port.port_type for port in motif.ports}.issuperset({
        MotifPortType.BRANCH_INSERTION_POINT,
        MotifPortType.RETURN_PATH_INPUT,
        MotifPortType.RETURN_PATH_OUTPUT,
        MotifPortType.OBJECTIVE_ATTACHMENT,
        MotifPortType.STATE_CHANGE_ATTACHMENT,
        MotifPortType.FAILURE_EXIT,
    })


def test_all_initial_seed_motifs_validate_independently() -> None:
    motifs = seed_motif_factories()
    assert {motif.motif_id for motif in motifs} == EXPECTED
    assert all(motif.validate() == () for motif in motifs)


def test_default_registry_exposes_each_seed_motif() -> None:
    assert {motif.motif_id for motif in default_motif_registry().all()} == EXPECTED


def test_package_state_motifs_embed_package_and_conditional_roads() -> None:
    registry = default_motif_registry()
    for motif_id in PACKAGE_STATE_MOTIFS:
        motif = registry.get(motif_id).build()
        metadata = dict(motif.mechanic_metadata)
        assert metadata["embeddedPackageNode"] == "package"
        assert any(edge.availability != "always" for edge in motif.edges)
        assert motif.may_introduce_revisit is True


def test_straight_segment_is_the_first_v2_motif_with_typed_route_ports() -> None:
    motif = default_motif_registry().get("straight_segment").build()

    assert tuple(port.port_type for port in motif.ports) == (
        MotifPortType.MAIN_ROUTE_ENTRY,
        MotifPortType.MAIN_ROUTE_EXIT,
    )
    assert motif.main_route_entry_connector == motif.entry_connector
    assert motif.main_route_exit_connectors == motif.exit_connectors


def test_package_state_motifs_expose_typed_ports_and_objective_contracts() -> None:
    registry = default_motif_registry()
    for motif_id in PACKAGE_STATE_MOTIFS:
        motif = registry.get(motif_id).build()

        assert motif.preconditions is not None
        assert motif.effects is not None
        assert (
            motif.preconditions.required_incoming_objective_state
            is MotifIncomingObjectiveState.BEFORE_ACTIVE_OBJECTIVE
        )
        assert motif.effects.completed_objective_node_ids == ("package",)
        assert (
            motif.effects.expected_downstream_dependency
            is MotifDependencyEffect.OBJECTIVE_STATE
        )
        assert motif.effects.introduces_cycle is True
        assert motif.effects.introduces_revisit is True
        assert motif.effects.maximum_instances_per_composition == 1
        assert {port.port_type for port in motif.ports}.issuperset({
            MotifPortType.MAIN_ROUTE_ENTRY,
            MotifPortType.MAIN_ROUTE_EXIT,
            MotifPortType.OBJECTIVE_ATTACHMENT,
            MotifPortType.STATE_CHANGE_ATTACHMENT,
            MotifPortType.RETURN_PATH_INPUT,
            MotifPortType.RETURN_PATH_OUTPUT,
        })


def test_package_state_effects_match_their_conditional_edges() -> None:
    registry = default_motif_registry()
    expected_changes = {
        "road_opens_after_package": {MotifEdgeStateChangeKind.OPEN},
        "shortcut_closes_after_package": {MotifEdgeStateChangeKind.CLOSE},
        "return_route_changes_after_package": {
            MotifEdgeStateChangeKind.OPEN,
            MotifEdgeStateChangeKind.CLOSE,
        },
        "package_state_revisited_switch": {
            MotifEdgeStateChangeKind.OPEN,
            MotifEdgeStateChangeKind.CLOSE,
        },
    }
    for motif_id, expected in expected_changes.items():
        motif = registry.get(motif_id).build()

        assert {change.kind for change in motif.effects.edge_state_changes} == expected
        assert motif.validate() == ()
