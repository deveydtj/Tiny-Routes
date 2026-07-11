import Foundation

/// The observable result of asking the route engine to rotate a switch.
///
/// Rejection cases are intentionally explicit so gameplay UI, replay tooling, and
/// parity tests can distinguish an invalid target from a tap that arrived after
/// the dot committed to a route.
enum SwitchTapResult: Equatable {
    case accepted(nodeID: String, activeEdgeID: String)
    case rejectedNoLevel
    case rejectedPaused
    case rejectedLevelFinished
    case rejectedNotSwitchable
    case rejectedNotEligible(expectedNodeID: String?)
    case rejectedCooldown
    case rejectedCommitted

    /// Transitional convenience for callers that only need the former Boolean result.
    var didRotate: Bool {
        if case .accepted = self {
            return true
        }
        return false
    }
}
