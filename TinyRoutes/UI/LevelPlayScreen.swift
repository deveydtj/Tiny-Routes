import SwiftUI
import UIKit

/// Hosts one multi-van level from the main level map and records its progress.
struct LevelPlayScreen: View {
    let level: MultiVanLevel
    let nextLevelID: String?
    @ObservedObject var settingsService: UserSettingsService
    let progressService: ProgressService
    let economyService: EconomyService
    /// The player's shop choices, drawn on both boards.
    var cosmetics = MultiVanCosmetics.standard
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
                gameplay(engine)
                    .onChange(of: engine.outcome) { _, outcome in
                        // Autoplay's robot wins earn nothing and unlock nothing.
                        if outcome == .win, !isAutoplaying { recordWin(engine) }
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
        .environment(\.multiVanCosmetics, cosmetics)
        .background(Color(red: 0.88, green: 0.94, blue: 0.97).ignoresSafeArea())
        .task {
            guard engine == nil else { return }
            do {
                engine = try MultiVanEngine(level: level)
            } catch {
                loadError = "Could not open \(level.name). \(error.localizedDescription)"
            }
            #if DEBUG || MULTIVAN_INTERNAL
            if isAutoplaying {
                // A profiling run outlasts the auto-lock.
                UIApplication.shared.isIdleTimerDisabled = true
                MultiVanPerformanceMeter.shared?.start()
            }
            #endif
        }
        .onDisappear {
            if isAutoplaying { UIApplication.shared.isIdleTimerDisabled = false }
        }
    }

    private func gameplay(_ engine: MultiVanEngine) -> some View {
        let onNext = {
            if let nextLevelID {
                onNextLevel(nextLevelID)
            } else {
                onBackToLevels()
            }
        }
        #if DEBUG || MULTIVAN_INTERNAL
        return MultiVanGameplayScreen(
            engine: engine, settingsService: settingsService, onNext: onNext, onBack: onBackToLevels, autoplay: autoplay
        )
        #else
        return MultiVanGameplayScreen(engine: engine, settingsService: settingsService, onNext: onNext, onBack: onBackToLevels)
        #endif
    }

    #if DEBUG || MULTIVAN_INTERNAL
    /// The profiling option, when this launch is one for this level; see `MultiVanAutoplay`.
    private var autoplay: MultiVanAutoplay? {
        MultiVanAutoplay.launchConfiguration.flatMap { $0.levelID == level.id ? $0 : nil }
    }
    #endif

    private var isAutoplaying: Bool {
        #if DEBUG || MULTIVAN_INTERNAL
        autoplay != nil
        #else
        false
        #endif
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
            previousBestStars: update.previousBestStars
        )
        onProfileChanged()
    }
}
