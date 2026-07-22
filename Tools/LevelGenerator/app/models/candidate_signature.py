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
    decision_dependency_pattern: tuple[int, int, float] = (0, 0, 0.0)
    switch_degree_sequence: tuple[int, ...] = ()
    revisit_state_reversal_pattern: tuple[int, int, int] = (0, 0, 0)
    failure_outcome_distribution: tuple[tuple[str, int], ...] = ()
    package_phase_pattern: tuple[int, int] = (0, 0)
    layout_silhouette: tuple[tuple[float, float], ...] = ()
    mirrored_layout_silhouette: tuple[tuple[float, float], ...] = ()
    road_direction_histogram: tuple[tuple[str, int], ...] = ()
    solution_decision_timing_pattern: tuple[float, ...] = ()
    blueprint_archetype: str = ""
    objective_count: int = 0
    objective_kinds: tuple[str, ...] = ()
    dependency_dag_signature: str = ""
    adaptive_decision_pattern: tuple[tuple[object, ...], ...] = ()
    state_transition_pattern: tuple[tuple[object, ...], ...] = ()
    static_policy_proof_signature: str = ""
    agent_performance_profile: tuple[tuple[object, ...], ...] = ()
    revisit_pattern: tuple[tuple[int, int, int], ...] = ()
    success_failure_distribution: tuple[tuple[str, int], ...] = ()
    optimal_strategy_signature: str = ""
    road_state_visual_signature: str = ""
    structural_behavior_signature: str = ""
