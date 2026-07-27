"""Blueprint-driven schema-3 level realization for production V3 candidates."""

from __future__ import annotations

import math
import random

from tiny_routes_core.models import LevelDocument

from ..models.decision_dependency_graph import DecisionNode
from ..models.puzzle_blueprint import PuzzleBlueprint


class ProductionLevelRealizationService:
    """Realize validated player-intent blueprints as deterministic route graphs.

    The realized graph uses ordered objective phases and exact-phase road
    availability. Each phase revisits a decision hub whose correct authored
    exit changes with objective state. Candidate seeds vary objective count,
    hub structure, recovery loops, geometry, and road shapes without using a
    legacy template or fixed recipe.
    """

    def realize(
        self,
        *,
        level_id: str,
        difficulty: str,
        blueprint: PuzzleBlueprint,
        seed: int,
        attempt_index: int,
    ) -> LevelDocument:
        if blueprint.validate():
            raise ValueError("production realization requires a valid blueprint")
        target = blueprint.experience_target
        objective_count = len(blueprint.objectives)
        decisions = blueprint.decision_graph.decisions
        trap_depth = 1 + (
            self._level_number(level_id) + attempt_index + seed % 7
        ) % 5
        rng = random.Random(seed)
        nodes: list[dict[str, object]] = []
        edges: list[dict[str, object]] = []
        outgoing: dict[str, list[str]] = {}
        road_shapes = ("horizontalFirst", "verticalFirst")

        def add_node(node_id: str, x: float, y: float) -> None:
            nodes.append(
                {
                    "id": node_id,
                    "x": round(x + rng.uniform(-0.06, 0.06), 4),
                    "y": round(y + rng.uniform(-0.06, 0.06), 4),
                    "outgoingEdgeIDs": outgoing.setdefault(node_id, []),
                }
            )

        def phase_rule(
            phase_index: int,
            *,
            usage_limit: int | None = None,
        ) -> dict[str, object]:
            rule: dict[str, object] = {
                "minimumObjectiveIndex": phase_index,
                "maximumObjectiveIndex": phase_index,
            }
            if usage_limit is not None:
                rule["usageLimit"] = usage_limit
            return rule

        def usage_rule(usage_limit: int) -> dict[str, object]:
            return {"usageLimit": usage_limit}

        def add_edge(
            edge_id: str,
            source: str,
            destination: str,
            *,
            rule: dict[str, object] | None = None,
            shape_offset: int = 0,
        ) -> None:
            outgoing.setdefault(source, []).append(edge_id)
            payload: dict[str, object] = {
                "id": edge_id,
                "fromNodeID": source,
                "toNodeID": destination,
                "roadShape": road_shapes[(seed + shape_offset) % 2],
            }
            if rule is not None:
                payload["availabilityRule"] = rule
            edges.append(payload)

        decisions_by_phase = tuple(
            tuple(
                decision
                for decision in decisions
                if decision.phase_index == phase_index
            )
            for phase_index in range(objective_count)
        )
        phase_end_ordinals = {
            phase_decisions[-1].sequence_index
            for phase_decisions in decisions_by_phase
            if phase_decisions
        }
        planning_gate_ordinals: set[int] = set()
        deep_planning_ordinal: int | None = None
        decisions_by_shared_role: dict[str, list[DecisionNode]] = {}
        for decision in decisions:
            decisions_by_shared_role.setdefault(decision.switch_role, []).append(
                decision
            )

        decision_node_by_id: dict[str, str] = {}
        shared_group_count = 0
        for role_decisions in decisions_by_shared_role.values():
            if len(role_decisions) == 1:
                decision = role_decisions[0]
                decision_node_by_id[decision.id] = (
                    f"decision_{decision.sequence_index}"
                )
                continue
            for visit_index, decision in enumerate(role_decisions):
                group_index = visit_index // 2
                decision_node_by_id[decision.id] = (
                    f"shared_hub_{shared_group_count + group_index}"
                )
            shared_group_count += (len(role_decisions) + 1) // 2
        if difficulty != "easy":
            deep_planning_ordinal = min(phase_end_ordinals)
            planning_gate_ordinals = {deep_planning_ordinal}
        first_ordinal_by_node: dict[str, int] = {}
        last_ordinal_by_node: dict[str, int] = {}
        for decision in decisions:
            node_id = decision_node_by_id[decision.id]
            first_ordinal_by_node.setdefault(node_id, decision.sequence_index)
            last_ordinal_by_node[node_id] = decision.sequence_index

        add_node("start", -8.0, 0.0)
        for decision in decisions:
            node_id = decision_node_by_id[decision.id]
            if node_id in outgoing:
                continue
            sequence = decision.sequence_index
            x = -4.5 + (sequence % 4) * 2.8
            y = ((sequence // 4) % 3 - 1) * 2.5
            if node_id.startswith("shared_hub"):
                x = -3.5 + int(node_id.rsplit("_", 1)[1]) * 0.8
                y = 0.0
            add_node(node_id, x, y)
        first_decision = decision_node_by_id[decisions[0].id]
        add_edge("start_to_first_decision", "start", first_decision)

        objectives: list[dict[str, object]] = []
        realized_recovery_nodes: set[str] = set()

        def add_recovery_route(
            *,
            decision_node: str,
            ordinal: int,
            wrong_x: float,
            wrong_y: float,
        ) -> None:
            realized_recovery_nodes.add(decision_node)
            wrong_node = f"wrong_{ordinal}_0"
            add_node(wrong_node, wrong_x, wrong_y)
            add_edge(
                f"decision_{ordinal}_wrong",
                decision_node,
                wrong_node,
                rule=usage_rule(1),
                shape_offset=ordinal,
            )
            previous_wrong = wrong_node
            for wrong_index in range(1, trap_depth):
                next_wrong = f"wrong_{ordinal}_{wrong_index}"
                add_node(
                    next_wrong,
                    wrong_x + wrong_index * 0.35,
                    wrong_y - wrong_index * 0.28,
                )
                add_edge(
                    f"decision_{ordinal}_wrong_segment_{wrong_index}",
                    previous_wrong,
                    next_wrong,
                    shape_offset=ordinal + wrong_index,
                )
                previous_wrong = next_wrong
            add_edge(
                f"decision_{ordinal}_recover",
                previous_wrong,
                (
                    f"deep_recovery_switch_{ordinal}"
                    if difficulty != "easy"
                    and ordinal == deep_planning_ordinal
                    else decision_node
                ),
                shape_offset=ordinal + trap_depth,
            )
            if difficulty != "easy" and ordinal == deep_planning_ordinal:
                recovery_switch = f"deep_recovery_switch_{ordinal}"
                recovery_detour = f"deep_recovery_detour_{ordinal}"
                add_node(recovery_switch, wrong_x * 0.95, wrong_y * 0.95)
                add_node(recovery_detour, wrong_x * 0.7, wrong_y * 0.7)
                add_edge(
                    f"deep_recovery_{ordinal}_return",
                    recovery_switch,
                    decision_node,
                    shape_offset=ordinal + trap_depth + 1,
                )
                add_edge(
                    f"deep_recovery_{ordinal}_detour",
                    recovery_switch,
                    recovery_detour,
                    shape_offset=ordinal + trap_depth + 2,
                )
                add_edge(
                    f"deep_recovery_{ordinal}_detour_return",
                    recovery_detour,
                    decision_node,
                    shape_offset=ordinal + trap_depth + 3,
                )

        for phase_index in range(objective_count):
            angle = (
                phase_index * 2.399963229728653
                + (seed % 360) * math.pi / 1800.0
            ) % (2 * math.pi)
            objective = blueprint.objectives[phase_index]
            objective_node = f"objective_node_{phase_index}"
            radius = 4.0 + (phase_index % 2)
            objective_x = math.cos(angle) * radius
            objective_y = math.sin(angle) * radius

            add_node(objective_node, objective_x, objective_y)
            objective_entry = f"objective_entry_{phase_index}"
            add_node(
                objective_entry,
                -objective_x * 0.55,
                -objective_y * 0.55,
            )
            add_edge(
                f"phase_{phase_index}_objective_finish",
                objective_entry,
                objective_node,
                shape_offset=phase_index + len(decisions),
            )
            phase_decisions = decisions_by_phase[phase_index]
            for local_index, decision in enumerate(phase_decisions):
                ordinal = decision.sequence_index
                decision_node = decision_node_by_id[decision.id]
                next_node = (
                    decision_node_by_id[phase_decisions[local_index + 1].id]
                    if local_index + 1 < len(phase_decisions)
                    else objective_entry
                )
                correct_destination = next_node
                if (
                    difficulty != "easy"
                    and ordinal in planning_gate_ordinals
                    and next_node == objective_entry
                ):
                    planning_gate = f"planning_gate_{ordinal}"
                    add_node(
                        planning_gate,
                        (
                            -objective_x * 4.5
                            if ordinal == deep_planning_ordinal
                            else -objective_x * 0.9
                        ),
                        (
                            -objective_y * 4.5
                            if ordinal == deep_planning_ordinal
                            else -objective_y * 0.9
                        ),
                    )
                    if ordinal == deep_planning_ordinal:
                        planning_dead_end = f"planning_dead_end_{ordinal}"
                        add_node(
                            planning_dead_end,
                            objective_x * 0.8,
                            objective_y * 0.8,
                        )
                        add_edge(
                            f"planning_gate_{ordinal}_wrong",
                            planning_gate,
                            planning_dead_end,
                            shape_offset=ordinal + len(decisions) + 1,
                        )
                        add_edge(
                            f"planning_gate_{ordinal}_finish",
                            planning_gate,
                            next_node,
                            shape_offset=ordinal + len(decisions) + 2,
                        )
                    else:
                        planning_detour = f"planning_detour_{ordinal}"
                        add_node(
                            planning_detour,
                            objective_x * 0.82,
                            objective_y * 0.82,
                        )
                        add_edge(
                            f"planning_gate_{ordinal}_finish",
                            planning_gate,
                            next_node,
                            shape_offset=ordinal + len(decisions) + 1,
                        )
                        add_edge(
                            f"planning_gate_{ordinal}_detour",
                            planning_gate,
                            planning_detour,
                            rule=usage_rule(1),
                            shape_offset=ordinal + len(decisions) + 2,
                        )
                        add_edge(
                            f"planning_gate_{ordinal}_recover",
                            planning_detour,
                            planning_gate,
                            shape_offset=ordinal + len(decisions) + 3,
                        )
                    correct_destination = planning_gate

                wrong_x = objective_x * (0.92 + local_index * 0.03)
                wrong_y = objective_y * (0.92 + local_index * 0.03)
                recovery_ordinal = first_ordinal_by_node[decision_node]
                if recovery_ordinal == 0:
                    # Keep the first choice from collapsing into one global
                    # cardinal-direction rule across the whole solution.
                    wrong_y = min(wrong_y, -abs(objective_y) - 4.0)
                if ordinal == 0:
                    fatal_node = "initial_fatal_dead_end"
                    add_node(
                        fatal_node,
                        objective_x * 0.985,
                        objective_y * 0.985,
                    )
                    add_edge(
                        "decision_0_fatal",
                        decision_node,
                        fatal_node,
                        shape_offset=ordinal + trap_depth + 2,
                    )

                recovery_unrealized = decision_node not in realized_recovery_nodes
                add_edge(
                    f"decision_{ordinal}_correct",
                    decision_node,
                    correct_destination,
                    rule=phase_rule(phase_index),
                    shape_offset=ordinal + 1,
                )

                if (
                    recovery_unrealized
                    and ordinal == last_ordinal_by_node[decision_node]
                ):
                    add_recovery_route(
                        decision_node=decision_node,
                        ordinal=recovery_ordinal,
                        wrong_x=wrong_x,
                        wrong_y=wrong_y,
                    )

            final = phase_index == objective_count - 1
            objectives.append(
                {
                    "id": objective.id,
                    "nodeID": objective_node,
                    "kind": (
                        "destination"
                        if final
                        else "pickup"
                        if phase_index == 0
                        else "checkpoint"
                    ),
                    "sequenceIndex": phase_index,
                    "revealPolicy": "always" if phase_index == 0 else "whenActive",
                }
            )
            if not final:
                next_phase = decisions_by_phase[phase_index + 1]
                next_hub = decision_node_by_id[next_phase[0].id]
                add_edge(
                    f"phase_{phase_index}_return",
                    objective_node,
                    next_hub,
                    shape_offset=phase_index + 8,
                )

        return LevelDocument.from_dict(
            {
                "schemaVersion": 3,
                "id": level_id,
                "name": level_id.replace("_", " ").title(),
                "rules": {
                    "switchInteractionMode": "liveLookahead",
                    "switchLookaheadSeconds": 2.0,
                    "switchTapCooldownSeconds": 0.12,
                },
                "startNodeID": "start",
                "packageNodeID": "objective_node_0",
                "destinationNodeID": f"objective_node_{objective_count - 1}",
                "timeLimitSeconds": max(
                    360,
                    int(target.desired_solve_time_range[1] * 4),
                ),
                "parTaps": max(2, target.meaningful_decision_range[0]),
                "objectives": objectives,
                "graph": {"nodes": nodes, "edges": edges},
            }
        )

    @staticmethod
    def _level_number(level_id: str) -> int:
        try:
            return int(level_id.rsplit("_", 1)[1])
        except (IndexError, ValueError):
            return 0
