from app.models.motif_contract import (
    MotifDependencyEffect,
    MotifEdgeStateChangeKind,
    MotifIncomingObjectiveState,
)
from app.models.motif_port import MotifPortType
from app.motifs.seed_motifs import default_motif_registry, seed_motif_factories


EXPECTED = {
    "straight_segment", "single_binary_choice", "dead_end_decoy", "recoverable_detour",
    "split_and_rejoin", "package_branch", "return_loop", "revisited_switch", "ring_route",
    "three_way_hub", "four_way_hub",
    "road_opens_after_package", "shortcut_closes_after_package",
    "return_route_changes_after_package", "package_state_revisited_switch",
}

PACKAGE_STATE_MOTIFS = {
    "road_opens_after_package",
    "shortcut_closes_after_package",
    "return_route_changes_after_package",
    "package_state_revisited_switch",
}


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
