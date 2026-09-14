import Foundation

struct License: Codable {
    let machine_id: String
    let expiry: String
    let can_print: Bool
    
    var isValid: Bool {
        if machine_id != MachineID.get() { return false }
        if expiry != "PERMANENT" {
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd"
            if let expDate = formatter.date(from: expiry) {
                if Date() > expDate { return false }
            } else {
                return false
            }
        }
        return true
    }
}
