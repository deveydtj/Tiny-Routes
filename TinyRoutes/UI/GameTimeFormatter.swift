import Foundation

enum GameTimeFormatter {
    static func countdown(_ timeInterval: TimeInterval?) -> String {
        formattedClock(timeInterval)
    }

    static func elapsed(_ timeInterval: TimeInterval?) -> String {
        formattedClock(timeInterval)
    }

    private static func formattedClock(_ timeInterval: TimeInterval?) -> String {
        guard let timeInterval else {
            return "--:--.-"
        }

        let clamped = max(timeInterval, 0)
        let wholeSeconds = Int(clamped)
        let minutes = wholeSeconds / 60
        let seconds = wholeSeconds % 60
        let tenths = Int((clamped * 10).rounded(.down)) % 10
        return "\(minutes):\(String(format: "%02d", seconds)).\(tenths)"
    }
}
