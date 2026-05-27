import CoreGraphics

struct TREdgeSwipeBackPolicy {
    static let edgeActivationWidth: CGFloat = 32
    static let minimumHorizontalTranslation: CGFloat = 64
    static let minimumPredictedHorizontalTranslation: CGFloat = 96
    static let maximumVerticalDrift: CGFloat = 72

    static func shouldTriggerBack(
        startLocation: CGPoint,
        translation: CGSize,
        predictedEndTranslation: CGSize
    ) -> Bool {
        guard startLocation.x <= edgeActivationWidth else { return false }

        let hasEnoughRightwardMovement = translation.width >= minimumHorizontalTranslation
            || predictedEndTranslation.width >= minimumPredictedHorizontalTranslation
        guard hasEnoughRightwardMovement else { return false }

        guard translation.width > 0 else { return false }
        guard abs(translation.height) <= maximumVerticalDrift else { return false }
        guard abs(translation.width) > abs(translation.height) else { return false }

        return true
    }
}
