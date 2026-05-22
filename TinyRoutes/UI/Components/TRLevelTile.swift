import SwiftUI

enum TRLevelTileState {
    case completed
    case current
    case locked
}

struct TRLevelTile: View {
    static let size = CGSize(width: 50, height: 50)

    let levelNumber: Int
    let state: TRLevelTileState
    let stars: Int
    let action: () -> Void

    private let tileSize = Self.size

    var body: some View {
        Button(action: action) {
            VStack(spacing: 0) {
                Spacer(minLength: 0)
                Text("\(levelNumber)")
                    .font(.system(size: 20, weight: .bold, design: .rounded))
                    .foregroundStyle(numberColor)
                Spacer(minLength: 0)
                bottomContent
                    .frame(height: 10)
            }
            .padding(.vertical, 5)
            .frame(width: tileSize.width, height: tileSize.height)
            .background(tileFill)
            .overlay(alignment: .top) {
                if state == .completed {
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(
                            LinearGradient(
                                colors: [Color.white.opacity(0.35), Color.white.opacity(0)],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                        .frame(height: 18)
                        .allowsHitTesting(false)
                }
            }
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(Color.white, lineWidth: 6)
            )
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .shadow(
                color: shadowColor,
                radius: shadowRadius,
                x: 0,
                y: shadowYOffset
            )
            .overlay(alignment: .top) {
                if state == .current {
                    currentPin
                        .offset(y: -9)
                        .allowsHitTesting(false)
                }
            }
            .overlay(alignment: .topTrailing) {
                if state == .completed {
                    completedBadge
                        .offset(x: 6, y: -6)
                }
            }
        }
        .buttonStyle(.plain)
        .disabled(state == .locked)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("Level \(levelNumber)"))
        .accessibilityValue(Text(accessibilityValueDescription))
    }

    @ViewBuilder
    private var bottomContent: some View {
        if state == .locked {
            Image(systemName: "lock.fill")
                .font(.system(size: 8, weight: .semibold))
                .foregroundStyle(Color(red: 0.46, green: 0.53, blue: 0.63))
        } else if state == .completed {
            HStack(spacing: 2) {
                ForEach(0..<3, id: \.self) { index in
                    Image(systemName: "star.fill")
                        .font(.system(size: 6, weight: .semibold))
                        .foregroundStyle(Color(red: 1.0, green: 0.86, blue: 0.20).opacity(index < clampedStarCount ? 1.0 : 0.25))
                }
            }
            .accessibilityHidden(true)
        } else {
            HStack(spacing: 2) {
                ForEach(0..<3, id: \.self) { index in
                    Image(systemName: index < clampedStarCount ? "star.fill" : "star")
                        .font(.system(size: 6, weight: .semibold))
                        .foregroundStyle(
                            index < clampedStarCount
                                ? Color(red: 1.0, green: 0.86, blue: 0.20)
                                : Color(red: 1.0, green: 0.90, blue: 0.60).opacity(0.35)
                        )
                }
            }
            .accessibilityHidden(true)
        }
    }

    private var tileFill: some ShapeStyle {
        switch state {
        case .completed:
            LinearGradient(colors: [Color(red: 0.16, green: 0.72, blue: 0.60), Color(red: 0.11, green: 0.58, blue: 0.48)], startPoint: .top, endPoint: .bottom)
        case .current:
            LinearGradient(colors: [Color(red: 0.26, green: 0.58, blue: 0.98), Color(red: 0.18, green: 0.43, blue: 0.92)], startPoint: .top, endPoint: .bottom)
        case .locked:
            LinearGradient(colors: [Color(red: 0.95, green: 0.97, blue: 1.0), Color(red: 0.88, green: 0.91, blue: 0.96)], startPoint: .top, endPoint: .bottom)
        }
    }

    private var numberColor: Color {
        state == .locked ? Color(red: 0.44, green: 0.50, blue: 0.60) : .white
    }

    private var completedBadge: some View {
        ZStack {
            Circle()
                .fill(Color.white)
                .frame(width: 16, height: 16)
            Circle()
                .fill(Color(red: 0.20, green: 0.74, blue: 0.50))
                .frame(width: 13, height: 13)
            Image(systemName: "checkmark")
                .font(.system(size: 7, weight: .bold))
                .foregroundStyle(.white)
        }
        .accessibilityHidden(true)
    }

    private var currentPin: some View {
        Image(systemName: "mappin.circle.fill")
            .font(.system(size: 13, weight: .bold))
            .foregroundStyle(.white, Color(red: 0.19, green: 0.48, blue: 0.98))
            .accessibilityHidden(true)
    }

    private var shadowColor: Color {
        switch state {
        case .completed:
            Color(red: 0.10, green: 0.42, blue: 0.34).opacity(0.35)
        case .current:
            Color(red: 0.16, green: 0.40, blue: 0.98).opacity(0.45)
        case .locked:
            Color.black.opacity(0.10)
        }
    }

    private var shadowRadius: CGFloat {
        switch state {
        case .completed:
            9
        case .current:
            10
        case .locked:
            3
        }
    }

    private var shadowYOffset: CGFloat {
        switch state {
        case .completed:
            5
        case .current:
            6
        case .locked:
            1
        }
    }

    private var accessibilityStateDescription: String {
        switch state {
        case .completed:
            "Completed"
        case .current:
            "Current"
        case .locked:
            "Locked"
        }
    }

    private var clampedStarCount: Int {
        min(max(stars, 0), 3)
    }

    private var starCountDescription: String {
        let starCount = clampedStarCount
        return starCount == 1 ? "1 star" : "\(starCount) stars"
    }

    private var accessibilityValueDescription: String {
        guard state != .locked else {
            return accessibilityStateDescription
        }
        return "\(accessibilityStateDescription), \(starCountDescription)"
    }
}

#Preview("Level Tile States") {
    HStack(spacing: 16) {
        TRLevelTile(levelNumber: 1, state: .completed, stars: 3, action: {})
        TRLevelTile(levelNumber: 2, state: .current, stars: 2, action: {})
        TRLevelTile(levelNumber: 3, state: .locked, stars: 0, action: {})
    }
    .padding()
    .background(Color(red: 0.93, green: 0.96, blue: 1.0))
}
