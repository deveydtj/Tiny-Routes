import SwiftUI

struct TRGameplayCosmeticStyle {
    let loadout: GameplayCosmeticLoadout

    var roadEdgeColor: Color {
        loadout.routeTheme.accent.routeShadowColor
    }

    var roadFillColor: Color {
        loadout.routeTheme.accent.routeColor
    }

    var roadHighlightColor: Color {
        Color.white.opacity(0.28)
    }

    var roadShadowColor: Color {
        Color.black.opacity(0.20)
    }

    var boardOverlayGradient: LinearGradient {
        loadout.routeTheme.accent.backgroundGradient
    }

    var deliveryDotGradient: LinearGradient {
        TRDeliveryDotVisual.gradient(for: loadout.deliveryDot)
    }

    var trailColor: Color {
        loadout.trail.accent.routeColor
    }

    var destinationTintColor: Color {
        loadout.destination.accent.routeColor
    }
}
