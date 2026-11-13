import SwiftUI

/// A route theme tried out on a scrap of the village: its colours on the road
/// winding across the lawn, from the van to a house roofed to match.
struct TRShopRoutePreviewView: View {
    let accent: ShopCosmeticAccent
    var compact: Bool = false

    private typealias Art = TRVillageArt

    var body: some View {
        let shape = RoundedRectangle(cornerRadius: compact ? 15 : 22, style: .continuous)
        Canvas { context, size in draw(context, size: size) }
            .clipShape(shape)
            .overlay { shape.strokeBorder(.white.opacity(0.85), lineWidth: compact ? 1.5 : 2) }
            .accessibilityHidden(true)
    }

    private func draw(_ context: GraphicsContext, size: CGSize) {
        let w = size.width, h = size.height
        let rect = CGRect(origin: .zero, size: size)
        context.fill(Path(rect), with: .linearGradient(
            Gradient(colors: [Color(hex: 0x9CD174), Color(hex: 0x7DB457)]),
            startPoint: .zero, endPoint: CGPoint(x: 0, y: h)
        ))
        // The theme's colours wash lightly over the grass.
        var wash = context
        wash.opacity = 0.22
        wash.fill(Path(rect), with: .linearGradient(
            Gradient(colors: accent.backgroundColors),
            startPoint: .zero, endPoint: CGPoint(x: w, y: h)
        ))
        var lit = context
        lit.addFilter(.blur(radius: h * 0.12))
        lit.fill(Art.ellipse(w * 0.25, h * 0.15, w * 0.4, h * 0.3), with: .color(Color(hex: 0xFFF0D6, opacity: 0.35)))

        let scale = h / 150
        let start = CGPoint(x: w * 0.08, y: h * 0.82)
        let end = CGPoint(x: w * 0.80, y: h * 0.50)
        let control1 = CGPoint(x: w * 0.42, y: h * 1.02)
        let control2 = CGPoint(x: w * 0.46, y: h * 0.38)
        var road = Path()
        road.move(to: start)
        road.addCurve(to: end, control1: control1, control2: control2)

        Art.place(context, at: CGPoint(x: w * 0.30, y: h * 0.42), scale: scale * 0.9, anchor: Art.treeAnchor, opacity: 1) {
            Art.drawTree($0, color: TRVillagePalette.greens[2])
        }
        Art.place(context, at: CGPoint(x: w * 0.12, y: h * 0.40), scale: scale * 0.7, anchor: Art.treeAnchor, opacity: 1) {
            Art.drawPine($0, color: TRVillagePalette.greens[3])
        }

        let roadWidth = h * 0.14
        context.stroke(road, with: .color(Color(hex: 0xF3E8D3)), style: StrokeStyle(lineWidth: roadWidth + max(3, h * 0.035), lineCap: .round))
        context.stroke(road, with: .color(accent.routeShadowColor), style: StrokeStyle(lineWidth: roadWidth, lineCap: .round))
        context.stroke(road, with: .color(accent.routeColor), style: StrokeStyle(lineWidth: roadWidth * 0.72, lineCap: .round))
        context.stroke(road, with: .color(TRVillagePalette.cream.opacity(0.9)), style: StrokeStyle(lineWidth: max(1, h * 0.012), lineCap: .round, dash: [h * 0.04, h * 0.04]))

        Art.place(context, at: CGPoint(x: w * 0.88, y: h * 0.56), scale: scale * 1.05, anchor: Art.houseAnchor, opacity: 1) {
            Art.drawHouse($0, roof: accent.routeColor, smoke: false, parcel: true, flag: false, time: 1)
        }
        Art.place(context, at: CGPoint(x: w * 0.58, y: h * 0.94), scale: scale, anchor: Art.bushAnchor, opacity: 1) {
            Art.drawBush($0, color: TRVillagePalette.greens[0])
        }
        if !compact {
            Art.place(context, at: CGPoint(x: w * 0.68, y: h * 0.30), scale: scale, anchor: Art.flowersAnchor, opacity: 1) {
                Art.drawFlowers($0)
            }
        }

        // The van just setting off, tilted a little less than the road.
        let t = 0.14
        let van = bezier(t, start, control1, control2, end)
        let ahead = bezier(t + 0.01, start, control1, control2, end)
        let heading = Angle(radians: 0.6 * atan2(ahead.y - van.y, ahead.x - van.x))
        Art.place(context, at: van, scale: scale * 1.1, anchor: Art.vanPivot, rotation: heading, opacity: 1) {
            Art.drawVan($0, spin: 0, puffs: compact ? 0 : 0.7, idle: 0, time: 0)
        }
    }

    private func bezier(_ t: Double, _ p0: CGPoint, _ p1: CGPoint, _ p2: CGPoint, _ p3: CGPoint) -> CGPoint {
        let u = 1 - t
        let a = u * u * u, b = 3 * u * u * t, c = 3 * u * t * t, d = t * t * t
        return CGPoint(
            x: a * p0.x + b * p1.x + c * p2.x + d * p3.x,
            y: a * p0.y + b * p1.y + c * p2.y + d * p3.y
        )
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
    .background(TRVillageSky())
}
