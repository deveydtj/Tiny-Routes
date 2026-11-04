import SwiftUI

/// Front faces up at zero rotation. All details scale with the overall length.
struct MultiVanVanView: View {
    let color: VanColor
    var length: CGFloat = 28
    var status: MultiVanVanState.Status = .waiting
    var reaction: MultiVanPersonality.Reaction?
    var reducesExtraAnimations = false
    var isDelivered = false
    var turnSignal: TurnSignal?
    var signalIsLit = true
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    enum TurnSignal: Double {
        case left = -1, right = 1
    }

    private static let signalClearance = 0.6

    private struct Motion {
        var scale = 1.0
        var rotation = 0.0
    }

    var body: some View {
        let reduced = reduceMotion || reducesExtraAnimations
        let idle = MultiVanPersonality.isIdle(status: status, reduceMotion: reduced)
        let activeReaction = MultiVanPersonality.activeReaction(reaction, status: status, reduceMotion: reduced)

        ZStack {
            ForEach([-1.0, 1.0], id: \.self) { side in
                ForEach([-1.0, 1.0], id: \.self) { axle in
                    RoundedRectangle(cornerRadius: length * 0.04)
                        .fill(Color(white: 0.22))
                        .frame(width: length * 0.11, height: length * 0.19)
                        .offset(x: length * 0.32 * side, y: length * 0.25 * axle)
                }
            }

            RoundedRectangle(cornerRadius: length * 0.15)
                .fill(color.boardColor.gradient)
                .overlay {
                    RoundedRectangle(cornerRadius: length * 0.15)
                        .strokeBorder(.white, lineWidth: length * 0.055)
                }
                .frame(width: length * 0.64, height: length)

            // Wide blue-black glass and two bright lamps identify the front.
            RoundedRectangle(cornerRadius: length * 0.045)
                .fill(Color(red: 0.12, green: 0.25, blue: 0.34))
                .overlay(alignment: .top) {
                    Capsule()
                        .fill(.white.opacity(0.6))
                        .frame(width: length * 0.29, height: length * 0.025)
                        .padding(.top, length * 0.025)
                }
                .frame(width: length * 0.43, height: length * 0.17)
                .offset(y: -length * 0.24)

            ForEach([-1.0, 1.0], id: \.self) { side in
                let signalling = turnSignal?.rawValue == side
                let lit = signalling && (reduceMotion || signalIsLit)
                ForEach([-1.0, 1.0], id: \.self) { end in
                    Capsule()
                        .fill(signalling
                              ? Color(red: 1, green: 0.67, blue: 0.12).opacity(lit ? 1 : 0.18)
                              : (end < 0 ? .white : Color(red: 0.75, green: 0.16, blue: 0.12)))
                        .frame(width: length * 0.15, height: length * 0.1)
                        .shadow(color: .orange.opacity(lit ? 0.8 : 0), radius: length * 0.14)
                        .animation(reduceMotion ? nil : .easeInOut(duration: 0.06), value: lit)
                        .offset(x: length * 0.17 * side, y: length * 0.4 * end)
                }
            }

            Text(color.symbol)
                .font(.system(size: length * 0.29, weight: .bold))
                .foregroundStyle(.white)
                .shadow(color: .black.opacity(0.35), radius: 0, y: length * 0.015)
                .offset(y: length * 0.055)

            // Decorative parcel stays behind the roof symbol, clear of the cab.
            RoundedRectangle(cornerRadius: length * 0.025)
                .fill(Color(red: 0.76, green: 0.49, blue: 0.25))
                .overlay {
                    Rectangle()
                        .fill(Color(red: 1, green: 0.85, blue: 0.57))
                        .frame(width: length * 0.04)
                }
                .frame(width: length * 0.23, height: length * 0.17)
                .offset(y: length * 0.32)
        }
        .frame(width: length * 0.75, height: length)
        .keyframeAnimator(initialValue: 0.0, repeating: idle) { content, angle in
            content.rotationEffect(.degrees(idle ? angle : 0))
        } keyframes: { _ in
            CubicKeyframe(2.2, duration: 0.7)
            CubicKeyframe(-2.2, duration: 1.4)
            CubicKeyframe(0, duration: 0.7)
        }
        .keyframeAnimator(initialValue: Motion(), trigger: activeReaction) { content, motion in
            let scale = activeReaction == nil ? 1 : motion.scale
            content
                // Squash/stretch in the van's local forward axis, before the
                // board applies the road heading and physical position.
                .scaleEffect(x: activeReaction?.kind == .departure ? 1 / scale : scale, y: scale)
                .rotationEffect(.degrees(activeReaction == nil ? 0 : motion.rotation))
        } keyframes: { _ in
            KeyframeTrack(\.scale) {
                switch activeReaction?.kind {
                case .delivery:
                    CubicKeyframe(1.16, duration: 0.12)
                    CubicKeyframe(1, duration: 0.28)
                case .departure:
                    CubicKeyframe(1.1, duration: 0.08)
                    CubicKeyframe(1, duration: 0.18)
                default:
                    MoveKeyframe(1)
                }
            }
            KeyframeTrack(\.rotation) {
                if activeReaction?.kind == .crash {
                    CubicKeyframe(-12, duration: 0.06)
                    CubicKeyframe(370, duration: 0.3)
                    CubicKeyframe(360, duration: 0.14)
                } else {
                    MoveKeyframe(0)
                }
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Self.accessibilityLabel(color: color))
        .accessibilityValue(Self.accessibilityValue(color: color, status: status, isDelivered: isDelivered))
    }

    static func accessibilityLabel(color: VanColor) -> String {
        "\(color.displayName) \(color.accessibilitySymbolName) van"
    }

    static func accessibilityValue(color: VanColor, status: MultiVanVanState.Status, isDelivered: Bool) -> String {
        let state: String
        switch status {
        case .waiting: state = "Waiting"
        case .driving: state = "Driving"
        case .parked: state = isDelivered ? "Delivered, parked at its matching house" : "Parked at a different house"
        case .crashed: state = "Crashed"
        case .stuck: state = "Stopped at a dead end"
        }
        return "\(state). Destination: \(color.displayName.lowercased()) \(color.accessibilitySymbolName) house"
    }

    static func heading(
        for van: MultiVanVanState, startNodeID: String?, graph: RuntimeRouteGraph
    ) -> Angle {
        heading(for: MultiVanBoardRules.vanTangent(for: van, startNodeID: startNodeID, in: graph))
    }

    static func heading(for tangent: RoadVector) -> Angle {
        let magnitude = hypot(tangent.x, tangent.y)
        guard magnitude.isFinite, magnitude > 1e-9 else { return .zero }
        // MV-12 projects (x, y) to (x, -y). With the artwork facing screen-up,
        // atan2(x, y) gives clockwise SwiftUI rotation: up 0, right π/2.
        return .radians(atan2(tangent.x, tangent.y))
    }

    static func signalIsLit(for van: MultiVanVanState, graph: RuntimeRouteGraph, speed: Double) -> Bool {
        guard speed > 0, let edgeID = van.currentEdgeID,
              let edge = graph.edgesByID[edgeID] else { return true }
        let distance: Double
        if van.distanceAlongEdge < signalClearance,
           let previousID = van.previousEdgeID, let previous = graph.edgesByID[previousID],
           turnSignal(from: previous, to: edge, graph: graph) != nil {
            distance = van.distanceAlongEdge
        } else {
            distance = van.distanceAlongEdge - edge.roadPath.totalLength
        }
        // Center a flash on each junction, with a visible on/off rhythm on both sides.
        return cos(distance / speed * 2 * .pi / 0.6) > 0
    }

    static func turnSignal(for van: MultiVanVanState, graph: RuntimeRouteGraph) -> TurnSignal? {
        guard van.status == .driving,
              let edgeID = van.currentEdgeID, let edge = graph.edgesByID[edgeID] else { return nil }

        // Keep the same side lit until the rear of the van clears the junction.
        if van.distanceAlongEdge < signalClearance,
           let previousID = van.previousEdgeID, let previous = graph.edgesByID[previousID],
           let signal = turnSignal(from: previous, to: edge, graph: graph) {
            return signal
        }
        guard edge.roadPath.totalLength - van.distanceAlongEdge <= 1.5,
              let node = graph.nodesByID[edge.toNodeID],
              let exitID = node.activeOutgoingEdgeID, let exit = graph.edgesByID[exitID] else { return nil }
        return turnSignal(from: edge, to: exit, graph: graph)
    }

    private static func turnSignal(
        from incoming: RuntimeRouteEdge, to outgoing: RuntimeRouteEdge, graph: RuntimeRouteGraph
    ) -> TurnSignal? {
        let nodeID = incoming.toNodeID
        guard outgoing.fromNodeID == nodeID else { return nil }
        // Count physical branches, so a bend (including a two-way road) stays quiet.
        let neighbors = Set(graph.edgesByID.values.compactMap { edge -> String? in
            if edge.fromNodeID == nodeID { return edge.toNodeID }
            if edge.toNodeID == nodeID { return edge.fromNodeID }
            return nil
        })
        guard neighbors.count > 2 else { return nil }
        let approach = incoming.roadPath.tangent(atDistance: incoming.roadPath.totalLength)
        let departure = outgoing.roadPath.tangent(atDistance: 0)
        let cross = approach.x * departure.y - approach.y * departure.x
        guard abs(cross) > 0.35 else { return nil }
        // World Y points up; positive cross products turn toward the van's left.
        return cross > 0 ? .left : .right
    }
}

#if DEBUG
#Preview("Toy vans — 28 pt and 56 pt") {
    VStack(spacing: 24) {
        ForEach([VanColor.red, .blue, .yellow, .green], id: \.rawValue) { color in
            HStack(spacing: 28) {
                Text(color.displayName).frame(width: 60, alignment: .leading)
                MultiVanVanView(color: color)
                MultiVanVanView(color: color).rotationEffect(.degrees(90))
                MultiVanVanView(color: color, length: 56, turnSignal: .left).rotationEffect(.degrees(-45))
                MultiVanVanView(color: color, length: 56, turnSignal: .right).rotationEffect(.degrees(180))
            }
        }
    }
    .padding(28)
    .background(Color(white: 0.9))
}
#endif
