import SwiftUI

struct TRResultStatItem: Identifiable, Equatable {
    let id: String
    let title: String
    let value: String
    let footnote: String?
    let systemImage: String?
    let spriteName: String?
    let accent: Color

    static func == (lhs: TRResultStatItem, rhs: TRResultStatItem) -> Bool {
        lhs.id == rhs.id
            && lhs.title == rhs.title
            && lhs.value == rhs.value
            && lhs.footnote == rhs.footnote
            && lhs.systemImage == rhs.systemImage
            && lhs.spriteName == rhs.spriteName
    }
}

struct TRResultStatsGrid: View {
    let items: [TRResultStatItem]

    var body: some View {
        HStack(spacing: 0) {
            ForEach(Array(items.prefix(4).enumerated()), id: \.element.id) { index, item in
                statCell(item)
                    .frame(maxWidth: .infinity)

                if index < min(items.count, 4) - 1 {
                    Rectangle()
                        .fill(Color(red: 0.76, green: 0.82, blue: 0.90).opacity(0.34))
                        .frame(width: 1, height: 58)
                }
            }
        }
        .padding(.vertical, 12)
        .padding(.horizontal, 6)
        .background {
            RoundedRectangle(cornerRadius: 22, style: .continuous)
                .fill(Color(red: 0.95, green: 0.98, blue: 1.00).opacity(0.88))
                .overlay {
                    RoundedRectangle(cornerRadius: 22, style: .continuous)
                        .stroke(.white.opacity(0.82), lineWidth: 1)
                }
        }
    }

    private func statCell(_ item: TRResultStatItem) -> some View {
        VStack(spacing: 5) {
            HStack(spacing: 4) {
                statIcon(item)

                Text(item.title)
                    .font(.system(size: 10, weight: .heavy, design: .rounded))
                    .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                    .lineLimit(1)
                    .minimumScaleFactor(0.62)
            }

            Text(item.value)
                .font(.system(size: 17, weight: .black, design: .rounded))
                .monospacedDigit()
                .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                .lineLimit(1)
                .minimumScaleFactor(0.62)

            if let footnote = item.footnote {
                Text(footnote)
                    .font(.system(size: 9, weight: .bold, design: .rounded))
                    .foregroundStyle(item.accent)
                    .lineLimit(1)
                    .minimumScaleFactor(0.58)
            }
        }
        .padding(.horizontal, 4)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(accessibilityText(for: item)))
    }

    @ViewBuilder
    private func statIcon(_ item: TRResultStatItem) -> some View {
        if let spriteName = item.spriteName {
            SpriteImage(name: spriteName)
                .scaledToFit()
                .frame(width: 13, height: 13)
                .accessibilityHidden(true)
        } else if let systemImage = item.systemImage {
            Image(systemName: systemImage)
                .font(.system(size: 10, weight: .black, design: .rounded))
                .foregroundStyle(item.accent)
                .accessibilityHidden(true)
        }
    }

    private func accessibilityText(for item: TRResultStatItem) -> String {
        if let footnote = item.footnote {
            return "\(item.title), \(item.value), \(footnote)"
        }

        return "\(item.title), \(item.value)"
    }
}

#Preview("Result Stats") {
    VStack(spacing: 16) {
        TRResultStatsGrid(items: [
            TRResultStatItem(id: "moves", title: "Moves", value: "14", footnote: "Best: 12", systemImage: "hand.tap.fill", spriteName: nil, accent: .blue),
            TRResultStatItem(id: "time", title: "Time", value: "1:32.0", footnote: "Goal: 1:15.0", systemImage: "stopwatch.fill", spriteName: nil, accent: .teal),
            TRResultStatItem(id: "coins", title: "Coins", value: "150", footnote: "+50 Bonus", systemImage: nil, spriteName: "gold_coin", accent: .orange),
            TRResultStatItem(id: "streak", title: "Streak", value: "7", footnote: "Amazing!", systemImage: "flame.fill", spriteName: nil, accent: .orange)
        ])
    }
    .padding()
    .background(Color(red: 0.88, green: 0.95, blue: 1.0))
}
