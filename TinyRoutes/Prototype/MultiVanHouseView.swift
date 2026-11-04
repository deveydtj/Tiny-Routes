import SwiftUI

struct MultiVanHouseView: View {
    let color: VanColor
    var isDelivered = false
    var side: CGFloat = 36

    var body: some View {
        let roof = Path { path in
            path.move(to: CGPoint(x: side * 0.05, y: side * 0.4))
            path.addLine(to: CGPoint(x: side * 0.5, y: side * 0.04))
            path.addLine(to: CGPoint(x: side * 0.95, y: side * 0.4))
            path.closeSubpath()
        }
        ZStack {
            RoundedRectangle(cornerRadius: side * 0.08)
                .fill(Color(red: 0.98, green: 0.93, blue: 0.81).gradient)
                .overlay {
                    RoundedRectangle(cornerRadius: side * 0.08)
                        .strokeBorder(.white, lineWidth: side * 0.04)
                }
                .frame(width: side * 0.76, height: side * 0.62)
                .offset(y: side * 0.16)

            roof.fill(color.boardColor.gradient)
                .overlay {
                    roof.stroke(.white, style: StrokeStyle(lineWidth: side * 0.04, lineJoin: .round))
                }

            RoundedRectangle(cornerRadius: side * 0.045)
                .fill(Color(red: 0.19, green: 0.28, blue: 0.34))
                .overlay {
                    Text(color.symbol)
                        .font(.system(size: side * 0.28, weight: .bold))
                        .foregroundStyle(.white)
                }
                .frame(width: side * 0.4, height: side * 0.46)
                .offset(y: side * 0.23)

            if isDelivered {
                Image(systemName: "checkmark")
                    .font(.system(size: side * 0.23, weight: .heavy))
                    .foregroundStyle(.white)
                    .frame(width: side * 0.38, height: side * 0.38)
                    .background(Color(red: 0.13, green: 0.46, blue: 0.27), in: Circle())
                    .overlay { Circle().strokeBorder(.white, lineWidth: side * 0.035) }
                    // Beside the parked van, below the route-preview indicators.
                    .offset(x: -side * 0.48, y: side * 0.32)
            }
        }
        .frame(width: side, height: side)
        .shadow(color: .black.opacity(0.15), radius: side * 0.025, y: side * 0.035)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Self.accessibilityLabel(color: color))
        .accessibilityValue(Self.accessibilityValue(isDelivered: isDelivered))
    }

    static func accessibilityLabel(color: VanColor) -> String {
        "\(color.displayName) \(color.accessibilitySymbolName) house"
    }

    static func accessibilityValue(isDelivered: Bool) -> String {
        isDelivered ? "Delivered" : "Awaiting delivery"
    }
}

#if DEBUG
#Preview("Houses — gameplay and enlarged") {
    VStack(spacing: 24) {
        ForEach([VanColor.red, .blue, .yellow, .green], id: \.rawValue) { color in
            HStack(spacing: 24) {
                MultiVanHouseView(color: color)
                MultiVanHouseView(color: color, isDelivered: true)
                MultiVanHouseView(color: color, side: 72)
                MultiVanHouseView(color: color, isDelivered: true, side: 72)
            }
        }
    }
    .padding(28)
    .background(Color(white: 0.9))
}
#endif
