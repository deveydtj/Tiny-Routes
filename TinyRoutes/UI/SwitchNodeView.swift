import SwiftUI

enum SwitchNodeInteractionState: String, Equatable {
    case inactive
    case upcoming
    case eligible
    case locked

    var accessibilityValue: String {
        switch self {
        case .inactive: return "Not currently available"
        case .upcoming: return "Upcoming; not yet available"
        case .eligible: return "Available to change"
        case .locked: return "Locked after route commitment"
        }
    }
}

struct SpriteImage: View {
    let name: String

    var body: some View {
        if let image = Self.loadImage(named: name) {
            Image(uiImage: image)
                .resizable()
        } else {
            Color.clear
        }
    }

    private static func loadImage(named name: String) -> UIImage? {
        if let image = UIImage(named: "\(name).png") ?? UIImage(named: name) {
            return image
        }

        let imageURLs = ["png", "jpg"].flatMap { fileExtension in
            [
                Bundle.main.url(forResource: name, withExtension: fileExtension),
                Bundle.main.url(forResource: name, withExtension: fileExtension, subdirectory: "Sprites"),
                Bundle.main.url(forResource: name, withExtension: fileExtension, subdirectory: "Resources/Sprites")
            ]
        }

        return imageURLs
            .compactMap { $0 }
            .lazy
            .compactMap { UIImage(contentsOfFile: $0.path) }
            .first
    }
}

struct SwitchNodeView: View {
    let activeDirectionAngle: Double
    let spriteSize: CGFloat
    let ringSize: CGFloat
    let optionCount: Int
    let optionAngles: [Double]
    let interactionState: SwitchNodeInteractionState
    let pressEventToken: Int?
    let rejectionEventToken: Int?

    @State private var isPressed = false
    @State private var isPulsing = false
    @State private var rejectionOffset: CGFloat = 0

    init(
        activeDirectionAngle: Double,
        spriteSize: CGFloat,
        ringSize: CGFloat,
        optionCount: Int = 2,
        optionAngles: [Double] = [],
        interactionState: SwitchNodeInteractionState = .inactive,
        pressEventToken: Int? = nil,
        rejectionEventToken: Int? = nil
    ) {
        self.activeDirectionAngle = activeDirectionAngle
        self.spriteSize = spriteSize
        self.ringSize = ringSize
        self.optionCount = optionCount
        self.optionAngles = optionAngles
        self.interactionState = interactionState
        self.pressEventToken = pressEventToken
        self.rejectionEventToken = rejectionEventToken
    }

    var body: some View {
        ZStack {
            Circle()
                .fill(stateColor.opacity(interactionState == .eligible ? 0.18 : 0.07))
                .frame(width: TRGameplayStyle.Metrics.switchTouchHaloSize, height: TRGameplayStyle.Metrics.switchTouchHaloSize)
                .overlay {
                    Circle()
                        .stroke(stateColor.opacity(interactionState == .eligible ? 0.65 : 0.16), lineWidth: interactionState == .eligible ? 2 : 1)
                }
                .accessibilityHidden(true)

            Circle()
                .stroke(stateColor.opacity(isPulsing ? 0.32 : 0), lineWidth: 2)
                .frame(
                    width: isPulsing ? TRGameplayStyle.Metrics.switchTouchHaloSize + 8 : ringSize + 4,
                    height: isPulsing ? TRGameplayStyle.Metrics.switchTouchHaloSize + 8 : ringSize + 4
                )
                .accessibilityHidden(true)

            Circle()
                .fill(Color.white.opacity(0.96))
                .frame(width: ringSize, height: ringSize)
                .overlay {
                    Circle()
                        .stroke(Color.white, lineWidth: 3)
                }
                .overlay {
                    Circle()
                        .stroke(TRGameplayStyle.Colors.markerStroke, lineWidth: 2)
                        .padding(1)
                }
                .shadow(color: Color.black.opacity(0.18), radius: 7, x: 0, y: 4)

            ForEach(Array(optionIndicatorAngles.enumerated()), id: \.offset) { _, angle in
                SwitchOptionNub(
                    angle: angle,
                    radius: max(ringSize * 0.44, 1),
                    isActive: SwitchOptionIndicatorLayout.anglesMatch(angle, activeDirectionAngle)
                )
            }

            ConceptDirectionArrowGlyph(activeDirectionAngle: activeDirectionAngle)
        }
        .scaleEffect(isPressed ? 0.94 : 1)
        .opacity(interactionState == .locked ? 0.58 : 1)
        .offset(x: rejectionOffset)
        .frame(
            width: max(spriteSize, ringSize, TRGameplayStyle.Metrics.switchTapTargetSize),
            height: max(spriteSize, ringSize, TRGameplayStyle.Metrics.switchTapTargetSize)
        )
        .contentShape(Circle())
        .accessibilityLabel(accessibilityLabel)
        .accessibilityValue(interactionState.accessibilityValue)
        .onChange(of: pressEventToken) { _, newValue in
            guard newValue != nil else {
                return
            }
            playPressAnimation()
        }
        .onChange(of: rejectionEventToken) { _, newValue in
            guard newValue != nil else { return }
            playRejectedAnimation()
        }
    }

    private var stateColor: Color {
        switch interactionState {
        case .eligible: return TRGameplayStyle.Colors.primaryBlue
        case .upcoming: return TRGameplayStyle.Colors.successGreen
        case .inactive, .locked: return TRGameplayStyle.Colors.markerStroke
        }
    }

    private var optionIndicatorAngles: [Double] {
        SwitchOptionIndicatorLayout.angles(optionCount: optionCount, optionAngles: optionAngles)
    }

    private var accessibilityLabel: String {
        let clampedOptionCount = max(0, min(optionCount, SwitchNodeKind.maximumSupportedOutgoingEdgeCount))
        let direction = SwitchOptionIndicatorLayout.cardinalDirectionLabel(for: activeDirectionAngle)
        if clampedOptionCount == 4 {
            return "4-way switch, active \(direction)"
        }
        return "\(clampedOptionCount)-way switch, active \(direction)"
    }

    private func playPressAnimation() {
        withAnimation(.easeOut(duration: 0.07)) {
            isPressed = true
            isPulsing = true
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.08) {
            withAnimation(.spring(response: 0.18, dampingFraction: 0.58)) {
                isPressed = false
            }
            withAnimation(.easeOut(duration: 0.18)) {
                isPulsing = false
            }
        }
    }

    private func playRejectedAnimation() {
        withAnimation(.easeInOut(duration: 0.06).repeatCount(3, autoreverses: true)) {
            rejectionOffset = 3
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.36) {
            rejectionOffset = 0
        }
    }
}

struct SwitchOptionNub: View {
    let angle: Double
    let radius: CGFloat
    let isActive: Bool

    var body: some View {
        Circle()
            .fill(isActive ? TRGameplayStyle.Colors.titleNavy.opacity(0.50) : TRGameplayStyle.Colors.markerStroke.opacity(0.26))
            .frame(width: isActive ? 6 : 4, height: isActive ? 6 : 4)
            .offset(
                x: CGFloat(cos(angle)) * radius,
                y: CGFloat(-sin(angle)) * radius
            )
            .accessibilityHidden(true)
    }
}

struct SwitchOptionIndicatorLayout {
    static func angles(optionCount: Int, optionAngles: [Double]) -> [Double] {
        let clampedCount = max(0, min(optionCount, SwitchNodeKind.maximumSupportedOutgoingEdgeCount))
        guard clampedCount > 1 else {
            return []
        }

        let validAngles = optionAngles.prefix(clampedCount).map(normalizedAngle)
        if validAngles.count == clampedCount {
            return validAngles
        }

        return (0..<clampedCount).map { index in
            normalizedAngle((Double(index) / Double(clampedCount)) * 2 * .pi)
        }
    }

    static func anglesMatch(_ first: Double, _ second: Double, tolerance: Double = 0.001) -> Bool {
        abs(normalizedAngle(first - second)) <= tolerance
    }

    static func cardinalDirectionLabel(for angle: Double) -> String {
        let normalized = normalizedAngle(angle)
        let directions: [(label: String, angle: Double)] = [
            ("east", 0),
            ("north", -.pi / 2),
            ("west", .pi),
            ("south", .pi / 2)
        ]
        return directions.min { first, second in
            abs(normalizedAngle(normalized - first.angle)) < abs(normalizedAngle(normalized - second.angle))
        }?.label ?? "east"
    }

    private static func normalizedAngle(_ angle: Double) -> Double {
        var normalizedAngle = angle
        while normalizedAngle <= -.pi {
            normalizedAngle += 2 * .pi
        }
        while normalizedAngle > .pi {
            normalizedAngle -= 2 * .pi
        }
        return normalizedAngle
    }
}

struct ConceptDirectionArrowGlyph: View {
    let activeDirectionAngle: Double

    private var arrowTransform: DirectionalArrowTransform {
        DirectionalArrowTransform(angle: activeDirectionAngle)
    }

    var body: some View {
        Image(systemName: "arrow.right")
            .font(.system(size: 22, weight: .heavy, design: .rounded))
            .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
            .scaleEffect(x: arrowTransform.xScale, y: 1)
            .rotationEffect(.radians(arrowTransform.rotationAngle))
            .accessibilityHidden(true)
    }
}

struct DirectionalArrowTransform {
    let rotationAngle: Double
    let xScale: CGFloat

    init(angle: Double) {
        let normalizedAngle = Self.normalizedAngle(angle)
        if cos(normalizedAngle) < 0 {
            rotationAngle = Self.normalizedAngle(normalizedAngle - .pi)
            xScale = -1
        } else {
            rotationAngle = normalizedAngle
            xScale = 1
        }
    }

    private static func normalizedAngle(_ angle: Double) -> Double {
        var normalizedAngle = angle
        while normalizedAngle <= -.pi {
            normalizedAngle += 2 * .pi
        }
        while normalizedAngle > .pi {
            normalizedAngle -= 2 * .pi
        }
        return normalizedAngle
    }
}

struct SwitchNodeView_Previews: PreviewProvider {
    static var previews: some View {
        HStack(spacing: 18) {
            SwitchNodeView(activeDirectionAngle: 0, spriteSize: 52, ringSize: 42)
            SwitchNodeView(activeDirectionAngle: -.pi / 2, spriteSize: 52, ringSize: 42, optionCount: 3)
            SwitchNodeView(activeDirectionAngle: .pi, spriteSize: 52, ringSize: 42, optionCount: 4)
            SwitchNodeView(activeDirectionAngle: .pi / 2, spriteSize: 52, ringSize: 42, optionCount: 4)
        }
        .padding()
        .background(Color(red: 0.86, green: 0.93, blue: 0.98))
    }
}
