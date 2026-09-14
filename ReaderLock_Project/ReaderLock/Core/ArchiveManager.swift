import Foundation

struct ArchivedPDF: Hashable {
    let name: String
    let data: Data
}

struct ArchiveManager {
    static func extractInMemory(zipData: Data) -> (pdfs: [ArchivedPDF], revocations: [String: Int]) {
        var pdfs: [ArchivedPDF] = []
        var revocations: [String: Int] = [:]
        
        guard let archive = try? Archive(data: zipData, accessMode: .read) else {
            return (pdfs, revocations)
        }
        
        for entry in archive {
            var entryData = Data()
            do {
                _ = try archive.extract(entry) { data in
                    entryData.append(data)
                }
                
                if entry.path == "revocations.json" {
                    if let revDict = try? JSONDecoder().decode([String: Int].self, from: entryData) {
                        revocations = revDict
                    }
                } else if entry.path.hasSuffix(".pdf") {
                    pdfs.append(ArchivedPDF(name: entry.path, data: entryData))
                }
            } catch {
                print("Lỗi giải nén: \(error)")
            }
        }
        
        return (pdfs, revocations)
    }
}
