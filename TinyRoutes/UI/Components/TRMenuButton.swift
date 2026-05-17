import SwiftUI

/// A reusable menu button matching the soft, generated Tiny Routes home style.
struct TRMenuButton: View {
    let title: String
    let systemImage: String
    let variant: TRButtonVariant
    let size: TRButtonSize
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Image(systemName: systemImage)
                    .font(.system(size: size.iconSize, weight: .bold))
                    .frame(width: 44)

                Text(title)
                    .font(.system(size: size.fontSize, weight: .heavy, design: .rounded))
                    .lineLimit(1)
                    .minimumScaleFactor(0.82)

                Color.clear
                    .frame(width: 44, height: 1)
            }
            .frame(maxWidth: .infinity)
            .frame(height: size.height)
            .padding(.horizontal, 20)
        }
        .buttonStyle(TRMenuButtonStyle(variant: variant, size: size))
        .accessibilityLabel(Text(title))
    }
}

enum TRButtonSize: Equatable {
    case primary
    case secondary

    var height: CGFloat {
        switch self {
        case .primary:
            return 74
        case .secondary:
            return 62
        }
    }

    var cornerRadius: CGFloat {
        switch self {
        case .primary:
            return 21
        case .secondary:
            return 18
        }
    }

    var fontSize: CGFloat {
        switch self {
        case .primary:
            return 25
        case .secondary:
            return 21
        }
    }

    var iconSize: CGFloat {
        switch self {
        case .primary:
            return 26
        case .secondary:
            return 22
        }
    }
}

enum TRButtonVariant {
    case play
    case dailyRoute
    case shop
    case settings

    var foregroundColor: Color {
        switch self {
        case .play, .dailyRoute, .shop:
            return .white
        case .settings:
            return Color(red: 0.20, green: 0.26, blue: 0.36)
        }
    }

    var gradient: LinearGradient {
        LinearGradient(colors: gradientColors, startPoint: .top, endPoint: .bottom)
    }

    var shadowColor: Color {
        switch self {
        case .play:
            return Color(red: 0.03, green: 0.46, blue: 0.85)
        case .dailyRoute:
            return Color(red: 0.08, green: 0.60, blue: 0.53)
        case .shop:
            return Color(red: 0.29, green: 0.19, blue: 0.78)
        case .settings:
            return Color(red: 0.61, green: 0.69, blue: 0.77)
        }
    }

    var highlightOpacity: Double {
        switch self {
        case .settings:
            return 0.82
        default:
            return 0.32
        }
    }

    var strokeOpacity: Double {
        switch self {
        case .settings:
            return 0.72
        default:
            return 0.38
        }
    }

    var glowOpacity: Double {
        switch self {
        case .settings:
            return 0.08
        default:
            return 0.18
        }
    }

    private var gradientColors: [Color] {
        switch self {
        case .play:
            return [
                Color(red: 0.20, green: 0.72, blue: 1.00),
                Color(red: 0.04, green: 0.50, blue: 0.92)
            ]
        case .dailyRoute:
            return [
                Color(red: 0.26, green: 0.87, blue: 0.77),
                Color(red: 0.10, green: 0.72, blue: 0.62)
            ]
        case .shop:
            return [
                Color(red: 0.55, green: 0.40, blue: 0.96),
                Color(red: 0.36, green: 0.23, blue: 0.87)
            ]
        case .settings:
            return [
                Color.white,
                Color(red: 0.92, green: 0.95, blue: 0.98)
            ]
        }
    }
}

private struct TRMenuButtonStyle: ButtonStyle {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.isEnabled) private var isEnabled

    let variant: TRButtonVariant
    let size: TRButtonSize

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(variant.foregroundColor)
            .background {
                TRButtonBackground(
                    variant: variant,
                    size: size,
                    isPressed: configuration.isPressed,
                    isEnabled: isEnabled
                )
            }
            .scaleEffect(scale(isPressed: configuration.isPressed))
            .opacity(opacity(isPressed: configuration.isPressed))
            .animation(animation, value: configuration.isPressed)
            .animation(.easeOut(duration: 0.12), value: isEnabled)
    }

    private var animation: Animation? {
        reduceMotion ? .easeOut(duration: 0.08) : .spring(response: 0.22, dampingFraction: 0.72)
    }

    private func scale(isPressed: Bool) -> CGFloat {
        guard !reduceMotion, isPressed else { return 1.0 }
        return 0.97
    }

    private func opacity(isPressed: Bool) -> Double {
        if !isEnabled {
            return 0.62
        }
        return isPressed ? 0.94 : 1.0
    }
}

private struct TRButtonBackground: View {
    let variant: TRButtonVariant
    let size: TRButtonSize
    let isPressed: Bool
    let isEnabled: Bool

    var body: some View {
        RoundedRectangle(cornerRadius: size.cornerRadius, style: .continuous)
            .fill(variant.gradient)
            .saturation(isEnabled ? 1.0 : 0.42)
            .overlay(alignment: .top) {
                RoundedRectangle(cornerRadius: size.cornerRadius, style: .continuous)
                    .fill(.white.opacity(variant.highlightOpacity))
                    .frame(height: size.height * 0.42)
                    .blur(radius: 10)
                    .offset(y: -size.height * 0.22)
                    .clipShape(RoundedRectangle(cornerRadius: size.cornerRadius, style: .continuous))
            }
            .overlay(alignment: .bottom) {
                RoundedRectangle(cornerRadius: size.cornerRadius, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: [.black.opacity(0.11), .clear],
                            startPoint: .bottom,
                            endPoint: .top
                        )
                    )
                    .frame(height: size.height * 0.45)
                    .clipShape(RoundedRectangle(cornerRadius: size.cornerRadius, style: .continuous))
            }
            .overlay {
                RoundedRectangle(cornerRadius: size.cornerRadius, style: .continuous)
                    .stroke(.white.opacity(variant.strokeOpacity), lineWidth: 1)
            }
            .shadow(
                color: variant.shadowColor.opacity(isEnabled ? variant.glowOpacity : 0.04),
                radius: isPressed ? 8 : 16,
                x: 0,
                y: isPressed ? 4 : 10
            )
            .shadow(
                color: variant.shadowColor.opacity(isEnabled ? 0.28 : 0.10),
                radius: isPressed ? 6 : 12,
                x: 0,
                y: isPressed ? 3 : 8
            )
    }
}

struct TRMenuButton_Previews: PreviewProvider {
    static var previews: some View {
        VStack(spacing: 14) {
            TRMenuButton(title: "Play", systemImage: "play.fill", variant: .play, size: .primary, action: {})
            TRMenuButton(title: "Daily Route", systemImage: "calendar", variant: .dailyRoute, size: .secondary, action: {})
            TRMenuButton(title: "Shop", systemImage: "bag.fill", variant: .shop, size: .secondary, action: {})
            TRMenuButton(title: "Settings", systemImage: "gearshape.fill", variant: .settings, size: .secondary, action: {})
            TRMenuButton(title: "Daily Route", systemImage: "calendar", variant: .dailyRoute, size: .secondary, action: {})
                .disabled(true)
        }
        .padding(32)
        .previewLayout(.sizeThatFits)
    }
}
