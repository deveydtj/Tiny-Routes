import SwiftUI
import UIKit

/// Post-level result screen.
struct ResultScreen: View {

    enum ResultType: Equatable {
        case completed
        case failed
    }

    let levelID: String
    let result: ResultType
    let presentationID: UUID
    let elapsedTime: TimeInterval
    let tapCount: Int
    let failureReason: LevelFailureReason?
    let canAdvanceToNextLevel: Bool
    let onRestartTapped: () -> Void
    let onNextLevelTapped: () -> Void
    let onBackToLevelsTapped: () -> Void
    let onHomeTapped: () -> Void
    let onShareTapped: () -> Void
    let onUseHintTapped: () -> Void
    let onSkipLevelTapped: (() -> Void)?

    private let summaryFactory: TRResultSummaryFactory

    @State private var summary: TRResultSummary
    @State private var didPlayCompletionFeedback = false

    init(
        levelID: String,
        result: ResultType,
        presentationID: UUID = UUID(),
        elapsedTime: TimeInterval,
        tapCount: Int,
        failureReason: LevelFailureReason?,
        canAdvanceToNextLevel: Bool = false,
        onRestartTapped: @escaping () -> Void,
        onNextLevelTapped: @escaping () -> Void = {},
        onExitTapped: @escaping () -> Void,
        onBackToLevelsTapped: (() -> Void)? = nil,
        onHomeTapped: (() -> Void)? = nil,
        onShareTapped: @escaping () -> Void = {},
        onUseHintTapped: @escaping () -> Void = {},
        onSkipLevelTapped: (() -> Void)? = nil,
        levelRepository: LevelRepository = LevelRepository(),
        scoringService: ScoringService = ScoringService(),
        progressService: ProgressService = ProgressService()
    ) {
        let summaryFactory = TRResultSummaryFactory(
            levelRepository: levelRepository,
            scoringService: scoringService,
            progressService: progressService
        )

        self.levelID = levelID
        self.result = result
        self.presentationID = presentationID
        self.elapsedTime = elapsedTime
        self.tapCount = tapCount
        self.failureReason = failureReason
        self.canAdvanceToNextLevel = canAdvanceToNextLevel
        self.onRestartTapped = onRestartTapped
        self.onNextLevelTapped = onNextLevelTapped
        self.onBackToLevelsTapped = onBackToLevelsTapped ?? onExitTapped
        self.onHomeTapped = onHomeTapped ?? onExitTapped
        self.onShareTapped = onShareTapped
        self.onUseHintTapped = onUseHintTapped
        self.onSkipLevelTapped = onSkipLevelTapped
        self.summaryFactory = summaryFactory
        _summary = State(initialValue: summaryFactory.makeSummary(
            levelID: levelID,
            resultType: result,
            elapsedTime: elapsedTime,
            tapCount: tapCount,
            failureReason: failureReason,
            persistCompletion: false
        ))
    }

    var body: some View {
        ZStack {
            TRResultScreenBackground()

            VStack(spacing: 0) {
                resultHeader

                ScrollView(.vertical, showsIndicators: false) {
                    VStack(spacing: 14) {
                        accessibilitySummary

                        resultCard

                        smallIconActions
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 4)
                    .padding(.bottom, 26)
                    .frame(maxWidth: .infinity)
                }
            }
            .zIndex(1)

            if result == .completed {
                TRConfettiEmitter(mode: .success, playbackID: presentationID)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .ignoresSafeArea()
                    .zIndex(2)
            }
        }
        .onAppear {
            playCompletionFeedbackIfNeeded()
        }
        .task(id: summaryRefreshKey) {
            summary = summaryFactory.makeSummary(
                levelID: levelID,
                resultType: result,
                elapsedTime: elapsedTime,
                tapCount: tapCount,
                failureReason: failureReason,
                persistCompletion: true
            )
        }
    }

    private var resultHeader: some View {
        ZStack {
            HStack {
                Button(action: {}) {
                    Image(systemName: "gearshape.fill")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundStyle(TRGameplayStyle.Colors.primaryBlue)
                        .frame(width: 44, height: 44)
                        .background {
                            Circle()
                                .fill(.white.opacity(0.90))
                                .overlay {
                                    Circle()
                                        .stroke(.white.opacity(0.70), lineWidth: 1)
                                }
                                .shadow(color: .black.opacity(0.08), radius: 8, x: 0, y: 4)
                        }
                }
                .buttonStyle(.plain)
                .accessibilityLabel(Text("Settings"))

                Spacer()

                TRCurrencyPill(coinTotal: summary.coinTotal, onAddTapped: {})
            }

            TRTinyRoutesLogo(subtitle: nil, size: .compact)
                .frame(maxWidth: 150)
                .accessibilityAddTraits(.isHeader)
        }
        .padding(.horizontal, 16)
        .padding(.top, 8)
        .padding(.bottom, 3)
    }

    private var resultCard: some View {
        ZStack(alignment: .top) {
            TRResultCard {
                VStack(spacing: 12) {
                    titleBlock

                    TRResultStarRatingView(stars: summary.displayedStars)

                    TRResultRouteStrip(state: result == .completed ? .success : .failure)

                    TRResultStatsGrid(items: statItems)

                    infoBanner

                    actionButtons
                }
            }
            .padding(.top, TRGameplayStyle.Metrics.resultStatusBadgeSize / 2)

            TRResultStatusBadge(status: result == .completed ? .success : .failure)
        }
    }

    private var titleBlock: some View {
        VStack(spacing: 7) {
            Text(summary.headline)
                .font(.system(size: 30, weight: .black, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                .multilineTextAlignment(.center)
                .lineLimit(2)
                .minimumScaleFactor(0.72)
                .accessibilityAddTraits(.isHeader)

            Text(summary.subtitle)
                .font(.system(size: 15, weight: .semibold, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                .multilineTextAlignment(.center)
                .lineLimit(2)
                .minimumScaleFactor(0.76)

            Text(summary.levelTitle)
                .font(.system(size: 13, weight: .black, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.primaryBlue)
                .padding(.horizontal, 12)
                .frame(height: 28)
                .background {
                    Capsule()
                        .fill(Color(red: 0.90, green: 0.96, blue: 1.00))
                        .overlay {
                            Capsule()
                                .stroke(.white.opacity(0.82), lineWidth: 1)
                        }
                }
        }
    }

    @ViewBuilder
    private var infoBanner: some View {
        switch result {
        case .completed:
            TRResultInfoBanner(
                kind: .streak,
                systemImage: "flame.fill",
                title: "\(summary.streakDays) Day Streak!",
                bodyText: "Keep it going!",
                progressCount: 7,
                activeProgressCount: min(summary.streakDays, 7),
                coinBonus: summary.streakBonus,
                encouragementText: nil
            )
        case .failed:
            TRResultInfoBanner(
                kind: .failure,
                systemImage: failureSystemImage,
                title: summary.failureTitle ?? "Route stopped",
                bodyText: summary.failureBody ?? "The delivery could not be completed this time.",
                progressCount: 0,
                activeProgressCount: 0,
                coinBonus: nil,
                encouragementText: summary.encouragementText
            )
        }
    }

    @ViewBuilder
    private var actionButtons: some View {
        VStack(spacing: 9) {
            switch result {
            case .completed:
                TRResultActionButton(
                    title: "Next Level",
                    systemImage: "arrow.right",
                    variant: .primary,
                    action: onNextLevelTapped
                )
                .disabled(!canAdvanceToNextLevel)
                .accessibilityHint(canAdvanceToNextLevel ? Text("") : Text("No next level is available"))

                TRResultActionButton(
                    title: "Restart",
                    systemImage: "arrow.counterclockwise",
                    variant: .secondary,
                    action: onRestartTapped
                )

                TRResultActionButton(
                    title: "Back to Levels",
                    systemImage: "map.fill",
                    variant: .secondary,
                    action: onBackToLevelsTapped
                )

            case .failed:
                TRResultActionButton(
                    title: "Try Again",
                    systemImage: "arrow.counterclockwise",
                    variant: .primary,
                    action: onRestartTapped
                )

                TRResultActionButton(
                    title: "Use Hint",
                    systemImage: "lightbulb.fill",
                    badgeText: "\(summary.hintCount)",
                    variant: .secondary,
                    action: onUseHintTapped
                )

                TRResultActionButton(
                    title: "Back to Levels",
                    systemImage: "map.fill",
                    variant: .secondary,
                    action: onBackToLevelsTapped
                )

                if canAdvanceToNextLevel {
                    TRResultActionButton(
                        title: "Skip Level",
                        variant: .tertiary,
                        action: onSkipLevelTapped ?? onNextLevelTapped
                    )
                }
            }
        }
    }

    private var smallIconActions: some View {
        HStack(spacing: 14) {
            TRResultIconButton(
                systemImage: "square.and.arrow.up",
                label: "Share result",
                action: onShareTapped
            )

            TRResultIconButton(
                systemImage: "house.fill",
                label: "Home",
                action: onHomeTapped
            )
        }
        .padding(.top, 2)
    }

    private var accessibilitySummary: some View {
        Text(accessibilitySummaryText)
            .font(.system(size: 1))
            .foregroundStyle(.clear)
            .frame(width: 1, height: 1)
            .accessibilityLabel(Text(accessibilitySummaryText))
    }

    private var statItems: [TRResultStatItem] {
        switch result {
        case .completed:
            return [
                TRResultStatItem(
                    id: "moves",
                    title: "Moves",
                    value: summary.tapCountText,
                    footnote: "Best: \(summary.movesGoalText)",
                    systemImage: "hand.tap.fill",
                    spriteName: nil,
                    accent: TRGameplayStyle.Colors.primaryBlue
                ),
                TRResultStatItem(
                    id: "time",
                    title: "Time",
                    value: summary.elapsedTimeText,
                    footnote: "Goal: \(summary.timeGoalText)",
                    systemImage: "stopwatch.fill",
                    spriteName: nil,
                    accent: Color(red: 0.10, green: 0.65, blue: 0.72)
                ),
                TRResultStatItem(
                    id: "coins",
                    title: "Coins",
                    value: "\(summary.coinReward)",
                    footnote: "+\(summary.streakBonus) Bonus",
                    systemImage: nil,
                    spriteName: "gold_coin",
                    accent: TRGameplayStyle.Colors.resultWarningOrange
                ),
                TRResultStatItem(
                    id: "streak",
                    title: "Streak",
                    value: "\(summary.streakDays)",
                    footnote: "Amazing!",
                    systemImage: "flame.fill",
                    spriteName: nil,
                    accent: TRGameplayStyle.Colors.resultWarningOrange
                )
            ]
        case .failed:
            return [
                TRResultStatItem(
                    id: "moves",
                    title: "Moves",
                    value: summary.tapCountText,
                    footnote: "Goal: \(summary.movesGoalText)",
                    systemImage: "hand.tap.fill",
                    spriteName: nil,
                    accent: TRGameplayStyle.Colors.primaryBlue
                ),
                TRResultStatItem(
                    id: "time",
                    title: "Time",
                    value: summary.elapsedTimeText,
                    footnote: "Goal: \(summary.timeGoalText)",
                    systemImage: "stopwatch.fill",
                    spriteName: nil,
                    accent: Color(red: 0.10, green: 0.65, blue: 0.72)
                ),
                TRResultStatItem(
                    id: "goal",
                    title: "Goal",
                    value: "Not met",
                    footnote: summary.failureTitle,
                    systemImage: "flag.checkered",
                    spriteName: nil,
                    accent: TRGameplayStyle.Colors.resultWarningOrange
                ),
                TRResultStatItem(
                    id: "best",
                    title: "Best",
                    value: summary.bestStars > 0 ? "\(summary.bestStars)/3" : "-",
                    footnote: summary.bestStars > 0 ? "Saved best" : "No best yet",
                    systemImage: "star.fill",
                    spriteName: nil,
                    accent: TRGameplayStyle.Colors.resultGold
                )
            ]
        }
    }

    private var failureSystemImage: String {
        switch failureReason {
        case .timeExpired:
            return "timer"
        case .deadEnd:
            return "arrow.uturn.left.circle.fill"
        case .reachedDestinationWithoutPackage:
            return "shippingbox.fill"
        case nil:
            return "exclamationmark.triangle.fill"
        }
    }

    private var summaryRefreshKey: String {
        let resultKey = result == .completed ? "completed" : "failed"
        let failureKey = failureReason?.message ?? "none"
        return "\(levelID)|\(resultKey)|\(elapsedTime)|\(tapCount)|\(failureKey)"
    }

    private func playCompletionFeedbackIfNeeded() {
        guard result == .completed else { return }
        guard !didPlayCompletionFeedback else { return }
        didPlayCompletionFeedback = true
        UINotificationFeedbackGenerator().notificationOccurred(.success)
    }

    private var accessibilitySummaryText: String {
        switch result {
        case .completed:
            return "Level complete, \(summary.displayedStars) stars, \(summary.tapCountText) moves, time \(spokenElapsedTime)."
        case .failed:
            let reason = (summary.failureTitle ?? "route failed").lowercased()
            return "Route failed, \(reason), \(summary.tapCountText) moves, time \(spokenElapsedTime)."
        }
    }

    private var spokenElapsedTime: String {
        let wholeSeconds = max(Int(elapsedTime.rounded()), 0)
        let minutes = wholeSeconds / 60
        let seconds = wholeSeconds % 60

        if minutes > 0 {
            let minuteText = minutes == 1 ? "1 minute" : "\(minutes) minutes"
            let secondText = seconds == 1 ? "1 second" : "\(seconds) seconds"
            return "\(minuteText) \(secondText)"
        }

        return wholeSeconds == 1 ? "1 second" : "\(wholeSeconds) seconds"
    }
}

struct ResultScreen_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            ResultScreen(
                levelID: "level_001",
                result: .completed,
                elapsedTime: 18.4,
                tapCount: 2,
                failureReason: nil,
                canAdvanceToNextLevel: true,
                onRestartTapped: {},
                onNextLevelTapped: {},
                onExitTapped: {}
            )
            .previewDisplayName("Success - 3 Stars")

            ResultScreen(
                levelID: "level_001",
                result: .completed,
                elapsedTime: 18.4,
                tapCount: 20,
                failureReason: nil,
                canAdvanceToNextLevel: true,
                onRestartTapped: {},
                onNextLevelTapped: {},
                onExitTapped: {}
            )
            .previewDisplayName("Success - 2 Stars")

            ResultScreen(
                levelID: "level_001",
                result: .failed,
                elapsedTime: 45,
                tapCount: 19,
                failureReason: .timeExpired,
                canAdvanceToNextLevel: true,
                onRestartTapped: {},
                onNextLevelTapped: {},
                onExitTapped: {}
            )
            .previewDisplayName("Failed - Time")

            ResultScreen(
                levelID: "level_001",
                result: .failed,
                elapsedTime: 12,
                tapCount: 7,
                failureReason: .deadEnd,
                onRestartTapped: {},
                onExitTapped: {}
            )
            .previewDisplayName("Failed - Dead End")

            ResultScreen(
                levelID: "level_001",
                result: .failed,
                elapsedTime: 22,
                tapCount: 8,
                failureReason: .reachedDestinationWithoutPackage,
                onRestartTapped: {},
                onExitTapped: {}
            )
            .previewDisplayName("Failed - Package Missed")

            ResultScreen(
                levelID: "level_001",
                result: .failed,
                elapsedTime: 45,
                tapCount: 19,
                failureReason: .timeExpired,
                onRestartTapped: {},
                onExitTapped: {}
            )
            .previewDisplayName("Narrow Device")
            .previewDevice("iPhone SE (3rd generation)")

            ResultScreen(
                levelID: "level_001",
                result: .completed,
                elapsedTime: 18.4,
                tapCount: 2,
                failureReason: nil,
                canAdvanceToNextLevel: true,
                onRestartTapped: {},
                onNextLevelTapped: {},
                onExitTapped: {}
            )
            .previewDisplayName("Large Device")
            .previewDevice("iPhone 15 Pro Max")
        }
    }
}
