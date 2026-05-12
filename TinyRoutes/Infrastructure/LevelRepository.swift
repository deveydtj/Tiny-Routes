import Foundation

/// Errors produced when loading a level from the bundle.
enum LevelRepositoryError: Error, LocalizedError {
    case fileNotFound(id: String)
    case decodingFailed(id: String, underlying: Error)

    var errorDescription: String? {
        switch self {
        case let .fileNotFound(id):
            return "Level file not found in bundle for id '\(id)'."
        case let .decodingFailed(id, underlying):
            return "Failed to decode level '\(id)': \(underlying.localizedDescription)"
        }
    }
}

/// Loads level data from bundled JSON files.
final class LevelRepository {
    private let bundle: Bundle
    private let decoder: JSONDecoder

    init(bundle: Bundle = .main) {
        self.bundle = bundle
        self.decoder = JSONDecoder()
    }

    /// Loads and decodes a single level by its ID.
    /// - Parameter id: The level identifier, matching the JSON filename (e.g. "level_001").
    /// - Returns: The decoded `LevelData`.
    /// - Throws: `LevelRepositoryError.fileNotFound` or `LevelRepositoryError.decodingFailed`.
    func loadLevel(id: String) throws -> LevelData {
        guard let url = bundle.url(forResource: id, withExtension: "json", subdirectory: "Levels") else {
            throw LevelRepositoryError.fileNotFound(id: id)
        }
        do {
            let data = try Data(contentsOf: url)
            return try decoder.decode(LevelData.self, from: data)
        } catch {
            throw LevelRepositoryError.decodingFailed(id: id, underlying: error)
        }
    }
}
