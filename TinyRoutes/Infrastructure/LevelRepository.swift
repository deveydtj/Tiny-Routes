import Foundation

/// Errors produced when loading a level from the bundle.
enum LevelRepositoryError: Error, LocalizedError {
    case fileNotFound(id: String)
    case readFailed(id: String, underlying: Error)
    case decodingFailed(id: String, underlying: Error)

    var errorDescription: String? {
        switch self {
        case let .fileNotFound(id):
            return "Level file not found in bundle for id '\(id)'."
        case let .readFailed(id, underlying):
            return "Failed to read level file for '\(id)': \(underlying.localizedDescription)"
        case let .decodingFailed(id, underlying):
            return "Failed to decode level '\(id)': \(underlying.localizedDescription)"
        }
    }
}

/// Loads level data from bundled JSON files.
final class LevelRepository {
    private let urlResolver: (String) -> URL?
    private let allLevelURLs: () -> [URL]
    private let dataLoader: (URL) throws -> Data
    private let decoder: JSONDecoder

    /// Creates a repository that reads levels from a bundle.
    init(bundle: Bundle = .main) {
        let b = bundle
        self.urlResolver = { id in b.url(forResource: id, withExtension: "json", subdirectory: "Levels") }
        self.allLevelURLs = { b.urls(forResourcesWithExtension: "json", subdirectory: "Levels") ?? [] }
        self.dataLoader = { try Data(contentsOf: $0) }
        self.decoder = JSONDecoder()
    }

    /// Creates a repository with injectable dependencies, intended for testing.
    init(
        urlResolver: @escaping (String) -> URL?,
        dataLoader: @escaping (URL) throws -> Data,
        allLevelURLs: @escaping () -> [URL] = { [] }
    ) {
        self.urlResolver = urlResolver
        self.allLevelURLs = allLevelURLs
        self.dataLoader = dataLoader
        self.decoder = JSONDecoder()
    }

    /// Loads and decodes all bundled levels.
    /// - Returns: An array of decoded `LevelData` values, one per JSON file found in the bundle.
    /// - Throws: `LevelRepositoryError.readFailed` or `.decodingFailed` for the first level that cannot be loaded.
    func loadAllLevels() throws -> [LevelData] {
        let urls = allLevelURLs()
        var levels: [LevelData] = []
        for url in urls {
            let id = url.deletingPathExtension().lastPathComponent
            let data: Data
            do {
                data = try dataLoader(url)
            } catch {
                throw LevelRepositoryError.readFailed(id: id, underlying: error)
            }
            do {
                let level = try decoder.decode(LevelData.self, from: data)
                levels.append(level)
            } catch {
                throw LevelRepositoryError.decodingFailed(id: id, underlying: error)
            }
        }
        return levels
    }

    /// Loads and decodes a single level by its ID.
    /// - Parameter id: The level identifier, matching the JSON filename (e.g. "level_001").
    /// - Returns: The decoded `LevelData`.
    /// - Throws: `LevelRepositoryError.fileNotFound`, `.readFailed`, or `.decodingFailed`.
    func loadLevel(id: String) throws -> LevelData {
        guard let url = urlResolver(id) else {
            throw LevelRepositoryError.fileNotFound(id: id)
        }
        let data: Data
        do {
            data = try dataLoader(url)
        } catch {
            throw LevelRepositoryError.readFailed(id: id, underlying: error)
        }
        do {
            return try decoder.decode(LevelData.self, from: data)
        } catch {
            throw LevelRepositoryError.decodingFailed(id: id, underlying: error)
        }
    }
}
