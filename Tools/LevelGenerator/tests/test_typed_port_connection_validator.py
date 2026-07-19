from __future__ import annotations

import pytest

from app.models import (
    CompositionGraph,
    CompositionState,
    MotifPort,
    MotifPortType,
    OpenCompositionPort,
)
from app.models.graph_recipe import GraphRecipeNode
from app.services import (
    PortConnectionKind,
    PortConnectionValidationError,
    TypedPortConnectionValidator,
)


def _port(port_id: str, node_id: str, port_type: MotifPortType) -> MotifPort:
    return MotifPort(port_id, node_id, port_type)


@pytest.mark.parametrize(
    ("source_type", "target_type", "expected_kind"),
    (
        (MotifPortType.MAIN_ROUTE_EXIT, MotifPortType.MAIN_ROUTE_ENTRY, PortConnectionKind.MAIN_ROUTE),
        (MotifPortType.BRANCH_INSERTION_POINT, MotifPortType.MAIN_ROUTE_ENTRY, PortConnectionKind.BRANCH_EXPANSION),
        (MotifPortType.MAIN_ROUTE_EXIT, MotifPortType.REJOIN_INPUT, PortConnectionKind.REJOIN),
        (MotifPortType.REJOIN_INPUT, MotifPortType.MAIN_ROUTE_ENTRY, PortConnectionKind.REJOIN),
        (MotifPortType.RECOVERY_EXIT, MotifPortType.REJOIN_INPUT, PortConnectionKind.REJOIN),
        (MotifPortType.RECOVERY_EXIT, MotifPortType.MAIN_ROUTE_ENTRY, PortConnectionKind.REJOIN),
        (MotifPortType.RETURN_PATH_OUTPUT, MotifPortType.RETURN_PATH_INPUT, PortConnectionKind.RETURN_PATH),
        (MotifPortType.OBJECTIVE_ATTACHMENT, MotifPortType.OBJECTIVE_ATTACHMENT, PortConnectionKind.OBJECTIVE_ATTACHMENT),
        (MotifPortType.STATE_CHANGE_ATTACHMENT, MotifPortType.STATE_CHANGE_ATTACHMENT, PortConnectionKind.STATE_CHANGE_ATTACHMENT),
    ),
)
def test_explicit_compatibility_matrix_accepts_supported_connections(
    source_type: MotifPortType,
    target_type: MotifPortType,
    expected_kind: PortConnectionKind,
) -> None:
    validator = TypedPortConnectionValidator()
    source_phase = 2 if expected_kind is PortConnectionKind.RETURN_PATH else 1
    target_phase = 0 if expected_kind is PortConnectionKind.RETURN_PATH else 1

    result = validator.validate(
        _port("source", "a", source_type),
        _port("target", "b", target_type),
        source_phase_index=source_phase,
        target_phase_index=target_phase,
    )

    assert result.is_valid
    assert result.kind is expected_kind


def test_failure_exit_is_terminal_and_direction_is_not_implicitly_reversed() -> None:
    validator = TypedPortConnectionValidator()

    result = validator.validate(
        _port("failure", "a", MotifPortType.FAILURE_EXIT),
        _port("rejoin", "b", MotifPortType.REJOIN_INPUT),
    )
    reversed_result = validator.validate(
        _port("entry", "a", MotifPortType.MAIN_ROUTE_ENTRY),
        _port("exit", "b", MotifPortType.MAIN_ROUTE_EXIT),
    )

    assert result.issues == ("port_connection_types_incompatible:failureExit:rejoinInput",)
    assert reversed_result.issues == (
        "port_connection_types_incompatible:mainRouteEntry:mainRouteExit",
    )


def test_phase_rules_distinguish_forward_routes_returns_and_attachments() -> None:
    validator = TypedPortConnectionValidator()

    forward = validator.validate(
        _port("out", "a", MotifPortType.MAIN_ROUTE_EXIT),
        _port("in", "b", MotifPortType.MAIN_ROUTE_ENTRY),
        source_phase_index=2,
        target_phase_index=1,
    )
    invalid_return = validator.validate(
        _port("return_out", "a", MotifPortType.RETURN_PATH_OUTPUT),
        _port("return_in", "b", MotifPortType.RETURN_PATH_INPUT),
        source_phase_index=1,
        target_phase_index=1,
    )
    cross_phase_attachment = validator.validate(
        _port("objective_a", "a", MotifPortType.OBJECTIVE_ATTACHMENT),
        _port("objective_b", "b", MotifPortType.OBJECTIVE_ATTACHMENT),
        source_phase_index=0,
        target_phase_index=1,
    )

    assert forward.issues == ("port_connection_route_moves_backward:2:1",)
    assert invalid_return.issues == ("port_connection_return_path_not_earlier:1:1",)
    assert cross_phase_attachment.issues == (
        "port_connection_attachment_phase_mismatch:0:1",
    )


def test_state_validation_requires_both_qualified_ports_to_be_open() -> None:
    source = OpenCompositionPort(
        "left",
        _port("exit", "a", MotifPortType.MAIN_ROUTE_EXIT),
        0,
    )
    target = OpenCompositionPort(
        "right",
        _port("entry", "b", MotifPortType.MAIN_ROUTE_ENTRY),
        0,
    )
    state = CompositionState(
        blueprint_id="blueprint",
        unfulfilled_decision_ids=(),
        open_ports=(source,),
        objective_phase_boundaries=(),
        current_graph=CompositionGraph(
            nodes=(GraphRecipeNode("a"), GraphRecipeNode("b")),
        ),
    )

    result = TypedPortConnectionValidator().validate(source, target, state=state)

    assert result.issues == ("port_connection_target_not_open:right:entry",)


def test_require_valid_returns_kind_or_raises_stable_first_issue() -> None:
    validator = TypedPortConnectionValidator()
    source = _port("exit", "a", MotifPortType.MAIN_ROUTE_EXIT)
    target = _port("entry", "b", MotifPortType.MAIN_ROUTE_ENTRY)

    assert validator.require_valid(source, target) is PortConnectionKind.MAIN_ROUTE
    with pytest.raises(PortConnectionValidationError, match="types_incompatible"):
        validator.require_valid(target, source)


def test_compatible_target_types_are_deterministic() -> None:
    assert TypedPortConnectionValidator().compatible_target_types(
        MotifPortType.MAIN_ROUTE_EXIT
    ) == (MotifPortType.MAIN_ROUTE_ENTRY, MotifPortType.REJOIN_INPUT)


def test_equal_local_port_ids_from_different_motifs_are_not_the_same_port() -> None:
    validator = TypedPortConnectionValidator()

    result = validator.validate(
        _port("objective", "pickup_a", MotifPortType.OBJECTIVE_ATTACHMENT),
        _port("objective", "pickup_b", MotifPortType.OBJECTIVE_ATTACHMENT),
        source_phase_index=0,
        target_phase_index=0,
    )

    assert result.is_valid
