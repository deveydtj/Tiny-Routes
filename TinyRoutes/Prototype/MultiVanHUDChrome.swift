import SwiftUI

/// The gameplay HUD's look: a pine-green title banner up top, cream cards and a
/// cream control tray sitting on rolling hills at the bottom.
enum MultiVanHUDStyle {
    static let bannerTop = Color(red: 0.13, green: 0.36, blue: 0.38)
    static let bannerBottom = Color(red: 0.09, green: 0.29, blue: 0.31)
    static let cream = Color(red: 0.995, green: 0.975, blue: 0.935)
    static let creamDeep = Color(red: 0.965, green: 0.935, blue: 0.865)
    /// The darker cream under a card or button, read as its thickness.
    static let creamLip = Color(red: 0.84, green: 0.79, blue: 0.68)
    static let pineLight = Color(red: 0.55, green: 0.80, blue: 0.42)
    static let pine = Color(red: 0.19, green: 0.50, blue: 0.31)
    static let pineDark = Color(red: 0.13, green: 0.40, blue: 0.26)
    static let hillBack = Color(red: 0.42, green: 0.70, blue: 0.38)
    static let hillFront = Color(red: 0.30, green: 0.60, blue: 0.33)
    static let shadow = Color(red: 0.10, green: 0.20, blue: 0.16)
}

/// The banner behind the top of the HUD, its bottom edge curving gently down.
struct MultiVanHUDBanner: View {
    var body: some View {
        BannerShape()
            .fill(LinearGradient(colors: [MultiVanHUDStyle.bannerTop, MultiVanHUDStyle.bannerBottom], startPoint: .top, endPoint: .bottom))
            .overlay { BannerEdge().stroke(.white.opacity(0.22), lineWidth: 2) }
            .shadow(color: MultiVanHUDStyle.shadow.opacity(0.28), radius: 10, x: 0, y: 6)
            .accessibilityHidden(true)
    }

    private static let sag: CGFloat = 14

    private struct BannerShape: Shape {
        func path(in rect: CGRect) -> Path {
            var path = Path()
            path.move(to: CGPoint(x: rect.minX, y: rect.minY))
            path.addLine(to: CGPoint(x: rect.maxX, y: rect.minY))
            path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY - MultiVanHUDBanner.sag))
            path.addQuadCurve(
                to: CGPoint(x: rect.minX, y: rect.maxY - MultiVanHUDBanner.sag),
                control: CGPoint(x: rect.midX, y: rect.maxY + MultiVanHUDBanner.sag)
            )
            path.closeSubpath()
            return path
        }
    }

    /// The highlight along the bottom edge.
    private struct BannerEdge: Shape {
        func path(in rect: CGRect) -> Path {
            var path = Path()
            path.move(to: CGPoint(x: rect.maxX, y: rect.maxY - MultiVanHUDBanner.sag - 1))
            path.addQuadCurve(
                to: CGPoint(x: rect.minX, y: rect.maxY - MultiVanHUDBanner.sag - 1),
                control: CGPoint(x: rect.midX, y: rect.maxY + MultiVanHUDBanner.sag - 1)
            )
            return path
        }
    }
}

/// The wordmark in the banner: cream lettering over a dashed road, between pines.
struct MultiVanHUDLogo: View {
    var body: some View {
        HStack(alignment: .bottom, spacing: 8) {
            pinePair
            VStack(spacing: 2) {
                Text("Tiny Routes")
                    .font(.system(size: 26, weight: .black, design: .rounded))
                    .foregroundStyle(MultiVanHUDStyle.cream)
                    .shadow(color: MultiVanHUDStyle.shadow.opacity(0.55), radius: 0, x: 0, y: 2)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
                RoadLine()
                    .stroke(MultiVanHUDStyle.cream.opacity(0.85), style: StrokeStyle(lineWidth: 2.5, lineCap: .round, dash: [9, 6]))
                    .frame(width: 112, height: 6)
            }
            pinePair.scaleEffect(x: -1)
        }
        .accessibilityHidden(true)
    }

    private var pinePair: some View {
        ZStack(alignment: .bottomLeading) {
            MultiVanPineShape().fill(MultiVanHUDStyle.pineLight).frame(width: 18, height: 26).offset(x: 9)
            MultiVanPineShape().fill(MultiVanHUDStyle.pineLight.opacity(0.75)).frame(width: 12, height: 18)
        }
        .frame(width: 28, height: 28, alignment: .bottomLeading)
        .padding(.bottom, 6)
    }

    /// A road that dips and rises once, like the one on the title screen.
    private struct RoadLine: Shape {
        func path(in rect: CGRect) -> Path {
            var path = Path()
            path.move(to: CGPoint(x: rect.minX, y: rect.maxY))
            path.addCurve(
                to: CGPoint(x: rect.maxX, y: rect.minY),
                control1: CGPoint(x: rect.width * 0.4, y: rect.minY - 4),
                control2: CGPoint(x: rect.width * 0.6, y: rect.maxY + 4)
            )
            return path
        }
    }
}

/// Three stacked tiers on a trunk.
struct MultiVanPineShape: Shape {
    func path(in rect: CGRect) -> Path {
        let w = rect.width, h = rect.height
        var path = Path()
        path.addRect(CGRect(x: rect.minX + w * 0.43, y: rect.minY + h * 0.84, width: w * 0.14, height: h * 0.16))
        for (apex, base, halfWidth) in [(0.0, 0.42, 0.30), (0.18, 0.66, 0.40), (0.38, 0.88, 0.50)] {
            path.move(to: CGPoint(x: rect.midX, y: rect.minY + h * apex))
            path.addLine(to: CGPoint(x: rect.midX + w * halfWidth, y: rect.minY + h * base))
            path.addLine(to: CGPoint(x: rect.midX - w * halfWidth, y: rect.minY + h * base))
            path.closeSubpath()
        }
        return path
    }
}

/// Hills with pines behind the control tray, highest at the screen's sides.
struct MultiVanHUDHills: View {
    /// How far the hills climb above the tray's top edge.
    static let rise: CGFloat = 40

    var body: some View {
        GeometryReader { geometry in
            let size = geometry.size
            ZStack(alignment: .topLeading) {
                HillShape(leftPeak: 0.10, rightPeak: 0.86, valley: 0.62)
                    .fill(MultiVanHUDStyle.hillBack)
                HillShape(leftPeak: 0.0, rightPeak: 1.0, valley: 0.78)
                    .fill(MultiVanHUDStyle.hillFront)
                    .offset(y: 14)
                ForEach(Self.pines, id: \.x) { pine in
                    MultiVanPineShape()
                        .fill(pine.isBack ? MultiVanHUDStyle.pine : MultiVanHUDStyle.pineDark)
                        .frame(width: pine.height * 0.72, height: pine.height)
                        .position(x: size.width * pine.x, y: pine.baseY - pine.height / 2)
                }
            }
        }
        .accessibilityHidden(true)
    }

    private struct Pine {
        let x: Double
        let height: CGFloat
        /// Where the trunk meets the hill, from the top of the hills.
        let baseY: CGFloat
        let isBack: Bool
    }

    private static let pines = [
        Pine(x: 0.035, height: 58, baseY: 26, isBack: false),
        Pine(x: 0.105, height: 40, baseY: 22, isBack: true),
        Pine(x: 0.165, height: 30, baseY: 28, isBack: true),
        Pine(x: 0.84, height: 32, baseY: 26, isBack: true),
        Pine(x: 0.905, height: 46, baseY: 22, isBack: true),
        Pine(x: 0.965, height: 60, baseY: 26, isBack: false),
    ]

    /// A ridge with a peak near each side and a dip between, flat below.
    private struct HillShape: Shape {
        let leftPeak: Double
        let rightPeak: Double
        /// How far down the dip sits, as a share of the rise.
        let valley: Double

        func path(in rect: CGRect) -> Path {
            let top = rect.minY + 6
            let dip = rect.minY + MultiVanHUDHills.rise * valley
            var path = Path()
            path.move(to: CGPoint(x: rect.minX, y: rect.maxY))
            path.addLine(to: CGPoint(x: rect.minX, y: top + 10))
            path.addQuadCurve(to: CGPoint(x: rect.minX + rect.width * leftPeak + 30, y: top),
                              control: CGPoint(x: rect.minX + rect.width * leftPeak, y: top - 2))
            path.addCurve(to: CGPoint(x: rect.minX + rect.width * rightPeak - 30, y: top),
                          control1: CGPoint(x: rect.minX + rect.width * 0.4, y: dip + 8),
                          control2: CGPoint(x: rect.minX + rect.width * 0.6, y: dip + 8))
            path.addQuadCurve(to: CGPoint(x: rect.maxX, y: top + 10),
                              control: CGPoint(x: rect.minX + rect.width * rightPeak, y: top - 2))
            path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY))
            path.closeSubpath()
            return path
        }
    }
}

/// A cream card with a darker lip along its bottom edge.
struct MultiVanHUDCardBackground: View {
    var cornerRadius: CGFloat = 26

    var body: some View {
        let shape = RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
        shape
            .fill(LinearGradient(colors: [MultiVanHUDStyle.cream, MultiVanHUDStyle.creamDeep], startPoint: .top, endPoint: .bottom))
            .overlay { shape.strokeBorder(.white.opacity(0.9), lineWidth: 1.5) }
            .background { shape.fill(MultiVanHUDStyle.creamLip).offset(y: 3) }
            .shadow(color: MultiVanHUDStyle.shadow.opacity(0.22), radius: 14, x: 0, y: 8)
    }
}

/// A chunky button that sits on its own darker base and presses down into it:
/// a tinted face for going on, cream for everything else.
struct MultiVanHUDButtonStyle: ButtonStyle {
    var isProminent = false
    var tint = TRGameplayStyle.Colors.primaryBlue
    var shape = AnyShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
    @Environment(\.isEnabled) private var isEnabled

    static let lipDepth: CGFloat = 4

    func makeBody(configuration: Configuration) -> some View {
        let isPressed = configuration.isPressed
        return configuration.label
            .foregroundStyle(isProminent ? Color.white : TRGameplayStyle.Colors.titleNavy)
            .background { face }
            .offset(y: isPressed ? Self.lipDepth - 1 : 0)
            .background {
                lip
                    .offset(y: Self.lipDepth)
                    .shadow(
                        color: (isProminent ? tint : MultiVanHUDStyle.shadow).opacity(isProminent ? 0.35 : 0.18),
                        radius: isPressed ? 3 : 7, x: 0, y: isPressed ? 2 : 5
                    )
            }
            .padding(.bottom, Self.lipDepth)
            .contentShape(shape)
            .opacity(isEnabled ? 1 : 0.55)
            .animation(.spring(response: 0.18, dampingFraction: 0.7), value: isPressed)
    }

    private var face: some View {
        shape
            .fill(isProminent
                ? AnyShapeStyle(tint)
                : AnyShapeStyle(LinearGradient(colors: [.white, MultiVanHUDStyle.cream], startPoint: .top, endPoint: .bottom)))
            .overlay {
                if isProminent {
                    shape.fill(LinearGradient(colors: [.white.opacity(0.30), .clear, .black.opacity(0.08)], startPoint: .top, endPoint: .bottom))
                }
            }
            .overlay { shape.stroke(.white.opacity(isProminent ? 0.45 : 0.95), lineWidth: 1.5) }
    }

    private var lip: some View {
        shape
            .fill(isProminent ? AnyShapeStyle(tint) : AnyShapeStyle(MultiVanHUDStyle.creamLip))
            .overlay { if isProminent { shape.fill(.black.opacity(0.28)) } }
    }
}

extension ButtonStyle where Self == MultiVanHUDButtonStyle {
    /// The round cream buttons in the banner.
    static var multiVanHUDCircle: MultiVanHUDButtonStyle { MultiVanHUDButtonStyle(shape: AnyShape(Circle())) }
}

#Preview("HUD chrome") {
    VStack(spacing: 0) {
        ZStack {
            MultiVanHUDBanner()
            MultiVanHUDLogo()
        }
        .frame(height: 120)
        Spacer()
        ZStack(alignment: .top) {
            MultiVanHUDHills()
            HStack(spacing: 12) {
                Button {} label: { Image(systemName: "chevron.left").frame(width: 46, height: 46) }
                    .buttonStyle(.multiVanHUDCircle)
                Button {} label: { Text("Go").frame(maxWidth: .infinity, minHeight: 60) }
                    .buttonStyle(MultiVanHUDButtonStyle(isProminent: true))
            }
            .padding(12)
            .background { MultiVanHUDCardBackground(cornerRadius: 30) }
            .padding(.horizontal, 16)
            .padding(.top, MultiVanHUDHills.rise)
        }
        .frame(height: 180)
    }
    .background(Color(red: 0.62, green: 0.80, blue: 0.93))
}
