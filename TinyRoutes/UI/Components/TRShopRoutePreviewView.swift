import SwiftUI

struct TRShopRoutePreviewView: View {
    let accent: ShopCosmeticAccent
    var compact: Bool = false

    var body: some View {
        GeometryReader { geometry in
            let points = routePoints(in: geometry.size)
            ZStack {
                TRMapBackgroundView()

                accent.backgroundGradient
                    .opacity(compact ? 0.28 : 0.36)

                Path { path in
                    guard let firstPoint = points.first else { return }
                    path.move(to: firstPoint)
                    for point in points.dropFirst() {
                        path.addLine(to: point)
                    }
                }
                .stroke(
                    TRGameplayStyle.Colors.roadShadow,
                    style: StrokeStyle(lineWidth: compact ? 12 : 18, lineCap: .round, lineJoin: .round)
                )
                .offset(y: compact ? 2 : 4)
                .opacity(compact ? 0.16 : 0.20)

                Path { path in
                    guard let firstPoint = points.first else { return }
                    path.move(to: firstPoint)
                    for point in points.dropFirst() {
                        path.addLine(to: point)
                    }
                }
                .stroke(
                    accent.routeShadowColor,
                    style: StrokeStyle(lineWidth: compact ? 10 : 15, lineCap: .round, lineJoin: .round)
                )

                Path { path in
                    guard let firstPoint = points.first else { return }
                    path.move(to: firstPoint)
                    for point in points.dropFirst() {
                        path.addLine(to: point)
                    }
                }
                .stroke(
                    accent.routeColor,
                    style: StrokeStyle(lineWidth: compact ? 6 : 10, lineCap: .round, lineJoin: .round)
                )

                ForEach(Array(points.enumerated()), id: \.offset) { index, point in
                    marker(index: index, total: points.count)
                        .position(point)
                }
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: compact ? 15 : 24, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: compact ? 15 : 24, style: .continuous)
                .stroke(.white.opacity(0.62), lineWidth: 1)
        }
        .accessibilityHidden(true)
    }

    private func routePoints(in size: CGSize) -> [CGPoint] {
        [
            CGPoint(x: size.width * 0.18, y: size.height * 0.72),
            CGPoint(x: size.width * 0.18, y: size.height * 0.31),
            CGPoint(x: size.width * 0.50, y: size.height * 0.31),
            CGPoint(x: size.width * 0.50, y: size.height * 0.66),
            CGPoint(x: size.width * 0.82, y: size.height * 0.66),
            CGPoint(x: size.width * 0.82, y: size.height * 0.25)
        ]
    }

    @ViewBuilder
    private func marker(index: Int, total: Int) -> some View {
        if index == 0 {
            TRCircularMarkerShell(size: compact ? 25 : 42, rimWidth: compact ? 2 : 4, shadowOpacity: 0.12) {
                SpriteImage(name: "shipping_box")
                    .scaledToFit()
                    .frame(width: compact ? 16 : 26, height: compact ? 16 : 26)
            }
        } else if index == total - 1 {
            TRCircularMarkerShell(size: compact ? 25 : 42, rimWidth: compact ? 2 : 4, shadowOpacity: 0.12) {
                SpriteImage(name: "finish_flag_pin")
                    .scaledToFit()
                    .frame(width: compact ? 16 : 26, height: compact ? 16 : 26)
            }
        } else if index == 2 || index == 3 {
            SwitchNodeView(
                activeDirectionAngle: index == 2 ? 0 : .pi / 2,
                spriteSize: compact ? 25 : 38,
                ringSize: compact ? 22 : 34
            )
        } else {
            Circle()
                .fill(.white.opacity(0.96))
                .overlay {
                    Circle()
                        .stroke(accent.routeColor.opacity(0.75), lineWidth: compact ? 2 : 3)
                }
                .frame(width: compact ? 18 : 28, height: compact ? 18 : 28)
                .shadow(color: .black.opacity(0.10), radius: 4, x: 0, y: 2)
        }
    }
}

extension ShopCosmeticAccent {
    var routeColor: Color {
        switch self {
        case .classic:
            return TRGameplayStyle.Colors.roadFill
        case .oceanDrive:
            return Color(red: 0.06, green: 0.57, blue: 1.00)
        case .forestPath:
            return Color(red: 0.20, green: 0.67, blue: 0.39)
        case .sunsetBlvd:
            return Color(red: 1.00, green: 0.46, blue: 0.20)
        case .neonNights:
            return Color(red: 0.54, green: 0.31, blue: 1.00)
        case .candyLane:
            return Color(red: 1.00, green: 0.34, blue: 0.67)
        }
    }

    var routeShadowColor: Color {
        switch self {
        case .classic:
            return TRGameplayStyle.Colors.roadEdge
        case .oceanDrive:
            return Color(red: 0.05, green: 0.34, blue: 0.76)
        case .forestPath:
            return Color(red: 0.11, green: 0.41, blue: 0.26)
        case .sunsetBlvd:
            return Color(red: 0.74, green: 0.25, blue: 0.17)
        case .neonNights:
            return Color(red: 0.25, green: 0.12, blue: 0.58)
        case .candyLane:
            return Color(red: 0.66, green: 0.20, blue: 0.48)
        }
    }

    var backgroundGradient: LinearGradient {
        LinearGradient(
            colors: backgroundColors,
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    var backgroundColors: [Color] {
        switch self {
        case .classic:
            return [
                Color(red: 0.90, green: 0.94, blue: 0.98),
                Color(red: 0.78, green: 0.86, blue: 0.92)
            ]
        case .oceanDrive:
            return [
                Color(red: 0.70, green: 0.93, blue: 1.00),
                Color(red: 0.72, green: 0.83, blue: 1.00)
            ]
        case .forestPath:
            return [
                Color(red: 0.74, green: 0.94, blue: 0.76),
                Color(red: 0.66, green: 0.86, blue: 0.63)
            ]
        case .sunsetBlvd:
            return [
                Color(red: 1.00, green: 0.83, blue: 0.52),
                Color(red: 1.00, green: 0.62, blue: 0.46)
            ]
        case .neonNights:
            return [
                Color(red: 0.78, green: 0.66, blue: 1.00),
                Color(red: 0.35, green: 0.25, blue: 0.76)
            ]
        case .candyLane:
            return [
                Color(red: 1.00, green: 0.78, blue: 0.90),
                Color(red: 0.74, green: 0.90, blue: 1.00)
            ]
        }
    }
}

#Preview("Shop Route Preview") {
    VStack(spacing: 16) {
        TRShopRoutePreviewView(accent: .oceanDrive)
            .frame(height: 180)

        TRShopRoutePreviewView(accent: .candyLane, compact: true)
            .frame(width: 140, height: 86)
    }
    .padding(20)
    .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
