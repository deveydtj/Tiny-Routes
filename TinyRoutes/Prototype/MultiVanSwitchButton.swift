import SwiftUI

/// What one switch button shows and says, worked out once so every board offers the
/// same switches with the same words. It has no position: each board places the
/// button at its own projection of `nodeID`.
struct MultiVanSwitchControl: Identifiable {
    let nodeID: String
    let activeAngle: Double
    let optionAngles: [Double]
    let appearance: MultiVanSwitchAppearance
    let accessibilityLabel: String
    let accessibilityValue: String

    var id: String { nodeID }

    /// Nil when the node has no active exit to point at.
    init?(
        node: RuntimeRouteNode, engine: MultiVanEngine, graph: RuntimeRouteGraph,
        systemReduceMotion: Bool = false, reducesExtraAnimations: Bool = false
    ) {
        guard let edgeID = node.activeOutgoingEdgeID, let edge = graph.edgesByID[edgeID] else { return nil }
        nodeID = node.id
        activeAngle = SwitchArrowDirectionResolver.directionAngle(for: edge, from: node, in: graph)
        optionAngles = node.outgoingEdgeIDs.compactMap { graph.edgesByID[$0] }.map {
            SwitchArrowDirectionResolver.directionAngle(for: $0, from: node, in: graph)
        }
        appearance = MultiVanSwitchAppearance(
            engine: engine, nodeID: node.id,
            systemReduceMotion: systemReduceMotion, reducesExtraAnimations: reducesExtraAnimations
        )
        accessibilityLabel = MultiVanSwitchAppearance.accessibilityLabel(node: node, gridRows: engine.tuning.gridRows)
        accessibilityValue = appearance.routeAccessibilityValue(
            direction: SwitchOptionIndicatorLayout.cardinalDirectionLabel(for: activeAngle),
            exitCount: node.outgoingEdgeIDs.count
        )
    }

    /// Every switch on the board, in the stable order both boards list them.
    static func controls(
        engine: MultiVanEngine, graph: RuntimeRouteGraph,
        systemReduceMotion: Bool = false, reducesExtraAnimations: Bool = false
    ) -> [Self] {
        MultiVanBoardRules.switchNodes(in: graph).compactMap {
            Self(node: $0, engine: engine, graph: graph,
                 systemReduceMotion: systemReduceMotion, reducesExtraAnimations: reducesExtraAnimations)
        }
    }
}

/// A switch button where its board puts it, with the tap target it gets there.
struct MultiVanSwitchPlacement: Identifiable {
    let control: MultiVanSwitchControl
    /// The button's centre, in the board's coordinates.
    let point: CGPoint
    let hitShape: MultiVanSwitchHitShape

    var id: String { control.id }

    /// Each switch takes taps in its 44-point square, except where the square
    /// leaves `bounds` or overlaps a nearer switch's square. A tap then reaches the
    /// nearest switch whose square holds it, so any tap within 22 points of a
    /// switch reaches it unless two switches stand closer than 44 points.
    static func make(_ controls: [(MultiVanSwitchControl, CGPoint)], bounds: CGRect) -> [Self] {
        let half = MultiVanSwitchButton.hitSize / 2
        let squares = controls.map { _, point in
            CGRect(x: point.x - half, y: point.y - half, width: half * 2, height: half * 2).intersection(bounds)
        }
        return controls.enumerated().map { index, pair in
            let (control, point) = pair
            var region = Path(squares[index].isNull ? .zero : squares[index])
            for (otherIndex, (_, other)) in controls.enumerated() where otherIndex != index {
                let theirs = squares[otherIndex]
                guard !theirs.isNull, theirs.intersects(squares[index]) else { continue }
                let corners = [
                    CGPoint(x: theirs.minX, y: theirs.minY), CGPoint(x: theirs.maxX, y: theirs.minY),
                    CGPoint(x: theirs.maxX, y: theirs.maxY), CGPoint(x: theirs.minX, y: theirs.maxY),
                ]
                var claimed = Path()
                claimed.addLines(keepingNearer(corners, to: other, than: point))
                claimed.closeSubpath()
                region = region.subtracting(claimed)
            }
            let local = region.offsetBy(dx: half - point.x, dy: half - point.y)
            return Self(control: control, point: point, hitShape: MultiVanSwitchHitShape(region: local))
        }
    }

    /// The switch a tap at `point` reaches, as SwiftUI hit-tests the buttons.
    static func target(at point: CGPoint, in placements: [Self]) -> String? {
        let half = MultiVanSwitchButton.hitSize / 2
        return placements.first { placement in
            placement.hitShape.region.contains(CGPoint(x: point.x - placement.point.x + half, y: point.y - placement.point.y + half))
        }?.id
    }

    /// Clips a convex polygon to the half of the plane nearer `point` than `other`.
    private static func keepingNearer(_ polygon: [CGPoint], to point: CGPoint, than other: CGPoint) -> [CGPoint] {
        let middle = CGPoint(x: (point.x + other.x) / 2, y: (point.y + other.y) / 2)
        let away = CGPoint(x: other.x - point.x, y: other.y - point.y)
        let side = { (p: CGPoint) in (p.x - middle.x) * away.x + (p.y - middle.y) * away.y }
        var clipped: [CGPoint] = []
        for (index, current) in polygon.enumerated() {
            let next = polygon[(index + 1) % polygon.count]
            let a = side(current), b = side(next)
            if a <= 0 { clipped.append(current) }
            if (a <= 0) != (b <= 0) {
                let t = a / (a - b)
                clipped.append(CGPoint(x: current.x + (next.x - current.x) * t, y: current.y + (next.y - current.y) * t))
            }
        }
        return clipped
    }
}

/// A switch button's tap target, in the button's own 44-point square.
struct MultiVanSwitchHitShape: Shape {
    var region: Path

    static let square = Self(region: Path(CGRect(x: 0, y: 0, width: MultiVanSwitchButton.hitSize, height: MultiVanSwitchButton.hitSize)))

    func path(in rect: CGRect) -> Path {
        region
    }
}

/// The one place a switch tap reaches the engine. Boards only decide where it sits.
struct MultiVanSwitchButton: View {
    static let hitSize: CGFloat = 44

    let control: MultiVanSwitchControl
    let engine: MultiVanEngine
    var onSwitchTapped: ((String, MultiVanTapResult) -> Void)? = nil
    var onEventsProduced: (() -> Void)? = nil
    var rejectionToken: UUID? = nil
    var animates = true
    var hitShape = MultiVanSwitchHitShape.square
    /// False when the board draws its own dial under the button, as the diorama does.
    var drawsDial = true

    var body: some View {
        Button(action: tap) {
            label
                .frame(width: Self.hitSize, height: Self.hitSize)
                .contentShape(hitShape)
        }
        .buttonStyle(.plain)
        // Sizes the element too: a clear label alone leaves VoiceOver's frame unset.
        .frame(width: Self.hitSize, height: Self.hitSize)
        .accessibilityElement(children: .ignore)
        // A fresh element drops the button's own trait and action, and VoiceOver
        // would fall back to a synthetic tap; act directly instead.
        .accessibilityAddTraits(.isButton)
        .accessibilityAction(.default, tap)
        .accessibilityLabel(control.accessibilityLabel)
        .accessibilityValue(control.accessibilityValue)
        .accessibilityHint(control.appearance.accessibilityHint)
    }

    private func tap() {
        let result = engine.tapSwitch(nodeID: control.nodeID)
        onSwitchTapped?(control.nodeID, result)
        onEventsProduced?()
    }

    @ViewBuilder
    private var label: some View {
        if drawsDial {
            MultiVanSwitchDialView(
                activeAngle: control.activeAngle,
                optionAngles: control.optionAngles,
                tint: control.appearance.dialTint,
                animates: animates
            )
            .opacity(control.appearance.opacity)
            .overlay {
                MultiVanSwitchIndicators(
                    appearance: control.appearance,
                    rejectionToken: rejectionToken,
                    reduceMotion: !animates
                )
                .allowsHitTesting(false)
                .accessibilityHidden(true)
            }
            .keyframeAnimator(initialValue: 0.0, trigger: rejectionToken) { content, progress in
                content.offset(x: animates ? MultiVanCrashEffects.shakeOffset(progress: progress) * 0.75 : 0)
            } keyframes: { _ in
                MoveKeyframe(0.0)
                LinearKeyframe(1.0, duration: 0.32)
            }
        } else {
            Color.clear
        }
    }
}

/// All decoration stays inside the existing 44-point target, clear of the route arrow.
private struct MultiVanSwitchIndicators: View {
    let appearance: MultiVanSwitchAppearance
    let rejectionToken: UUID?
    let reduceMotion: Bool

    var body: some View {
        ZStack {
            if appearance.isLive {
                Circle()
                    .strokeBorder(Color.orange, style: StrokeStyle(
                        lineWidth: appearance.showsLock ? 3 : 2,
                        dash: appearance.showsLock ? [3, 2] : []
                    ))
                    .frame(width: 38, height: 38)
                    .phaseAnimator(appearance.pulses ? [false, true] : [false]) { content, phase in
                        content.opacity(phase ? 0.55 : 1)
                    } animation: { _ in appearance.pulses ? .easeInOut(duration: 0.9) : nil }
                badge("bolt.fill", color: .orange)
                    .offset(x: -13, y: -13)
            }
            if appearance.showsLock {
                badge("lock.fill", color: .primary)
                    .keyframeAnimator(initialValue: 1.0, trigger: rejectionToken) { content, opacity in
                        content.opacity(reduceMotion ? 1 : opacity)
                    } keyframes: { _ in
                        MoveKeyframe(1.0)
                        LinearKeyframe(0.25, duration: 0.08)
                        LinearKeyframe(1.0, duration: 0.08)
                        LinearKeyframe(0.25, duration: 0.08)
                        LinearKeyframe(1.0, duration: 0.08)
                    }
                    .offset(x: 13, y: -13)
            }
        }
        .frame(width: MultiVanSwitchButton.hitSize, height: MultiVanSwitchButton.hitSize)
    }

    private func badge(_ symbol: String, color: Color) -> some View {
        Image(systemName: symbol)
            .font(.system(size: 9, weight: .heavy))
            .foregroundStyle(color)
            .frame(width: 14, height: 14)
            .background(.white, in: Circle())
    }
}
