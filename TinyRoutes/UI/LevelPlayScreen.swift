import SwiftUI

/// Hosts one multi-van level from the main level map and records its progress.
struct LevelPlayScreen: View {
    let level: MultiVanLevel
    let nextLevelID: String?
    @ObservedObject var settingsService: UserSettingsService
    let progressService: ProgressService
    let economyService: EconomyService
    let onNextLevel: (String) -> Void
    let onBackToLevels: () -> Void
    let onProfileChanged: () -> Void

    // Owned here so the engine survives re-renders; ContentView gives each
    // level a fresh identity, and therefore a fresh engine.
    @State private var engine: MultiVanEngine?
    @State private var loadError: String?

    var body: some View {
        Group {
            if let engine {
                MultiVanGameplayScreen(
                    engine: engine,
                    settingsService: settingsService,
                    onNext: {
                        if let nextLevelID {
                            onNextLevel(nextLevelID)
                        } else {
                            onBackToLevels()
                        }
                    },
                    onBack: onBackToLevels
                )
                .onChange(of: engine.outcome) { _, outcome in
                    if outcome == .win { recordWin(engine) }
                }
            } else {
                VStack(spacing: 0) {
                    HStack {
                        Button(action: onBackToLevels) {
                            Label("Levels", systemImage: "chevron.left")
                                .font(.system(.headline, design: .rounded, weight: .bold))
                                .frame(minHeight: 44)
                        }
                        .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                        .accessibilityHint("Return to the level map")
                        Spacer()
                    }
                    .padding(.horizontal, 16)
                    Spacer()
                    Text(loadError ?? "Loading level…")
                        .multilineTextAlignment(.center)
                        .padding()
                    Spacer()
                }
            }
        }
        .background(Color(red: 0.88, green: 0.94, blue: 0.97).ignoresSafeArea())
        .task {
            guard engine == nil else { return }
            do {
                engine = try MultiVanEngine(level: level)
            } catch {
                loadError = "Could not open \(level.name). \(error.localizedDescription)"
            }
        }
    }

    private func recordWin(_ engine: MultiVanEngine) {
        let stars = MultiVanStars.rating(changes: engine.changeCount, par: level.parChanges)
        let update = progressService.completeLevel(
            levelID: level.id,
            earnedStars: stars,
            nextLevelID: nextLevelID
        )
        economyService.awardLevelCompletionReward(
            levelID: level.id,
            earnedStars: stars,
            isFirstCompletion: update.wasFirstCompletion
        )
        onProfileChanged()
    }
}
