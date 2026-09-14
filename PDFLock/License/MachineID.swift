import Foundation
import CryptoKit

struct MachineID {
    static func get() -> String {
        let task = Process()
        task.launchPath = "/usr/sbin/ioreg"
        task.arguments = ["-rd1", "-c", "IOPlatformExpertDevice"]
        
        let pipe = Pipe()
        task.standardOutput = pipe
        task.launch()
        task.waitUntilExit()
        
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        if let output = String(data: data, encoding: .utf8) {
            let lines = output.components(separatedBy: .newlines)
            for line in lines {
                if line.contains("IOPlatformUUID") {
                    let parts = line.components(separatedBy: "\"")
                    if parts.count >= 4 {
                        let uuid = parts[3]
                        let hash = SHA256.hash(data: Data(uuid.utf8))
                        let hashString = hash.compactMap { String(format: "%02x", $0.byte) }.joined()
                        return "MAC-" + String(hashString.prefix(10)).uppercased()
                    }
                }
            }
        }
        return "UNKNOWN-MAC-ID"
    }
}

extension UInt8 {
    var byte: UInt8 { return self }
}
