import SwiftUI

struct TRDestinationMarkerView: View {
    let option: ShopCosmeticOption
    let shellSize: CGFloat
    let iconSize: CGFloat

    var body: some View {
        let visual = TRDestinationMarkerVisual(option: option)

        TRCircularMarkerShell(size: shellSize) {
            if visual.usesFinishFlagSprite {
                SpriteImage(name: "finish_flag_pin")
                    .scaledToFit()
                    .frame(width: iconSize, height: iconSize)
                    .scaleEffect(1.10)
            } else {
                ZStack {
                    Circle()
                        .fill(option.accent.routeColor.opacity(0.13))
                        .frame(width: iconSize * 0.92, height: iconSize * 0.92)

                    Image(systemName: visual.systemImageName)
                        .font(.system(size: iconSize * 0.60, weight: .black, design: .rounded))
                        .foregroundStyle(option.accent.routeColor)
                        .symbolRenderingMode(.hierarchical)
                }
            }
        }
        .accessibilityHidden(true)
    }
}

struct TRDestinationMarkerVisual: Equatable {
    let optionID: String

    init(option: ShopCosmeticOption) {
        self.optionID = option.id
    }

    var usesFinishFlagSprite: Bool {
        optionID == "destinationFlag"
    }

    var systemImageName: String {
        Self.systemImageName(forOptionID: optionID)
    }

    static func systemImageName(forOptionID optionID: String) -> String {
        switch optionID {
        case "destinationBeach":
            return "beach.umbrella.fill"
        case "destinationCabin":
            return "house.fill"
        case "destinationArcade":
            return "gamecontroller.fill"
        default:
            return "mappin.circle.fill"
        }
    }
}

#Preview("Destination Markers") {
    let options = ShopCatalogService().options(forCategoryID: ShopCosmeticCategoryID.destinations)

    return HStack(spacing: 18) {
        ForEach(options) { option in
            TRDestinationMarkerView(
                option: option,
                shellSize: TRGameplayStyle.Metrics.packageMarkerSize,
                iconSize: TRGameplayStyle.Metrics.markerIconSize
            )
        }
    }
    .padding()
    .background(Color(red: 0.86, green: 0.93, blue: 0.98))
}
