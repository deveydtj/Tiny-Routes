import SwiftUI

/// What an experiment board is trying out, read from its content.
enum MultiVanExperimentKind: String, CaseIterable {
    case pickup = "Package pickup"
    case signal = "Signals"
    case ice = "Icy roads"
    case control = "Matched controls"

    static func kind(of level: MultiVanLevel) -> Self {
        if !level.roadZones.isEmpty { return .ice }
        if !level.signals.isEmpty { return .signal }
        if !level.packages.isEmpty { return .pickup }
        return .control
    }

    var symbol: String {
        switch self {
        case .pickup: "shippingbox.fill"
        case .signal: "light.beacon.max.fill"
        case .ice: "snowflake"
        case .control: "equal.circle.fill"
        }
    }
}

/// The boards on trial, for internal builds. A win here is only a win: no stars
/// are saved, nothing unlocks and no coins are paid.
struct MultiVanExperimentsScreen: View {
    let levels: [MultiVanLevel]
    let onSelect: (String) -> Void
    let onBack: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Button(action: onBack) {
                    Label("Settings", systemImage: "chevron.left")
                        .font(.system(.headline, design: .rounded, weight: .bold))
                        .frame(minHeight: 44)
                }
                .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                Spacer()
            }
            .padding(.horizontal, 16)

            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    Text("Experiment Boards")
                        .font(.system(.title, design: .rounded, weight: .heavy))
                        .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                        .accessibilityAddTraits(.isHeader)
                    Text("Boards on trial. Wins here save no stars, unlock nothing and pay no coins.")
                        .font(.system(.subheadline, design: .rounded))
                        .foregroundStyle(TRGameplayStyle.Colors.secondaryText)

                    if levels.isEmpty {
                        Text("No experiment boards are bundled in this build.")
                            .font(.system(.body, design: .rounded))
                            .padding(.top, 24)
                    }
                    ForEach(levels, id: \.id) { level in
                        Button { onSelect(level.id) } label: { row(level) }
                            .buttonStyle(.plain)
                    }
                }
                .padding(16)
            }
        }
    }

    private func row(_ level: MultiVanLevel) -> some View {
        let kind = MultiVanExperimentKind.kind(of: level)
        return HStack(spacing: 12) {
            Image(systemName: kind.symbol)
                .font(.system(.title3, weight: .bold))
                .foregroundStyle(TRGameplayStyle.Colors.primaryBlue)
                .frame(width: 36)
            VStack(alignment: .leading, spacing: 2) {
                Text(level.name)
                    .font(.system(.headline, design: .rounded, weight: .heavy))
                    .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                Text("\(kind.rawValue) · \(level.biome.displayName) · \(level.vans.count) van\(level.vans.count == 1 ? "" : "s")")
                    .font(.system(.footnote, design: .rounded, weight: .semibold))
                    .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
            }
            Spacer(minLength: 0)
            Image(systemName: "chevron.right")
                .font(.system(.footnote, weight: .bold))
                .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
        }
        .padding(14)
        .frame(maxWidth: .infinity, minHeight: 60, alignment: .leading)
        .background { MultiVanHUDCardBackground(cornerRadius: 20) }
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityHint("Play this experiment board")
    }
}

/// Hosts one experiment board. Deliberately has no progress or economy service:
/// trial wins cannot become campaign records.
struct MultiVanExperimentPlayScreen: View {
    let level: MultiVanLevel
    @ObservedObject var settingsService: UserSettingsService
    let onNext: (() -> Void)?
    let onBack: () -> Void

    @State private var engine: MultiVanEngine?
    @State private var loadError: String?

    var body: some View {
        Group {
            if let engine {
                gameplay(engine)
            } else {
                VStack(spacing: 16) {
                    Text(loadError ?? "Loading experiment…")
                        .multilineTextAlignment(.center)
                    Button("Back", action: onBack)
                }
                .padding()
            }
        }
        .background(Color(red: 0.88, green: 0.94, blue: 0.97).ignoresSafeArea())
        .task {
            guard engine == nil else { return }
            Self.scratchDefaults.removeObject(forKey: MultiVanTutorialProgress.storageKey)
            do {
                engine = try MultiVanEngine(level: level)
            } catch {
                loadError = "Could not open \(level.name). \(error.localizedDescription)"
            }
        }
    }

    private func gameplay(_ engine: MultiVanEngine) -> some View {
        // Tips on trial boards show every visit: nothing is remembered.
        let progress = MultiVanTutorialProgress(defaults: Self.scratchDefaults)
        #if DEBUG || MULTIVAN_INTERNAL
        let autoplay = MultiVanAutoplay.launchConfiguration.flatMap { $0.levelID == level.id ? $0 : nil }
        return MultiVanGameplayScreen(
            engine: engine, settingsService: settingsService, onNext: onNext ?? onBack, onBack: onBack,
            tutorialProgress: progress, autoplay: autoplay
        )
        #else
        return MultiVanGameplayScreen(
            engine: engine, settingsService: settingsService, onNext: onNext ?? onBack, onBack: onBack,
            tutorialProgress: progress
        )
        #endif
    }

    private static let scratchDefaults = UserDefaults(suiteName: "multiVanExperiments") ?? .standard
}
