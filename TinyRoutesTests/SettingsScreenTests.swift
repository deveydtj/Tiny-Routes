import SwiftUI
import XCTest
@testable import TinyRoutes

final class SettingsScreenTests: XCTestCase {
    @MainActor
    func testSettingsScreenCanBeConstructedWithInjectedServices() {
        let screen = SettingsScreen(
            settingsService: makeSettingsService(),
            progressService: ProgressService(userDefaults: makeDefaults()),
            playerName: "Player One",
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

        XCTAssertNotNil(screen)
    }

    @MainActor
    func testSettingsHeaderCanBeConstructed() {
        let header = TRSettingsHeader(onBackTapped: {})

        XCTAssertNotNil(header)
    }

    @MainActor
    func testSettingsSectionCardCanBeConstructed() {
        let card = TRSettingsSectionCard(title: "Player") {
            Text("Row")
        }

        XCTAssertNotNil(card)
    }

    @MainActor
    func testSettingsRowCanBeConstructed() {
        let row = TRSettingsRow(
            title: "Edit Profile",
            subtitle: "Coming soon",
            iconSystemName: "pencil.circle.fill",
            trailingText: "Player One",
            action: {}
        )

        XCTAssertNotNil(row)
    }

    @MainActor
    func testSettingsToggleRowCanBeConstructed() {
        let row = TRSettingsToggleRow(
            title: "Music",
            subtitle: "Background soundtrack",
            iconSystemName: "music.note",
            isOn: true,
            onChanged: { _ in }
        )

        XCTAssertNotNil(row)
    }

    @MainActor
    func testSettingsSliderRowCanBeConstructed() {
        let row = TRSettingsSliderRow(
            title: "Music Volume",
            iconSystemName: "speaker.wave.2.fill",
            value: 0.75,
            onChanged: { _ in }
        )

        XCTAssertNotNil(row)
    }

    @MainActor
    func testSettingsDangerRowCanBeConstructed() {
        let row = TRSettingsDangerRow(
            title: "Reset Progress",
            subtitle: "Clear local level stars",
            iconSystemName: "exclamationmark.triangle.fill",
            action: {}
        )

        XCTAssertNotNil(row)
    }

    @MainActor
    private func makeSettingsService() -> UserSettingsService {
        UserSettingsService(
            repository: UserSettingsRepository(
                userDefaults: makeDefaults(),
                storageKey: "userSettings.screen.test"
            )
        )
    }

    private func makeDefaults() -> UserDefaults {
        let suiteName = "SettingsScreenTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        addTeardownBlock {
            defaults.removePersistentDomain(forName: suiteName)
        }
        return defaults
    }
}
