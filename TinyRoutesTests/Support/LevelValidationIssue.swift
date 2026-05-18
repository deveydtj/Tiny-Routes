struct LevelValidationIssue: Equatable {
    enum Severity: Equatable {
        case error
        case warning
    }

    let severity: Severity
    let levelID: String
    let message: String

    var displayText: String {
        "[\(severity.displayName.uppercased())] \(levelID): \(message)"
    }
}

private extension LevelValidationIssue.Severity {
    var displayName: String {
        switch self {
        case .error:
            return "error"
        case .warning:
            return "warning"
        }
    }
}
