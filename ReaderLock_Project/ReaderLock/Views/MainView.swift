import SwiftUI

struct MainView: View {
    @State private var pdfs: [ArchivedPDF] = []
    @State private var selectedPDF: ArchivedPDF?
    @State private var isBanned = false
    @State private var banMessage = ""
    
    var body: some View {
        HStack(spacing: 0) {
            List(pdfs, id: \.name, selection: $selectedPDF) { pdf in
                Text(pdf.name).tag(pdf)
            }
            .listStyle(SidebarListStyle())
            .frame(width: 250)
            
            if isBanned {
                VStack {
                    Image(systemName: "hand.raised.slash.fill")
                        .resizable().frame(width: 100, height: 100).foregroundColor(.red)
                    Text("BẢN QUYỀN ĐÃ BỊ THU HỒI")
                        .font(.title).padding()
                    Text(banMessage)
                        .foregroundColor(.gray)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                if let pdf = selectedPDF {
                    ProtectedPDFViewer(pdfData: pdf.data)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    Text("Vui lòng chọn bài giảng bên trái").frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
        }
        .onAppear { loadBundleData() }
    }
    
    func loadBundleData() {
        guard let url = Bundle.main.url(forResource: "tailieu", withExtension: "khoa") else {
            return
        }
        do {
            let encryptedData = try Data(contentsOf: url)
            if let decryptedZip = CryptoManager.decryptPayload(data: encryptedData) {
                let archiveData = ArchiveManager.extractInMemory(zipData: decryptedZip)
                let myMid = MachineID.get()
                
                let savedVersion = UserDefaults.standard.integer(forKey: "LicenseVersion")
                if let bannedVersion = archiveData.revocations[myMid] {
                    if savedVersion <= bannedVersion {
                        UserDefaults.standard.removeObject(forKey: "LicenseKey")
                        self.banMessage = "Mật khẩu cho thiết bị này đã bị xóa và thu hồi."
                        self.isBanned = true
                        return
                    }
                }
                
                self.pdfs = archiveData.pdfs.sorted(by: { $0.name < $1.name })
                self.selectedPDF = self.pdfs.first
            }
        } catch { }
    }
}
