from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SimulationStep:
    time_seconds: float
    event: str
    node_id: str | None = None
    edge_id: str | None = None
    detail: str = ""


@dataclass
class SimulationResult:
    passed: bool
    outcome: str
    failure_reason: str | None = None
    elapsed_time_seconds: float = 0.0
    tap_count: int = 0
    reached_package: bool = False
    reached_destination: bool = False
    steps: list[SimulationStep] = field(default_factory=list)
