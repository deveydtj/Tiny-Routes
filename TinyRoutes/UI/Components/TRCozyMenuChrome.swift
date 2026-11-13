import SwiftUI

// MARK: - Banner

/// The teal banner across the top of a cozy menu, as on the level map: the
/// page's title under a mint eyebrow, with its buttons alongside.
struct TRCozyMenuBanner<Leading: View, Trailing: View>: View {
    let eyebrow: String
    let title: String
    @ViewBuilder let leading: Leading
    @ViewBuilder let trailing: Trailing

    init(
        eyebrow: String,
        title: String,
        @ViewBuilder leading: () -> Leading = { EmptyView() },
        @ViewBuilder trailing: () -> Trailing = { EmptyView() }
    ) {
        self.eyebrow = eyebrow
        self.title = title
        self.leading = leading()
        self.trailing = trailing()
    }

    var body: some View {
        HStack(spacing: 10) {
            leading

            TRMenuTitleLogo(pageTitle: title, subtitleOverride: eyebrow)

            Spacer(minLength: 4)

            HStack(spacing: 6) { trailing }
        }
        .padding(.horizontal, 16)
        .padding(.top, 4)
        .frame(maxWidth: 760)
        // As tall as the level map's banner, so the pages line up as you switch tabs.
        .frame(maxWidth: .infinity, minHeight: TRVillageBoard.bannerEdge + 14, alignment: .top)
        .background(alignment: .bottom) {
            MultiVanHUDBanner().ignoresSafeArea(edges: .top)
        }
    }
}

/// The coin count in a banner, opening the shop.
struct TRCozyCoinButton: View {
    let coinTotal: Int
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            TRVillagePill {
                TRVillageCoin()
                Text(coinTotal.formatted())
            }
        }
        .buttonStyle(TRVillagePressStyle())
        .accessibilityLabel(Text(coinTotal == 1 ? "1 coin" : "\(coinTotal.formatted()) coins"))
        .accessibilityHint("Get more coins")
    }
}

/// A round cream button in a banner, like the level map's settings button.
struct TRCozyCircleButton: View {
    let systemName: String
    let label: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: systemName)
                .font(.system(size: 19, weight: .semibold))
                .foregroundStyle(TRVillagePalette.navy)
                .frame(width: 44, height: 44)
        }
        .buttonStyle(.multiVanHUDCircle)
        .accessibilityLabel(Text(label))
    }
}

/// A cream pill in the banner, holding a count.
struct TRVillagePill<Content: View>: View {
    @ViewBuilder let content: Content

    var body: some View {
        HStack(spacing: 5) { content }
            .font(.system(size: 14, weight: .semibold, design: .rounded))
            .monospacedDigit()
            .foregroundStyle(TRVillagePalette.navy)
            .padding(.horizontal, 10)
            .frame(height: 32)
            .background {
                Capsule()
                    .fill(LinearGradient(colors: [TRVillagePalette.cream, TRVillagePalette.creamDeep], startPoint: .top, endPoint: .bottom))
                    .background { Capsule().fill(TRVillagePalette.creamLip).offset(y: 3) }
            }
            .fixedSize()
    }
}

struct TRVillageCoin: View {
    var size: CGFloat = 15

    var body: some View {
        Circle()
            .fill(TRVillagePalette.gold)
            .overlay { Circle().stroke(Color(hex: 0xC8921A), lineWidth: size * 0.08).padding(size * 0.17) }
            .frame(width: size, height: size)
            .accessibilityHidden(true)
    }
}

/// Shrinks a little under the finger.
struct TRVillagePressStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.93 : 1)
            .animation(.spring(response: 0.18, dampingFraction: 0.7), value: configuration.isPressed)
    }
}

// MARK: - Inside the cards

/// A heading sitting on the sky between the cards.
struct TRCozySectionTitle: View {
    let title: String

    var body: some View {
        Text(title)
            .font(.system(size: 22, weight: .bold, design: .rounded))
            .foregroundStyle(TRVillagePalette.teal)
            .shadow(color: .white.opacity(0.6), radius: 0, x: 0, y: 1)
            .lineLimit(1)
            .minimumScaleFactor(0.82)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.leading, 4)
            .accessibilityAddTraits(.isHeader)
    }
}

/// A heading inside a cream card.
struct TRCozyCardTitle: View {
    let title: String

    var body: some View {
        Text(title)
            .font(.system(size: 20, weight: .bold, design: .rounded))
            .foregroundStyle(TRVillagePalette.navy)
            .lineLimit(1)
            .minimumScaleFactor(0.82)
            .accessibilityAddTraits(.isHeader)
    }
}

/// A sunken patch in a cream card, holding a tile or a row.
struct TRCozyWellBackground<S: InsettableShape>: View {
    let shape: S

    var body: some View {
        shape
            .fill(Self.fill)
            .overlay { shape.strokeBorder(TRVillagePalette.creamLip.opacity(0.55), lineWidth: 1) }
    }

    static var fill: Color { Color(hex: 0xF2E8D4) }
}

extension TRCozyWellBackground where S == RoundedRectangle {
    init(cornerRadius: CGFloat = 18) {
        self.init(shape: RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
    }
}

/// A small tag on a darker lip, like the home screen's "Soon": teal by default.
struct TRCozyTag: View {
    let text: String
    var systemImage: String?
    var tint = TRVillagePalette.teal

    var body: some View {
        HStack(spacing: 4) {
            if let systemImage {
                Image(systemName: systemImage)
                    .font(.system(size: 10, weight: .bold))
            }
            Text(text)
                .font(.system(size: 12, weight: .semibold, design: .rounded))
                .lineLimit(1)
                .minimumScaleFactor(0.8)
        }
        .foregroundStyle(TRVillagePalette.cream)
        .padding(.horizontal, 9)
        .frame(height: 24)
        .background {
            Capsule()
                .fill(tint)
                .background { Capsule().fill(tint).overlay { Capsule().fill(.black.opacity(0.25)) }.offset(y: 2) }
        }
        .fixedSize()
    }
}

/// A thin line between a card's columns.
struct TRCozyDivider: View {
    var body: some View {
        Capsule()
            .fill(TRVillagePalette.creamLip.opacity(0.8))
            .frame(width: 1.5)
            .accessibilityHidden(true)
    }
}

/// A round badge on a darker lip holding a symbol, like a level's plaque.
struct TRCozyIconBadge: View {
    let systemName: String
    var tint = TRVillagePalette.teal
    var size: CGFloat = 40

    var body: some View {
        Image(systemName: systemName)
            .font(.system(size: size * 0.42, weight: .semibold))
            .foregroundStyle(TRVillagePalette.cream)
            .frame(width: size, height: size)
            .background {
                Circle()
                    .fill(tint)
                    .overlay { Circle().fill(LinearGradient(colors: [.white.opacity(0.22), .clear], startPoint: .top, endPoint: .center)) }
                    .background { Circle().fill(tint).overlay { Circle().fill(.black.opacity(0.25)) }.offset(y: 2.5) }
            }
            .padding(.bottom, 2.5)
            .accessibilityHidden(true)
    }
}

/// A choice between a few options, as a teal pill sliding along a sunken track.
struct TRCozySegmentedPicker<Value: Hashable>: View {
    let title: String
    let options: [(value: Value, label: String)]
    let selection: Value
    let onSelect: (Value) -> Void

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Namespace private var namespace

    var body: some View {
        HStack(spacing: 4) {
            ForEach(Array(options.enumerated()), id: \.offset) { _, option in
                let isSelected = option.value == selection
                Button { onSelect(option.value) } label: {
                    Text(option.label)
                        .font(.system(size: 15, weight: .semibold, design: .rounded))
                        .foregroundStyle(isSelected ? TRVillagePalette.cream : TRVillagePalette.navy)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                        .frame(maxWidth: .infinity, minHeight: 38)
                        .background {
                            if isSelected {
                                Capsule()
                                    .fill(TRVillagePalette.teal)
                                    .background { Capsule().fill(TRVillagePalette.tealDark).offset(y: 2) }
                                    .matchedGeometryEffect(id: "selection", in: namespace)
                            }
                        }
                        .contentShape(Capsule())
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(isSelected ? [.isSelected] : [])
            }
        }
        .padding(4)
        .padding(.bottom, 2)
        .background { TRCozyWellBackground(shape: Capsule()) }
        .animation(reduceMotion ? nil : .spring(response: 0.25, dampingFraction: 0.8), value: selection)
        .accessibilityElement(children: .contain)
        .accessibilityLabel(Text(title))
    }
}

#Preview("Cozy menu chrome") {
    ZStack(alignment: .top) {
        TRCozySkyBackground()
        VStack(spacing: 16) {
            TRCozyMenuBanner(eyebrow: "Customize your journey", title: "Shop") {
                EmptyView()
            } trailing: {
                TRCozyCoinButton(coinTotal: 1_250, action: {})
                TRCozyCircleButton(systemName: "gearshape", label: "Settings", action: {})
            }
            TRCozySectionTitle(title: "Featured").padding(.horizontal, 20)
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    TRCozyCardTitle(title: "Card")
                    Spacer()
                    TRCozyTag(text: "In Use", systemImage: "checkmark")
                }
                HStack(spacing: 12) {
                    TRCozyIconBadge(systemName: "music.note")
                    TRCozyIconBadge(systemName: "exclamationmark.triangle.fill", tint: TRVillagePalette.roofs[0])
                    TRCozyDivider().frame(height: 40)
                    Text("Well").padding(12).background { TRCozyWellBackground() }
                }
                TRCozySegmentedPicker(title: "Board", options: [(1, "3D Diorama"), (2, "2D Map")], selection: 1, onSelect: { _ in })
            }
            .padding(18)
            .background { MultiVanHUDCardBackground() }
            .padding(.horizontal, 20)
            Spacer()
        }
    }
}
