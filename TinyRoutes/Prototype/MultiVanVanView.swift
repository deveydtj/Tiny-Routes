import SwiftUI

/// Front faces up at zero rotation. All details scale with the overall length.
struct MultiVanVanView: View {
    let color: VanColor
    var length: CGFloat = 28
    var status: MultiVanVanState.Status = .waiting
    var reaction: MultiVanPersonality.Reaction?
    var reducesExtraAnimations = false
    var isDelivered = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

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
                Capsule()
                    .fill(.white)
                    .frame(width: length * 0.11, height: length * 0.075)
                    .offset(x: length * 0.17 * side, y: -length * 0.4)
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
        .accessibilityLabel("\(color.displayName) \(color.accessibilitySymbolName) van")
        .accessibilityValue(Self.accessibilityValue(color: color, status: status, isDelivered: isDelivered))
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
        let road: RoadPath?
        let distance: Double
        if let edgeID = van.currentEdgeID, let edge = graph.edgesByID[edgeID] {
            // Parked/crashed vans retain this edge and their last travel distance.
            road = edge.roadPath
            distance = van.distanceAlongEdge
        } else {
            let firstExit = startNodeID.flatMap { graph.nodesByID[$0]?.outgoingEdgeIDs.first }
            road = firstExit.flatMap { graph.edgesByID[$0]?.roadPath }
            distance = 0
        }
        return heading(for: road?.tangent(atDistance: distance) ?? RoadVector(x: 0, y: 0))
    }

    static func heading(for tangent: RoadVector) -> Angle {
        let magnitude = hypot(tangent.x, tangent.y)
        guard magnitude.isFinite, magnitude > 1e-9 else { return .zero }
        // MV-12 projects (x, y) to (x, -y). With the artwork facing screen-up,
        // atan2(x, y) gives clockwise SwiftUI rotation: up 0, right π/2.
        return .radians(atan2(tangent.x, tangent.y))
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
                MultiVanVanView(color: color, length: 56).rotationEffect(.degrees(-45))
                MultiVanVanView(color: color, length: 56).rotationEffect(.degrees(180))
            }
        }
    }
    .padding(28)
    .background(Color(white: 0.9))
}
#endif
