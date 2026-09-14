import Foundation
import IOKit
import CryptoKit

struct MachineID {
    static func get() -> String {
        var serialNumber: String = "DEFAULT_PC"
        let platformExpert = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("IOPlatformExpertDevice"))
        
        if platformExpert != 0 {
            if let serial = IORegistryEntryCreateCFProperty(platformExpert, kIOPlatformSerialNumberKey as CFString, kCFAllocatorDefault, 0)?.takeUnretainedValue() as? String {
                serialNumber = serial
            }
            IOObjectRelease(platformExpert)
        }
        
        let digest = Insecure.MD5.hash(data: Data(serialNumber.utf8))
        let hexString = digest.map { String(format: "%02x", $0) }.joined()
        
        return "MAC-" + String(hexString.prefix(12)).uppercased()
    }
}
