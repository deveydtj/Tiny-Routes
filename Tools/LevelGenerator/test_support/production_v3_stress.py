"""Nightly and release-stress harness for the exact V3 production path."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from test_support.production_v3_smoke import (
    ProductionV3SmokeEvidence,
    run_campaign_regression,
)


_DEFAULT_SEED = 20_202


@dataclass(frozen=True)
class ProductionV3CampaignStressSummary:
    seed: int
    passed: bool
    deterministic: bool
    requested_count: int
    selected_count: int
    fallback_count: int
    stage_path_violation_count: int
    behavior_duplicate_count: int
    one_tap_or_less_count: int
    static_policy_solvable_count: int
    unproven_optimal_count: int
    parity_error_count: int
    production_unchanged: bool
    staged: bool
    fingerprint: str

    @classmethod
    def from_evidence(
        cls,
        evidence: ProductionV3SmokeEvidence,
    ) -> "ProductionV3CampaignStressSummary":
        return cls(
            seed=evidence.seed,
            passed=evidence.passed,
            deterministic=evidence.deterministic,
            requested_count=evidence.requested_count,
            selected_count=evidence.selected_count,
            fallback_count=evidence.fallback_count,
            stage_path_violation_count=evidence.stage_path_violation_count,
            behavior_duplicate_count=evidence.behavior_duplicate_count,
            one_tap_or_less_count=evidence.one_tap_or_less_count,
            static_policy_solvable_count=evidence.static_policy_solvable_count,
            unproven_optimal_count=evidence.unproven_optimal_count,
            parity_error_count=evidence.parity_error_count,
            production_unchanged=evidence.production_unchanged,
            staged=evidence.staging_artifact_count > 0,
            fingerprint=evidence.fingerprint,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "passed": self.passed,
            "deterministic": self.deterministic,
            "requestedCount": self.requested_count,
            "selectedCount": self.selected_count,
            "fallbackCount": self.fallback_count,
            "stagePathViolationCount": self.stage_path_violation_count,
            "behaviorDuplicateCount": self.behavior_duplicate_count,
            "oneTapOrLessCount": self.one_tap_or_less_count,
            "staticPolicySolvableCount": self.static_policy_solvable_count,
            "unprovenOptimalCount": self.unproven_optimal_count,
            "parityErrorCount": self.parity_error_count,
            "productionUnchanged": self.production_unchanged,
            "staged": self.staged,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True)
class ProductionV3StressEvidence:
    passed: bool
    generator_architecture: str
    generator_architecture_version: int
    start_level_number: int
    difficulty: str
    campaign_count: int
    executed_campaign_count: int
    levels_per_campaign: int
    requested_level_count: int
    selected_level_count: int
    complete_batch_count: int
    deterministic_batch_count: int
    staged_batch_count: int
    fallback_count: int
    stage_path_violation_count: int
    behavior_duplicate_count: int
    one_tap_or_less_count: int
    static_policy_solvable_count: int
    unproven_optimal_count: int
    parity_error_count: int
    production_mutation_count: int
    seeds: tuple[int, ...]
    campaign_summaries: tuple[ProductionV3CampaignStressSummary, ...]
    fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "generatorArchitecture": self.generator_architecture,
            "generatorArchitectureVersion": self.generator_architecture_version,
            "startLevelNumber": self.start_level_number,
            "difficulty": self.difficulty,
            "campaignCount": self.campaign_count,
            "executedCampaignCount": self.executed_campaign_count,
            "levelsPerCampaign": self.levels_per_campaign,
            "requestedLevelCount": self.requested_level_count,
            "selectedLevelCount": self.selected_level_count,
            "completeBatchCount": self.complete_batch_count,
            "deterministicBatchCount": self.deterministic_batch_count,
            "stagedBatchCount": self.staged_batch_count,
            "fallbackCount": self.fallback_count,
            "stagePathViolationCount": self.stage_path_violation_count,
            "behaviorDuplicateCount": self.behavior_duplicate_count,
            "oneTapOrLessCount": self.one_tap_or_less_count,
            "staticPolicySolvableCount": self.static_policy_solvable_count,
            "unprovenOptimalCount": self.unproven_optimal_count,
            "parityErrorCount": self.parity_error_count,
            "productionMutationCount": self.production_mutation_count,
            "seeds": list(self.seeds),
            "campaigns": [item.to_dict() for item in self.campaign_summaries],
            "fingerprint": self.fingerprint,
        }


def parse_seed_range(value: str) -> tuple[int, ...]:
    """Parse an inclusive ``FIRST-LAST`` release-stress seed range."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError("seed range must not be empty")
    parts = value.strip().split("-")
    if len(parts) != 2 or any(not part.strip() for part in parts):
        raise ValueError("seed range must use FIRST-LAST syntax")
    try:
        first, last = (int(part) for part in parts)
    except ValueError as error:
        raise ValueError("seed range bounds must be integers") from error
    if last < first:
        raise ValueError("seed range must be ascending")
    return tuple(range(first, last + 1))


def resolve_campaign_seeds(
    campaign_count: int,
    *,
    seed: int | None = None,
    seed_range: str | None = None,
) -> tuple[int, ...]:
    if not isinstance(campaign_count, int) or isinstance(campaign_count, bool):
        raise ValueError("campaign_count must be a positive integer")
    if campaign_count <= 0:
        raise ValueError("campaign_count must be a positive integer")
    if seed is not None and seed_range is not None:
        raise ValueError("use either seed or seed_range, not both")
    if seed_range is not None:
        seeds = parse_seed_range(seed_range)
        if len(seeds) != campaign_count:
            raise ValueError(
                "seed range size must exactly match campaign_count "
                f"({len(seeds)} != {campaign_count})"
            )
        return seeds
    first = _DEFAULT_SEED if seed is None else seed
    if not isinstance(first, int) or isinstance(first, bool):
        raise ValueError("seed must be an integer")
    return tuple(first + offset for offset in range(campaign_count))


def run_production_v3_stress(
    root: Path,
    *,
    campaign_count: int,
    levels_per_campaign: int,
    start_level_number: int = 901,
    difficulty: str = "easy",
    seeds: Iterable[int],
    retain_campaign_artifacts: bool = False,
) -> ProductionV3StressEvidence:
    """Run deterministic complete campaigns through ProductionCampaignService."""

    if (
        not isinstance(campaign_count, int)
        or isinstance(campaign_count, bool)
        or campaign_count <= 0
    ):
        raise ValueError("campaign_count must be a positive integer")
    if (
        not isinstance(levels_per_campaign, int)
        or isinstance(levels_per_campaign, bool)
        or levels_per_campaign <= 0
    ):
        raise ValueError("levels_per_campaign must be a positive integer")
    resolved_seeds = tuple(seeds)
    if len(resolved_seeds) != campaign_count:
        raise ValueError("seed count must exactly match campaign_count")
    if any(
        not isinstance(seed, int) or isinstance(seed, bool)
        for seed in resolved_seeds
    ):
        raise ValueError("campaign seeds must be integers")
    if len(resolved_seeds) != len(set(resolved_seeds)):
        raise ValueError("campaign seeds must be unique")
    if not isinstance(retain_campaign_artifacts, bool):
        raise ValueError("retain_campaign_artifacts must be a Boolean")

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    summaries = []
    for campaign_index, seed in enumerate(resolved_seeds):
        campaign_root = root / f"campaign_{campaign_index + 1:03d}_seed_{seed}"
        evidence = run_campaign_regression(
            campaign_root,
            start_level_number=start_level_number,
            level_count=levels_per_campaign,
            seed=seed,
            difficulty=difficulty,
        )
        summaries.append(ProductionV3CampaignStressSummary.from_evidence(evidence))
        if evidence.passed and not retain_campaign_artifacts:
            shutil.rmtree(campaign_root)
        if not evidence.passed:
            break

    campaign_summaries = tuple(summaries)
    executed_campaign_count = len(campaign_summaries)
    requested_level_count = campaign_count * levels_per_campaign
    selected_level_count = sum(item.selected_count for item in campaign_summaries)
    complete_batch_count = sum(
        item.passed
        and item.requested_count == item.selected_count == levels_per_campaign
        for item in campaign_summaries
    )
    deterministic_batch_count = sum(item.deterministic for item in campaign_summaries)
    staged_batch_count = sum(item.staged for item in campaign_summaries)
    fallback_count = sum(item.fallback_count for item in campaign_summaries)
    stage_path_violation_count = sum(
        item.stage_path_violation_count for item in campaign_summaries
    )
    behavior_duplicate_count = sum(
        item.behavior_duplicate_count for item in campaign_summaries
    )
    one_tap_or_less_count = sum(
        item.one_tap_or_less_count for item in campaign_summaries
    )
    static_policy_solvable_count = sum(
        item.static_policy_solvable_count for item in campaign_summaries
    )
    unproven_optimal_count = sum(
        item.unproven_optimal_count for item in campaign_summaries
    )
    parity_error_count = sum(item.parity_error_count for item in campaign_summaries)
    production_mutation_count = sum(
        not item.production_unchanged for item in campaign_summaries
    )
    fingerprint_payload = {
        "architecture": "production_v3",
        "architectureVersion": 3,
        "startLevelNumber": start_level_number,
        "difficulty": difficulty,
        "campaignCount": campaign_count,
        "executedCampaignCount": executed_campaign_count,
        "levelsPerCampaign": levels_per_campaign,
        "campaigns": [
            (item.seed, item.fingerprint, item.selected_count)
            for item in campaign_summaries
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    passed = (
        complete_batch_count == campaign_count
        and deterministic_batch_count == campaign_count
        and staged_batch_count == campaign_count
        and selected_level_count == requested_level_count
        and fallback_count == 0
        and stage_path_violation_count == 0
        and behavior_duplicate_count == 0
        and one_tap_or_less_count == 0
        and static_policy_solvable_count == 0
        and unproven_optimal_count == 0
        and parity_error_count == 0
        and production_mutation_count == 0
    )
    return ProductionV3StressEvidence(
        passed=passed,
        generator_architecture="production_v3",
        generator_architecture_version=3,
        start_level_number=start_level_number,
        difficulty=difficulty,
        campaign_count=campaign_count,
        executed_campaign_count=executed_campaign_count,
        levels_per_campaign=levels_per_campaign,
        requested_level_count=requested_level_count,
        selected_level_count=selected_level_count,
        complete_batch_count=complete_batch_count,
        deterministic_batch_count=deterministic_batch_count,
        staged_batch_count=staged_batch_count,
        fallback_count=fallback_count,
        stage_path_violation_count=stage_path_violation_count,
        behavior_duplicate_count=behavior_duplicate_count,
        one_tap_or_less_count=one_tap_or_less_count,
        static_policy_solvable_count=static_policy_solvable_count,
        unproven_optimal_count=unproven_optimal_count,
        parity_error_count=parity_error_count,
        production_mutation_count=production_mutation_count,
        seeds=resolved_seeds,
        campaign_summaries=campaign_summaries,
        fingerprint=fingerprint,
    )
