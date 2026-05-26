from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from ..models.candidate_signature import CandidateSignature


@dataclass(frozen=True)
class CandidateUniquenessResult:
    is_duplicate: bool
    score: float
    threshold: float
    matched_level_id: str | None = None
    reason_code: str | None = None
    message: str = ""


class CandidateUniquenessService:
    DEFAULT_DUPLICATE_THRESHOLD = 0.88

    def is_duplicate(
        self,
        candidate_signature: CandidateSignature,
        existing_signatures: Iterable[CandidateSignature],
    ) -> bool:
        return self.check_duplicate(candidate_signature, existing_signatures).is_duplicate

    def check_duplicate(
        self,
        candidate_signature: CandidateSignature,
        existing_signatures: Iterable[CandidateSignature],
        threshold: float | None = None,
    ) -> CandidateUniquenessResult:
        resolved_threshold = threshold if threshold is not None else self.DEFAULT_DUPLICATE_THRESHOLD
        best_result = CandidateUniquenessResult(
            is_duplicate=False,
            score=0.0,
            threshold=resolved_threshold,
            message="No comparable signatures.",
        )

        for existing_signature in existing_signatures:
            result = self._compare(candidate_signature, existing_signature, resolved_threshold)
            if result.is_duplicate:
                return result
            if result.score > best_result.score:
                best_result = result
        return best_result

    def similarity_score(
        self,
        candidate_signature: CandidateSignature,
        existing_signature: CandidateSignature,
    ) -> float:
        return self._score(candidate_signature, existing_signature)

    def _compare(
        self,
        candidate_signature: CandidateSignature,
        existing_signature: CandidateSignature,
        threshold: float,
    ) -> CandidateUniquenessResult:
        if (
            candidate_signature.topology_hash == existing_signature.topology_hash
            and candidate_signature.solution_hash == existing_signature.solution_hash
            and candidate_signature.layout_hash == existing_signature.layout_hash
        ):
            return CandidateUniquenessResult(
                is_duplicate=True,
                score=1.0,
                threshold=threshold,
                matched_level_id=existing_signature.level_id,
                reason_code="same_topology_and_solution",
                message=(
                    f"matches {existing_signature.level_id}: same topology, solution, and layout "
                    f"({candidate_signature.topology_hash[:8]}/{candidate_signature.solution_hash[:8]})"
                ),
            )

        score = self._score(candidate_signature, existing_signature)
        layout_score = self._layout_similarity(candidate_signature, existing_signature)
        if (
            candidate_signature.topology_hash == existing_signature.topology_hash
            and candidate_signature.template_name == existing_signature.template_name
            and layout_score >= threshold
        ):
            return CandidateUniquenessResult(
                is_duplicate=True,
                score=score,
                threshold=threshold,
                matched_level_id=existing_signature.level_id,
                reason_code="same_topology_and_layout",
                message=(
                    f"matches {existing_signature.level_id}: same template/topology and "
                    f"layout similarity {layout_score:.2f}"
                ),
            )

        if score >= threshold:
            return CandidateUniquenessResult(
                is_duplicate=True,
                score=score,
                threshold=threshold,
                matched_level_id=existing_signature.level_id,
                reason_code="similarity_threshold",
                message=f"matches {existing_signature.level_id}: similarity {score:.2f} >= {threshold:.2f}",
            )

        return CandidateUniquenessResult(
            is_duplicate=False,
            score=score,
            threshold=threshold,
            matched_level_id=existing_signature.level_id,
            message=f"closest match {existing_signature.level_id}: similarity {score:.2f}",
        )

    def _score(self, candidate: CandidateSignature, existing: CandidateSignature) -> float:
        score = 0.0
        if candidate.template_name == existing.template_name:
            score += 0.12
        if candidate.node_count == existing.node_count:
            score += 0.04
        if candidate.edge_count == existing.edge_count:
            score += 0.04
        if candidate.switch_count == existing.switch_count:
            score += 0.04
        if candidate.required_tap_count == existing.required_tap_count:
            score += 0.04
        if candidate.dead_end_count == existing.dead_end_count:
            score += 0.04
        if candidate.topology_hash == existing.topology_hash:
            score += 0.28
        if candidate.solution_hash == existing.solution_hash:
            score += 0.13
        score += 0.27 * self._layout_similarity(candidate, existing)
        return round(min(score, 1.0), 4)

    def _layout_similarity(self, candidate: CandidateSignature, existing: CandidateSignature) -> float:
        candidate_positions = {node_id: (x, y) for node_id, x, y in candidate.normalized_positions}
        existing_positions = {node_id: (x, y) for node_id, x, y in existing.normalized_positions}
        comparable_ids = sorted(set(candidate_positions) & set(existing_positions))
        if not comparable_ids:
            return 0.0

        distances = [
            math.hypot(
                candidate_positions[node_id][0] - existing_positions[node_id][0],
                candidate_positions[node_id][1] - existing_positions[node_id][1],
            )
            for node_id in comparable_ids
        ]
        average_distance = sum(distances) / len(distances)
        missing_ratio = 1.0 - (len(comparable_ids) / max(len(candidate_positions), len(existing_positions), 1))
        normalized_distance = min(1.0, (average_distance / math.sqrt(2)) + missing_ratio)
        return round(max(0.0, 1.0 - normalized_distance), 4)
