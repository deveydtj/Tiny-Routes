import Foundation

/// Errors produced when loading a solution script from the test bundle.
enum LevelSolutionRepositoryError: Error, LocalizedError {
    case fileNotFound(levelID: String)
    case readFailed(levelID: String, underlying: Error)
    case decodingFailed(levelID: String, underlying: Error)

    var errorDescription: String? {
        switch self {
        case let .fileNotFound(levelID):
            return "Solution script not found for level '\(levelID)'. Expected file: \(levelID).solution.json in LevelSolutions/."
        case let .readFailed(levelID, underlying):
            return "Failed to read solution script for '\(levelID)': \(underlying.localizedDescription)"
        case let .decodingFailed(levelID, underlying):
            return "Failed to decode solution script for '\(levelID)': \(underlying.localizedDescription)"
        }
    }
}

/// Loads level solution scripts from the test bundle resources.
final class LevelSolutionRepository {
    private let bundle: Bundle
    private let decoder: JSONDecoder

    /// Creates a repository that reads solution scripts from a bundle.
    init(bundle: Bundle = Bundle(for: BundleSolutionMarker.self)) {
        self.bundle = bundle
        self.decoder = JSONDecoder()
    }

    /// Loads a single solution script by level ID.
    /// - Parameter levelID: The level identifier (e.g. "level_001").
    /// - Returns: The decoded `LevelSolutionScript`.
    /// - Throws: `LevelSolutionRepositoryError.fileNotFound`, `.readFailed`, or `.decodingFailed`.
    func loadScript(levelID: String) throws -> LevelSolutionScript {
        let filename = "\(levelID).solution"
        guard let url = bundle.url(forResource: filename, withExtension: "json", subdirectory: "LevelSolutions")
                ?? bundle.url(forResource: filename, withExtension: "json") else {
            throw LevelSolutionRepositoryError.fileNotFound(levelID: levelID)
        }
        let data: Data
        do {
            data = try Data(contentsOf: url)
        } catch {
            throw LevelSolutionRepositoryError.readFailed(levelID: levelID, underlying: error)
        }
        do {
            return try decoder.decode(LevelSolutionScript.self, from: data)
        } catch {
            throw LevelSolutionRepositoryError.decodingFailed(levelID: levelID, underlying: error)
        }
    }

    /// Loads all solution scripts found in the `LevelSolutions` bundle directory.
    /// - Returns: An array of decoded `LevelSolutionScript` values, sorted by `levelID`.
    /// - Throws: `LevelSolutionRepositoryError.readFailed` or `.decodingFailed` for the first script that cannot be loaded.
    func loadAllScripts() throws -> [LevelSolutionScript] {
        let urls = resolveAllScriptURLs()
        var scripts: [LevelSolutionScript] = []
        for url in urls {
            let rawName = url.deletingPathExtension().lastPathComponent
            let levelID = rawName.hasSuffix(".solution")
                ? String(rawName.dropLast(".solution".count))
                : rawName
            let data: Data
            do {
                data = try Data(contentsOf: url)
            } catch {
                throw LevelSolutionRepositoryError.readFailed(levelID: levelID, underlying: error)
            }
            do {
                let script = try decoder.decode(LevelSolutionScript.self, from: data)
                scripts.append(script)
            } catch {
                throw LevelSolutionRepositoryError.decodingFailed(levelID: levelID, underlying: error)
            }
        }
        return scripts.sorted { $0.levelID < $1.levelID }
    }

    // MARK: - Private

    private func resolveAllScriptURLs() -> [URL] {
        let subdirURLs = bundle.urls(forResourcesWithExtension: "json", subdirectory: "LevelSolutions") ?? []
        let rootURLs = bundle.urls(forResourcesWithExtension: "json", subdirectory: nil) ?? []
        let allURLs = subdirURLs + rootURLs
        let solutionURLs = allURLs.filter { $0.lastPathComponent.contains(".solution.") }
        var seen = Set<URL>()
        return solutionURLs.filter { seen.insert($0).inserted }
    }
}

private final class BundleSolutionMarker {}
