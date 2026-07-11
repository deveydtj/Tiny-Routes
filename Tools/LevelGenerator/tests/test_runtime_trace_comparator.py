from app.services.runtime_parity_validator import NormalizedRuntimeTrace, RuntimeTraceComparator


def _trace(edge="edge_b"):
    return NormalizedRuntimeTrace(
        "completed", ("package",), ((1.2, "switch", edge),), (),
        (("switch", edge),), 3.0,
        ((1.2, "tap_accepted", "switch", edge, "accepted"),),
    )


def test_matching_normalized_runtime_traces_pass():
    assert RuntimeTraceComparator().compare(_trace(), _trace()).matches


def test_rotation_order_divergence_reports_first_event_context():
    comparison = RuntimeTraceComparator().compare(_trace("edge_b"), _trace("edge_c"))
    assert not comparison.matches
    assert comparison.divergent_event_index == 0
    assert "first divergent event 0" in comparison.message
