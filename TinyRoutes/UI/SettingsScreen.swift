import SwiftUI

/// Settings screen.
struct SettingsScreen: View {
    @ObservedObject var settingsService: UserSettingsService

    let progressService: ProgressService
    let playerName: String
    let onBackTapped: () -> Void
    let onEditProfileTapped: () -> Void
    let onCustomizeTapped: () -> Void
    let onRestorePurchasesTapped: () -> Void
    let onRemoveAdsTapped: () -> Void
    let onContactSupportTapped: () -> Void
    let onRateAppTapped: () -> Void
    let onPrivacyPolicyTapped: () -> Void
    let onTermsTapped: () -> Void
    let onProfileChanged: () -> Void

    @State private var activeAlert: SettingsAlert?

    init(
        settingsService: UserSettingsService,
        progressService: ProgressService,
        playerName: String = "Player One",
        onBackTapped: @escaping () -> Void,
        onEditProfileTapped: @escaping () -> Void,
        onCustomizeTapped: @escaping () -> Void,
        onRestorePurchasesTapped: @escaping () -> Void,
        onRemoveAdsTapped: @escaping () -> Void,
        onContactSupportTapped: @escaping () -> Void,
        onRateAppTapped: @escaping () -> Void,
        onPrivacyPolicyTapped: @escaping () -> Void,
        onTermsTapped: @escaping () -> Void,
        onProfileChanged: @escaping () -> Void = {}
    ) {
        self.settingsService = settingsService
        self.progressService = progressService
        self.playerName = playerName
        self.onBackTapped = onBackTapped
        self.onEditProfileTapped = onEditProfileTapped
        self.onCustomizeTapped = onCustomizeTapped
        self.onRestorePurchasesTapped = onRestorePurchasesTapped
        self.onRemoveAdsTapped = onRemoveAdsTapped
        self.onContactSupportTapped = onContactSupportTapped
        self.onRateAppTapped = onRateAppTapped
        self.onPrivacyPolicyTapped = onPrivacyPolicyTapped
        self.onTermsTapped = onTermsTapped
        self.onProfileChanged = onProfileChanged
    }

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(spacing: 16) {
                TRSettingsHeader(onBackTapped: onBackTapped)
                    .padding(.top, 10)

                playerSection
                audioSection
                gameplaySection
                notificationsSection
                purchasesSection
                dataSection
                supportSection
                aboutSection
                    .padding(.bottom, 18)
            }
            .frame(maxWidth: 760)
            .frame(maxWidth: .infinity)
            .padding(.horizontal, 20)
            .padding(.top, 4)
            .padding(.bottom, 30)
        }
        .background {
            LinearGradient(
                colors: [
                    Color.white.opacity(0.24),
                    Color(red: 0.69, green: 0.89, blue: 0.80).opacity(0.12)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()
        }
        .alert(item: $activeAlert) { alert in
            makeAlert(alert)
        }
        .simultaneousGesture(edgeSwipeBackGesture)
    }

    private var settings: UserSettings {
        settingsService.settings
    }

    private var edgeSwipeBackGesture: some Gesture {
        DragGesture(minimumDistance: 18, coordinateSpace: .local)
            .onEnded { value in
                guard TREdgeSwipeBackPolicy.shouldTriggerBack(
                    startLocation: value.startLocation,
                    translation: value.translation,
                    predictedEndTranslation: value.predictedEndTranslation
                ) else {
                    return
                }

                onBackTapped()
            }
    }

    private var playerSection: some View {
        TRSettingsSectionCard(title: "Player") {
            TRSettingsRow(
                title: "Player Profile",
                subtitle: "Current driver name",
                iconSystemName: "person.crop.circle.fill",
                trailingText: playerName,
                action: showEditProfilePlaceholder
            )

            TRSettingsRow(
                title: "Edit Profile",
                subtitle: "Name and avatar options",
                iconSystemName: "pencil.circle.fill",
                action: showEditProfilePlaceholder
            )

            TRSettingsRow(
                title: "Customize Route",
                subtitle: "Open shop themes and cosmetics",
                iconSystemName: "paintpalette.fill",
                action: onCustomizeTapped
            )
        }
    }

    private var audioSection: some View {
        TRSettingsSectionCard(title: "Audio & Haptics") {
            TRSettingsToggleRow(
                title: "Music",
                subtitle: "Background soundtrack",
                iconSystemName: "music.note",
                isOn: settings.isMusicEnabled,
                onChanged: settingsService.setMusicEnabled
            )

            TRSettingsSliderRow(
                title: "Music Volume",
                iconSystemName: "speaker.wave.2.fill",
                value: settings.musicVolume,
                isEnabled: settings.isMusicEnabled,
                onChanged: settingsService.setMusicVolume
            )

            TRSettingsToggleRow(
                title: "Sound Effects",
                subtitle: "Taps, pickups, and results",
                iconSystemName: "speaker.wave.3.fill",
                isOn: settings.areSoundEffectsEnabled,
                onChanged: settingsService.setSoundEffectsEnabled
            )

            TRSettingsSliderRow(
                title: "SFX Volume",
                iconSystemName: "slider.horizontal.3",
                value: settings.soundEffectsVolume,
                isEnabled: settings.areSoundEffectsEnabled,
                onChanged: settingsService.setSoundEffectsVolume
            )

            TRSettingsToggleRow(
                title: "Haptics",
                subtitle: "Light feedback for game actions",
                iconSystemName: "iphone.radiowaves.left.and.right",
                isOn: settings.areHapticsEnabled,
                onChanged: settingsService.setHapticsEnabled
            )
        }
    }

    private var gameplaySection: some View {
        TRSettingsSectionCard(title: "Gameplay") {
            TRSettingsToggleRow(
                title: "Tutorial Tips",
                subtitle: "Show help on early puzzles",
                iconSystemName: "lightbulb.fill",
                isOn: settings.showsTutorialTips,
                onChanged: settingsService.setShowsTutorialTips
            )

            TRSettingsToggleRow(
                title: "Route Hints",
                subtitle: "Show beginner route help",
                iconSystemName: "signpost.right.fill",
                isOn: settings.showsRouteHints,
                onChanged: settingsService.setShowsRouteHints
            )

            TRSettingsToggleRow(
                title: "Reduce Animations",
                subtitle: "Keep extra motion subtle",
                iconSystemName: "sparkles",
                isOn: settings.reducesExtraAnimations,
                onChanged: settingsService.setReducesExtraAnimations
            )

            TRSettingsToggleRow(
                title: "Confirm Restart",
                subtitle: "Ask before restarting a route",
                iconSystemName: "arrow.counterclockwise.circle.fill",
                isOn: settings.confirmsBeforeRestarting,
                onChanged: settingsService.setConfirmsBeforeRestarting
            )
        }
    }

    private var notificationsSection: some View {
        TRSettingsSectionCard(
            title: "Notifications",
            subtitle: "Preferences are saved now; permission prompts will wait for scheduling support."
        ) {
            TRSettingsToggleRow(
                title: "Daily Route Reminder",
                subtitle: "Save a preferred daily reminder",
                iconSystemName: "bell.fill",
                isOn: settings.isDailyReminderEnabled,
                onChanged: { isEnabled in
                    settingsService.setDailyReminderEnabled(isEnabled)
                    activeAlert = .notificationsComingSoon
                }
            )

            TRSettingsRow(
                title: "Reminder Time",
                subtitle: "Preferred notification time",
                iconSystemName: "clock.fill",
                trailingText: formattedReminderTime,
                action: {
                    activeAlert = .notificationsComingSoon
                }
            )
        }
    }

    private var purchasesSection: some View {
        TRSettingsSectionCard(title: "Purchases & Ads") {
            TRSettingsRow(
                title: "Remove Ads",
                subtitle: "Manage the future ad-free upgrade",
                iconSystemName: "nosign",
                action: {
                    onRemoveAdsTapped()
                    activeAlert = .removeAdsComingSoon
                }
            )

            TRSettingsRow(
                title: "Restore Purchases",
                subtitle: "Recover purchases on this device",
                iconSystemName: "receipt.fill",
                action: {
                    onRestorePurchasesTapped()
                    activeAlert = .restorePurchasesComingSoon
                }
            )
        }
    }

    private var dataSection: some View {
        TRSettingsSectionCard(title: "Data") {
            TRSettingsDangerRow(
                title: "Reset Progress",
                subtitle: "Clear local level progress",
                iconSystemName: "exclamationmark.triangle.fill",
                action: {
                    activeAlert = .resetProgressConfirmation
                }
            )

            TRSettingsDangerRow(
                title: "Reset Settings",
                subtitle: "Restore preferences to defaults",
                iconSystemName: "arrow.counterclockwise.circle.fill",
                action: {
                    activeAlert = .resetSettingsConfirmation
                }
            )
        }
    }

    private var supportSection: some View {
        TRSettingsSectionCard(title: "Support & Legal") {
            TRSettingsRow(
                title: "Contact Support",
                iconSystemName: "envelope.fill",
                action: {
                    onContactSupportTapped()
                    activeAlert = .contactSupportComingSoon
                }
            )

            TRSettingsRow(
                title: "Rate Tiny Routes",
                iconSystemName: "star.fill",
                action: {
                    onRateAppTapped()
                    activeAlert = .rateAppComingSoon
                }
            )

            TRSettingsRow(
                title: "Privacy Policy",
                iconSystemName: "lock.shield.fill",
                action: {
                    onPrivacyPolicyTapped()
                    activeAlert = .privacyPolicyComingSoon
                }
            )

            TRSettingsRow(
                title: "Terms of Use",
                iconSystemName: "doc.text.fill",
                action: {
                    onTermsTapped()
                    activeAlert = .termsComingSoon
                }
            )
        }
    }

    private var aboutSection: some View {
        TRSettingsSectionCard(title: "About") {
            settingsInfoRow(
                title: "App Version",
                value: appVersionText,
                iconSystemName: "info.circle.fill"
            )

            TRSettingsRow(
                title: "Credits",
                iconSystemName: "heart.fill",
                action: {
                    activeAlert = .credits
                }
            )

            #if DEBUG
            settingsInfoRow(
                title: "Build Configuration",
                value: "Debug",
                iconSystemName: "hammer.fill"
            )
            #endif
        }
    }

    private func settingsInfoRow(
        title: String,
        value: String,
        iconSystemName: String
    ) -> some View {
        HStack(spacing: 12) {
            TRSettingsIconCircle(
                systemName: iconSystemName,
                tint: TRGameplayStyle.Colors.primaryBlue
            )

            Text(title)
                .font(.system(size: 16, weight: .black, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.titleNavy)
                .lineLimit(1)
                .minimumScaleFactor(0.76)

            Spacer(minLength: 8)

            Text(value)
                .font(.system(size: 15, weight: .bold, design: .rounded))
                .foregroundStyle(TRGameplayStyle.Colors.secondaryText)
                .lineLimit(1)
                .minimumScaleFactor(0.72)
                .accessibilityHidden(true)
        }
        .frame(maxWidth: .infinity, minHeight: 54, alignment: .leading)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("\(title), \(value)"))
    }

    private var formattedReminderTime: String {
        let hour = settings.dailyReminderHour
        let minute = settings.dailyReminderMinute
        let period = hour < 12 ? "AM" : "PM"
        let displayHour = hour % 12 == 0 ? 12 : hour % 12

        return "\(displayHour):\(String(format: "%02d", minute)) \(period)"
    }

    private var appVersionText: String {
        let infoDictionary = Bundle.main.infoDictionary
        let version = infoDictionary?["CFBundleShortVersionString"] as? String
        let build = infoDictionary?["CFBundleVersion"] as? String

        switch (version?.isEmpty == false ? version : nil, build?.isEmpty == false ? build : nil) {
        case let (version?, build?):
            return "Version \(version) (\(build))"
        case let (version?, nil):
            return "Version \(version)"
        default:
            return "Version Unknown"
        }
    }

    private func showEditProfilePlaceholder() {
        onEditProfileTapped()
        activeAlert = .editProfileComingSoon
    }

    private func resetProgress() {
        progressService.resetProgress()
        onProfileChanged()
        activeAlert = .resetProgressComplete
    }

    private func resetSettings() {
        settingsService.resetToDefaults()
    }

    private func makeAlert(_ alert: SettingsAlert) -> Alert {
        switch alert {
        case .resetProgressConfirmation:
            return Alert(
                title: Text("Reset Progress?"),
                message: Text("This clears level stars, completions, and unlocks. Coins and owned cosmetics are kept."),
                primaryButton: .destructive(Text("Reset"), action: resetProgress),
                secondaryButton: .cancel()
            )

        case .resetSettingsConfirmation:
            return Alert(
                title: Text("Reset Settings?"),
                message: Text("This restores preferences to defaults."),
                primaryButton: .destructive(Text("Reset"), action: resetSettings),
                secondaryButton: .cancel()
            )

        default:
            return Alert(
                title: Text(alert.title),
                message: Text(alert.message),
                dismissButton: .default(Text("OK"))
            )
        }
    }
}

private enum SettingsAlert: Identifiable {
    case editProfileComingSoon
    case notificationsComingSoon
    case restorePurchasesComingSoon
    case removeAdsComingSoon
    case contactSupportComingSoon
    case rateAppComingSoon
    case privacyPolicyComingSoon
    case termsComingSoon
    case credits
    case resetProgressConfirmation
    case resetProgressComplete
    case resetSettingsConfirmation

    var id: String {
        title
    }

    var title: String {
        switch self {
        case .editProfileComingSoon:
            "Edit Profile"
        case .notificationsComingSoon:
            "Notifications"
        case .restorePurchasesComingSoon:
            "Restore Purchases"
        case .removeAdsComingSoon:
            "Remove Ads"
        case .contactSupportComingSoon:
            "Contact Support"
        case .rateAppComingSoon:
            "Rate Tiny Routes"
        case .privacyPolicyComingSoon:
            "Privacy Policy"
        case .termsComingSoon:
            "Terms of Use"
        case .credits:
            "Credits"
        case .resetProgressConfirmation:
            "Reset Progress?"
        case .resetProgressComplete:
            "Progress Reset"
        case .resetSettingsConfirmation:
            "Reset Settings?"
        }
    }

    var message: String {
        switch self {
        case .editProfileComingSoon:
            "Profile editing coming soon."
        case .notificationsComingSoon:
            "Reminder settings are saved. Scheduling will be connected later."
        case .restorePurchasesComingSoon:
            "StoreKit restore support will be connected later."
        case .removeAdsComingSoon:
            "The ad-free upgrade will be connected later."
        case .contactSupportComingSoon:
            "Support contact details will be added before launch."
        case .rateAppComingSoon:
            "App Store ratings will be connected before launch."
        case .privacyPolicyComingSoon:
            "The final privacy policy link will be added before launch."
        case .termsComingSoon:
            "The final terms link will be added before launch."
        case .credits:
            "Tiny Routes is built as a small delivery puzzle game. More credits are coming soon."
        case .resetProgressComplete:
            "Local level progress was cleared. Coins and owned cosmetics were kept."
        case .resetProgressConfirmation, .resetSettingsConfirmation:
            ""
        }
    }
}

struct SettingsScreen_Previews: PreviewProvider {
    @MainActor
    static var previews: some View {
        ZStack {
            SpriteImage(name: "background")
                .scaledToFill()
                .ignoresSafeArea()

            SettingsScreen(
                settingsService: UserSettingsService(),
                progressService: ProgressService(),
                onBackTapped: {},
                onEditProfileTapped: {},
                onCustomizeTapped: {},
                onRestorePurchasesTapped: {},
                onRemoveAdsTapped: {},
                onContactSupportTapped: {},
                onRateAppTapped: {},
                onPrivacyPolicyTapped: {},
                onTermsTapped: {}
            )
        }
    }
}
