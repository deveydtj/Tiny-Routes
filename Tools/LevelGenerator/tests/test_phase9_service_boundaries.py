from app.services.failure_outcome_classifier import FailureOutcomeClassifier
from app.services.layout_coordinate_service import LayoutCoordinateService
from app.services.layout_geometric_validation_service import LayoutGeometricValidationService
from app.services.layout_metric_reporting_service import LayoutMetricReportingService
from app.services.solution_equivalence_service import SolutionEquivalenceService


def test_failure_classifier_uses_decision_outcomes() -> None:
    classifier = FailureOutcomeClassifier()
    assert classifier.classify("destination_before_package") == "package_bypass"
    assert classifier.classify("dead_end") == "wrong_branch_failure"


def test_solution_equivalence_uses_ordered_decision_profile() -> None:
    summary = type("Summary", (), {"tap_history": ("switch_a", "switch_b")})()
    changed = type("Summary", (), {"tap_history": ("switch_b", "switch_a")})()
    service = SolutionEquivalenceService()
    assert service.are_equivalent(summary, summary)
    assert not service.are_equivalent(summary, changed)


def test_layout_boundaries_are_independently_callable() -> None:
    positions = {"a": (0.0, 0.0), "b": (1.0, 1.0), "c": (0.0, 1.0), "d": (1.0, 0.0)}
    edges = [("a", "b", "ab"), ("c", "d", "cd")]
    assert LayoutCoordinateService().snap_point(0.12, 0.12) == (0.1, 0.1)
    assert LayoutGeometricValidationService().crossings(positions, edges) == (("ab", "cd"),)
    assert LayoutMetricReportingService().readability_metrics(positions, edges)["crossings"] == 1
