import SwiftUI

/// A transverse cap: zero rotation closes a road travelling screen-up.
struct MultiVanBarrierView: View {
    var width: CGFloat = 30

    var body: some View {
        let height = width * 0.34
        RoundedRectangle(cornerRadius: height * 0.2)
            .fill(Color(red: 0.98, green: 0.83, blue: 0.52))
            .overlay {
                Path { path in
                    for index in -1...4 {
                        let x = CGFloat(index) * width * 0.32
                        path.move(to: CGPoint(x: x, y: height))
                        path.addLine(to: CGPoint(x: x + width * 0.16, y: height))
                        path.addLine(to: CGPoint(x: x + width * 0.16 + height, y: 0))
                        path.addLine(to: CGPoint(x: x + height, y: 0))
                        path.closeSubpath()
                    }
                }
                .fill(Color(white: 0.35))
            }
            .clipShape(RoundedRectangle(cornerRadius: height * 0.2))
            .overlay {
                RoundedRectangle(cornerRadius: height * 0.2)
                    .strokeBorder(.white, lineWidth: width * 0.045)
            }
            .frame(width: width, height: height)
            .shadow(color: .black.opacity(0.2), radius: width * 0.02, y: width * 0.03)
            .accessibilityLabel(Self.accessibilityLabel)
    }

    static let accessibilityLabel = "Dead end barrier"
}

#if DEBUG
#Preview("Barriers — gameplay and enlarged") {
    HStack(spacing: 32) {
        MultiVanBarrierView()
        MultiVanBarrierView().rotationEffect(.degrees(90))
        MultiVanBarrierView(width: 60)
    }
    .padding(32)
    .background(Color(white: 0.9))
}
#endif
