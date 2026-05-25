import SwiftUI

struct TRDeliveryDotView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    let option: ShopCosmeticOption
    let isMoving: Bool
    let outerSize: CGFloat
    let coreSize: CGFloat
    let scale: CGFloat

    @State private var isPulseExpanded = false

    var body: some View {
        let visual = TRDeliveryDotVisual(option: option)

        ZStack {
            Circle()
                .fill(visual.glowColor.opacity(0.24))
                .frame(width: outerSize + 18, height: outerSize + 18)
                .blur(radius: 8)

            Circle()
                .fill(Color.white)
                .frame(width: outerSize, height: outerSize)
                .shadow(color: Color.black.opacity(0.14), radius: 8, x: 0, y: 4)

            Circle()
                .fill(visual.gradient)
                .frame(width: coreSize, height: coreSize)
                .overlay {
                    Circle()
                        .stroke(Color.white.opacity(0.28), lineWidth: 0.5)
                }

            Circle()
                .fill(Color.white.opacity(0.40))
                .frame(width: 9, height: 9)
                .offset(x: -7, y: -8)

            if isMoving, !reduceMotion {
                Circle()
                    .stroke(visual.pulseColor.opacity(0.42), lineWidth: 0)
                    .frame(
                        width: isPulseExpanded ? outerSize + 20 : outerSize + 8,
                        height: isPulseExpanded ? outerSize + 20 : outerSize + 8
                    )
                    .opacity(isPulseExpanded ? 0.08 : 0.32)
                    .animation(.easeInOut(duration: 0.85).repeatForever(autoreverses: true), value: isPulseExpanded)
            }
        }
        .frame(width: outerSize + 24, height: outerSize + 24)
        .scaleEffect(scale)
        .accessibilityHidden(true)
        .onAppear {
            isPulseExpanded = true
        }
        .onChange(of: isMoving) { _, moving in
            if moving {
                isPulseExpanded = true
            }
        }
    }
}

struct TRDeliveryDotVisual {
    let option: ShopCosmeticOption

    var gradient: LinearGradient {
        Self.gradient(for: option)
    }

    var glowColor: Color {
        Self.colors(for: option).last ?? TRGameplayStyle.Colors.primaryBlue
    }

    var pulseColor: Color {
        glowColor
    }

    static func gradient(for option: ShopCosmeticOption) -> LinearGradient {
        LinearGradient(
            colors: colors(for: option),
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    static func colors(for option: ShopCosmeticOption) -> [Color] {
        switch option.id {
        case "dotCourierBlue":
            return [
                Color(red: 0.36, green: 0.78, blue: 1.0),
                TRGameplayStyle.Colors.primaryBlue
            ]
        case "dotGarden":
            return [
                Color(red: 0.58, green: 0.90, blue: 0.45),
                Color(red: 0.16, green: 0.58, blue: 0.32)
            ]
        case "dotGolden":
            return [
                Color(red: 1.00, green: 0.88, blue: 0.32),
                Color(red: 1.00, green: 0.48, blue: 0.12)
            ]
        case "dotCandy":
            return [
                Color(red: 1.00, green: 0.62, blue: 0.83),
                Color(red: 0.93, green: 0.24, blue: 0.62)
            ]
        default:
            return [
                option.accent.routeColor.opacity(0.72),
                option.accent.routeColor
            ]
        }
    }
}

#Preview("Delivery Dots") {
    let options = ShopCatalogService().options(forCategoryID: ShopCosmeticCategoryID.deliveryDots)

    return HStack(spacing: 16) {
        ForEach(options) { option in
            TRDeliveryDotView(
                option: option,
                isMoving: true,
                outerSize: TRGameplayStyle.Metrics.playerOuterSize,
                coreSize: TRGameplayStyle.Metrics.playerCoreSize,
                scale: 1
            )
        }
    }
    .padding()
    .background(Color(red: 0.86, green: 0.93, blue: 0.98))
}
