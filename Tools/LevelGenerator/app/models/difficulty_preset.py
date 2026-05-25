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
    dead_end_count_range: Range
    max_outgoing_edges_per_switch: int
    allow_return_loops: bool
    allow_repeated_switch_taps: bool
    min_tap_spacing_seconds: float
    time_limit_padding_seconds: int
    coordinate_bounds: Bounds = (-1.2, 1.2, -1.3, 1.0)
    minimum_node_distance: float = 0.2
    allow_ring_routes: bool = False
