from app.motifs.seed_motifs import default_motif_registry, seed_motif_factories


EXPECTED = {
    "straight_segment", "single_binary_choice", "dead_end_decoy", "recoverable_detour",
    "split_and_rejoin", "package_branch", "return_loop", "revisited_switch", "ring_route",
    "three_way_hub", "four_way_hub",
}


def test_all_initial_seed_motifs_validate_independently() -> None:
    motifs = seed_motif_factories()
    assert {motif.motif_id for motif in motifs} == EXPECTED
    assert all(motif.validate() == () for motif in motifs)


def test_default_registry_exposes_each_seed_motif() -> None:
    assert {motif.motif_id for motif in default_motif_registry().all()} == EXPECTED
