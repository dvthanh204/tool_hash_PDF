import Foundation
import IOKit

struct MachineID {
    static func get() -> String {
        var serialNumber: String = "UNKNOWN"
        let platformExpert = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("IOPlatformExpertDevice"))
        
        if platformExpert != 0 {
            if let serial = IORegistryEntryCreateCFProperty(platformExpert, kIOPlatformSerialNumberKey as CFString, kCFAllocatorDefault, 0)?.takeUnretainedValue() as? String {
                serialNumber = serial
            }
            IOObjectRelease(platformExpert)
        }
        return serialNumber
    }
}
