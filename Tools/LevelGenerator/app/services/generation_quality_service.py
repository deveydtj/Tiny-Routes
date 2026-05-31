from __future__ import annotations

from collections.abc import Iterable

from ..models.candidate_signature import CandidateSignature
from ..models.difficulty_preset import DifficultyPreset
from ..models.generation_quality import GenerationQualityScore
from .candidate_uniqueness_service import CandidateUniquenessService
from .difficulty_service import DifficultyService
from .graph_layout_service import GraphLayoutService


class GenerationQualityService:
    def __init__(self) -> None:
        self.layout = GraphLayoutService()
        self.uniqueness = CandidateUniquenessService()
        self.difficulty = DifficultyService()

    def score(
        self,
        generated_level,
        preset: DifficultyPreset,
        comparison_signatures: Iterable[CandidateSignature] = (),
    ) -> GenerationQualityScore:
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

        difficulty_issues = self.difficulty.check_candidate_matches_difficulty(level, solution, preset)
        difficulty_fit = 1.0 if not difficulty_issues else 0.45
        penalties.extend(difficulty_issues)

        route_interest = self._route_interest(generated_level)
        total = (
            (readability * 0.35)
            + (uniqueness * 0.25)
            + (difficulty_fit * 0.25)
            + (route_interest * 0.15)
        )
        return GenerationQualityScore(
            total=round(self._clamp(total), 4),
            readability=round(readability, 4),
            uniqueness=round(uniqueness, 4),
            difficulty_fit=round(difficulty_fit, 4),
            route_interest=round(route_interest, 4),
            penalties=tuple(dict.fromkeys(penalties)),
            details={
                **readability_details,
                "maxSimilarity": round(max_similarity, 4),
                "nodeCount": generated_level.node_count,
                "edgeCount": generated_level.edge_count,
                "switchCount": generated_level.switch_count,
                "requiredTapCount": generated_level.required_tap_count,
                "roadShapeScore": round(road_shape_score, 4),
                "roadShapeIssues": list(road_shape_metadata.get("issues", [])),
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
