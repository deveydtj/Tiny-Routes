import SwiftUI

/// The home / main menu screen: the village's teal banner over a little floating
/// island, its van driving the road, and chunky HUD buttons beneath.
struct HomeScreen: View {
    let onPlayTapped: () -> Void
    let onDailyRouteTapped: (() -> Void)? = nil

    var body: some View {
        VStack(spacing: 0) {
            banner

            Spacer(minLength: 8)

            TRHomeIsland()
                .frame(maxWidth: 380)
                .padding(.horizontal, 8)

            Text("One-tap delivery puzzles")
                .font(.system(size: 18, weight: .semibold, design: .rounded))
                .foregroundStyle(TRVillagePalette.teal)
                .padding(.top, 4)

            Spacer(minLength: 16)

            VStack(spacing: 12) {
                Button(action: onPlayTapped) {
                    HStack(spacing: 10) {
                        Image(systemName: "play.fill")
                            .font(.system(size: 22, weight: .bold))
                        Text("Play")
                            .font(.system(size: 25, weight: .bold, design: .rounded))
                    }
                    .frame(maxWidth: .infinity, minHeight: 64)
                }
                .buttonStyle(MultiVanHUDButtonStyle(isProminent: true, tint: TRVillagePalette.blue, shape: AnyShape(Capsule())))
                .accessibilityLabel("Play")
                .accessibilityHint("Opens the level map")

                Button(action: onDailyRouteTapped ?? {}) {
                    HStack(spacing: 10) {
                        Image(systemName: "calendar")
                            .font(.system(size: 18, weight: .semibold))
                        Text("Daily Route")
                            .font(.system(size: 19, weight: .semibold, design: .rounded))
                        if onDailyRouteTapped == nil {
                            Text("Soon".uppercased())
                                .font(.system(size: 10, weight: .bold, design: .rounded))
                                .tracking(0.8)
                                .foregroundStyle(TRVillagePalette.cream)
                                .padding(.horizontal, 7)
                                .frame(height: 18)
                                .background { Capsule().fill(TRVillagePalette.teal) }
                        }
                    }
                    .frame(maxWidth: .infinity, minHeight: 52)
                }
                .buttonStyle(MultiVanHUDButtonStyle(shape: AnyShape(Capsule())))
                .disabled(onDailyRouteTapped == nil)
                .accessibilityLabel("Daily Route")
                .accessibilityHint(onDailyRouteTapped == nil ? Text("Coming soon") : Text(""))

            }
            .frame(maxWidth: 340)
            .padding(.horizontal, 24)

            Spacer(minLength: 20)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    /// The level map's banner, carrying the wordmark.
    private var banner: some View {
        MultiVanHUDLogo()
            .scaleEffect(1.3)
            .padding(.top, 14)
            .padding(.bottom, 30)
            .frame(maxWidth: .infinity)
            .background(alignment: .bottom) {
                MultiVanHUDBanner().ignoresSafeArea(edges: .top)
            }
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("Tiny Routes")
            .accessibilityAddTraits(.isHeader)
    }
}

/// A scrap of the village on a floating board: cottages, trees and the van
/// driving its road, with the sun and clouds behind.
///
/// Only what moves redraws: the sky, the smoke and the van each frame, at most 30
/// times a second. The rest is drawn once, in a layer behind the van and one in
/// front of it. It all holds still under Reduce Motion, in Low Power Mode and
/// while the app is away.
private struct TRHomeIsland: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase
    @State private var power = MultiVanPowerMonitor()

    /// The island's own units; the canvases scale them to fit.
    private static let size = CGSize(width: 320, height: 240)
    /// The moment shown while held still, with the van parked mid-road.
    private static let stillTime = 3.8

    private var isAnimating: Bool { !reduceMotion && !power.isLowPowerModeEnabled && scenePhase == .active }

    var body: some View {
        ZStack {
            moving(Self.drawSky)
            still { Self.drawScene($0, inFront: false) }
            moving(Self.drawTraffic)
            still { Self.drawScene($0, inFront: true) }
        }
        .aspectRatio(Self.size.width / Self.size.height, contentMode: .fit)
        .task { await power.monitor() }
        .accessibilityHidden(true)
    }

    /// A layer drawn once, and again only if the view resizes.
    private func still(_ draw: @escaping (GraphicsContext) -> Void) -> some View {
        Canvas { context, size in draw(Self.fitted(context, to: size)) }
    }

    /// A layer redrawn on the clock while the island is animating.
    private func moving(_ draw: @escaping (GraphicsContext, Double) -> Void) -> some View {
        let isAnimating = isAnimating
        return TimelineView(.animation(minimumInterval: 1.0 / 30, paused: !isAnimating)) { timeline in
            let time = isAnimating ? timeline.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 3600) : Self.stillTime
            Canvas { context, size in draw(Self.fitted(context, to: size), time) }
        }
    }

    /// The context scaled from the island's units into the middle of `size`.
    private static func fitted(_ context: GraphicsContext, to size: CGSize) -> GraphicsContext {
        var context = context
        let scale = min(size.width / Self.size.width, size.height / Self.size.height)
        context.translateBy(x: (size.width - Self.size.width * scale) / 2, y: (size.height - Self.size.height * scale) / 2)
        context.scaleBy(x: scale, y: scale)
        return context
    }

    private typealias Art = TRVillageArt

    private static let center = CGPoint(x: 160, y: 128)
    private static let radii = CGSize(width: 140, height: 58)

    private static func face(dropped dy: Double = 0) -> Path {
        Art.ellipse(center.x, center.y + dy, radii.width, radii.height)
    }

    /// The road's curve across the island, left to right.
    private static let road: [CGPoint] = [CGPoint(x: 6, y: 158), CGPoint(x: 110, y: 192), CGPoint(x: 190, y: 74), CGPoint(x: 318, y: 116)]

    private static func roadPoint(_ t: Double) -> CGPoint {
        let u = 1 - t
        let a = u * u * u, b = 3 * u * u * t, c = 3 * u * t * t, d = t * t * t
        return CGPoint(
            x: a * road[0].x + b * road[1].x + c * road[2].x + d * road[3].x,
            y: a * road[0].y + b * road[1].y + c * road[2].y + d * road[3].y
        )
    }

    /// Whether a piece standing at `point` is nearer than the road, and so in
    /// front of the van as it passes.
    private static func isInFront(_ point: CGPoint) -> Bool {
        let nearest = stride(from: 0.0, through: 1, by: 0.01).map(roadPoint).min { abs($0.x - point.x) < abs($1.x - point.x) }
        return point.y > (nearest?.y ?? 0)
    }

    private enum Piece {
        case house(roof: Color, smoke: Bool, parcel: Bool)
        case tree(Color)
        case pine(Color)
        case bush(Color)
        case flowers
    }

    private static let scenery: [(point: CGPoint, scale: Double, piece: Piece)] = [
        (CGPoint(x: 120, y: 100), 0.78, .house(roof: TRVillagePalette.roofs[1], smoke: true, parcel: false)),
        (CGPoint(x: 66, y: 120), 0.86, .house(roof: TRVillagePalette.roofs[0], smoke: true, parcel: false)),
        (CGPoint(x: 206, y: 166), 0.92, .house(roof: TRVillagePalette.roofs[2], smoke: false, parcel: true)),
        (CGPoint(x: 236, y: 92), 0.72, .tree(TRVillagePalette.greens[0])),
        (CGPoint(x: 270, y: 98), 0.62, .pine(TRVillagePalette.greens[2])),
        (CGPoint(x: 38, y: 134), 0.7, .pine(TRVillagePalette.greens[3])),
        (CGPoint(x: 168, y: 96), 0.6, .tree(TRVillagePalette.greens[1])),
        (CGPoint(x: 282, y: 142), 0.8, .bush(TRVillagePalette.greens[0])),
        (CGPoint(x: 128, y: 176), 0.7, .tree(TRVillagePalette.greens[2])),
        (CGPoint(x: 96, y: 178), 1, .flowers),
        (CGPoint(x: 246, y: 150), 1, .flowers),
    ].sorted { $0.point.y < $1.point.y }

    /// The sun and clouds behind the island.
    private static func drawSky(_ context: GraphicsContext, time: Double) {
        // A gradient rather than a blur, which the canvas's edge would square off.
        let glow = 46 * (1 + 0.05 * sin(time * 0.9))
        context.fill(Art.circle(58, 40, glow), with: .radialGradient(
            Gradient(colors: [Color(hex: 0xFFF0D6, opacity: 0.7), Color(hex: 0xFFF0D6, opacity: 0)]),
            center: CGPoint(x: 58, y: 40), startRadius: 14, endRadius: glow
        ))
        context.fill(Art.circle(58, 40, 18), with: .color(Color(hex: 0xFFF6DE)))
        Art.drawCloud(context, at: CGPoint(x: 196 + 6 * sin(time * 0.16), y: 8), width: 96, opacity: 0.9)
        Art.drawCloud(context, at: CGPoint(x: 106 + 4 * sin(time * 0.21 + 2), y: 30), width: 56, opacity: 0.8)
    }

    /// The board, its road and the pieces behind it, or just the pieces in front:
    /// everything that holds still.
    private static func drawScene(_ context: GraphicsContext, inFront: Bool) {
        if !inFront {
            var blurred = context
            blurred.addFilter(.blur(radius: 8))
            blurred.fill(Art.ellipse(center.x, 212, 128, 12), with: .color(TRVillagePalette.ink.opacity(0.22)))
            context.fill(face(dropped: 34), with: .color(Color(hex: 0x7B5339)))
            context.fill(face(dropped: 24), with: .color(Color(hex: 0xA26E48)))
            context.fill(face(dropped: 9), with: .color(Color(hex: 0x7DB457)))
            context.fill(face(), with: .color(Color(hex: 0x8FC766)))

            var lawn = context
            lawn.clip(to: face())
            var lit = lawn
            lit.addFilter(.blur(radius: 10))
            lit.fill(Art.ellipse(80, 96, 110, 50), with: .color(Color(hex: 0xFFF0D6, opacity: 0.3)))
            lit.fill(Art.ellipse(280, 170, 100, 50), with: .color(TRVillagePalette.ink.opacity(0.08)))

            var path = Path()
            path.move(to: road[0])
            path.addCurve(to: road[3], control1: road[1], control2: road[2])
            lawn.stroke(path, with: .color(Color(hex: 0xF3E8D3)), style: StrokeStyle(lineWidth: 19, lineCap: .round))
            lawn.stroke(path, with: .color(Color(hex: 0x4E5563)), style: StrokeStyle(lineWidth: 14, lineCap: .round))
            lawn.stroke(path, with: .color(TRVillagePalette.cream.opacity(0.9)), style: StrokeStyle(lineWidth: 1.6, lineCap: .round, dash: [6, 6]))
        }

        for item in scenery where isInFront(item.point) == inFront {
            switch item.piece {
            case let .house(roof, _, parcel):
                // The smoke rises in the moving layer; at this time the parcel sits still.
                Art.place(context, at: item.point, scale: item.scale, anchor: Art.houseAnchor, opacity: 1) {
                    Art.drawHouse($0, roof: roof, smoke: false, parcel: parcel, flag: false, time: 1)
                }
            case let .tree(color):
                Art.place(context, at: item.point, scale: item.scale, anchor: Art.treeAnchor, opacity: 1) { Art.drawTree($0, color: color) }
            case let .pine(color):
                Art.place(context, at: item.point, scale: item.scale, anchor: Art.treeAnchor, opacity: 1) { Art.drawPine($0, color: color) }
            case let .bush(color):
                Art.place(context, at: item.point, scale: item.scale, anchor: Art.bushAnchor, opacity: 1) { Art.drawBush($0, color: color) }
            case .flowers:
                Art.place(context, at: item.point, scale: item.scale, anchor: Art.flowersAnchor, opacity: 1) { Art.drawFlowers($0) }
            }
        }
    }

    /// The chimney smoke, and the van looping along the road, fading in and out
    /// at the island's ends.
    private static func drawTraffic(_ context: GraphicsContext, time: Double) {
        for item in scenery {
            guard case .house(_, true, _) = item.piece else { continue }
            Art.place(context, at: item.point, scale: item.scale, anchor: Art.houseAnchor, opacity: 1) {
                Art.drawSmoke($0, wind: Art.breeze(at: time, x: item.point.x) * 0.4, time: time + item.point.x)
            }
        }

        let loop = Art.phase(time, every: 8)
        let t = 0.08 + 0.84 * loop
        let van = roadPoint(t)
        let ahead = roadPoint(min(t + 0.01, 1))
        // Tilted a little less than the road, so it reads as driving on a slope.
        let heading = Angle(radians: 0.6 * atan2(ahead.y - van.y, ahead.x - van.x))
        let fade = min(1, min(loop, 1 - loop) / 0.08)
        Art.place(context, at: van, scale: 0.9, anchor: Art.vanPivot, rotation: heading, opacity: fade) {
            Art.drawVan($0, spin: time * 360, puffs: 0.8, idle: 0, time: time)
        }
    }
}

struct HomeScreen_Previews: PreviewProvider {
    static var previews: some View {
        ZStack {
            TRVillageSky()
            HomeScreen(onPlayTapped: {})
        }
    }
}
