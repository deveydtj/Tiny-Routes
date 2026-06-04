from __future__ import annotations

from collections import Counter, deque
from collections.abc import Iterable
from dataclasses import replace

from ..models.candidate_signature import CandidateSignature
from ..models.difficulty_preset import DifficultyPreset
from ..models.generation_quality import GenerationQualityScore
from .candidate_uniqueness_service import CandidateUniquenessService
from .campaign_pacing_service import CampaignPacingService
from .difficulty_service import DifficultyService
from .graph_layout_service import GraphLayoutService
from .visual_clarity_validation_service import VisualClarityValidationService


class GenerationQualityService:
    def __init__(self) -> None:
        self.layout = GraphLayoutService()
        self.uniqueness = CandidateUniquenessService()
        self.difficulty = DifficultyService()
        self.visual_clarity = VisualClarityValidationService()
        self.campaign_pacing = CampaignPacingService()

    def score(
        self,
        generated_level,
        preset: DifficultyPreset,
        comparison_signatures: Iterable[CandidateSignature] = (),
        *,
        accepted_signatures: Iterable[CandidateSignature] | None = None,
    ) -> GenerationQualityScore:
        comparison_signatures = list(comparison_signatures)
        diversity_signatures = (
            list(accepted_signatures)
            if accepted_signatures is not None
            else list(comparison_signatures)
        )
        level = generated_level.level_document
        solution = generated_level.solution
        positions = {node.id: (node.x, node.y) for node in level.graph.nodes}
        edges = [(edge.fromNodeID, edge.toNodeID, edge.id) for edge in level.graph.edges]
        readability_details = self.layout.readability_summary(positions, edges)

        penalties: list[str] = []
        readability = 1.0
        if readability_details["overlaps"]:
            readability -= 0.35 * readability_details["overlaps"]
            penalties.append("overlapping_nodes")
        if readability_details["crossings"]:
            readability -= 0.18 * readability_details["crossings"]
            penalties.append("edge_crossings")
        if readability_details["edgeSpacingIssues"]:
            readability -= 0.08 * readability_details["edgeSpacingIssues"]
            penalties.append("tight_edge_spacing")
        road_shape_metadata = getattr(generated_level, "road_shape_metadata", None) or {}
        road_shape_score = float(road_shape_metadata.get("score", 1.0))
        if road_shape_score < readability:
            readability = (readability * 0.75) + (road_shape_score * 0.25)
        for issue in road_shape_metadata.get("issues", []):
            if issue.startswith("switch_choices_same_visual_direction"):
                penalties.append("ambiguous_switch_exit")
            elif issue.startswith("required_path_crossing"):
                penalties.append("required_path_crossing")
            elif issue.startswith("long_parallel_road_segments"):
                penalties.append("long_parallel_road_segments")
        visual_clarity_report = self.visual_clarity.report_for_generated_level(generated_level)
        if visual_clarity_report.score < readability:
            readability = (readability * 0.65) + (visual_clarity_report.score * 0.35)
        for issue in visual_clarity_report.issues:
            if issue.severity == "warning":
                penalties.append(issue.code)
            elif issue.severity == "info":
                penalties.append(issue.code)
        readability = self._clamp(readability)
        switch_clarity = self._switch_clarity_score(road_shape_metadata, visual_clarity_report)

        signature = generated_level.candidate_signature
        max_similarity = 0.0
        if signature is not None:
            max_similarity = max(
                (self.uniqueness.similarity_score(signature, other) for other in comparison_signatures),
                default=0.0,
            )
        uniqueness = self._clamp(1.0 - max_similarity)
        if max_similarity >= 0.75:
            penalties.append("similar_to_existing_candidate")

        difficulty_metrics = self.difficulty.metrics_for_generated_level(generated_level)
        difficulty_issues = self.difficulty.check_candidate_matches_difficulty(level, solution, preset)
        band_distance = abs(
            self.difficulty.band_index(difficulty_metrics.estimated_band)
            - self.difficulty.band_index(preset.name)
        )
        difficulty_fit = 1.0 if not difficulty_issues else 0.45
        penalties.extend(difficulty_issues)
        if band_distance >= 2:
            penalties.append("estimated_difficulty_band_far_from_target")

        abstract_mechanic_quality = self._abstract_mechanic_quality(generated_level, preset)
        runtime_solvability = self._runtime_solvability(generated_level)
        mobile_tap_comfort = self._mobile_tap_comfort(difficulty_metrics, preset)
        visual_appeal = self._visual_appeal(readability, visual_clarity_report.score, difficulty_metrics)
        if mobile_tap_comfort < 1.0:
            penalties.append("awkward_tap_timing")
        if preset.name in {"tutorial", "easy"} and difficulty_metrics.visual_score > 0.55:
            penalties.append("route_too_complex_for_difficulty")
        campaign_pacing = self.campaign_pacing.score(
            signature,
            diversity_signatures,
            estimated_band=difficulty_metrics.estimated_band,
            target_band=preset.name,
        ) if signature is not None else None
        campaign_pacing_score = campaign_pacing.score if campaign_pacing is not None else 1.0
        if campaign_pacing is not None:
            penalties.extend(campaign_pacing.penalties)
        diversity = self._topology_diversity(signature, diversity_signatures)
        if signature is not None:
            generated_level.candidate_signature = replace(
                signature,
                topology_diversity_score=diversity["topologyDiversityScore"],
                nearby_mechanic_tag_penalty=diversity["nearbyMechanicTagPenalty"],
                nearby_topology_class_penalty=diversity["nearbyTopologyClassPenalty"],
                diversity_score=diversity["diversityScore"],
            )
            signature = generated_level.candidate_signature
        if diversity["nearbyTopologyClassPenalty"] >= 0.20:
            penalties.append("nearby_topology_class_repetition")
        if diversity["nearbyMechanicTagPenalty"] >= 0.18:
            penalties.append("nearby_mechanic_tag_repetition")
        if diversity["nearbyFamilyStreakPenalty"] > 0:
            penalties.append("nearby_recipe_family_streak")
        route_interest_audit = self._route_interest_audit(generated_level, diversity)
        route_interest = route_interest_audit["score"]
        if preset.name in {"medium", "hard", "expert"} and route_interest < 0.45:
            penalties.append("route_too_straight_for_difficulty")
        for penalty in route_interest_audit["penalties"]:
            if penalty not in penalties:
                penalties.append(penalty)
        base_total = (
            (abstract_mechanic_quality * 0.12)
            + (runtime_solvability * 0.12)
            + (readability * 0.10)
            + (switch_clarity * 0.12)
            + (difficulty_fit * 0.14)
            + (uniqueness * 0.05)
            + (route_interest * 0.10)
            + (campaign_pacing_score * 0.06)
            + (mobile_tap_comfort * 0.07)
            + (visual_appeal * 0.06)
        )
        total = (
            (abstract_mechanic_quality * 0.12)
            + (runtime_solvability * 0.12)
            + (readability * 0.10)
            + (switch_clarity * 0.12)
            + (difficulty_fit * 0.14)
            + (uniqueness * 0.05)
            + (route_interest * 0.10)
            + (campaign_pacing_score * 0.06)
            + (mobile_tap_comfort * 0.07)
            + (visual_appeal * 0.06)
            + (diversity["diversityScore"] * 0.06)
        )
        return GenerationQualityScore(
            total=round(self._clamp(total), 4),
            readability=round(readability, 4),
            uniqueness=round(uniqueness, 4),
            difficulty_fit=round(difficulty_fit, 4),
            route_interest=round(route_interest, 4),
            abstract_mechanic_quality=round(abstract_mechanic_quality, 4),
            runtime_solvability=round(runtime_solvability, 4),
            switch_clarity=round(switch_clarity, 4),
            mobile_tap_comfort=round(mobile_tap_comfort, 4),
            visual_appeal=round(visual_appeal, 4),
            campaign_pacing=round(campaign_pacing_score, 4),
            topology_diversity_score=diversity["topologyDiversityScore"],
            nearby_mechanic_tag_penalty=diversity["nearbyMechanicTagPenalty"],
            nearby_topology_class_penalty=diversity["nearbyTopologyClassPenalty"],
            diversity_score=diversity["diversityScore"],
            mechanical_difficulty=difficulty_metrics.mechanical_score,
            visual_difficulty=difficulty_metrics.visual_score,
            estimated_difficulty_band=difficulty_metrics.estimated_band,
            penalties=tuple(dict.fromkeys(penalties)),
            details={
                **readability_details,
                "maxSimilarity": round(max_similarity, 4),
                "nodeCount": generated_level.node_count,
                "edgeCount": generated_level.edge_count,
                "switchCount": generated_level.switch_count,
                "requiredTapCount": generated_level.required_tap_count,
                "difficultyMetrics": difficulty_metrics.to_dict(),
                "campaignPacing": campaign_pacing.details if campaign_pacing is not None else {},
                "roadShapeScore": round(road_shape_score, 4),
                "roadShapeIssues": list(road_shape_metadata.get("issues", [])),
                "visualClarityScore": visual_clarity_report.score,
                "abstractMechanicQuality": round(abstract_mechanic_quality, 4),
                "runtimeSolvability": round(runtime_solvability, 4),
                "switchClarity": round(switch_clarity, 4),
                "mobileTapComfort": round(mobile_tap_comfort, 4),
                "visualAppeal": round(visual_appeal, 4),
                "baseQualityScore": round(self._clamp(base_total), 4),
                "routeInterest": route_interest_audit,
                "topologyDiversityScore": diversity["topologyDiversityScore"],
                "nearbyMechanicTagPenalty": diversity["nearbyMechanicTagPenalty"],
                "nearbyTopologyClassPenalty": diversity["nearbyTopologyClassPenalty"],
                "nearbyFamilyStreakPenalty": diversity["nearbyFamilyStreakPenalty"],
                "diversityScore": diversity["diversityScore"],
                "visualClarityIssues": [
                    {
                        "severity": issue.severity,
                        "code": issue.code,
                        "message": issue.message,
                        "relatedNodeID": issue.related_node_id,
                        "relatedEdgeID": issue.related_edge_id,
                        "relatedEdgeIDs": list(issue.related_edge_ids),
                    }
                    for issue in visual_clarity_report.issues
                ],
            },
        )

    def _abstract_mechanic_quality(self, generated_level, preset: DifficultyPreset) -> float:
        metadata = getattr(generated_level, "abstract_solution_metadata", None)
        if metadata is None:
            return self._route_interest(generated_level)

        score = 0.55
        score += min(metadata.false_route_count, 4) * 0.07
        score += min(metadata.dead_end_count, 3) * 0.06
        score += min(metadata.loop_count, 2) * 0.08
        if preset.required_tap_range[0] <= metadata.minimum_required_taps <= preset.required_tap_range[1]:
            score += 0.14
        if metadata.repeated_switch_usage and preset.allow_repeated_switch_taps:
            score += 0.05
        if not metadata.package_before_destination:
            score -= 0.35
        if metadata.alternate_path_count > 2:
            score -= min(metadata.alternate_path_count - 2, 4) * 0.05
        return self._clamp(score)

    def _runtime_solvability(self, generated_level) -> float:
        simulation = getattr(generated_level, "simulation_result", None)
        if simulation is None:
            return 0.85
        if not simulation.passed:
            return 0.0
        if simulation.elapsed_time_seconds <= 0:
            return 0.8
        time_limit = max(float(generated_level.level_document.timeLimitSeconds), 1.0)
        slack_ratio = (time_limit - simulation.elapsed_time_seconds) / time_limit
        return self._clamp(0.82 + min(max(slack_ratio, 0.0), 0.18))

    def _switch_clarity_score(self, road_shape_metadata: dict, visual_clarity_report) -> float:
        score = float(road_shape_metadata.get("switchClarityScore", 1.0))
        for issue in road_shape_metadata.get("issues", []):
            if str(issue).startswith("switch_choices_same_visual_direction"):
                score -= 0.35
            elif str(issue).startswith("required_and_wrong_route_first_segments_overlap"):
                score -= 0.30
            elif str(issue).startswith("same_switch_first_segments_overlap"):
                score -= 0.30
        for issue in visual_clarity_report.issues:
            if "switch" not in issue.code and "arrow" not in issue.code:
                continue
            if issue.severity == "error":
                score -= 0.35
            elif issue.severity == "warning":
                score -= 0.16
            else:
                score -= 0.04
        return self._clamp(score)

    def _mobile_tap_comfort(self, difficulty_metrics, preset: DifficultyPreset) -> float:
        if difficulty_metrics.required_tap_count == 0:
            return 1.0
        score = 1.0
        minimum_spacing = difficulty_metrics.minimum_reaction_window_before_required_switch
        average_spacing = difficulty_metrics.average_time_between_required_taps
        if minimum_spacing is not None and minimum_spacing < preset.min_tap_spacing_seconds:
            score -= 0.45
        if average_spacing is not None and average_spacing < preset.min_tap_spacing_seconds * 1.35:
            score -= 0.20
        if difficulty_metrics.required_tap_count > preset.required_tap_range[1]:
            score -= 0.15
        return self._clamp(score)

    def _visual_appeal(self, readability: float, visual_clarity_score: float, difficulty_metrics) -> float:
        crossing_penalty = difficulty_metrics.route_crossing_score * 0.25
        complexity = difficulty_metrics.visual_complexity_score
        if difficulty_metrics.estimated_band in {"tutorial", "easy"}:
            complexity_penalty = max(0.0, complexity - 0.35) * 0.6
        else:
            complexity_penalty = max(0.0, complexity - 0.75) * 0.35
        return self._clamp((readability * 0.45) + (visual_clarity_score * 0.45) + 0.10 - crossing_penalty - complexity_penalty)

    def _route_interest(self, generated_level) -> float:
        return self._route_interest_audit(generated_level)["score"]

    def _route_interest_audit(
        self,
        generated_level,
        diversity: dict[str, float] | None = None,
    ) -> dict:
        level = generated_level.level_document
        route = self._solution_route(generated_level)
        route_edges = set(zip(route, route[1:]))
        outgoing: dict[str, list[str]] = {}
        incoming: dict[str, list[str]] = {}
        for edge in level.graph.edges:
            outgoing.setdefault(edge.fromNodeID, []).append(edge.toNodeID)
            incoming.setdefault(edge.toNodeID, []).append(edge.fromNodeID)

        positions = {node.id: (float(node.x), float(node.y)) for node in level.graph.nodes}
        route_index = {node_id: index for index, node_id in enumerate(route)}
        metadata = getattr(generated_level, "abstract_solution_metadata", None)
        mechanic_tags = set(getattr(generated_level, "mechanic_tags", ()) or ())
        topology_class = getattr(generated_level, "topology_class", "") or ""
        route_node_counts = Counter(route)

        split_rejoin_count = sum(
            1
            for node_id in route
            if len(incoming.get(node_id, [])) >= 2
            and any(parent not in route_index or route_index[parent] < route_index[node_id] for parent in incoming[node_id])
        )
        off_route_branches = [
            (from_node_id, to_node_id)
            for from_node_id in route_index
            for to_node_id in outgoing.get(from_node_id, [])
            if (from_node_id, to_node_id) not in route_edges
        ]
        fake_shortcut_count = sum(
            1
            for from_node_id, to_node_id in off_route_branches
            if self._is_fake_shortcut_branch(
                to_node_id,
                level.destinationNodeID,
                level.packageNodeID,
                outgoing,
                route_index,
                route_index.get(from_node_id, 0),
            )
        )
        visually_tempting_wrong_branch_count = sum(
            1
            for from_node_id, to_node_id in off_route_branches
            if self._shortest_distance(to_node_id, level.destinationNodeID, outgoing) is not None
            and (
                self._shortest_distance(to_node_id, level.destinationNodeID, outgoing) or 99
            ) < max(len(route) - route_index.get(from_node_id, 0) - 1, 1)
        )
        package_index = route_index.get(level.packageNodeID)
        package_gate_tension = bool(
            package_index is not None
            and any(
                route_index.get(from_node_id, 0) < package_index
                and (
                    route_index.get(to_node_id, -1) > package_index
                    or self._can_reach_without(to_node_id, level.destinationNodeID, level.packageNodeID, outgoing)
                )
                for from_node_id, to_node_id in off_route_branches
            )
        )
        loop_or_revisit = (
            any(count > 1 for count in route_node_counts.values())
            or bool(metadata is not None and metadata.loop_count > 0)
            or self._has_cycle(outgoing)
        )
        meaningful_turns = self._meaningful_turn_count(route, positions)
        filler_node_count = self._filler_node_count(route, outgoing, incoming, level.packageNodeID, level.destinationNodeID)
        max_outgoing = max((len(targets) for targets in outgoing.values()), default=0)

        tags: list[str] = []
        bonuses: dict[str, float] = {}
        if fake_shortcut_count or "fake_shortcut" in mechanic_tags:
            tags.append("fake_shortcut")
            bonuses["fakeShortcut"] = 0.18
        if split_rejoin_count or "split_path" in mechanic_tags or "rejoin" in mechanic_tags:
            tags.append("split_rejoin")
            bonuses["branchRejoin"] = 0.15
        if "long_route" in mechanic_tags or "detour" in mechanic_tags:
            tags.append("correct_detour")
            bonuses["correctDetour"] = 0.13
        if package_gate_tension or "package_gate" in mechanic_tags:
            tags.append("package_gate_tension")
            bonuses["packageGateTension"] = 0.12
        if visually_tempting_wrong_branch_count:
            tags.append("tempting_wrong_branch")
            bonuses["temptingWrongBranch"] = 0.11
        if loop_or_revisit or any(tag in mechanic_tags for tag in {"loop", "revisit", "repeated_tap"}):
            tags.append("loop_or_revisit")
            bonuses["loopOrRevisit"] = 0.14
        if max_outgoing >= 3 or "hub" in mechanic_tags:
            tags.append("multi_exit_hub")
            bonuses["multiExitHub"] = 0.12
        if "two_phase" in mechanic_tags:
            tags.append("two_phase")
            bonuses["twoPhaseRoute"] = 0.10
        if meaningful_turns >= 2:
            tags.append("meaningful_turns")
            bonuses["meaningfulTurns"] = min(0.14, meaningful_turns * 0.035)
        if topology_class and topology_class not in {"straight_line", "single_branch", "two_switch_order"}:
            bonuses["distinctTopologyClass"] = 0.08

        penalties: list[str] = []
        penalty_values: dict[str, float] = {}
        mostly_straight_chain = (
            meaningful_turns <= 1
            and max_outgoing <= 2
            and not split_rejoin_count
            and not fake_shortcut_count
            and not loop_or_revisit
            and topology_class in {"", "straight_line", "single_branch", "two_switch_order"}
        )
        if mostly_straight_chain:
            penalties.append("boring_straight_switch_chain")
            penalty_values["straightSwitchChain"] = 0.24
        if filler_node_count:
            penalties.append("filler_route_nodes")
            penalty_values["fillerRouteNodes"] = min(0.18, filler_node_count * 0.06)
        if generated_level.switch_count >= 3 and len(tags) <= 1:
            penalties.append("difficulty_from_switch_count_only")
            penalty_values["switchCountOnlyDifficulty"] = 0.16
        nearby_topology_penalty = float((diversity or {}).get("nearbyTopologyClassPenalty", 0.0))
        if nearby_topology_penalty > 0:
            penalty_values["nearbyTopologyRepetition"] = min(0.16, nearby_topology_penalty * 0.6)

        score = 0.24
        score += min(generated_level.required_tap_count, 4) * 0.035
        score += min(max(len(route) - 4, 0), 6) * 0.025
        score += sum(bonuses.values())
        score -= sum(penalty_values.values())
        score = round(self._clamp(score), 4)
        return {
            "score": score,
            "tags": list(dict.fromkeys(tags)),
            "bonuses": {key: round(value, 4) for key, value in bonuses.items()},
            "penalties": tuple(dict.fromkeys(penalties)),
            "penaltyValues": {key: round(value, 4) for key, value in penalty_values.items()},
            "fakeShortcutPresent": bool(fake_shortcut_count or "fake_shortcut" in mechanic_tags),
            "branchRejoinPresent": bool(split_rejoin_count or "split_path" in mechanic_tags or "rejoin" in mechanic_tags),
            "packageGateTensionPresent": bool(package_gate_tension or "package_gate" in mechanic_tags),
            "loopRevisitPresent": bool(loop_or_revisit or any(tag in mechanic_tags for tag in {"loop", "revisit", "repeated_tap"})),
            "meaningfulTurnCount": meaningful_turns,
            "fillerNodeCount": filler_node_count,
            "offRouteBranchCount": len(off_route_branches),
            "visuallyTemptingWrongBranchCount": visually_tempting_wrong_branch_count,
            "repeatedTopologyPenalty": round(nearby_topology_penalty, 4),
        }

    def _solution_route(self, generated_level) -> tuple[str, ...]:
        metadata = getattr(generated_level, "abstract_solution_metadata", None)
        if metadata is not None and getattr(metadata, "required_path", None):
            return tuple(metadata.required_path)
        solution_metadata = dict(getattr(generated_level.solution, "_extra", {}).get("metadata", {}))
        route = solution_metadata.get("solutionRoute") or []
        if route:
            return tuple(route)
        return (generated_level.level_document.startNodeID, generated_level.level_document.destinationNodeID)

    def _is_fake_shortcut_branch(
        self,
        node_id: str,
        destination_node_id: str,
        package_node_id: str,
        outgoing: dict[str, list[str]],
        route_index: dict[str, int],
        from_index: int,
    ) -> bool:
        lowered = node_id.lower()
        if "shortcut" in lowered or "bypass" in lowered or "direct" in lowered:
            return True
        if self._can_reach_without(node_id, destination_node_id, package_node_id, outgoing):
            return True
        if node_id in route_index and route_index[node_id] > from_index + 1:
            return True
        return False

    def _shortest_distance(self, start_node_id: str, target_node_id: str, outgoing: dict[str, list[str]]) -> int | None:
        queue: deque[tuple[str, int]] = deque([(start_node_id, 0)])
        seen = {start_node_id}
        while queue:
            node_id, distance = queue.popleft()
            if node_id == target_node_id:
                return distance
            for next_node_id in outgoing.get(node_id, []):
                if next_node_id in seen:
                    continue
                seen.add(next_node_id)
                queue.append((next_node_id, distance + 1))
        return None

    def _can_reach_without(
        self,
        start_node_id: str,
        target_node_id: str,
        excluded_node_id: str,
        outgoing: dict[str, list[str]],
    ) -> bool:
        if start_node_id == excluded_node_id:
            return False
        queue: deque[str] = deque([start_node_id])
        seen = {start_node_id, excluded_node_id}
        while queue:
            node_id = queue.popleft()
            if node_id == target_node_id:
                return True
            for next_node_id in outgoing.get(node_id, []):
                if next_node_id in seen:
                    continue
                seen.add(next_node_id)
                queue.append(next_node_id)
        return False

    def _has_cycle(self, outgoing: dict[str, list[str]]) -> bool:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> bool:
            if node_id in visiting:
                return True
            if node_id in visited:
                return False
            visiting.add(node_id)
            for next_node_id in outgoing.get(node_id, []):
                if visit(next_node_id):
                    return True
            visiting.remove(node_id)
            visited.add(node_id)
            return False

        return any(visit(node_id) for node_id in outgoing)

    def _meaningful_turn_count(self, route: tuple[str, ...], positions: dict[str, tuple[float, float]]) -> int:
        turns = 0
        for previous_id, current_id, next_id in zip(route, route[1:], route[2:]):
            if previous_id not in positions or current_id not in positions or next_id not in positions:
                continue
            first = (
                positions[current_id][0] - positions[previous_id][0],
                positions[current_id][1] - positions[previous_id][1],
            )
            second = (
                positions[next_id][0] - positions[current_id][0],
                positions[next_id][1] - positions[current_id][1],
            )
            first_length = max((first[0] ** 2 + first[1] ** 2) ** 0.5, 1e-9)
            second_length = max((second[0] ** 2 + second[1] ** 2) ** 0.5, 1e-9)
            cosine = ((first[0] * second[0]) + (first[1] * second[1])) / (first_length * second_length)
            if cosine < 0.92:
                turns += 1
        return turns

    def _filler_node_count(
        self,
        route: tuple[str, ...],
        outgoing: dict[str, list[str]],
        incoming: dict[str, list[str]],
        package_node_id: str,
        destination_node_id: str,
    ) -> int:
        meaningful_terms = ("switch", "gate", "choice", "hub", "branch", "rejoin", "detour", "loop", "phase")
        count = 0
        for node_id in route[1:-1]:
            if node_id in {package_node_id, destination_node_id}:
                continue
            if any(term in node_id for term in meaningful_terms):
                continue
            if len(outgoing.get(node_id, [])) == 1 and len(incoming.get(node_id, [])) <= 1:
                count += 1
        return count

    def _topology_diversity(
        self,
        candidate: CandidateSignature | None,
        previous_signatures: list[CandidateSignature],
    ) -> dict[str, float]:
        if candidate is None or not previous_signatures:
            return {
                "topologyDiversityScore": 1.0,
                "nearbyMechanicTagPenalty": 0.0,
                "nearbyTopologyClassPenalty": 0.0,
                "nearbyFamilyStreakPenalty": 0.0,
                "diversityScore": 1.0,
            }

        topology_penalty = self._nearby_topology_penalty(candidate, previous_signatures)
        mechanic_penalty = self._nearby_mechanic_tag_penalty(candidate, previous_signatures)
        family_streak_penalty = self._nearby_family_streak_penalty(candidate, previous_signatures)
        topology_score = self._clamp(1.0 - topology_penalty)
        mechanic_score = self._clamp(1.0 - mechanic_penalty)
        diversity_score = self._clamp((topology_score * 0.55) + (mechanic_score * 0.45) - family_streak_penalty)
        return {
            "topologyDiversityScore": round(topology_score, 4),
            "nearbyMechanicTagPenalty": round(mechanic_penalty, 4),
            "nearbyTopologyClassPenalty": round(topology_penalty, 4),
            "nearbyFamilyStreakPenalty": round(family_streak_penalty, 4),
            "diversityScore": round(diversity_score, 4),
        }

    def _nearby_topology_penalty(
        self,
        candidate: CandidateSignature,
        previous_signatures: list[CandidateSignature],
    ) -> float:
        topology_class = candidate.topology_class
        if not topology_class:
            return 0.0
        recent = previous_signatures[-3:]
        repeat_count = sum(1 for signature in recent if signature.topology_class == topology_class)
        penalty = repeat_count * 0.08
        if recent and recent[-1].topology_class == topology_class:
            penalty += 0.22
        return self._clamp(min(penalty, 0.45))

    def _nearby_mechanic_tag_penalty(
        self,
        candidate: CandidateSignature,
        previous_signatures: list[CandidateSignature],
    ) -> float:
        candidate_tags = set(candidate.mechanic_tags)
        if not candidate_tags and not candidate.primary_mechanic_tag:
            return 0.0

        penalty = 0.0
        weighted_recent = [
            (signature, weight)
            for signature, weight in zip(reversed(previous_signatures[-5:]), (0.12, 0.09, 0.07, 0.05, 0.04))
        ]
        for signature, weight in weighted_recent:
            previous_tags = set(signature.mechanic_tags)
            if not candidate_tags or not previous_tags:
                continue
            overlap_ratio = len(candidate_tags & previous_tags) / max(len(candidate_tags), 1)
            penalty += overlap_ratio * weight
        previous = previous_signatures[-1]
        if candidate.primary_mechanic_tag and candidate.primary_mechanic_tag == previous.primary_mechanic_tag:
            penalty += 0.14
        return self._clamp(min(penalty, 0.45))

    def _nearby_family_streak_penalty(
        self,
        candidate: CandidateSignature,
        previous_signatures: list[CandidateSignature],
    ) -> float:
        if not candidate.template_name:
            return 0.0
        streak = 0
        for signature in reversed(previous_signatures):
            if signature.template_name != candidate.template_name:
                break
            streak += 1
        if streak == 0:
            return 0.0
        return round(min(0.12, 0.04 * streak), 4)

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))
