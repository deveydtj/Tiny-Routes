import SwiftUI

struct TRDeliveryTrailView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    let option: ShopCosmeticOption
    let dotPoint: CGPoint
    let isMoving: Bool
    let roadPath: Path?

    @State private var animate = false

    init(
        option: ShopCosmeticOption,
        dotPoint: CGPoint,
        isMoving: Bool,
        roadPath: Path? = nil
    ) {
        self.option = option
        self.dotPoint = dotPoint
        self.isMoving = isMoving
        self.roadPath = roadPath
    }

    var body: some View {
        ZStack {
            if let roadPath, option.id == "trailNeon", isMoving {
                roadPath
                    .stroke(option.accent.routeColor.opacity(0.16), style: StrokeStyle(lineWidth: 22, lineCap: .round, lineJoin: .round))
                    .blur(radius: 10)
            }

            effect
                .position(dotPoint)
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
        .onAppear {
            animate = true
        }
    }

    @ViewBuilder
    private var effect: some View {
        switch option.id {
        case "trailBubbles":
            bubbleTrail
        case "trailFireflies":
            fireflyTrail
        case "trailNeon":
            neonTrail
        default:
            cleanTrail
        }
    }

    private var cleanTrail: some View {
        Circle()
            .fill(option.accent.routeColor.opacity(isMoving ? 0.10 : 0.05))
            .frame(width: 46, height: 46)
            .blur(radius: 10)
    }

    private var bubbleTrail: some View {
        ZStack {
            ForEach(0..<5, id: \.self) { index in
                Circle()
                    .fill(Color.white.opacity(0.58))
                    .overlay {
                        Circle()
                            .stroke(option.accent.routeColor.opacity(0.58), lineWidth: 1.2)
                    }
                    .frame(width: CGFloat(7 + (index % 3) * 3), height: CGFloat(7 + (index % 3) * 3))
                    .offset(
                        x: CGFloat(-16 - (index * 6)),
                        y: CGFloat((index % 2 == 0 ? -1 : 1) * (5 + index))
                    )
                    .opacity(isMoving ? 0.80 : 0.34)
                    .scaleEffect(animatedScale(base: 1.0, delta: 0.16, index: index))
            }
        }
    }

    private var fireflyTrail: some View {
        ZStack {
            ForEach(0..<6, id: \.self) { index in
                Image(systemName: index.isMultiple(of: 2) ? "sparkle" : "circle.fill")
                    .font(.system(size: index.isMultiple(of: 2) ? 10 : 5, weight: .black))
                    .foregroundStyle(index.isMultiple(of: 2) ? Color.white : option.accent.routeColor)
                    .shadow(color: option.accent.routeColor.opacity(0.55), radius: 5, x: 0, y: 0)
                    .offset(
                        x: CGFloat(-14 - (index * 5)),
                        y: CGFloat((index % 3 - 1) * 9)
                    )
                    .opacity(isMoving ? 0.90 : 0.36)
                    .scaleEffect(animatedScale(base: 0.92, delta: 0.20, index: index))
            }
        }
    }

    private var neonTrail: some View {
        ZStack {
            Capsule()
                .fill(option.accent.routeColor.opacity(isMoving ? 0.34 : 0.12))
                .frame(width: 62, height: 20)
                .blur(radius: 8)
                .offset(x: -22)

            Circle()
                .stroke(option.accent.routeColor.opacity(isMoving ? 0.46 : 0.16), lineWidth: 2)
                .frame(width: animate && isMoving && !reduceMotion ? 60 : 44, height: animate && isMoving && !reduceMotion ? 60 : 44)
                .opacity(animate && isMoving && !reduceMotion ? 0.12 : 0.30)
                .animation(.easeInOut(duration: 0.7).repeatForever(autoreverses: true), value: animate)
        }
    }

    private func animatedScale(base: CGFloat, delta: CGFloat, index: Int) -> CGFloat {
        guard isMoving, !reduceMotion else {
            return base
        }

        return animate == index.isMultiple(of: 2) ? base + delta : base
    }
}

#Preview("Delivery Trails") {
    let options = ShopCatalogService().options(forCategoryID: ShopCosmeticCategoryID.trails)

    return ZStack {
        Color(red: 0.86, green: 0.93, blue: 0.98)

        VStack(spacing: 22) {
            ForEach(options) { option in
                ZStack {
                    RoundedRectangle(cornerRadius: 8)
                        .fill(.white.opacity(0.72))
                    TRDeliveryTrailView(
                        option: option,
                        dotPoint: CGPoint(x: 120, y: 36),
                        isMoving: true
                    )
                    TRDeliveryDotView(
                        option: ShopCatalogService().option(withID: "dotCourierBlue") ?? option,
                        isMoving: false,
                        outerSize: 52,
                        coreSize: 40,
                        scale: 0.55
                    )
                    .position(x: 120, y: 36)
                }
                .frame(width: 220, height: 72)
            }
        }
    }
}
