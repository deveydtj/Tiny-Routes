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

#Preview("Gameplay Marker Shells") {
    HStack(spacing: 18) {
        TRCircularMarkerShell(size: TRGameplayStyle.Metrics.packageMarkerSize) {
            SpriteImage(name: "shipping_box")
                .scaledToFit()
                .frame(width: TRGameplayStyle.Metrics.markerIconSize, height: TRGameplayStyle.Metrics.markerIconSize)
        }

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
