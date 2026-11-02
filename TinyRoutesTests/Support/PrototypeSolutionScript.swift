import Foundation

struct PrototypeSolutionScript: Decodable {
    struct LiveTap: Decodable {
        let atTime: TimeInterval
        let nodeID: String
    }

    let planTaps: [String]
    let liveTaps: [LiveTap]

    init(planTaps: [String] = [], liveTaps: [LiveTap] = []) {
        self.planTaps = planTaps
        self.liveTaps = liveTaps
    }

    private enum CodingKeys: String, CodingKey {
        case planTaps, liveTaps
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        planTaps = try container.decode([String].self, forKey: .planTaps)
        liveTaps = try container.decodeIfPresent([LiveTap].self, forKey: .liveTaps) ?? []
    }

    static func load(levelID: String, bundle: Bundle = Bundle(for: PrototypeSolutionBundleMarker.self)) throws -> Self {
        let filename = "\(levelID).solution.json"
        guard let url = bundle.url(forResource: "\(levelID).solution", withExtension: "json",
                                   subdirectory: "PrototypeSolutions") else {
            throw PrototypeSolutionError("\(levelID): missing solution file PrototypeSolutions/\(filename)")
        }
        do {
            return try JSONDecoder().decode(Self.self, from: Data(contentsOf: url))
        } catch {
            throw PrototypeSolutionError("\(levelID): could not read/decode \(filename): \(error)")
        }
    }
}

private final class PrototypeSolutionBundleMarker {}

struct PrototypeSolutionError: Error, LocalizedError {
    let message: String

    init(_ message: String) { self.message = message }

    var errorDescription: String? { message }
}
