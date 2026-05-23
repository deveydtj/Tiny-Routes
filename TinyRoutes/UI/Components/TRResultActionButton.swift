import SwiftUI

struct TRResultActionButton: View {
    enum Variant {
        case primary
        case secondary
        case tertiary
    }

    let title: String
    let systemImage: String?
    let badgeText: String?
    let variant: Variant
    let action: () -> Void

    init(
        title: String,
        systemImage: String? = nil,
        badgeText: String? = nil,
        variant: Variant,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.systemImage = systemImage
        self.badgeText = badgeText
        self.variant = variant
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if let systemImage {
                    Image(systemName: systemImage)
                        .font(.system(size: iconSize, weight: .black, design: .rounded))
                        .accessibilityHidden(true)
                }

                Text(title)
                    .font(.system(size: fontSize, weight: .black, design: .rounded))
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)

                if let badgeText {
                    Text(badgeText)
                        .font(.system(size: 11, weight: .black, design: .rounded))
                        .foregroundStyle(.white)
                        .monospacedDigit()
                        .padding(.horizontal, 7)
                        .frame(height: 22)
                        .background {
                            Capsule()
                                .fill(TRGameplayStyle.Colors.resultWarningOrange)
                        }
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: height)
            .padding(.horizontal, 14)
            .contentShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
        }
        .buttonStyle(TRResultActionButtonStyle(variant: variant, height: height, cornerRadius: cornerRadius))
        .accessibilityLabel(Text(title))
    }

    private var height: CGFloat {
        switch variant {
        case .primary:
            return TRGameplayStyle.Metrics.resultPrimaryButtonHeight
        case .secondary:
            return TRGameplayStyle.Metrics.resultSecondaryButtonHeight
        case .tertiary:
            return 42
        }
    }

    private var cornerRadius: CGFloat {
        switch variant {
        case .primary:
            return 18
        case .secondary:
            return 16
        case .tertiary:
            return 14
        }
    }

    private var fontSize: CGFloat {
        switch variant {
        case .primary:
            return 20
        case .secondary:
            return 17
        case .tertiary:
            return 15
        }
    }

    private var iconSize: CGFloat {
        variant == .primary ? 18 : 15
    }
}

struct TRResultIconButton: View {
    let systemImage: String
    let label: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: 18, weight: .black, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.primaryBlue)
                .frame(width: 46, height: 46)
                .background {
                    Circle()
                        .fill(.white.opacity(0.90))
                        .overlay {
                            Circle()
                                .stroke(.white.opacity(0.72), lineWidth: 1)
                        }
                        .shadow(color: .black.opacity(0.08), radius: 8, x: 0, y: 5)
                }
        }
        .buttonStyle(.plain)
        .accessibilityLabel(Text(label))
    }
}

private struct TRResultActionButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled

    let variant: TRResultActionButton.Variant
    let height: CGFloat
    let cornerRadius: CGFloat

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(foregroundColor)
            .background {
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .fill(backgroundFill)
                    .overlay(alignment: .top) {
                        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                            .fill(.white.opacity(highlightOpacity))
                            .frame(height: height * 0.42)
                            .blur(radius: 8)
                            .offset(y: -height * 0.22)
                            .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
                    }
                    .overlay {
                        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                            .stroke(strokeColor, lineWidth: 1)
                    }
                    .shadow(color: shadowColor, radius: configuration.isPressed ? 6 : 11, x: 0, y: configuration.isPressed ? 3 : 7)
            }
            .opacity(isEnabled ? 1.0 : 0.58)
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(.spring(response: 0.20, dampingFraction: 0.72), value: configuration.isPressed)
    }

    private var foregroundColor: Color {
        switch variant {
        case .primary:
            return .white
        case .secondary:
            return TRGameplayStyle.Colors.titleNavy
        case .tertiary:
            return TRGameplayStyle.Colors.primaryBlue
        }
    }

    private var backgroundFill: some ShapeStyle {
        switch variant {
        case .primary:
            return LinearGradient(
                colors: [
                    Color(red: 0.21, green: 0.72, blue: 1.00),
                    TRGameplayStyle.Colors.primaryBlue
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        case .secondary:
            return LinearGradient(
                colors: [
                    .white,
                    Color(red: 0.94, green: 0.97, blue: 1.00)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        case .tertiary:
            return LinearGradient(
                colors: [
                    Color.white.opacity(0.01),
                    Color.white.opacity(0.01)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        }
    }

    private var strokeColor: Color {
        switch variant {
        case .primary:
            return .white.opacity(0.38)
        case .secondary:
            return .white.opacity(0.80)
        case .tertiary:
            return .clear
        }
    }

    private var shadowColor: Color {
        switch variant {
        case .primary:
            return TRGameplayStyle.Colors.primaryBlue.opacity(isEnabled ? 0.30 : 0.08)
        case .secondary:
            return Color(red: 0.50, green: 0.62, blue: 0.74).opacity(0.16)
        case .tertiary:
            return .clear
        }
    }

    private var highlightOpacity: Double {
        switch variant {
        case .primary:
            return 0.30
        case .secondary:
            return 0.62
        case .tertiary:
            return 0
        }
    }
}

#Preview("Result Actions") {
    VStack(spacing: 12) {
        TRResultActionButton(title: "Next Level", systemImage: "arrow.right", variant: .primary, action: {})
        TRResultActionButton(title: "Use Hint", systemImage: "lightbulb.fill", badgeText: "3", variant: .secondary, action: {})
        TRResultActionButton(title: "Skip Level", variant: .tertiary, action: {})
        HStack {
            TRResultIconButton(systemImage: "square.and.arrow.up", label: "Share", action: {})
            TRResultIconButton(systemImage: "house.fill", label: "Home", action: {})
        }
    }
    .padding()
    .background(Color(red: 0.88, green: 0.95, blue: 1.0))
}
