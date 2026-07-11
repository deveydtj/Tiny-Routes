from __future__ import annotations

from app.random_source import RandomSource
from app.level_editor_imports import LevelDocument, RouteEdgeModel, RouteGraphModel, RouteNodeModel, SolutionModel
from app.models.generated_level import GeneratedLevel
from app.models.decision_profile import DecisionProfile
from app.recipes.recipe_family_registry import RecipeFamilyRegistry
from app.services.abstract_puzzle_solver_service import AbstractPuzzleSolverService
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
from app.services.generation_quality_service import GenerationQualityService
from app.services.recipe_to_level_builder_service import RecipeToLevelBuilderService
from app.templates.package_gate_template import PackageGateTemplate
from app.templates.single_switch_template import SingleSwitchTemplate


def test_generation_quality_service_scores_valid_candidate() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = PackageGateTemplate().generate("level_012", 12, preset, RandomSource(3))
    generated.candidate_signature = CandidateSignatureService().signature_for(generated)

    score = GenerationQualityService().score(generated, preset)

    assert 0 < score.total <= 1
    assert score.difficulty_fit > 0.7
    assert 0 < score.abstract_mechanic_quality <= 1
    assert 0 < score.runtime_solvability <= 1
    assert 0 < score.switch_clarity <= 1
    assert 0 < score.mobile_tap_comfort <= 1
    assert 0 < score.visual_appeal <= 1
    assert "switchCount" in score.details
    assert "abstractMechanicQuality" in score.details
    assert "runtimeSolvability" in score.details
    assert "switchClarity" in score.details
    assert "mobileTapComfort" in score.details
    assert "visualAppeal" in score.details
    assert "presetContentFit" in score.details
    assert "diversityScore" in score.details
    assert score.diversity_score == 1.0


def test_generation_quality_penalizes_similar_candidates() -> None:
    preset = DifficultyService().get_preset("easy")
    first = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(2))
    second = SingleSwitchTemplate().generate("level_013", 13, preset, RandomSource(2))
    signature_service = CandidateSignatureService()
    first.candidate_signature = signature_service.signature_for(first)
    second.candidate_signature = signature_service.signature_for(second)

    score = GenerationQualityService().score(second, preset, [first.candidate_signature])

    assert score.uniqueness < 0.2
    assert "similar_to_existing_candidate" in score.penalties


def test_generation_quality_penalizes_adjacent_duplicate_mechanics() -> None:
    preset = DifficultyService().get_preset("easy")
    first = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(2))
    second = SingleSwitchTemplate().generate("level_013", 13, preset, RandomSource(3))
    signature_service = CandidateSignatureService()
    first.candidate_signature = signature_service.signature_for(first)
    second.candidate_signature = signature_service.signature_for(second)

    score = GenerationQualityService().score(second, preset, [first.candidate_signature])

    assert score.campaign_pacing < 1
    assert "campaign_repeated_recipe_family" in score.penalties
    assert score.details["campaignPacing"]["previousLevelID"] == "level_012"


def test_generation_quality_penalizes_adjacent_repeated_topology_class() -> None:
    preset = DifficultyService().get_preset("easy")
    previous = _recipe_candidate("single_switch", "level_012", 12, preset, seed=2)
    candidate = _recipe_candidate("safe_dead_end_choice", "level_013", 13, preset, seed=3)

    score = GenerationQualityService().score(candidate, preset, [previous.candidate_signature])

    assert previous.candidate_signature.topology_class == candidate.candidate_signature.topology_class
    assert score.nearby_topology_class_penalty > 0
    assert score.topology_diversity_score < 1
    assert score.diversity_score < 1
    assert "nearby_topology_class_repetition" in score.penalties
    assert candidate.candidate_signature.diversity_score == score.diversity_score


def test_generation_quality_penalizes_nearby_repeated_mechanic_tags() -> None:
    preset = DifficultyService().get_preset("medium")
    previous = [
        _recipe_candidate("package_gate", "level_011", 11, preset, seed=2).candidate_signature,
        _recipe_candidate("package_gate_double_choice", "level_012", 12, preset, seed=3).candidate_signature,
    ]
    candidate = _recipe_candidate("package_gate_double_choice", "level_013", 13, preset, seed=4)

    score = GenerationQualityService().score(candidate, preset, previous)

    assert "package_gate" in candidate.candidate_signature.mechanic_tags
    assert score.nearby_mechanic_tag_penalty > 0
    assert score.diversity_score < 1
    assert "nearby_mechanic_tag_repetition" in score.penalties


def test_generation_quality_rewards_target_difficulty_fit() -> None:
    difficulty_service = DifficultyService()
    easy_preset = difficulty_service.get_preset("easy")
    hard_preset = difficulty_service.get_preset("hard")
    generated = SingleSwitchTemplate().generate("level_012", 12, easy_preset, RandomSource(2))
    generated.candidate_signature = CandidateSignatureService().signature_for(generated)
    quality_service = GenerationQualityService()

    easy_score = quality_service.score(generated, easy_preset)
    hard_score = quality_service.score(generated, hard_preset)

    assert easy_score.difficulty_fit > hard_score.difficulty_fit
    assert easy_score.total > hard_score.total


def test_generation_quality_visual_clarity_warnings_lower_readability_score() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = _parallel_warning_generated_level()

    score = GenerationQualityService().score(generated, preset)

    assert score.details["visualClarityScore"] < 1
    assert "difficultyMetrics" in score.details
    assert score.estimated_difficulty_band is not None
    assert score.readability < 1
    assert "long_parallel_road_segments_visually_merge" in score.penalties


def test_mechanic_tag_without_graph_evidence_does_not_improve_quality() -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(2))
    generated.candidate_signature = CandidateSignatureService().signature_for(generated)
    quality = GenerationQualityService()
    baseline = quality.score(generated, preset)

    generated.mechanic_tags = (*generated.mechanic_tags, "package_gate", "revisit", "fake_shortcut")
    tagged = quality.score(generated, preset)

    assert tagged.route_interest == baseline.route_interest
    assert tagged.details["routeInterest"] == baseline.details["routeInterest"]


def test_measured_revisit_and_state_reversal_improve_route_interest() -> None:
    preset = DifficultyService().get_preset("medium")
    generated = _recipe_candidate("return_loop_intro", "level_022", 22, preset, seed=6)
    quality = GenerationQualityService()
    without_evidence = quality.score(generated, preset)

    generated.decision_profile = DecisionProfile(
        required_decision_count=max(3, generated.required_tap_count),
        unique_switch_count=max(1, generated.switch_count),
        route_revisit_count=1,
        switch_state_change_on_revisit_count=1,
        ordered_dependency_count=1,
        independent_decision_ratio=0.25,
        minimum_window_seconds=1.1,
    )
    with_evidence = quality.score(generated, preset)

    assert with_evidence.route_interest > without_evidence.route_interest
    assert with_evidence.details["routeInterest"]["stateReversalPresent"] is True


def _parallel_warning_generated_level() -> GeneratedLevel:
    level = LevelDocument(
        id="level_visual_warning",
        name="Visual Warning",
        graph=RouteGraphModel(
            nodes=[
                RouteNodeModel(id="start", x=0.0, y=0.0, outgoingEdgeIDs=["e_start_package"]),
                RouteNodeModel(id="package", x=1.0, y=0.0, outgoingEdgeIDs=["e_package_destination"]),
                RouteNodeModel(id="destination", x=2.0, y=0.0, outgoingEdgeIDs=[]),
                RouteNodeModel(id="side_a", x=0.0, y=1.0, outgoingEdgeIDs=["e_side_ab"]),
                RouteNodeModel(id="side_b", x=1.0, y=1.0, outgoingEdgeIDs=[]),
                RouteNodeModel(id="side_c", x=0.0, y=1.1, outgoingEdgeIDs=["e_side_cd"]),
                RouteNodeModel(id="side_d", x=1.0, y=1.1, outgoingEdgeIDs=[]),
            ],
            edges=[
                RouteEdgeModel(id="e_start_package", fromNodeID="start", toNodeID="package"),
                RouteEdgeModel(id="e_package_destination", fromNodeID="package", toNodeID="destination"),
                RouteEdgeModel(id="e_side_ab", fromNodeID="side_a", toNodeID="side_b"),
                RouteEdgeModel(id="e_side_cd", fromNodeID="side_c", toNodeID="side_d"),
            ],
        ),
        startNodeID="start",
        packageNodeID="package",
        destinationNodeID="destination",
        timeLimitSeconds=30,
        parTaps=0,
    )
    return GeneratedLevel(
        level_document=level,
        solution=SolutionModel(
            levelID=level.id,
            description="No taps.",
            expectedOutcome="completed",
            maxTaps=0,
            requiresWithinTimeLimit=True,
            actions=[],
        ),
        template_name="visual_warning",
        difficulty="easy",
        seed=1,
    )


def _recipe_candidate(family_name: str, level_id: str, level_number: int, preset, seed: int) -> GeneratedLevel:
    family = RecipeFamilyRegistry().get_family(family_name)
    recipe = family.generate_recipe(level_id, preset, RandomSource(seed), family.variants[0])
    recipe = AbstractPuzzleSolverService().solve(recipe, preset)
    generated = RecipeToLevelBuilderService().build_level(recipe, level_number, seed=seed)
    generated.candidate_signature = CandidateSignatureService().signature_for(generated)
    return generated
