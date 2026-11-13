import SwiftUI

struct TRProfileStatsCard: View {
    let summary: TRProfileSummary

    var body: some View {
        ViewThatFits(in: .horizontal) {
            HStack(spacing: 0) {
                statColumns
            }

            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 2), spacing: 12) {
                statItems
            }
        }
        .padding(18)
        .background {
            MultiVanHUDCardBackground(cornerRadius: 26)
        }
    }

    private var statColumns: some View {
        Group {
            statItem(label: "Stars", value: "\(summary.totalStars)", icon: "star.fill", color: Color(hex: 0xE3A51C))
            divider
            statItem(label: "Levels", value: "\(summary.completedLevelCount)", icon: "map.fill", color: TRVillagePalette.blue)
            divider
            statItem(label: "Best Streak", value: "\(summary.bestStreakDays)", icon: "flame.fill", color: TRVillagePalette.roofs[0])
            divider
            statItem(label: "Fastest", value: summary.fastestTimeText, icon: "stopwatch.fill", color: Color(hex: 0x8A6FD1))
        }
    }

    private var statItems: some View {
        Group {
            statItem(label: "Stars", value: "\(summary.totalStars)", icon: "star.fill", color: Color(hex: 0xE3A51C))
            statItem(label: "Levels", value: "\(summary.completedLevelCount)", icon: "map.fill", color: TRVillagePalette.blue)
            statItem(label: "Best Streak", value: "\(summary.bestStreakDays)", icon: "flame.fill", color: TRVillagePalette.roofs[0])
            statItem(label: "Fastest", value: summary.fastestTimeText, icon: "stopwatch.fill", color: Color(hex: 0x8A6FD1))
        }
    }

    private var divider: some View {
        TRCozyDivider()
            .frame(height: 84)
    }

    private func statItem(label: String, value: String, icon: String, color: Color) -> some View {
        VStack(spacing: 7) {
            Text(label)
                .font(.system(size: 12, weight: .semibold, design: .rounded))
                .foregroundStyle(TRVillagePalette.slate)
                .lineLimit(1)
                .minimumScaleFactor(0.70)

            TRProfileStatIcon(systemImage: icon, color: color, size: 40)

            Text(value)
                .font(.system(size: 25, weight: .bold, design: .rounded))
                .foregroundStyle(TRVillagePalette.navy)
                .lineLimit(1)
                .minimumScaleFactor(0.70)
                .monospacedDigit()
        }
        .frame(maxWidth: .infinity, minHeight: 100)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("\(label), \(value)"))
    }
}

#Preview("Profile Stats Card") {
    TRProfileStatsCard(summary: .conceptPreview)
        .padding(20)
        .background(TRVillageSky())
}
