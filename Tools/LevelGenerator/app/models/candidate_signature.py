from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateSignature:
    """Stable fingerprint used for duplicate and similarity checks."""

    level_id: str
    template_name: str
    difficulty: str
    node_count: int
    edge_count: int
    switch_count: int
    required_tap_count: int
    dead_end_count: int
    topology_hash: str
    layout_hash: str
    solution_hash: str
    normalized_positions: tuple[tuple[str, float, float], ...]
    max_outgoing_edge_count: int = 0
    has_four_way_switch: bool = False
    central_switch_revisit_count: int = 0
    mechanic_tags: tuple[str, ...] = ()
    primary_mechanic_tag: str = ""
    topology_class: str = ""
    required_path_length: int | None = None
    layout_orientation: str = "unknown"
    layout_size_profile: str = "standard_portrait"
    topology_diversity_score: float | None = None
    nearby_mechanic_tag_penalty: float | None = None
    nearby_topology_class_penalty: float | None = None
    diversity_score: float | None = None
