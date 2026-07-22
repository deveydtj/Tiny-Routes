from __future__ import annotations

import json
from pathlib import Path

from ..repositories.existing_level_repository import ExistingLevelRepository


class ProductionManifestService:
    def rebuild(self, levels_dir: Path, solutions_dir: Path, output_path: Path) -> Path:
        load_result = ExistingLevelRepository().load_existing_levels(levels_dir, solutions_dir)
        entries = []
        for record in load_result.records:
            generated = record.generated_level
            signature = generated.candidate_signature
            entries.append(
                {
                    "levelID": generated.level_id,
                    "name": generated.level_document.name,
                    "difficultyEstimate": self._difficulty_estimate(generated),
                    "nodes": generated.node_count,
                    "edges": generated.edge_count,
                    "switches": generated.switch_count,
                    "tapCount": generated.required_tap_count,
                    "deadEndCount": signature.dead_end_count if signature else 0,
                    "template": signature.template_name if signature else "existing",
                    "topologyHash": signature.topology_hash if signature else None,
                    "layoutHash": signature.layout_hash if signature else None,
                    "solutionHash": signature.solution_hash if signature else None,
                    "normalizedPositions": list(signature.normalized_positions) if signature else [],
                    "blueprintArchetype": signature.blueprint_archetype if signature else "",
                    "objectiveCount": signature.objective_count if signature else 0,
                    "objectiveKinds": list(signature.objective_kinds) if signature else [],
                    "dependencyDAGSignature": signature.dependency_dag_signature if signature else "",
                    "adaptiveDecisionPattern": list(signature.adaptive_decision_pattern) if signature else [],
                    "stateTransitionPattern": list(signature.state_transition_pattern) if signature else [],
                    "staticPolicyProofSignature": signature.static_policy_proof_signature if signature else "",
                    "agentPerformanceProfile": list(signature.agent_performance_profile) if signature else [],
                    "revisitPattern": list(signature.revisit_pattern) if signature else [],
                    "successFailureDistribution": list(signature.success_failure_distribution) if signature else [],
                    "optimalStrategySignature": signature.optimal_strategy_signature if signature else "",
                    "roadStateVisualSignature": signature.road_state_visual_signature if signature else "",
                    "structuralBehaviorSignature": signature.structural_behavior_signature if signature else "",
                }
            )
        payload = {
            "levels": entries,
            "warnings": load_result.warnings,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return output_path

    def _difficulty_estimate(self, generated) -> str:
        if generated.required_tap_count == 0:
            return "tutorial"
        if generated.required_tap_count <= 2 and generated.switch_count <= 2:
            return "easy"
        if generated.required_tap_count <= 3 and generated.switch_count <= 3:
            return "medium"
        return "hard"
