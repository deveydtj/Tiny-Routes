"""Runtime-parity simulation services."""
from .results import LevelOutcome
from .runtime_graph import RuntimeGraph
from .runtime_state import RuntimeState
from .simulator import RuntimeSimulationResult, RuntimeSimulator, SimulationEvent, TapRecord, TapResultCode
from .switch_eligibility import SwitchEligibilityReason, SwitchEligibilitySnapshot, switch_eligibility

__all__ = [
    "LevelOutcome", "RuntimeGraph", "RuntimeState", "RuntimeSimulationResult", "RuntimeSimulator",
    "SimulationEvent", "TapRecord", "TapResultCode", "SwitchEligibilityReason",
    "SwitchEligibilitySnapshot", "switch_eligibility",
]
