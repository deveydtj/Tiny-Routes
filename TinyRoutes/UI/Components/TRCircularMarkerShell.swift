import SwiftUI

struct TRCircularMarkerShell<Content: View>: View {
    let size: CGFloat
    let rimWidth: CGFloat
    let shadowOpacity: Double
    let content: Content

    init(
        size: CGFloat,
        rimWidth: CGFloat = TRGameplayStyle.Metrics.crispWhiteRimWidth,
        shadowOpacity: Double = 0.16,
        @ViewBuilder content: () -> Content
    ) {
        self.size = size
        self.rimWidth = rimWidth
        self.shadowOpacity = shadowOpacity
        self.content = content()
    }

    var body: some View {
        ZStack {
            Circle()
                .fill(Color.white.opacity(0.96))
                .frame(width: size, height: size)
                .overlay {
                    Circle()
                        .stroke(Color.white, lineWidth: rimWidth)
                }
                .overlay {
                    Circle()
                        .stroke(TRGameplayStyle.Colors.markerStroke, lineWidth: 1.5)
                        .padding(rimWidth / 2)
                }
                .shadow(color: Color.black.opacity(shadowOpacity), radius: 10, x: 0, y: 5)

            content
        }
        .frame(width: size, height: size)
    }
}

struct TRPackageMarkerView: View {
    let size: CGFloat
    let iconSize: CGFloat
    let cornerRadius: CGFloat

    init(
        size: CGFloat = TRGameplayStyle.Metrics.packageBadgeSize,
        iconSize: CGFloat = TRGameplayStyle.Metrics.packageBadgeIconSize,
        cornerRadius: CGFloat = TRGameplayStyle.Metrics.packageBadgeCornerRadius
    ) {
        self.size = size
        self.iconSize = iconSize
        self.cornerRadius = cornerRadius
    }

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                .fill(Color(red: 1.0, green: 0.98, blue: 0.91).opacity(0.97))
                .frame(width: size, height: size)
                .overlay {
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .stroke(Color.white.opacity(0.85), lineWidth: 1)
                        .padding(1)
                }
                .overlay {
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .stroke(TRGameplayStyle.Colors.resultGold.opacity(0.82), lineWidth: 1.5)
                }
                .shadow(color: TRGameplayStyle.Colors.resultGold.opacity(0.20), radius: 7, x: 0, y: 1)
                .shadow(color: Color.black.opacity(0.08), radius: 3, x: 0, y: 2)

            SpriteImage(name: "shipping_box")
                .scaledToFit()
                .frame(width: iconSize, height: iconSize)
                .accessibilityHidden(true)
        }
        .frame(width: size, height: size)
        .accessibilityLabel("Package")
    }
}

struct TRCurrentObjectiveMarkerPresentation: Equatable {
    enum Visual: Equatable {
        case package
        case systemImage(String)
        case destination
    }

    let visual: Visual
    let title: String
    let orderText: String
    let accessibilityLabel: String

    init(objective: RouteObjective) {
        let authoredTitle: String?
        if case let .string(value)? = objective.displayMetadata?["title"],
           !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            authoredTitle = value
        } else {
            authoredTitle = nil
        }

        let fallbackTitle: String
        switch objective.kind {
        case .pickup:
            visual = .package
            fallbackTitle = "Pick up package"
        case .checkpoint:
            visual = .systemImage("checkmark.seal.fill")
            fallbackTitle = "Reach checkpoint"
        case .delivery:
            visual = .systemImage("shippingbox.fill")
            fallbackTitle = "Make delivery"
        case .destination:
            visual = .destination
            fallbackTitle = "Reach destination"
        }

        title = authoredTitle ?? fallbackTitle
        orderText = String(objective.sequenceIndex + 1)
        accessibilityLabel = "Current objective \(objective.sequenceIndex + 1): \(title)"
    }
}

struct TRCurrentObjectiveMarkerView: View {
    let objective: RouteObjective
    let destinationOption: ShopCosmeticOption
    let size: CGFloat
    let iconSize: CGFloat

    init(
        objective: RouteObjective,
        destinationOption: ShopCosmeticOption,
        size: CGFloat = TRGameplayStyle.Metrics.currentObjectiveMarkerSize,
        iconSize: CGFloat = TRGameplayStyle.Metrics.currentObjectiveIconSize
    ) {
        self.objective = objective
        self.destinationOption = destinationOption
        self.size = size
        self.iconSize = iconSize
    }

    var body: some View {
        let presentation = TRCurrentObjectiveMarkerPresentation(objective: objective)

        ZStack(alignment: .topTrailing) {
            markerContent(for: presentation)

            Circle()
                .stroke(TRGameplayStyle.Colors.primaryBlue, lineWidth: 4)
                .frame(width: size + 8, height: size + 8)
                .shadow(color: TRGameplayStyle.Colors.primaryBlue.opacity(0.42), radius: 8)

            Text(presentation.orderText)
                .font(.system(size: 12, weight: .black, design: .rounded))
                .foregroundStyle(.white)
                .frame(
                    width: TRGameplayStyle.Metrics.currentObjectiveOrderBadgeSize,
                    height: TRGameplayStyle.Metrics.currentObjectiveOrderBadgeSize
                )
                .background(TRGameplayStyle.Colors.primaryBlue, in: Circle())
                .overlay {
                    Circle().stroke(.white, lineWidth: 2)
                }
                .offset(x: 5, y: -5)
        }
        .frame(width: size + 12, height: size + 12)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(presentation.accessibilityLabel)
    }

    @ViewBuilder
    private func markerContent(
        for presentation: TRCurrentObjectiveMarkerPresentation
    ) -> some View {
        switch presentation.visual {
        case .package:
            TRCircularMarkerShell(size: size) {
                SpriteImage(name: "shipping_box")
                    .scaledToFit()
                    .frame(width: iconSize, height: iconSize)
            }
        case let .systemImage(name):
            TRCircularMarkerShell(size: size) {
                Image(systemName: name)
                    .font(.system(size: iconSize * 0.72, weight: .black, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.primaryBlue)
                    .symbolRenderingMode(.hierarchical)
            }
        case .destination:
            TRDestinationMarkerView(
                option: destinationOption,
                shellSize: size,
                iconSize: iconSize
            )
        }
    }
}

#Preview("Gameplay Marker Shells") {
    HStack(spacing: 18) {
        TRPackageMarkerView()

        TRCircularMarkerShell(size: TRGameplayStyle.Metrics.packageMarkerSize) {
            SpriteImage(name: "finish_flag_pin")
                .scaledToFit()
                .frame(width: TRGameplayStyle.Metrics.markerIconSize, height: TRGameplayStyle.Metrics.markerIconSize)
        }

        TRCircularMarkerShell(size: TRGameplayStyle.Metrics.switchCircleSize, rimWidth: 3) {
            Image(systemName: "arrow.right")
                .font(.system(size: 22, weight: .heavy, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
        }
    }
    .padding()
    .background(Color(red: 0.86, green: 0.93, blue: 0.98))
}
