from __future__ import annotations

import json

from app.generation_config import GenerationConfig
from app.models.generation_quality import GenerationQualityScore
from app.map_import.osm_seed_importer import MapSeedEdge, MapSeedGraph, MapSeedNode
from app.random_source import RandomSource
from app.repositories.generated_level_repository import GeneratedLevelRepository
from app.services.generated_level_validation_service import GeneratorValidationMessage, GeneratorValidationResult
from app.services.level_generation_service import LevelGenerationService
from app.templates.single_switch_template import SingleSwitchTemplate


def _config(tmp_path, **kwargs) -> GenerationConfig:
    return GenerationConfig(
        start_level_number=kwargs.pop("start_level_number", 12),
        count=kwargs.pop("count", 1),
        difficulty=kwargs.pop("difficulty", "tutorial"),
        template_name=kwargs.pop("template_name", "straight_delivery"),
        recipe_pool_size=kwargs.pop("recipe_pool_size", 1),
        layouts_per_recipe=kwargs.pop("layouts_per_recipe", 1),
        road_shapes_per_layout=kwargs.pop("road_shapes_per_layout", 1),
        candidate_pool_size=kwargs.pop("candidate_pool_size", 1),
        seed=kwargs.pop("seed", 1),
        dry_run=kwargs.pop("dry_run", False),
        overwrite=kwargs.pop("overwrite", False),
        run_swift_tests=False,
        levels_output_dir=tmp_path / "levels",
        solutions_output_dir=tmp_path / "solutions",
        report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
        **kwargs,
    )


def test_generation_service_generates_one_level_and_solution(tmp_path) -> None:
    result = LevelGenerationService().generate(_config(tmp_path))

    assert result.passed is True
    assert (tmp_path / "levels" / "level_012.json").exists()
    assert (tmp_path / "solutions" / "level_012.solution.json").exists()
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "report.json").exists()


def test_generation_service_dry_run_writes_no_levels(tmp_path) -> None:
    result = LevelGenerationService().generate(_config(tmp_path, dry_run=True))

    assert result.passed is True
    assert not (tmp_path / "levels").exists()
    assert not (tmp_path / "solutions").exists()
    assert (tmp_path / "report.md").exists()


def test_generation_service_dry_run_ignores_existing_output_files(tmp_path) -> None:
    (tmp_path / "levels").mkdir()
    (tmp_path / "solutions").mkdir()
    (tmp_path / "levels" / "level_012.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "solutions" / "level_012.solution.json").write_text("{}\n", encoding="utf-8")

    result = LevelGenerationService().generate(_config(tmp_path, dry_run=True))

    assert result.passed is True
    assert result.accepted[0].level_id == "level_012"


def test_generation_service_refuses_collision_without_overwrite(tmp_path) -> None:
    (tmp_path / "levels").mkdir()
    (tmp_path / "solutions").mkdir()
    (tmp_path / "levels" / "level_012.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "solutions" / "level_012.solution.json").write_text("{}\n", encoding="utf-8")

    result = LevelGenerationService().generate(_config(tmp_path))

    assert result.passed is False
    assert "Refusing to overwrite" in result.messages[0]


def test_generation_service_is_deterministic_for_seed(tmp_path) -> None:
    first = LevelGenerationService().generate(_config(tmp_path / "a", dry_run=True, seed=42))
    second = LevelGenerationService().generate(_config(tmp_path / "b", dry_run=True, seed=42))

    assert first.accepted[0].level_document.to_dict() == second.accepted[0].level_document.to_dict()
    assert first.accepted[0].solution.to_dict() == second.accepted[0].solution.to_dict()


def test_generation_service_retries_after_rejected_candidate(tmp_path) -> None:
    service = LevelGenerationService()
    calls = {"count": 0}

    def fake_validate(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return GeneratorValidationResult(
                [GeneratorValidationMessage(severity="error", code="forced_failure", message="forced")]
            )
        return GeneratorValidationResult([])

    service.validation_service.validate = fake_validate
    result = service.generate(_config(tmp_path, dry_run=True, candidate_pool_size=1))

    assert result.passed is True
    assert result.rejection_reason_counts["forced_failure"] == 1
    assert calls["count"] == 2


def test_generation_service_rejects_duplicate_batch_candidates(tmp_path) -> None:
    service = LevelGenerationService()

    class FixedSingleSwitchTemplate:
        requires_swift_validation = False

        def generate(self, level_id, level_number, preset, rng):
            return SingleSwitchTemplate().generate(level_id, level_number, preset, RandomSource(2))

    service.template_registry.choose = lambda *args, **kwargs: FixedSingleSwitchTemplate()

    result = service.generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            count=2,
            max_attempts_per_level=2,
            dry_run=True,
            generation_mode="legacy_template",
            candidate_pool_size=1,
        )
    )

    assert result.passed is False
    assert result.accepted[0].level_id == "level_012"
    assert result.rejection_reason_counts["candidate_too_similar_to_batch"] == 2


def test_generation_service_requires_swift_tests_for_hard_mixed_production_writes(tmp_path) -> None:
    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            difficulty="hard",
            template_name="mixed",
            dry_run=False,
        )
    )

    assert result.passed is False
    assert "--swift-tests" in result.messages[0]


def test_generation_service_requires_swift_tests_for_hard_production_writes(tmp_path) -> None:
    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            difficulty="hard",
            template_name="multi_switch_chain",
            dry_run=False,
        )
    )

    assert result.passed is False
    assert "--swift-tests" in result.messages[0]
    assert not (tmp_path / "levels").exists()


def test_generation_service_generates_unique_medium_mixed_batch(tmp_path) -> None:
    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            difficulty="medium",
            template_name="mixed",
            count=10,
            seed=20260525,
            dry_run=True,
        )
    )
    signatures = {
        (
            level.candidate_signature.topology_hash,
            level.candidate_signature.layout_hash,
            level.candidate_signature.solution_hash,
        )
        for level in result.accepted
    }

    assert result.passed is True
    assert len(result.accepted) == 10
    assert len(signatures) == len(result.accepted)


def test_generation_service_rejects_candidates_similar_to_existing_levels(tmp_path) -> None:
    preset_result = LevelGenerationService()
    preset = preset_result.difficulty_service.get_preset("easy")
    existing = SingleSwitchTemplate().generate("level_001", 1, preset, RandomSource(2))
    writer = GeneratedLevelRepository()
    writer.write_level(existing.level_document, tmp_path / "levels" / "level_001.json")
    writer.write_solution(existing.solution, tmp_path / "solutions" / "level_001.solution.json")

    service = LevelGenerationService()

    class FixedSingleSwitchTemplate:
        requires_swift_validation = False

        def generate(self, level_id, level_number, preset, rng):
            return SingleSwitchTemplate().generate(level_id, level_number, preset, RandomSource(2))

    service.template_registry.choose = lambda *args, **kwargs: FixedSingleSwitchTemplate()

    result = service.generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            max_attempts_per_level=1,
            dry_run=True,
            generation_mode="legacy_template",
            candidate_pool_size=1,
        )
    )

    assert result.passed is False
    assert result.rejection_reason_counts["candidate_too_similar_to_existing"] == 1
    assert "matches level_001" in result.messages[-2]


def test_generation_service_can_skip_existing_similarity_check(tmp_path) -> None:
    preset_result = LevelGenerationService()
    preset = preset_result.difficulty_service.get_preset("easy")
    existing = SingleSwitchTemplate().generate("level_001", 1, preset, RandomSource(2))
    writer = GeneratedLevelRepository()
    writer.write_level(existing.level_document, tmp_path / "levels" / "level_001.json")
    writer.write_solution(existing.solution, tmp_path / "solutions" / "level_001.solution.json")

    service = LevelGenerationService()
    service.template_registry.choose = lambda *args, **kwargs: SingleSwitchTemplate()

    result = service.generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            seed=2,
            dry_run=True,
            compare_against_existing=False,
            generation_mode="legacy_template",
            candidate_pool_size=1,
        )
    )

    assert result.passed is True
    assert result.rejection_reason_counts.get("candidate_too_similar_to_existing") is None


def test_generation_service_selects_highest_quality_candidate_from_pool(tmp_path) -> None:
    service = LevelGenerationService()
    seeds = iter([2, 3])

    class SequenceTemplate:
        requires_swift_validation = False

        def generate(self, level_id, level_number, preset, rng):
            return SingleSwitchTemplate().generate(level_id, level_number, preset, RandomSource(next(seeds)))

    class FakeQualityService:
        def score(self, candidate, preset, comparison_signatures):
            total = 0.9 if candidate.seed == 3 else 0.1
            return GenerationQualityScore(
                total=total,
                readability=total,
                uniqueness=1,
                difficulty_fit=1,
                route_interest=total,
            )

    service.template_registry.choose = lambda *args, **kwargs: SequenceTemplate()
    service.quality_service = FakeQualityService()

    result = service.generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            compare_against_existing=False,
            generation_mode="legacy_template",
            candidate_pool_size=2,
        )
    )

    assert result.passed is True
    assert result.accepted[0].seed == 3
    assert result.accepted[0].quality_score.total == 0.9


def test_generation_service_auto_difficulty_reports_actual_difficulty(tmp_path) -> None:
    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            start_level_number=9,
            count=4,
            difficulty="auto",
            template_name="mixed",
            dry_run=True,
            compare_against_existing=False,
        )
    )

    assert result.passed is True
    assert [level.difficulty for level in result.accepted] == ["easy", "easy", "medium", "medium"]


def test_generation_service_recipe_first_mode_generates_recipe_metadata(tmp_path) -> None:
    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            generation_mode="recipe_first",
        )
    )

    assert result.passed is True
    assert result.accepted[0].recipe_family == "single_switch"
    assert result.accepted[0].recipe_variant is not None
    assert result.accepted[0].abstract_graph_signature is not None
    assert result.accepted[0].selected_layout_variant is not None
    assert result.accepted[0].selected_road_shape_strategy == "auto"
    assert result.accepted[0].road_shape_metadata is not None
    assert "score" in result.accepted[0].road_shape_metadata
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert "roadShapeMetadata" in report["acceptedLevels"][0]
    assert "roadShapeScore" in report["acceptedLevels"][0]["quality"]["details"]


def test_generation_service_recipe_first_supports_current_recipe_families(tmp_path) -> None:
    specs = [
        ("tutorial", "straight_delivery"),
        ("easy", "single_switch"),
        ("easy", "package_gate"),
        ("medium", "return_loop"),
        ("medium", "multi_switch_chain"),
        ("hard", "ring_route"),
        ("expert", "four_way_intersection"),
    ]

    for index, (difficulty, template_name) in enumerate(specs):
        result = LevelGenerationService().generate(
            _config(
                tmp_path / template_name,
                start_level_number=90 + index,
                difficulty=difficulty,
                template_name=template_name,
                generation_mode="recipe_first",
                recipe_pool_size=2,
                layouts_per_recipe=2,
                road_shapes_per_layout=2,
                dry_run=True,
                compare_against_existing=False,
            )
        )

        assert result.passed is True, (difficulty, template_name, result.rejection_reason_counts, result.messages)
        assert result.accepted[0].recipe_family == template_name


def test_generation_service_hybrid_mode_keeps_legacy_templates_available(tmp_path) -> None:
    service = LevelGenerationService()
    config = _config(
        tmp_path,
        difficulty="easy",
        template_name="single_switch",
        generation_mode="hybrid",
        recipe_pool_size=1,
        layouts_per_recipe=1,
        road_shapes_per_layout=1,
        dry_run=True,
        compare_against_existing=False,
    )
    preset = service.difficulty_service.get_preset("easy")
    candidates = service._generate_raw_candidates(
        config=config,
        level_id="level_012",
        level_number=12,
        preset=preset,
        rng=RandomSource(12),
        plan_template_weights={},
    )

    assert len(candidates) == 2
    assert {candidate.recipe_family for candidate in candidates} == {"single_switch", None}


def test_generation_service_applies_map_seed_path(tmp_path) -> None:
    map_seed_path = tmp_path / "seed.json"
    seed_graph = MapSeedGraph(
        nodes=[
            MapSeedNode("a", 0, 0),
            MapSeedNode("b", 1, 0),
            MapSeedNode("c", 2, 1),
            MapSeedNode("d", 3, 1),
            MapSeedNode("e", 4, 0),
            MapSeedNode("f", 5, 0),
        ],
        edges=[
            MapSeedEdge("e1", "a", "b"),
            MapSeedEdge("e2", "b", "c"),
            MapSeedEdge("e3", "c", "d"),
            MapSeedEdge("e4", "d", "e"),
            MapSeedEdge("e5", "e", "f"),
        ],
        attribution="test map",
    )
    map_seed_path.write_text(json.dumps(seed_graph.to_dict()) + "\n", encoding="utf-8")

    result = LevelGenerationService().generate(
        _config(
            tmp_path,
            difficulty="easy",
            template_name="single_switch",
            dry_run=True,
            compare_against_existing=False,
            generation_mode="legacy_template",
            map_seed_path=map_seed_path,
        )
    )

    assert result.passed is True
    assert any("Map attribution" in note for note in result.accepted[0].generation_notes)
