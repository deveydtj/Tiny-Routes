import SwiftUI

/// The cozy menus' backdrop: a soft blue sky with paper clouds over rolling hills,
/// the same sky the 3D level map's island floats in.
struct TRCozySkyBackground: View {
    var body: some View {
        GeometryReader { geometry in
            let size = geometry.size
            ZStack(alignment: .topLeading) {
                LinearGradient(
                    colors: [
                        Color(red: 0.62, green: 0.82, blue: 0.95),
                        Color(red: 0.80, green: 0.91, blue: 0.97),
                        Color(red: 0.90, green: 0.96, blue: 0.95),
                    ],
                    startPoint: .top,
                    endPoint: .bottom
                )
                ForEach(Array(Self.clouds.enumerated()), id: \.offset) { _, cloud in
                    TRPaperCloud()
                        .frame(width: cloud.width, height: cloud.width * 0.42)
                        .opacity(cloud.opacity)
                        .position(x: size.width * cloud.x, y: size.height * cloud.y)
                }
                MultiVanHUDHills()
                    .frame(height: 150)
                    .offset(y: size.height - 150)
            }
        }
        .ignoresSafeArea()
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }

    /// Clear of the header's buttons, peeking out round the cards' sides.
    private static let clouds: [(x: CGFloat, y: CGFloat, width: CGFloat, opacity: Double)] = [
        (0.52, 0.035, 110, 0.85),
        (0.04, 0.30, 120, 0.8),
        (0.97, 0.44, 130, 0.75),
        (0.06, 0.60, 110, 0.7),
        (0.95, 0.74, 120, 0.65),
    ]
}

/// A puffy cloud: overlapping balls on a flat base, shaded underneath.
struct TRPaperCloud: View {
    var body: some View {
        GeometryReader { geometry in
            let w = geometry.size.width, h = geometry.size.height
            ZStack(alignment: .bottom) {
                Group {
                    Circle().frame(width: w * 0.34).offset(x: -w * 0.24, y: -h * 0.08)
                    Circle().frame(width: w * 0.48).offset(x: w * 0.02, y: -h * 0.22)
                    Circle().frame(width: w * 0.32).offset(x: w * 0.26, y: -h * 0.06)
                    Capsule().frame(width: w, height: h * 0.46)
                }
                .foregroundStyle(LinearGradient(colors: [.white, Color(red: 0.93, green: 0.95, blue: 0.98)], startPoint: .top, endPoint: .bottom))
            }
            .frame(width: w, height: h, alignment: .bottom)
            .shadow(color: Color(red: 0.35, green: 0.55, blue: 0.75).opacity(0.18), radius: 6, x: 0, y: 4)
        }
    }
}

#Preview("Cozy sky") {
    TRCozySkyBackground()
}
