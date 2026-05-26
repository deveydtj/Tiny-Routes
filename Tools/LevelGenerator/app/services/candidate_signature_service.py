from __future__ import annotations

import hashlib
import json
from typing import Any

from ..models.candidate_signature import CandidateSignature


class CandidateSignatureService:
    def signature_for(self, generated_level) -> CandidateSignature:
        level = generated_level.level_document
        solution = generated_level.solution
        normalized_edges = self._normalized_edges(level)
        normalized_positions = self._normalized_positions(level)
        tap_node_ids = [action.tapNodeID for action in sorted(solution.actions, key=lambda action: action.timeSeconds)]
        dead_end_count = sum(
            1
            for node in level.graph.nodes
            if not node.outgoingEdgeIDs and node.id != level.destinationNodeID
        )
        topology_payload = {
            "start": level.startNodeID,
            "package": level.packageNodeID,
            "destination": level.destinationNodeID,
            "edges": normalized_edges,
        }
        layout_payload = {
            "positions": normalized_positions,
        }
        solution_payload = {
            "tapNodeIDs": tap_node_ids,
        }
        return CandidateSignature(
            level_id=generated_level.level_id,
            template_name=generated_level.template_name,
            difficulty=generated_level.difficulty,
            node_count=len(level.graph.nodes),
            edge_count=len(level.graph.edges),
            switch_count=sum(1 for node in level.graph.nodes if len(node.outgoingEdgeIDs) > 1),
            required_tap_count=len(solution.actions),
            dead_end_count=dead_end_count,
            topology_hash=self._hash_payload(topology_payload),
            layout_hash=self._hash_payload(layout_payload),
            solution_hash=self._hash_payload(solution_payload),
            normalized_positions=normalized_positions,
        )

    def _normalized_edges(self, level_document) -> tuple[tuple[str, str], ...]:
        return tuple(
            sorted(
                (edge.fromNodeID, edge.toNodeID)
                for edge in level_document.graph.edges
            )
        )

    def _normalized_positions(self, level_document) -> tuple[tuple[str, float, float], ...]:
        raw_positions = {node.id: (float(node.x), float(node.y)) for node in level_document.graph.nodes}
        if not raw_positions:
            return ()

        xs = [position[0] for position in raw_positions.values()]
        ys = [position[1] for position in raw_positions.values()]
        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)
        width = max_x - min_x
        height = max_y - min_y

        normalized: list[tuple[str, float, float]] = []
        for node_id, (x, y) in raw_positions.items():
            normalized_x = 0.5 if width == 0 else (x - min_x) / width
            normalized_y = 0.5 if height == 0 else (y - min_y) / height
            normalized.append((node_id, round(normalized_x, 4), round(normalized_y, 4)))
        return tuple(sorted(normalized))

    def _hash_payload(self, payload: Any) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
