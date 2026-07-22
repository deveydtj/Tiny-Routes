from __future__ import annotations

from app.generation_config import GenerationConfig
from app.random_source import RandomSource
from app.recipes.recipe_family_registry import RecipeFamilyRegistry
from app.services.abstract_puzzle_solver_service import AbstractPuzzleSolverService
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
from app.services.generation_quality_service import GenerationQualityService
from app.services.level_generation_service import LevelGenerationService
from app.services.recipe_to_level_builder_service import RecipeToLevelBuilderService


class AlwaysTrueRandom(RandomSource):
    def bool(self, probability: float = 0.5) -> bool:
        return True


def test_phase4_presets_define_progression_targets() -> None:
    service = DifficultyService()
    tutorial = service.get_preset("tutorial")
    easy = service.get_preset("easy")
    medium = service.get_preset("medium")
    hard = service.get_preset("hard")
    expert = service.get_preset("expert")

    assert tutorial.route_length_range[1] < medium.route_length_range[1] < hard.route_length_range[1]
    assert tutorial.minimum_route_interest_score < medium.minimum_route_interest_score < hard.minimum_route_interest_score
    assert tutorial.map_size_profile_weights == (("standard_portrait", 1),)
    assert easy.map_size_profile_weights == (("standard_portrait", 1),)
    assert ("large_portrait", 1) in medium.map_size_profile_weights
    assert ("large_portrait", 3) in hard.map_size_profile_weights
    assert ("large_portrait", 3) in expert.map_size_profile_weights
    assert "split_rejoin" in hard.allowed_topology_classes
    assert "four_way_gate" in expert.allowed_topology_classes


def test_phase4_tutorial_and_easy_resolve_to_standard_portrait_only(tmp_path) -> None:
    service = LevelGenerationService()
    config = _config(tmp_path, difficulty="easy")
    recipe = _recipe("single_switch_package_choice", "level_004", service.difficulty_service.get_preset("easy"), 1)

    profiles = service._layout_size_profiles_for_recipe(
        config,
        service.difficulty_service.get_preset("easy"),
        recipe,
        AlwaysTrueRandom(1),
    )

    assert profiles == ["standard_portrait"]


def test_phase4_medium_can_include_large_portrait_for_interesting_routes(tmp_path) -> None:
    service = LevelGenerationService()
    preset = service.difficulty_service.get_preset("medium")
    config = _config(tmp_path, difficulty="medium")
    recipe = _recipe("split_path_rejoin", "level_016", preset, 2)

    profiles = service._layout_size_profiles_for_recipe(config, preset, recipe, AlwaysTrueRandom(2))

    assert profiles == ["standard_portrait", "large_portrait"]


def test_phase4_hard_and_expert_offer_large_portrait_candidates_for_complex_routes(tmp_path) -> None:
    service = LevelGenerationService()
    hard_preset = service.difficulty_service.get_preset("hard")
    expert_preset = service.difficulty_service.get_preset("expert")
    hard_recipe = _recipe("two_phase_route", "level_031", hard_preset, 3)
    expert_recipe = _recipe("four_way_ring", "level_046", expert_preset, 4)

    hard_profiles = service._layout_size_profiles_for_recipe(
        _config(tmp_path / "hard", difficulty="hard"),
        hard_preset,
        hard_recipe,
        RandomSource(3),
    )
    expert_profiles = service._layout_size_profiles_for_recipe(
        _config(tmp_path / "expert", difficulty="expert"),
        expert_preset,
        expert_recipe,
        RandomSource(4),
    )

    assert "large_portrait" in hard_profiles
    assert "large_portrait" in expert_profiles


def test_phase4_route_interest_strength_rises_from_medium_to_hard() -> None:
    medium = _quality_for_family("long_detour_gate", "medium", 21, 20)
    hard = _quality_for_family("long_detour_gate", "hard", 31, 30)

    assert medium.route_interest >= 0.42
    assert hard.route_interest >= medium.route_interest
    assert hard.details["presetContentFit"]["routeLength"] >= medium.details["presetContentFit"]["routeLength"]


def test_phase4_large_portrait_is_not_used_in_early_auto_levels(tmp_path) -> None:
    result = LevelGenerationService().generate(
        GenerationConfig(
            generator_architecture="v2_legacy",
            start_level_number=1,
            count=6,
            difficulty="auto",
            template_name="mixed",
            seed=20260604,
            dry_run=True,
            compare_against_existing=False,
            levels_output_dir=tmp_path / "levels",
            solutions_output_dir=tmp_path / "solutions",
            report_path=tmp_path / "report.md",
            json_report_path=tmp_path / "report.json",
            max_attempts_per_level=60,
            candidate_pool_size=3,
            recipe_pool_size=2,
            layouts_per_recipe=1,
            road_shapes_per_layout=1,
        )
    )

    assert result.passed is True, result.messages
    assert {(level.layout_metadata or {}).get("layoutSizeProfile") for level in result.accepted} == {
        "standard_portrait"
    }


def test_phase4_auto_generation_is_deterministic_with_difficulty_curve_profiles(tmp_path) -> None:
    first = _auto_batch(tmp_path / "a")
    second = _auto_batch(tmp_path / "b")

    assert first.passed is True
    assert second.passed is True
    assert [level.level_document.to_dict() for level in first.accepted] == [
        level.level_document.to_dict() for level in second.accepted
    ]
    assert [level.layout_metadata for level in first.accepted] == [level.layout_metadata for level in second.accepted]


def _config(tmp_path, *, difficulty: str) -> GenerationConfig:
    return GenerationConfig(
        generator_architecture="v2_legacy",
        start_level_number=12,
        count=1,
        difficulty=difficulty,
        template_name="mixed",
        dry_run=True,
        levels_output_dir=tmp_path / "levels",
        solutions_output_dir=tmp_path / "solutions",
        report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )


def _recipe(family_name: str, level_id: str, preset, seed: int):
    family = RecipeFamilyRegistry().get_family(family_name)
    return family.generate_recipe(level_id, preset, RandomSource(seed), family.variants[0])


def _quality_for_family(family_name: str, difficulty: str, level_number: int, seed: int):
    preset = DifficultyService().get_preset(difficulty)
    recipe = _recipe(family_name, f"level_{level_number:03d}", preset, seed)
    recipe = AbstractPuzzleSolverService().solve(recipe, preset)
    generated = RecipeToLevelBuilderService().build_level(
        recipe,
        level_number,
        seed=seed,
        layout_size_profile="standard_portrait",
    )
    generated.candidate_signature = CandidateSignatureService().signature_for(generated)
    return GenerationQualityService().score(generated, preset)


def _auto_batch(tmp_path):
    return LevelGenerationService().generate(
        GenerationConfig(
            generator_architecture="v2_legacy",
            start_level_number=11,
            count=4,
            difficulty="auto",
            template_name="mixed",
            seed=12345,
            dry_run=True,
            compare_against_existing=False,
            levels_output_dir=tmp_path / "levels",
            solutions_output_dir=tmp_path / "solutions",
            report_path=tmp_path / "report.md",
            json_report_path=tmp_path / "report.json",
            max_attempts_per_level=80,
            candidate_pool_size=4,
            recipe_pool_size=3,
            layouts_per_recipe=1,
            road_shapes_per_layout=1,
        )
    )
