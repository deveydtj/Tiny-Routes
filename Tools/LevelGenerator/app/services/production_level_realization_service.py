"""Blueprint-driven schema-3 level realization for production V3 candidates."""

from __future__ import annotations

import math

from tiny_routes_core.models import LevelDocument

from ..models.decision_dependency_graph import DecisionNode
from ..models.puzzle_blueprint import PuzzleBlueprint
from .road_shape_service import RoadShapeService


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
        nodes: list[dict[str, object]] = []
        edges: list[dict[str, object]] = []
        outgoing: dict[str, list[str]] = {}
        road_shapes = ("horizontalFirst", "verticalFirst")

        def add_node(node_id: str, x: float, y: float) -> None:
            nodes.append(
                {
                    "id": node_id,
                    "x": round(x, 4),
                    "y": round(y, 4),
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

        self._apply_readable_layout(
            nodes=nodes,
            edges=edges,
            decisions_by_phase=decisions_by_phase,
            decision_node_by_id=decision_node_by_id,
            objective_count=objective_count,
            seed=seed,
            difficulty=difficulty,
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

    def _apply_readable_layout(
        self,
        *,
        nodes: list[dict[str, object]],
        edges: list[dict[str, object]],
        decisions_by_phase: tuple[tuple[DecisionNode, ...], ...],
        decision_node_by_id: dict[str, str],
        objective_count: int,
        seed: int,
        difficulty: str,
    ) -> None:
        """Lay out phase routes in separated, deterministic road corridors.

        Production V3 previously used a radial sketch with objective-adjacent
        dead ends and a 4.5x planning-gate outlier.  Camera normalization then
        collapsed the useful part of the map and many unrelated L roads crossed.
        This layout gives each objective phase a dedicated upper/lower lane and
        gives recovery routes a separate outside corridor.
        """

        node_ids = {str(node["id"]) for node in nodes}
        positions: dict[str, tuple[float, float]] = {}
        phase_layout: dict[int, tuple[int, int]] = {}
        previous_start: str | None = None
        module_index = -1
        slot_index = 0

        for phase_index, phase_decisions in enumerate(decisions_by_phase):
            start_node_id = decision_node_by_id[phase_decisions[0].id]
            if start_node_id != previous_start:
                module_index += 1
                slot_index = 0
            else:
                slot_index += 1
            phase_layout[phase_index] = (module_index, slot_index)
            previous_start = start_node_id

        # Preserve the proportions of the corridor plan at gameplay scale. At
        # one world unit per second, unscaled diagram coordinates would turn a
        # clean map into long empty travel and force the camera to track across
        # thousands of screen points.
        layout_scale = 0.2
        # Each decision owns a local recovery box extending almost one decision
        # step to its left. Separate phase modules keep those boxes out of the
        # next phase's return approach.
        module_width = 60.0 * layout_scale
        decision_step = 10.0 * layout_scale
        lane_offset = 5.0 * layout_scale
        # Objective returns use the outermost corridor.  Keeping it well beyond
        # local switch/recovery branches prevents the long return road from
        # slicing through the choices it is meant to frame.
        objective_offset = 9.0 * layout_scale

        for phase_index, phase_decisions in enumerate(decisions_by_phase):
            module, slot = phase_layout[phase_index]
            origin_x = module * module_width
            lane_sign = 1.0 if slot % 2 == 0 else -1.0
            lane_y = lane_sign * lane_offset
            decision_node_ids = [
                decision_node_by_id[decision.id]
                for decision in phase_decisions
            ]
            positions.setdefault(decision_node_ids[0], (origin_x, 0.0))
            for local_index, node_id in enumerate(decision_node_ids[1:], 1):
                positions[node_id] = (
                    origin_x + local_index * decision_step,
                    lane_y
                    + lane_sign * (local_index - 1) * 4.0 * layout_scale,
                )

            compact_easy_revisit = (
                difficulty == "easy"
                and slot > 0
                and len(decision_node_ids) == 1
            )
            route_x = (
                origin_x
                if compact_easy_revisit
                else origin_x + max(1, len(decision_node_ids)) * decision_step
            )
            final_ordinal = phase_decisions[-1].sequence_index
            planning_gate_id = f"planning_gate_{final_ordinal}"
            if planning_gate_id in node_ids:
                positions[planning_gate_id] = (route_x, lane_y)
                route_x += decision_step

            positions[f"objective_entry_{phase_index}"] = (route_x, lane_y)
            positions[f"objective_node_{phase_index}"] = (
                route_x + 4.0 * layout_scale,
                lane_y + lane_sign * objective_offset,
            )

        first_decision_id = decision_node_by_id[decisions_by_phase[0][0].id]
        first_x, first_y = positions[first_decision_id]
        positions["start"] = (
            first_x - 4.0 * layout_scale,
            first_y + 3.0 * layout_scale,
        )
        if "initial_fatal_dead_end" in node_ids:
            positions["initial_fatal_dead_end"] = (
                first_x + 2.0 * layout_scale,
                first_y + 4.0 * layout_scale,
            )

        decision_by_ordinal = {
            decision.sequence_index: decision
            for phase_decisions in decisions_by_phase
            for decision in phase_decisions
        }
        for ordinal, decision in decision_by_ordinal.items():
            switch_id = decision_node_by_id[decision.id]
            switch_x, switch_y = positions[switch_id]
            phase_module, phase_slot = phase_layout[decision.phase_index]
            del phase_module
            lane_sign = 1.0 if phase_slot % 2 == 0 else -1.0
            # A decision's incoming main-route road approaches from the inside
            # of its phase lane.  Put the wrong/recovery loop on that inside
            # half and the optional deep detour on the outside half so neither
            # can cover the other switch ports.
            branch_sign = -1.0 if abs(switch_y) <= 1e-9 else -lane_sign

            planning_dead_end_id = f"planning_dead_end_{ordinal}"
            if planning_dead_end_id in node_ids:
                objective_x, objective_y = positions[
                    f"objective_node_{decision.phase_index}"
                ]
                positions[planning_dead_end_id] = (
                    objective_x - 3.0 * layout_scale,
                    objective_y - lane_sign * 2.0 * layout_scale,
                )

            wrong_node_ids = sorted(
                (
                    node_id
                    for node_id in node_ids
                    if node_id.startswith(f"wrong_{ordinal}_")
                ),
                key=lambda node_id: int(node_id.rsplit("_", 1)[1]),
            )
            wrong_count = len(wrong_node_ids)
            for wrong_index, wrong_node_id in enumerate(wrong_node_ids):
                if wrong_index == 0:
                    positions[wrong_node_id] = (
                        switch_x - 3.0 * layout_scale,
                        switch_y + branch_sign * 3.0 * layout_scale,
                    )
                    continue
                progress = (wrong_index - 1) / max(wrong_count - 1, 1)
                positions[wrong_node_id] = (
                    switch_x - 6.0 * layout_scale,
                    switch_y
                    + branch_sign * (3.0 - progress * 2.1) * layout_scale,
                )

            if difficulty == "easy" and ordinal == 0 and wrong_node_ids:
                # The later revisit must require reading state, not simply
                # pointing east at every switch.  This recovery loop makes the
                # west branch look locally tempting for the lower objective
                # while retaining a clean, nonfatal route back to the hub.
                positions[wrong_node_ids[0]] = (
                    switch_x - 3.0 * layout_scale,
                    switch_y - 8.0 * layout_scale,
                )
                for wrong_index, wrong_node_id in enumerate(wrong_node_ids[1:], 1):
                    progress = (wrong_index - 1) / max(len(wrong_node_ids) - 1, 1)
                    positions[wrong_node_id] = (
                        switch_x - 8.0 * layout_scale,
                        switch_y + (-8.0 + progress * 6.0) * layout_scale,
                    )

            recovery_switch_id = f"deep_recovery_switch_{ordinal}"
            recovery_detour_id = f"deep_recovery_detour_{ordinal}"
            if recovery_switch_id in node_ids:
                positions[recovery_switch_id] = (
                    switch_x - 6.0 * layout_scale,
                    switch_y,
                )
                if recovery_detour_id in node_ids:
                    positions[recovery_detour_id] = (
                        (
                            switch_x - 9.0 * layout_scale
                            if abs(switch_y) <= 1e-9
                            else switch_x - 6.0 * layout_scale
                        ),
                        (
                            switch_y - 6.0 * layout_scale
                            if abs(switch_y) <= 1e-9
                            else switch_y - branch_sign * 4.0 * layout_scale
                        ),
                    )

        # Defensive placement for future blueprint decorations.  Keeping these
        # in a separate far-right lane is preferable to silently stacking them
        # at (0, 0), and the layout gate below will still reject bad geometry.
        unplaced_index = 0
        for node_id in sorted(node_ids):
            if node_id in positions:
                continue
            positions[node_id] = (
                (module_index + 1) * module_width
                + unplaced_index * 4.0 * layout_scale,
                10.0 * layout_scale,
            )
            unplaced_index += 1

        # Mirror whole candidates for seed diversity without changing any
        # spacing or intersection property.
        if seed % 2:
            positions = {
                node_id: (x, -y)
                for node_id, (x, y) in positions.items()
            }

        for node in nodes:
            node_id = str(node["id"])
            x, y = positions[node_id]
            node["x"] = round(x, 4)
            node["y"] = round(y, 4)

        edge_pairs = [
            (str(edge["fromNodeID"]), str(edge["toNodeID"]))
            for edge in edges
        ]
        road_plan = RoadShapeService().plan_for_graph(
            positions,
            edge_pairs,
            strategy="auto",
            important_node_ids=(
                "start",
                "objective_node_0",
                f"objective_node_{objective_count - 1}",
            ),
        )
        start_node_counts: dict[str, int] = {}
        for phase_decisions in decisions_by_phase:
            node_id = decision_node_by_id[phase_decisions[0].id]
            start_node_counts[node_id] = start_node_counts.get(node_id, 0) + 1
        phase_entry_shape_by_edge_id = {
            f"decision_{phase_decisions[0].sequence_index}_correct": (
                "verticalFirst" if phase_layout[phase_index][1] > 0 else "horizontalFirst"
            )
            for phase_index, phase_decisions in enumerate(decisions_by_phase)
            if start_node_counts[decision_node_by_id[phase_decisions[0].id]] > 1
        }
        for edge, edge_pair in zip(edges, edge_pairs):
            edge["roadShape"] = road_plan.edge_shapes[edge_pair]
            edge_id = str(edge["id"])
            if edge_id == "start_to_first_decision":
                edge["roadShape"] = "verticalFirst"
            elif edge_id == "decision_0_fatal":
                edge["roadShape"] = "verticalFirst"
            elif edge_id.startswith("decision_") and edge_id.endswith("_wrong"):
                # Wrong-route boxes sit to the west of their decision. Reserve
                # that west port explicitly so stateful north/south phase exits
                # remain distinct at dense three- and four-way hubs.
                edge["roadShape"] = "horizontalFirst"
            elif (
                edge_id.startswith("decision_")
                and edge_id.endswith("_recover")
                and not str(edge["fromNodeID"]).endswith("_0")
            ):
                # The recovery road starts at the deepest point of a horizontal
                # wrong-route chain.  Leaving it horizontal-first would retrace
                # that chain through its earlier nodes, making the loop look
                # like one overlapping road instead of a clean return lane. A
                # one-node loop keeps the planner's shape because it has no
                # earlier node to avoid and may need to clear the start road.
                edge["roadShape"] = "verticalFirst"
            elif edge_id.startswith("planning_gate_") and edge_id.endswith("_wrong"):
                edge["roadShape"] = "verticalFirst"
            elif edge_id.startswith("phase_") and edge_id.endswith("_objective_finish"):
                edge["roadShape"] = "horizontalFirst"
            elif edge_id.startswith("phase_") and edge_id.endswith("_return"):
                from_x = positions[str(edge["fromNodeID"])][0]
                to_x = positions[str(edge["toNodeID"])][0]
                edge["roadShape"] = (
                    "verticalFirst" if to_x <= from_x else "horizontalFirst"
                )
            elif (
                edge_id.startswith("decision_")
                and edge_id.endswith("_correct")
                and str(edge["toNodeID"]).startswith(("decision_", "shared_hub_"))
            ):
                # Horizontal departure plus a vertical arrival reserves a
                # different port for the target's west-side recovery return.
                edge["roadShape"] = "horizontalFirst"
            elif edge_id.startswith("deep_recovery_") and edge_id.endswith("_detour_return"):
                edge["roadShape"] = "horizontalFirst"
            if edge_id in phase_entry_shape_by_edge_id:
                edge["roadShape"] = phase_entry_shape_by_edge_id[edge_id]

    @staticmethod
    def _level_number(level_id: str) -> int:
        try:
            return int(level_id.rsplit("_", 1)[1])
        except (IndexError, ValueError):
            return 0
