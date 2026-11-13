import SwiftUI

/// The level map's cottage, roofed in the house's colour, with the colour's shape on
/// a sticker in its gable. A parcel waits on the step until the delivery, then the
/// chimney smokes.
struct MultiVanHouseView: View {
    let color: VanColor
    var isDelivered = false
    var side: CGFloat = 36
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        ZStack {
            TimelineView(.animation(minimumInterval: 1 / 30, paused: reduceMotion)) { timeline in
                let time = reduceMotion ? 0 : timeline.date.timeIntervalSinceReferenceDate
                Canvas { context, size in
                    // The cottage's walls and roof span about 46 by 48 of its units.
                    let scale = size.width * 1.2 / 46
                    context.translateBy(x: size.width / 2, y: size.height / 2)
                    context.scaleBy(x: scale, y: scale)
                    context.translateBy(x: -23, y: -33)
                    TRVillageArt.drawHouse(
                        context, roof: color.boardColor, smoke: isDelivered, parcel: !isDelivered,
                        flag: false, time: time
                    )
                    let sticker = TRVillageArt.circle(19, 26.4, 7)
                    context.fill(sticker, with: .color(TRVillagePalette.cream))
                    context.stroke(sticker, with: .color(color.boardDeep), lineWidth: 1.2)
                    context.fill(
                        Path(color.dioramaSymbolPath(centre: CGPoint(x: 19, y: 26.6), radius: 4.3)),
                        with: .color(color.boardInk)
                    )
                }
            }

            if isDelivered {
                Image(systemName: "checkmark")
                    .font(.system(size: side * 0.23, weight: .heavy))
                    .foregroundStyle(.white)
                    .frame(width: side * 0.38, height: side * 0.38)
                    .background(MultiVanHUDStyle.pine, in: Circle())
                    .overlay { Circle().strokeBorder(MultiVanHUDStyle.cream, lineWidth: side * 0.035) }
                    // Beside the parked van, below the route-preview indicators.
                    .offset(x: -side * 0.48, y: side * 0.32)
            }
        }
        .frame(width: side, height: side)
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
    .background(Color(hex: 0x8FC766))
}
#endif
