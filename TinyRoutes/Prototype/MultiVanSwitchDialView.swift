import SwiftUI

/// A toy rotary knob. Angles use screen coordinates (0 points right, positive Y down),
/// matching `SwitchArrowDirectionResolver`, so they feed `rotationEffect` directly.
struct MultiVanSwitchDialView: View {
    enum Tint: Equatable {
        case ready, live, locked
    }

    let activeAngle: Double
    var optionAngles: [Double] = []
    var tint: Tint = .ready
    var side: CGFloat = 34
    var animates = true

    // The knob keeps an unwrapped angle so a turn from -π/2 to π never spins the long way.
    @State private var turnedAngle: Double
    @State private var turnDuration = 0.16
    @State private var turn = Turn()

    private struct Turn: Equatable {
        var token = 0
        var direction = 1.0
    }

    private struct Motion {
        var wobble = 0.0
        var scale = 1.0
    }

    init(
        activeAngle: Double, optionAngles: [Double] = [], tint: Tint = .ready,
        side: CGFloat = 34, animates: Bool = true
    ) {
        self.activeAngle = activeAngle
        self.optionAngles = optionAngles
        self.tint = tint
        self.side = side
        self.animates = animates
        _turnedAngle = State(initialValue: activeAngle)
    }

    var body: some View {
        ZStack {
            Circle()
                .fill(Color(red: 1, green: 0.965, blue: 0.89).gradient)
                .overlay { Circle().strokeBorder(.white, lineWidth: side * 0.075) }
                .shadow(color: .black.opacity(0.2), radius: side * 0.05, y: side * 0.05)

            ForEach(Array(optionAngles.enumerated()), id: \.offset) { _, angle in
                Circle()
                    .fill(Color(red: 0.8, green: 0.72, blue: 0.56))
                    .frame(width: side * 0.1, height: side * 0.1)
                    .offset(x: cos(angle) * side * 0.41, y: sin(angle) * side * 0.41)
            }

            DialKnobShape()
                .fill(knobGradient)
                .overlay {
                    DialKnobShape().stroke(.white, style: StrokeStyle(lineWidth: side * 0.05, lineJoin: .round))
                }
                .frame(width: side, height: side)
                .keyframeAnimator(initialValue: Motion(), trigger: turn) { content, motion in
                    content
                        .rotationEffect(.degrees(motion.wobble))
                        .scaleEffect(motion.scale)
                } keyframes: { _ in
                    // The turn snaps into its notch, then the spring overshoots and settles.
                    KeyframeTrack(\.wobble) {
                        MoveKeyframe(0)
                        LinearKeyframe(0, duration: turnDuration)
                        CubicKeyframe(11 * turn.direction, duration: 0.06)
                        CubicKeyframe(-6 * turn.direction, duration: 0.09)
                        CubicKeyframe(3 * turn.direction, duration: 0.09)
                        CubicKeyframe(-1 * turn.direction, duration: 0.08)
                        CubicKeyframe(0, duration: 0.08)
                    }
                    KeyframeTrack(\.scale) {
                        MoveKeyframe(1)
                        CubicKeyframe(0.9, duration: 0.06)
                        SpringKeyframe(1, duration: 0.3, spring: .bouncy)
                    }
                }
                .rotationEffect(.radians(turnedAngle))

            // Fixed cap and glint stay put while the knob turns beneath them.
            Circle()
                .fill(TRGameplayStyle.Colors.titleNavy)
                .frame(width: side * 0.15, height: side * 0.15)
            Ellipse()
                .fill(.white.opacity(0.5))
                .frame(width: side * 0.15, height: side * 0.09)
                .offset(x: -side * 0.1, y: -side * 0.12)
        }
        .frame(width: side, height: side)
        .onChange(of: activeAngle) { _, newAngle in
            let delta = Self.shortestTurn(from: turnedAngle, to: newAngle)
            guard abs(delta) > 0.001 else { return }
            guard animates else {
                turnedAngle += delta
                return
            }
            turnDuration = 0.1 + 0.06 * abs(delta) / (.pi / 2)
            // Ease in so the knob arrives fast and the wobble reads as the spring catching.
            withAnimation(.timingCurve(0.45, 0, 0.9, 0.6, duration: turnDuration)) {
                turnedAngle += delta
            }
            turn = Turn(token: turn.token + 1, direction: delta < 0 ? -1 : 1)
        }
        .accessibilityHidden(true)
    }

    private var knobGradient: AnyGradient {
        switch tint {
        case .ready: Color(red: 1, green: 0.78, blue: 0.2).gradient
        case .live: Color(red: 1, green: 0.55, blue: 0.16).gradient
        case .locked: Color(red: 0.62, green: 0.67, blue: 0.75).gradient
        }
    }

    /// Signed radians in (-π, π]; a half turn goes clockwise.
    static func shortestTurn(from current: Double, to target: Double) -> Double {
        var delta = (target - current).truncatingRemainder(dividingBy: 2 * .pi)
        if delta <= -.pi { delta += 2 * .pi }
        if delta > .pi { delta -= 2 * .pi }
        return delta
    }
}

/// A teardrop pointing right: a round grip with a tip that reaches the notch ring.
struct DialKnobShape: Shape {
    func path(in rect: CGRect) -> Path {
        let side = min(rect.width, rect.height)
        let center = CGPoint(x: rect.midX, y: rect.midY)
        let radius = side * 0.27
        let tip = side * 0.45
        let tangent = acos(radius / tip)
        var path = Path()
        path.move(to: CGPoint(x: center.x + tip, y: center.y))
        path.addArc(
            center: center, radius: radius,
            startAngle: .radians(tangent), endAngle: .radians(-tangent), clockwise: false
        )
        path.closeSubpath()
        return path
    }
}

#if DEBUG
#Preview("Switch dials — tap to turn") {
    struct Demo: View {
        @State private var index = 0
        let options: [Double] = [.pi, -.pi / 2, 0]

        var body: some View {
            VStack(spacing: 28) {
                Button {
                    index = (index + 1) % options.count
                } label: {
                    MultiVanSwitchDialView(activeAngle: options[index], optionAngles: options, side: 96)
                }
                .buttonStyle(.plain)
                HStack(spacing: 24) {
                    MultiVanSwitchDialView(activeAngle: 0, optionAngles: [.pi, 0])
                    MultiVanSwitchDialView(activeAngle: -.pi / 2, optionAngles: options, tint: .live)
                    MultiVanSwitchDialView(activeAngle: .pi, optionAngles: options, tint: .locked)
                }
            }
            .padding(32)
            .background(Color(white: 0.9))
        }
    }
    return Demo()
}
#endif
