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
            TRGlassCardBackground(cornerRadius: 25)
        }
    }

    private var statColumns: some View {
        Group {
            statItem(label: "Stars", value: "\(summary.totalStars)", icon: "star.fill", color: TRGameplayStyle.Colors.resultGold)
            divider
            statItem(label: "Levels", value: "\(summary.completedLevelCount)", icon: "map.fill", color: TRGameplayStyle.Colors.primaryBlue)
            divider
            statItem(label: "Best Streak", value: "\(summary.bestStreakDays)", icon: "flame.fill", color: TRGameplayStyle.Colors.orangeAccent)
            divider
            statItem(label: "Fastest", value: summary.fastestTimeText, icon: "stopwatch.fill", color: Color(red: 0.55, green: 0.33, blue: 0.95))
        }
    }

    private var statItems: some View {
        Group {
            statItem(label: "Stars", value: "\(summary.totalStars)", icon: "star.fill", color: TRGameplayStyle.Colors.resultGold)
            statItem(label: "Levels", value: "\(summary.completedLevelCount)", icon: "map.fill", color: TRGameplayStyle.Colors.primaryBlue)
            statItem(label: "Best Streak", value: "\(summary.bestStreakDays)", icon: "flame.fill", color: TRGameplayStyle.Colors.orangeAccent)
            statItem(label: "Fastest", value: summary.fastestTimeText, icon: "stopwatch.fill", color: Color(red: 0.55, green: 0.33, blue: 0.95))
        }
    }

    private var divider: some View {
        Divider()
            .frame(height: 84)
    }

    private func statItem(label: String, value: String, icon: String, color: Color) -> some View {
        VStack(spacing: 7) {
            Text(label)
                .font(.system(size: 12, weight: .black, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                .lineLimit(1)
                .minimumScaleFactor(0.70)

            TRProfileStatIcon(systemImage: icon, color: color, size: 42)

            Text(value)
                .font(.system(size: 27, weight: .black, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
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
        .background(Color(red: 0.86, green: 0.94, blue: 0.98))
}
