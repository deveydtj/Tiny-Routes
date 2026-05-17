import SwiftUI

/// A reusable menu button matching the soft, generated Tiny Routes home style.
struct TRMenuButton: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var activationProgress: CGFloat = 0

    let title: String
    let systemImage: String?
    let spriteName: String?
    let variant: TRButtonVariant
    let size: TRButtonSize
    let action: () -> Void

    var body: some View {
        Button(action: triggerAction) {
            HStack(spacing: 10) {
                decorativeIconView

                Text(title)
                    .font(.system(size: size.fontSize, weight: .heavy, design: .rounded))
                    .lineLimit(1)
                    .minimumScaleFactor(0.82)

                Color.clear
                    .frame(width: size.iconContainerSize, height: size.iconContainerSize)
            }
            .frame(maxWidth: .infinity)
            .frame(height: size.height)
            .padding(.horizontal, 18)
        }
        .buttonStyle(
            TRMenuButtonStyle(
                variant: variant,
                size: size,
                activationProgress: activationProgress
            )
        )
        .accessibilityLabel(Text(title))
    }

    @ViewBuilder
    private var decorativeIconView: some View {
        if let spriteName {
            SpriteImage(name: spriteName)
                .scaledToFill()
                .frame(width: size.iconFrameSize, height: size.iconFrameSize)
                .scaleEffect(size.spriteZoomScale)
                .frame(width: size.iconFrameSize, height: size.iconFrameSize)
                .clipped()
                .offset(y: spriteVerticalOffset)
                .frame(width: size.iconContainerSize, height: size.iconContainerSize)
        } else if let systemImage {
            Image(systemName: systemImage)
                .font(.system(size: size.iconSize, weight: .bold))
                .frame(width: size.iconContainerSize, height: size.iconContainerSize)
        } else {
            Color.clear
                .frame(width: size.iconContainerSize, height: size.iconContainerSize)
        }
    }

    private var spriteVerticalOffset: CGFloat {
        spriteName == "settings_gear" ? 2 : 0
    }

    private func triggerAction() {
        guard activationProgress == 0 else {
            action()
            return
        }

        if reduceMotion {
            activationProgress = 1
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.10) {
                activationProgress = 0
            }
        } else {
            withAnimation(.easeOut(duration: 0.08)) {
                activationProgress = 1
            }

            DispatchQueue.main.asyncAfter(deadline: .now() + 0.18) {
                withAnimation(.spring(response: 0.34, dampingFraction: 0.58)) {
                    activationProgress = 0
                }
            }
        }

        action()
    }
}

enum TRButtonSize: Equatable {
    case primary
    case secondary

    var height: CGFloat {
        switch self {
        case .primary:
            return 64
        case .secondary:
            return 54
        }
    }

    var cornerRadius: CGFloat {
        switch self {
        case .primary:
            return 18
        case .secondary:
            return 16
        }
    }

    var fontSize: CGFloat {
        switch self {
        case .primary:
            return 23
        case .secondary:
            return 20
        }
    }

    var iconSize: CGFloat {
        switch self {
        case .primary:
            return 24
        case .secondary:
            return 21
        }
    }

    var iconFrameSize: CGFloat {
        switch self {
        case .primary:
            return 36
        case .secondary:
            return 32
        }
    }

    var spriteZoomScale: CGFloat {
        switch self {
        case .primary:
            return 1.45
        case .secondary:
            return 1.50
        }
    }

    var iconContainerSize: CGFloat {
        switch self {
        case .primary:
            return 42
        case .secondary:
            return 40
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
    let activationProgress: CGFloat

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(variant.foregroundColor)
            .background {
                TRButtonBackground(
                    variant: variant,
                    size: size,
                    isPressed: configuration.isPressed,
                    isEnabled: isEnabled,
                    activationProgress: activationProgress
                )
            }
            .scaleEffect(scale(isPressed: configuration.isPressed))
            .offset(y: verticalOffset(isPressed: configuration.isPressed))
            .opacity(opacity(isPressed: configuration.isPressed))
            .animation(animation, value: configuration.isPressed)
            .animation(.easeOut(duration: 0.16), value: activationProgress)
            .animation(.easeOut(duration: 0.12), value: isEnabled)
    }

    private var animation: Animation? {
        reduceMotion ? .easeOut(duration: 0.08) : .spring(response: 0.22, dampingFraction: 0.72)
    }

    private func scale(isPressed: Bool) -> CGFloat {
        if reduceMotion {
            return isPressed ? 0.98 : 1.0
        }

        if isPressed {
            return 0.962
        }

        return 1.0 + (0.022 * activationProgress)
    }

    private func verticalOffset(isPressed: Bool) -> CGFloat {
        if isPressed {
            return 1.5
        }

        return reduceMotion ? 0 : (-1.2 * activationProgress)
    }

    private func opacity(isPressed: Bool) -> Double {
        if !isEnabled {
            return 0.62
        }
        return isPressed ? 0.95 : 1.0
    }
}

private struct TRButtonBackground: View {
    let variant: TRButtonVariant
    let size: TRButtonSize
    let isPressed: Bool
    let isEnabled: Bool
    let activationProgress: CGFloat

    var body: some View {
        RoundedRectangle(cornerRadius: size.cornerRadius, style: .continuous)
            .fill(variant.gradient)
            .saturation(isEnabled ? 1.0 : 0.42)
            .brightness(isEnabled ? 0.02 * activationProgress : 0)
            .overlay(alignment: .top) {
                RoundedRectangle(cornerRadius: size.cornerRadius, style: .continuous)
                    .fill(.white.opacity(variant.highlightOpacity))
                    .frame(height: size.height * 0.42)
                    .blur(radius: 10)
                    .offset(y: -size.height * 0.22)
                    .clipShape(RoundedRectangle(cornerRadius: size.cornerRadius, style: .continuous))
            }
            .overlay {
                GeometryReader { geometry in
                    RoundedRectangle(cornerRadius: size.cornerRadius * 0.84, style: .continuous)
                        .fill(
                            LinearGradient(
                                colors: [
                                    .white.opacity(0),
                                    .white.opacity(0.55),
                                    .white.opacity(0)
                                ],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                        .frame(width: geometry.size.width * 0.34)
                        .blur(radius: 5)
                        .rotationEffect(.degrees(16))
                        .offset(
                            x: (-geometry.size.width * 0.56) + (geometry.size.width * 1.12 * activationProgress),
                            y: -size.height * 0.04
                        )
                        .opacity(isEnabled ? activationProgress * 0.8 : 0)
                        .blendMode(.screen)
                }
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
                radius: isPressed ? 8 : (16 + (8 * activationProgress)),
                x: 0,
                y: isPressed ? 4 : (10 + (2 * activationProgress))
            )
            .shadow(
                color: variant.shadowColor.opacity(isEnabled ? 0.28 : 0.10),
                radius: isPressed ? 6 : (12 + (4 * activationProgress)),
                x: 0,
                y: isPressed ? 3 : (8 + activationProgress)
            )
    }
}

struct TRMenuButton_Previews: PreviewProvider {
    static var previews: some View {
        VStack(spacing: 14) {
            TRMenuButton(title: "Play", systemImage: nil, spriteName: "play_filled", variant: .play, size: .primary, action: {})
            TRMenuButton(title: "Daily Route", systemImage: nil, spriteName: "star_calendar", variant: .dailyRoute, size: .secondary, action: {})
            TRMenuButton(title: "Shop", systemImage: nil, spriteName: "shop_bag", variant: .shop, size: .secondary, action: {})
            TRMenuButton(title: "Settings", systemImage: nil, spriteName: "settings_gear", variant: .settings, size: .secondary, action: {})
            TRMenuButton(title: "Daily Route", systemImage: nil, spriteName: "star_calendar", variant: .dailyRoute, size: .secondary, action: {})
                .disabled(true)
        }
        .padding(32)
        .previewLayout(.sizeThatFits)
    }
}
