from __future__ import annotations

import json

from app.generation_config import GenerationConfig
from app.level_editor_imports import LevelDocument, RouteEdgeModel, RouteGraphModel, RouteNodeModel, SolutionModel
from app.models.generated_level import GeneratedLevel
from app.repositories.generation_report_repository import GenerationReportRepository
from app.services.candidate_signature_service import CandidateSignatureService
from app.services.difficulty_service import DifficultyService
from app.services.level_generation_service import LevelGenerationService
from app.random_source import RandomSource
from app.templates.single_switch_template import SingleSwitchTemplate


def test_generation_report_repository_writes_markdown_and_json(tmp_path) -> None:
    config = GenerationConfig(
        start_level_number=12,
        count=1,
        difficulty="tutorial",
        levels_output_dir=tmp_path / "levels",
        solutions_output_dir=tmp_path / "solutions",
        report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )
    result = type(
        "Result",
        (),
        {
            "accepted": [],
            "rejected_candidate_count": 0,
            "rejection_reason_counts": {},
            "written_level_paths": [],
            "written_solution_paths": [],
            "swift_test_summary": type("Swift", (), {"passed": None, "command": [], "exit_code": None, "summary": "not run"})(),
            "messages": [],
        },
    )()
    repository = GenerationReportRepository()

    repository.write_markdown(config.report_path, config, result)
    repository.write_json(config.json_report_path, config, result)

    assert "Tiny Routes Generation Report" in config.report_path.read_text(encoding="utf-8")
    assert json.loads(config.json_report_path.read_text(encoding="utf-8"))["difficulty"] == "tutorial"


def test_generation_report_repository_writes_candidate_signatures(tmp_path) -> None:
    preset = DifficultyService().get_preset("easy")
    generated = SingleSwitchTemplate().generate("level_012", 12, preset, RandomSource(10))
    generated.candidate_signature = CandidateSignatureService().signature_for(generated)
    config = GenerationConfig(
        start_level_number=12,
        count=1,
        difficulty="easy",
        levels_output_dir=tmp_path / "levels",
        solutions_output_dir=tmp_path / "solutions",
        report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )
    result = type(
        "Result",
        (),
        {
            "accepted": [generated],
            "rejected_candidate_count": 0,
            "rejection_reason_counts": {},
            "written_level_paths": [],
            "written_solution_paths": [],
            "swift_test_summary": type("Swift", (), {"passed": None, "command": [], "exit_code": None, "summary": "not run"})(),
            "messages": [],
        },
    )()

    GenerationReportRepository().write_markdown(config.report_path, config, result)
    GenerationReportRepository().write_json(config.json_report_path, config, result)

    payload = json.loads(config.json_report_path.read_text(encoding="utf-8"))
    signature = payload["acceptedLevels"][0]["signature"]
    assert signature["topologyHashShort"] == generated.candidate_signature.topology_hash[:8]
    assert "Signatures" in config.report_path.read_text(encoding="utf-8")
    assert payload["acceptedLevels"][0]["switchPreview"]
    assert payload["acceptedLevels"][0]["switchPreview"][0]["visualDirectionBuckets"]
    solution = payload["acceptedLevels"][0]["solution"]
    assert solution["metadata"]["validationVersion"] == "solution_sidecar_v1"
    assert solution["requiredTapOrder"] == [action.tapNodeID for action in generated.solution.actions]
    assert solution["actions"][0]["reason"]
    assert "Required taps" in config.report_path.read_text(encoding="utf-8")


def test_generation_report_repository_adds_duplicate_exhaustion_recommendations(tmp_path) -> None:
    config = GenerationConfig(
        start_level_number=29,
        count=1,
        difficulty="hard",
        template_name="mixed",
        levels_output_dir=tmp_path / "levels",
        solutions_output_dir=tmp_path / "solutions",
        report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )
    result = type(
        "Result",
        (),
        {
            "accepted": [],
            "rejected_candidate_count": 100,
            "rejection_reason_counts": {"candidate_too_similar_to_batch": 87},
            "written_level_paths": [],
            "written_solution_paths": [],
            "swift_test_summary": type("Swift", (), {"passed": None, "command": [], "exit_code": None, "summary": "not run"})(),
            "messages": ["Could not generate valid level_029 after 100 attempts."],
            "passed": False,
        },
    )()

    GenerationReportRepository().write_markdown(config.report_path, config, result)
    GenerationReportRepository().write_json(config.json_report_path, config, result)

    markdown = config.report_path.read_text(encoding="utf-8")
    payload = json.loads(config.json_report_path.read_text(encoding="utf-8"))
    assert "## Recommendations" in markdown
    assert payload["recommendations"][0] == "Most common rejection: `candidate_too_similar_to_batch`."


def test_generation_report_repository_writes_recipe_metadata(tmp_path) -> None:
    result = LevelGenerationService().generate(
        GenerationConfig(
            start_level_number=12,
            count=1,
            difficulty="easy",
            template_name="single_switch",
            generation_mode="recipe_first",
            layout_orientation_preference="vertical",
            dry_run=True,
            compare_against_existing=False,
            levels_output_dir=tmp_path / "levels",
            solutions_output_dir=tmp_path / "solutions",
            report_path=tmp_path / "report.md",
            json_report_path=tmp_path / "report.json",
        )
    )

    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    accepted = payload["acceptedLevels"][0]

    assert result.passed is True
    assert accepted["recipeFamily"] == "single_switch"
    assert accepted["recipeVariant"].startswith("single_switch_")
    assert accepted["mechanicTags"]
    assert accepted["primaryMechanicTag"] == "single_switch"
    assert accepted["topologyClass"] == "single_branch"
    assert accepted["requiredPathLength"] is not None
    assert accepted["layoutOrientation"] == "vertical"
    assert accepted["layoutSizeProfile"] == "standard_portrait"
    assert accepted["requestedLayoutSizeProfile"] == "difficulty_curve"
    assert accepted["layoutSizeSelectionReason"] == "difficulty_curve_standard_candidate"
    assert accepted["selectedPreset"] == "easy"
    assert accepted["validationResult"] == "passed"
    assert accepted["acceptedOrRejectedReason"] == "accepted"
    assert accepted["routeInterestScore"] is not None
    assert accepted["difficultyScore"] is not None
    assert accepted["pacingPenalties"] == []
    assert accepted["layoutStrategy"] == "vertical_route_progression"
    assert accepted["layoutVariant"] == "normal"
    assert accepted["layoutOrientationSelectionReason"] == "explicit_preference"
    assert accepted["verticalCandidateRejectedReason"] is None
    assert accepted["diversityAudit"] == {
        "topologyDiversityScore": 1.0,
        "nearbyMechanicTagPenalty": 0.0,
        "nearbyTopologyClassPenalty": 0.0,
        "diversityScore": 1.0,
    }
    assert accepted["topologyDiversityScore"] == 1.0
    assert accepted["nearbyMechanicTagPenalty"] == 0.0
    assert accepted["nearbyTopologyClassPenalty"] == 0.0
    assert accepted["diversityScore"] == 1.0
    assert accepted["abstractGraphSignature"]
    assert accepted["selectedLayoutVariant"] == "normal"
    assert accepted["selectedRoadShapeStrategy"] == "auto"
    assert accepted["quality"]["abstractMechanicQuality"] > 0
    assert accepted["quality"]["switchClarity"] > 0
    assert payload["candidateSelection"][0]["levelID"] == "level_012"
    assert payload["candidateSelection"][0]["scoreStats"]["maximum"] is not None
    assert payload["candidateSelection"][0]["acceptedCandidate"]["primaryMechanicTag"] == "single_switch"
    assert payload["candidateSelection"][0]["acceptedCandidate"]["topologyClass"] == "single_branch"
    assert payload["candidateSelection"][0]["acceptedCandidate"]["requiredPathLength"] == accepted["requiredPathLength"]
    assert payload["layoutOrientationPreference"] == "vertical"
    assert payload["layoutSizeProfile"] == "difficulty_curve"
    assert payload["verticalRouteProbability"] == 0.35
    assert payload["preferVerticalForLongRoutes"] is True
    assert payload["dryRunSummary"]["safeScratchRun"] is True
    assert payload["acceptedMapSizeDistribution"] == {"standard_portrait": 1}
    assert payload["candidateSelection"][0]["acceptedCandidate"]["layoutOrientation"] == "vertical"
    assert payload["candidateSelection"][0]["acceptedCandidate"]["layoutSizeProfile"] == "standard_portrait"
    assert payload["candidateSelection"][0]["acceptedCandidate"]["selectedPreset"] == "easy"
    assert payload["candidateSelection"][0]["acceptedCandidate"]["validationResult"] == "passed"
    assert payload["candidateSelection"][0]["acceptedCandidate"]["layoutStrategy"] == "vertical_route_progression"
    assert payload["candidateSelection"][0]["acceptedCandidate"]["layoutVariant"] == "normal"
    assert payload["candidateSelection"][0]["acceptedCandidate"]["layoutOrientationSelectionReason"] == "explicit_preference"
    assert payload["candidateSelection"][0]["acceptedCandidate"]["diversityAudit"]["diversityScore"] == 1.0
    assert payload["candidateSelection"][0]["acceptedCandidate"]["diversityScore"] == 1.0
    assert accepted["quality"]["diversityScore"] == 1.0
    assert accepted["quality"]["nearbyMechanicTagPenalty"] == 0.0
    assert "baseQualityScore" in accepted["quality"]
    assert "presetContentFit" in accepted["quality"]
    assert "campaignPacingDetails" in accepted["quality"]
    markdown = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Candidate selection" in markdown
    assert "Topology" in markdown
    assert "Map size" in markdown
    assert "preset fit" in markdown
    assert "primary `single_switch`" in markdown
    assert "required path length" in markdown
    assert "layout orientation `vertical` via `explicit_preference`" in markdown
    assert "strategy: `vertical_route_progression`" in markdown
    assert "Diversity audit:" in markdown
    assert "Accepted candidate audit:" in markdown
    assert "family `single_switch`" in markdown
    assert "variant `single_switch_" in markdown
    assert "primary `single_switch`" in markdown
    assert "mechanic penalty 0.0" in markdown


def test_generation_report_repository_writes_recipe_mechanic_metadata(tmp_path) -> None:
    result = LevelGenerationService().generate(
        GenerationConfig(
            start_level_number=44,
            count=1,
            difficulty="expert",
            template_name="four_way_intro",
            generation_mode="recipe_first",
            recipe_pool_size=1,
            layouts_per_recipe=1,
            road_shapes_per_layout=1,
            candidate_pool_size=1,
            max_attempts_per_level=5,
            dry_run=True,
            compare_against_existing=False,
            levels_output_dir=tmp_path / "levels",
            solutions_output_dir=tmp_path / "solutions",
            report_path=tmp_path / "report.md",
            json_report_path=tmp_path / "report.json",
        )
    )

    payload = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    accepted = payload["acceptedLevels"][0]

    assert result.passed is True
    assert accepted["recipeFamily"] == "four_way_intro"
    assert "four_way" in accepted["mechanicTags"]
    assert accepted["primaryMechanicTag"] == "four_way"
    assert accepted["topologyClass"] == "four_way_gate"
    assert accepted["unlockRequirement"]
    assert accepted["priorMechanicDependency"] == "hub_choice"
    assert accepted["mechanicMetadata"]["intendedMechanic"]
    assert "Mechanics:" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_generation_report_repository_includes_visual_clarity_node_and_edge_ids(tmp_path) -> None:
    generated = _visual_clarity_report_level()
    config = GenerationConfig(
        start_level_number=12,
        count=1,
        difficulty="easy",
        levels_output_dir=tmp_path / "levels",
        solutions_output_dir=tmp_path / "solutions",
        report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )
    result = type(
        "Result",
        (),
        {
            "accepted": [generated],
            "rejected_candidate_count": 0,
            "rejection_reason_counts": {},
            "written_level_paths": [],
            "written_solution_paths": [],
            "swift_test_summary": type("Swift", (), {"passed": None, "command": [], "exit_code": None, "summary": "not run"})(),
            "messages": [],
        },
    )()

    GenerationReportRepository().write_json(config.json_report_path, config, result)

    payload = json.loads(config.json_report_path.read_text(encoding="utf-8"))
    issues = payload["acceptedLevels"][0]["visualClarity"]["issues"]
    parallel_issue = next(
        issue
        for issue in issues
        if issue["code"] == "long_parallel_road_segments_visually_merge"
    )
    assert parallel_issue["relatedEdgeID"] == "e_side_ab"
    assert parallel_issue["relatedEdgeIDs"] == ["e_side_ab", "e_side_cd"]
    assert "relatedNodeID" in parallel_issue


def _visual_clarity_report_level() -> GeneratedLevel:
    level = LevelDocument(
        id="level_visual_report",
        name="Visual Report",
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
        template_name="visual_report",
        difficulty="easy",
        seed=1,
    )
