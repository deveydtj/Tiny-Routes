import SwiftUI

struct TRMapBackgroundView: View {
    var body: some View {
        ZStack {
            Color(red: 0.92, green: 0.96, blue: 1.0)

            Canvas { context, size in
                let blockColor = Color(red: 0.62, green: 0.74, blue: 0.90).opacity(0.12)
                let streetColor = Color.white.opacity(0.24)

                let blocks = [
                    CGRect(x: size.width * 0.04, y: size.height * 0.08, width: size.width * 0.34, height: size.height * 0.12),
                    CGRect(x: size.width * 0.56, y: size.height * 0.14, width: size.width * 0.36, height: size.height * 0.10),
                    CGRect(x: size.width * 0.18, y: size.height * 0.38, width: size.width * 0.30, height: size.height * 0.11),
                    CGRect(x: size.width * 0.58, y: size.height * 0.46, width: size.width * 0.32, height: size.height * 0.12),
                    CGRect(x: size.width * 0.08, y: size.height * 0.68, width: size.width * 0.40, height: size.height * 0.13),
                    CGRect(x: size.width * 0.52, y: size.height * 0.76, width: size.width * 0.38, height: size.height * 0.12)
                ]

                for block in blocks {
                    context.fill(
                        RoundedRectangle(cornerRadius: 16, style: .continuous).path(in: block),
                        with: .color(blockColor)
                    )
                }

                var verticalStreet = Path()
                verticalStreet.move(to: CGPoint(x: size.width * 0.28, y: 0))
                verticalStreet.addLine(to: CGPoint(x: size.width * 0.28, y: size.height))
                verticalStreet.move(to: CGPoint(x: size.width * 0.72, y: 0))
                verticalStreet.addLine(to: CGPoint(x: size.width * 0.72, y: size.height))

                var horizontalStreet = Path()
                horizontalStreet.move(to: CGPoint(x: 0, y: size.height * 0.30))
                horizontalStreet.addLine(to: CGPoint(x: size.width, y: size.height * 0.30))
                horizontalStreet.move(to: CGPoint(x: 0, y: size.height * 0.62))
                horizontalStreet.addLine(to: CGPoint(x: size.width, y: size.height * 0.62))

                context.stroke(
                    verticalStreet,
                    with: .color(streetColor),
                    style: StrokeStyle(lineWidth: 2, lineCap: .round, dash: [10, 14])
                )
                context.stroke(
                    horizontalStreet,
                    with: .color(streetColor),
                    style: StrokeStyle(lineWidth: 2, lineCap: .round, dash: [10, 14])
                )
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}
