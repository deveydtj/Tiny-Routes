"""Deterministic schema-3 fixtures for strategic and fuzz-style tests."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from tiny_routes_core.models import LevelDocument


@dataclass(frozen=True)
class StatefulFixtureSpec:
    fixture_id: str
    difficulty: str = "easy"
    objective_count: int = 2
    hub_count: int = 1
    include_alternate_route: bool = True
    include_one_use_ring: bool = False
    seed: int = 0

    def __post_init__(self) -> None:
        if self.objective_count < 2:
            raise ValueError("stateful fixtures require at least two objectives")
        if self.hub_count < 1:
            raise ValueError("stateful fixtures require at least one hub")


def build_stateful_fixture(spec: StatefulFixtureSpec) -> LevelDocument:
    """Build a finite relay whose correct hub exit changes by objective phase.

    Every phase exposes a trap first, the intended route second, and optionally
    a more expensive successful route third.  Exact-phase road conditions force
    a revisited hub to select a different authored edge, while one-use rings
    provide bounded recovery cycles without making exact search unbounded.
    """

    rng = random.Random(spec.seed)
    node_payloads: list[dict[str, object]] = []
    edge_payloads: list[dict[str, object]] = []
    outgoing: dict[str, list[str]] = {}

    def add_node(node_id: str, x: float, y: float) -> None:
        jitter_x = rng.uniform(-0.08, 0.08)
        jitter_y = rng.uniform(-0.08, 0.08)
        node_payloads.append(
            {
                "id": node_id,
                "x": round(x + jitter_x, 4),
                "y": round(y + jitter_y, 4),
                "outgoingEdgeIDs": outgoing.setdefault(node_id, []),
            }
        )

    def phase_rule(phase_index: int, *, usage_limit: int | None = None) -> dict:
        rule: dict[str, object] = {
            "minimumObjectiveIndex": phase_index,
            "maximumObjectiveIndex": phase_index,
        }
        if usage_limit is not None:
            rule["usageLimit"] = usage_limit
        return rule

    def add_edge(
        edge_id: str,
        source: str,
        destination: str,
        *,
        rule: dict | None = None,
    ) -> None:
        outgoing.setdefault(source, []).append(edge_id)
        payload: dict[str, object] = {
            "id": edge_id,
            "fromNodeID": source,
            "toNodeID": destination,
        }
        if rule is not None:
            payload["availabilityRule"] = rule
        edge_payloads.append(payload)

    add_node("start", -8.0, 0.0)
    for hub_index in range(spec.hub_count):
        add_node(f"hub_{hub_index}", -4.0 + hub_index * 3.0, 0.0)
    add_edge("start_to_hub", "start", "hub_0")

    objectives: list[dict[str, object]] = []
    for phase_index in range(spec.objective_count):
        hub_id = f"hub_{phase_index % spec.hub_count}"
        angle = (phase_index * 2.399963229728653) % (2 * math.pi)
        objective_id = f"objective_{phase_index}"
        objective_node = f"objective_node_{phase_index}"
        entry_node = f"entry_{phase_index}"
        trap_node = f"trap_{phase_index}"
        radius = 4.0 + (phase_index % 2)
        objective_x = math.cos(angle) * radius
        objective_y = math.sin(angle) * radius

        add_node(objective_node, objective_x, objective_y)
        # The intended entry is deliberately not the locally closest visible
        # road endpoint; the successful alternate prevents dead-end guessing.
        add_node(entry_node, -objective_x * 0.45, -objective_y * 0.45)
        # The greedy locally-closest road is an understandable trap.  The
        # intended route is recoverable from the visible state, but requires
        # reasoning beyond pointing at the current objective marker.
        add_node(trap_node, objective_x * 0.95, objective_y * 0.95)

        exact_phase = phase_rule(phase_index)
        add_edge(
            f"phase_{phase_index}_trap",
            hub_id,
            trap_node,
            rule=exact_phase,
        )
        add_edge(
            f"phase_{phase_index}_correct",
            hub_id,
            entry_node,
            rule=phase_rule(phase_index),
        )
        add_edge(
            f"phase_{phase_index}_finish",
            entry_node,
            objective_node,
        )

        if spec.include_alternate_route:
            alternate_node = f"alternate_{phase_index}"
            add_node(alternate_node, objective_x * 0.82, objective_y * 0.82)
            add_edge(
                f"phase_{phase_index}_alternate",
                hub_id,
                alternate_node,
                rule=phase_rule(phase_index),
            )
            add_edge(
                f"phase_{phase_index}_alternate_finish",
                alternate_node,
                objective_node,
            )

        if spec.include_one_use_ring:
            ring_a = f"ring_{phase_index}_a"
            ring_b = f"ring_{phase_index}_b"
            add_node(ring_a, objective_x * 0.35 - 1.0, objective_y * 0.35 - 1.0)
            add_node(ring_b, objective_x * 0.2 - 2.0, objective_y * 0.2 + 1.0)
            add_edge(
                f"phase_{phase_index}_ring",
                hub_id,
                ring_a,
                rule=phase_rule(phase_index, usage_limit=1),
            )
            add_edge(f"phase_{phase_index}_ring_middle", ring_a, ring_b)
            add_edge(f"phase_{phase_index}_ring_return", ring_b, hub_id)

        is_final = phase_index == spec.objective_count - 1
        objectives.append(
            {
                "id": objective_id,
                "nodeID": objective_node,
                "kind": (
                    "destination"
                    if is_final
                    else "pickup"
                    if phase_index == 0
                    else "checkpoint"
                ),
                "sequenceIndex": phase_index,
                "revealPolicy": "always" if phase_index == 0 else "whenActive",
            }
        )
        if not is_final:
            next_hub = f"hub_{(phase_index + 1) % spec.hub_count}"
            add_edge(
                f"phase_{phase_index}_return",
                objective_node,
                next_hub,
            )

    return LevelDocument.from_dict(
        {
            "schemaVersion": 3,
            "id": spec.fixture_id,
            "name": spec.fixture_id.replace("_", " ").title(),
            "startNodeID": "start",
            "packageNodeID": "objective_node_0",
            "destinationNodeID": f"objective_node_{spec.objective_count - 1}",
            "timeLimitSeconds": 180,
            "parTaps": spec.objective_count,
            "objectives": objectives,
            "graph": {"nodes": node_payloads, "edges": edge_payloads},
        }
    )


def deterministic_fuzz_fixture(seed: int) -> LevelDocument:
    """Return a varied but always finite stateful graph for one fuzz seed."""

    difficulty = ("easy", "medium", "hard")[seed % 3]
    minimum_objectives = {"easy": 2, "medium": 3, "hard": 5}[difficulty]
    return build_stateful_fixture(
        StatefulFixtureSpec(
            fixture_id=f"stateful_fuzz_{seed:03d}",
            difficulty=difficulty,
            objective_count=minimum_objectives + (seed % 2),
            hub_count=1 + (seed % 2),
            include_alternate_route=True,
            include_one_use_ring=seed % 4 == 0,
            seed=seed,
        )
    )
