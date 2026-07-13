from __future__ import annotations

from dataclasses import dataclass

from tiny_routes_core.simulation import LevelOutcome, TapRecord


@dataclass(frozen=True)
class PlaytestState:
    running: bool = False
    paused: bool = False
    elapsed_time: float = 0.0
    current_node_id: str | None = None
    current_edge_id: str | None = None
    edge_progress: float = 0.0
    package_collected: bool = False
    outcome: LevelOutcome = LevelOutcome.IN_PROGRESS
    eligible_switch_id: str | None = None
    accepted_taps: tuple[TapRecord, ...] = ()
    rejected_taps: tuple[TapRecord, ...] = ()
    switch_active_edge_ids: tuple[tuple[str, str], ...] = ()
    event_times: tuple[float, ...] = ()
