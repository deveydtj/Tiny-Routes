from __future__ import annotations

from dataclasses import dataclass


Range = tuple[int, int]
Bounds = tuple[float, float, float, float]


@dataclass(frozen=True)
class DifficultyPreset:
    name: str
    node_count_range: Range
    switch_count_range: Range
    required_tap_range: Range
    route_length_range: Range
    dead_end_count_range: Range
    max_outgoing_edges_per_switch: int
    allow_return_loops: bool
    allow_repeated_switch_taps: bool
    min_tap_spacing_seconds: float
    time_limit_padding_seconds: int
    map_size_profile_weights: tuple[tuple[str, int], ...] = (("standard_portrait", 1),)
    allowed_topology_classes: tuple[str, ...] = ()
    required_route_interest_tags: tuple[str, ...] = ()
    optional_route_interest_tags: tuple[str, ...] = ()
    minimum_route_interest_score: float = 0.0
    max_visual_complexity: float = 1.0
    max_repeated_mechanics: int = 2
    coordinate_bounds: Bounds = (-1.2, 1.2, -1.3, 1.0)
    minimum_node_distance: float = 0.2
    allow_ring_routes: bool = False
