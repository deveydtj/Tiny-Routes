import Foundation

enum SwitchEligibilityReason: Equatable {
    case eligible
    case outsideLookaheadWindow
    case noUpcomingSwitch
    case invalidSpeed
    case cycleDetected
    case stepLimitReached
}

struct SwitchEligibilitySnapshot: Equatable {
    let eligibleNodeID: String?
    let upcomingNodeID: String?
    let travelTimeSeconds: Double?
    let reason: SwitchEligibilityReason

    static let noUpcomingSwitch = SwitchEligibilitySnapshot(
        eligibleNodeID: nil,
        upcomingNodeID: nil,
        travelTimeSeconds: nil,
        reason: .noUpcomingSwitch
    )
}

/// Performs a read-only query along the dot's currently selected route.
struct SwitchEligibilityService {
    func snapshot(
        graph: RuntimeRouteGraph,
        dot: DeliveryDot,
        speed: Double,
        hasCollectedPackage: Bool,
        rules: LevelRules,
        maximumStepCount: Int? = nil
    ) -> SwitchEligibilitySnapshot {
        guard speed > 0 else {
            return SwitchEligibilitySnapshot(
                eligibleNodeID: nil, upcomingNodeID: nil, travelTimeSeconds: nil, reason: .invalidSpeed
            )
        }

        var distance = 0.0
        var nextNodeID: String

        if let transition = dot.transition {
            distance += max(0, 1 - transition.progressAlongTransition) * transition.roadPath.totalLength
            guard let edge = graph.edgesByID[transition.toEdgeID] else { return .noUpcomingSwitch }
            distance += max(0, edge.roadPath.totalLength - transition.exitDistanceAlongToEdge)
            nextNodeID = edge.toNodeID
        } else if let edgeID = dot.currentEdgeID {
            guard let edge = graph.edgesByID[edgeID] else { return .noUpcomingSwitch }
            distance += max(0, 1 - min(max(dot.progressAlongEdge, 0), 1)) * edge.roadPath.totalLength
            nextNodeID = edge.toNodeID
        } else {
            nextNodeID = dot.currentNodeID
        }

        var visited = Set<String>()
        let limit = maximumStepCount ?? max(graph.nodesByID.count + graph.edgesByID.count, 1)
        var steps = 0

        while steps < limit {
            steps += 1
            guard visited.insert(nextNodeID).inserted else {
                return SwitchEligibilitySnapshot(
                    eligibleNodeID: nil, upcomingNodeID: nil, travelTimeSeconds: nil, reason: .cycleDetected
                )
            }
            guard let node = graph.nodesByID[nextNodeID] else { return .noUpcomingSwitch }

            if graph.switchKind(
                for: node,
                hasCollectedPackage: hasCollectedPackage
            ).isSwitchable {
                let travelTime = distance / speed
                let isEligible = travelTime <= max(rules.switchLookaheadSeconds, 0)
                return SwitchEligibilitySnapshot(
                    eligibleNodeID: isEligible ? node.id : nil,
                    upcomingNodeID: node.id,
                    travelTimeSeconds: travelTime,
                    reason: isEligible ? .eligible : .outsideLookaheadWindow
                )
            }

            let usableEdgeIDs = graph.usableOutgoingEdgeIDs(
                for: node,
                hasCollectedPackage: hasCollectedPackage
            )
            let selectedEdgeID = node.activeOutgoingEdgeID.flatMap {
                usableEdgeIDs.contains($0) ? $0 : nil
            } ?? usableEdgeIDs.first
            guard let edgeID = selectedEdgeID,
                  let edge = graph.edgesByID[edgeID],
                  edge.fromNodeID == node.id else {
                return .noUpcomingSwitch
            }
            distance += edge.roadPath.totalLength
            nextNodeID = edge.toNodeID
        }

        return SwitchEligibilitySnapshot(
            eligibleNodeID: nil, upcomingNodeID: nil, travelTimeSeconds: nil, reason: .stepLimitReached
        )
    }
}
