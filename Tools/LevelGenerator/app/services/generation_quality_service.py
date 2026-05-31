from __future__ import annotations

from collections.abc import Iterable

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
    ) -> GenerationQualityScore:
        comparison_signatures = list(comparison_signatures)
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

        route_interest = self._route_interest(generated_level)
        campaign_pacing = self.campaign_pacing.score(
            signature,
            comparison_signatures,
            estimated_band=difficulty_metrics.estimated_band,
            target_band=preset.name,
        ) if signature is not None else None
        campaign_pacing_score = campaign_pacing.score if campaign_pacing is not None else 1.0
        if campaign_pacing is not None:
            penalties.extend(campaign_pacing.penalties)
        total = (
            (readability * 0.30)
            + (uniqueness * 0.20)
            + (difficulty_fit * 0.25)
            + (route_interest * 0.15)
            + (campaign_pacing_score * 0.10)
        )
        return GenerationQualityScore(
            total=round(self._clamp(total), 4),
            readability=round(readability, 4),
            uniqueness=round(uniqueness, 4),
            difficulty_fit=round(difficulty_fit, 4),
            route_interest=round(route_interest, 4),
            campaign_pacing=round(campaign_pacing_score, 4),
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

    def _route_interest(self, generated_level) -> float:
        score = 0.15
        score += min(generated_level.switch_count, 5) * 0.12
        score += min(generated_level.required_tap_count, 5) * 0.10
        score += min(generated_level.edge_count, 12) * 0.035
        score += min(max(generated_level.edge_count - generated_level.node_count, 0), 4) * 0.08
        return self._clamp(score)

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))
