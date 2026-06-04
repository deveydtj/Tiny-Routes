import SwiftUI

enum TRGameplayStyle {
    enum Colors {
        static let titleNavy = Color(red: 0.05, green: 0.18, blue: 0.43)
        static let primaryBlue = Color(red: 0.08, green: 0.50, blue: 0.96)
        static let roadShadow = Color.black.opacity(0.20)
        static let roadEdge = Color(red: 0.22, green: 0.30, blue: 0.46)
        static let roadFill = Color(red: 0.35, green: 0.45, blue: 0.62)
        static let roadHighlight = Color.white.opacity(0.22)
        static let cardWhite = Color.white.opacity(0.90)
        static let markerStroke = Color(red: 0.45, green: 0.55, blue: 0.72).opacity(0.65)
        static let orangeAccent = Color(red: 1.00, green: 0.55, blue: 0.16)
        static let successGreen = Color(red: 0.18, green: 0.68, blue: 0.45)
        static let secondaryText = Color(red: 0.34, green: 0.42, blue: 0.55)
        static let resultFailureRed = Color(red: 0.94, green: 0.22, blue: 0.23)
        static let resultWarningOrange = Color(red: 1.00, green: 0.48, blue: 0.18)
        static let resultGold = Color(red: 1.00, green: 0.76, blue: 0.18)
        static let resultEmptyStar = Color(red: 0.91, green: 0.94, blue: 0.98)
        static let resultCardStroke = Color.white.opacity(0.74)
        static let resultSoftYellow = Color(red: 1.00, green: 0.93, blue: 0.58)
    }

    enum Metrics {
        static let crispWhiteRimWidth: CGFloat = 6
        static let boardPadding: CGFloat = 64
        static let minimumReadableCoordinateScale: CGFloat = 96
        static let cameraSafeMarginWorld: Double = 0.36
        static let largeLevelPreviewHeightThreshold: Double = 2.75
        static let levelPreviewDurationNanoseconds: UInt64 = 1_400_000_000
        static let switchNodeSize: CGFloat = 52
        static let switchCircleSize: CGFloat = 42
        static let playerOuterSize: CGFloat = 52
        static let playerWhiteRimWidth: CGFloat = crispWhiteRimWidth
        static let playerScale: CGFloat = 0.5625
        static var playerCoreSize: CGFloat {
            max(playerOuterSize - (playerWhiteRimWidth * 2), .zero)
        }
        static let packageMarkerSize: CGFloat = 74
        static let collectedPackageMarkerSize: CGFloat = 44
        static let markerIconSize: CGFloat = 42
        static let roadOuterWidth: CGFloat = 20
        static let roadInnerWidth: CGFloat = 15
        static let roadHighlightWidth: CGFloat = 3
        static let resultCardCornerRadius: CGFloat = 30
        static let resultPrimaryButtonHeight: CGFloat = 58
        static let resultSecondaryButtonHeight: CGFloat = 50
        static let resultStatusBadgeSize: CGFloat = 74
        static let resultLargeStarSize: CGFloat = 58
    }
}
