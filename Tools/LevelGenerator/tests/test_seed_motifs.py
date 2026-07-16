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
