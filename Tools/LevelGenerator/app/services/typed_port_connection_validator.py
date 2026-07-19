"""Compatibility validation for typed V3 composition ports."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..models.composition_state import CompositionState, OpenCompositionPort
from ..models.motif_port import MotifPort, MotifPortType


class PortConnectionKind(str, Enum):
    MAIN_ROUTE = "mainRoute"
    BRANCH_EXPANSION = "branchExpansion"
    REJOIN = "rejoin"
    RETURN_PATH = "returnPath"
    OBJECTIVE_ATTACHMENT = "objectiveAttachment"
    STATE_CHANGE_ATTACHMENT = "stateChangeAttachment"


_CONNECTION_KINDS: dict[tuple[MotifPortType, MotifPortType], PortConnectionKind] = {
    (MotifPortType.MAIN_ROUTE_EXIT, MotifPortType.MAIN_ROUTE_ENTRY): (
        PortConnectionKind.MAIN_ROUTE
    ),
    (MotifPortType.BRANCH_INSERTION_POINT, MotifPortType.MAIN_ROUTE_ENTRY): (
        PortConnectionKind.BRANCH_EXPANSION
    ),
    (MotifPortType.MAIN_ROUTE_EXIT, MotifPortType.REJOIN_INPUT): PortConnectionKind.REJOIN,
    (MotifPortType.REJOIN_INPUT, MotifPortType.MAIN_ROUTE_ENTRY): PortConnectionKind.REJOIN,
    (MotifPortType.RECOVERY_EXIT, MotifPortType.REJOIN_INPUT): PortConnectionKind.REJOIN,
    (MotifPortType.RECOVERY_EXIT, MotifPortType.MAIN_ROUTE_ENTRY): PortConnectionKind.REJOIN,
    (MotifPortType.RETURN_PATH_OUTPUT, MotifPortType.RETURN_PATH_INPUT): (
        PortConnectionKind.RETURN_PATH
    ),
    (MotifPortType.OBJECTIVE_ATTACHMENT, MotifPortType.OBJECTIVE_ATTACHMENT): (
        PortConnectionKind.OBJECTIVE_ATTACHMENT
    ),
    (MotifPortType.STATE_CHANGE_ATTACHMENT, MotifPortType.STATE_CHANGE_ATTACHMENT): (
        PortConnectionKind.STATE_CHANGE_ATTACHMENT
    ),
}


class PortConnectionValidationError(ValueError):
    pass


@dataclass(frozen=True)
class PortConnectionValidationResult:
    kind: PortConnectionKind | None
    issues: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class _QualifiedPort:
    id: str
    port: MotifPort
    phase_index: int | None


class TypedPortConnectionValidator:
    """Validate port polarity, operation semantics, and phase direction."""

    def validate(
        self,
        source: MotifPort | OpenCompositionPort,
        target: MotifPort | OpenCompositionPort,
        *,
        source_phase_index: int | None = None,
        target_phase_index: int | None = None,
        state: CompositionState | None = None,
    ) -> PortConnectionValidationResult:
        same_port = source is target
        source_port = self._qualify(source, source_phase_index, "source")
        target_port = self._qualify(target, target_phase_index, "target")
        issues: list[str] = []

        if same_port or (
            isinstance(source, OpenCompositionPort)
            and isinstance(target, OpenCompositionPort)
            and source_port.id == target_port.id
        ):
            issues.append(f"port_connection_same_port:{source_port.id}")

        kind = _CONNECTION_KINDS.get(
            (source_port.port.port_type, target_port.port.port_type)
        )
        if kind is None:
            issues.append(
                "port_connection_types_incompatible:"
                f"{source_port.port.port_type.value}:{target_port.port.port_type.value}"
            )

        if state is not None:
            if not isinstance(state, CompositionState):
                raise TypeError("state must be a CompositionState")
            open_ids = {port.id for port in state.open_ports}
            for role, port in (("source", source_port), ("target", target_port)):
                if port.id not in open_ids:
                    issues.append(f"port_connection_{role}_not_open:{port.id}")

        if kind is not None:
            issues.extend(self._validate_phase_direction(kind, source_port, target_port))

        return PortConnectionValidationResult(kind if not issues else None, tuple(issues))

    def require_valid(
        self,
        source: MotifPort | OpenCompositionPort,
        target: MotifPort | OpenCompositionPort,
        **kwargs: object,
    ) -> PortConnectionKind:
        result = self.validate(source, target, **kwargs)
        if result.issues:
            raise PortConnectionValidationError(result.issues[0])
        assert result.kind is not None
        return result.kind

    def can_connect(
        self,
        source: MotifPort | OpenCompositionPort,
        target: MotifPort | OpenCompositionPort,
        **kwargs: object,
    ) -> bool:
        return self.validate(source, target, **kwargs).is_valid

    def compatible_target_types(
        self,
        source_type: MotifPortType | str,
    ) -> tuple[MotifPortType, ...]:
        if not isinstance(source_type, MotifPortType):
            source_type = MotifPortType(source_type)
        return tuple(
            target
            for source, target in _CONNECTION_KINDS
            if source is source_type
        )

    def _qualify(
        self,
        value: MotifPort | OpenCompositionPort,
        explicit_phase_index: int | None,
        role: str,
    ) -> _QualifiedPort:
        if isinstance(value, OpenCompositionPort):
            phase_index = value.objective_phase_index
            if explicit_phase_index is not None and explicit_phase_index != phase_index:
                raise ValueError(
                    f"{role}_phase_index conflicts with the qualified open port"
                )
            return _QualifiedPort(value.id, value.port, phase_index)
        if not isinstance(value, MotifPort):
            raise TypeError(f"{role} must be a MotifPort or OpenCompositionPort")
        if explicit_phase_index is not None and (
            not isinstance(explicit_phase_index, int)
            or isinstance(explicit_phase_index, bool)
            or explicit_phase_index < 0
        ):
            raise ValueError(f"{role}_phase_index must be a non-negative integer")
        return _QualifiedPort(f"{role}:{value.id}", value, explicit_phase_index)

    def _validate_phase_direction(
        self,
        kind: PortConnectionKind,
        source: _QualifiedPort,
        target: _QualifiedPort,
    ) -> tuple[str, ...]:
        if source.phase_index is None or target.phase_index is None:
            return ()

        if kind is PortConnectionKind.RETURN_PATH:
            if target.phase_index >= source.phase_index:
                return (
                    "port_connection_return_path_not_earlier:"
                    f"{source.phase_index}:{target.phase_index}",
                )
            return ()

        if kind in {
            PortConnectionKind.OBJECTIVE_ATTACHMENT,
            PortConnectionKind.STATE_CHANGE_ATTACHMENT,
        }:
            if target.phase_index != source.phase_index:
                return (
                    "port_connection_attachment_phase_mismatch:"
                    f"{source.phase_index}:{target.phase_index}",
                )
            return ()

        if target.phase_index < source.phase_index:
            return (
                "port_connection_route_moves_backward:"
                f"{source.phase_index}:{target.phase_index}",
            )
        return ()


# Keep the service name discoverable from either task wording convention.
MotifPortConnectionValidator = TypedPortConnectionValidator
