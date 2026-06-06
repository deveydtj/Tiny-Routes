import SwiftUI

struct TRCircularMarkerShell<Content: View>: View {
    let size: CGFloat
    let rimWidth: CGFloat
    let shadowOpacity: Double
    let content: Content

    init(
        size: CGFloat,
        rimWidth: CGFloat = TRGameplayStyle.Metrics.crispWhiteRimWidth,
        shadowOpacity: Double = 0.16,
        @ViewBuilder content: () -> Content
    ) {
        self.size = size
        self.rimWidth = rimWidth
        self.shadowOpacity = shadowOpacity
        self.content = content()
    }

    var body: some View {
        ZStack {
            Circle()
                .fill(Color.white.opacity(0.96))
                .frame(width: size, height: size)
                .overlay {
                    Circle()
                        .stroke(Color.white, lineWidth: rimWidth)
                }
                .overlay {
                    Circle()
                        .stroke(TRGameplayStyle.Colors.markerStroke, lineWidth: 1.5)
                        .padding(rimWidth / 2)
                }
                .shadow(color: Color.black.opacity(shadowOpacity), radius: 10, x: 0, y: 5)

            content
        }
        .frame(width: size, height: size)
    }
}

struct TRPackageMarkerView: View {
    let size: CGFloat
    let iconSize: CGFloat
    let cornerRadius: CGFloat

    init(
        size: CGFloat = TRGameplayStyle.Metrics.packageBadgeSize,
        iconSize: CGFloat = TRGameplayStyle.Metrics.packageBadgeIconSize,
        cornerRadius: CGFloat = TRGameplayStyle.Metrics.packageBadgeCornerRadius
    ) {
        self.size = size
        self.iconSize = iconSize
        self.cornerRadius = cornerRadius
    }

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                .fill(Color(red: 1.0, green: 0.98, blue: 0.91).opacity(0.97))
                .frame(width: size, height: size)
                .overlay {
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .stroke(Color.white.opacity(0.85), lineWidth: 1)
                        .padding(1)
                }
                .overlay {
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .stroke(TRGameplayStyle.Colors.resultGold.opacity(0.82), lineWidth: 1.5)
                }
                .shadow(color: TRGameplayStyle.Colors.resultGold.opacity(0.20), radius: 7, x: 0, y: 1)
                .shadow(color: Color.black.opacity(0.08), radius: 3, x: 0, y: 2)

            SpriteImage(name: "shipping_box")
                .scaledToFit()
                .frame(width: iconSize, height: iconSize)
                .accessibilityHidden(true)
        }
        .frame(width: size, height: size)
        .accessibilityLabel("Package")
    }
}

#Preview("Gameplay Marker Shells") {
    HStack(spacing: 18) {
        TRPackageMarkerView()

        TRCircularMarkerShell(size: TRGameplayStyle.Metrics.packageMarkerSize) {
            SpriteImage(name: "finish_flag_pin")
                .scaledToFit()
                .frame(width: TRGameplayStyle.Metrics.markerIconSize, height: TRGameplayStyle.Metrics.markerIconSize)
        }

        TRCircularMarkerShell(size: TRGameplayStyle.Metrics.switchCircleSize, rimWidth: 3) {
            Image(systemName: "arrow.right")
                .font(.system(size: 22, weight: .heavy, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
        }
    }
    .padding()
    .background(Color(red: 0.86, green: 0.93, blue: 0.98))
}
