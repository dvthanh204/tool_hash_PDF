import SwiftUI

struct MainView: View {
    @State private var pdfs: [ArchivedPDF] = []
    @State private var selectedPDF: ArchivedPDF?
    @State private var isBanned = false
    
    var body: some View {
        HStack(spacing: 0) {
            // Sidebar Menu
            List(pdfs, id: \.name, selection: $selectedPDF) { pdf in
                Text(pdf.name)
                    .tag(pdf)
            }
            .listStyle(SidebarListStyle())
            .frame(width: 200)
            
            // Content
            if isBanned {
                VStack {
                    Image(systemName: "xmark.octagon.fill")
                        .resizable().frame(width: 100, height: 100).foregroundColor(.red)
                    Text("Thiết bị này đã bị Admin khóa quyền truy cập!")
                        .font(.title).padding()
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                if let pdf = selectedPDF {
                    ProtectedPDFViewer(pdfData: pdf.data)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    Text("Vui lòng chọn PDF ở menu bên trái")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
        }
        .onAppear {
            loadBundleData()
        }
    }
    
    func loadBundleData() {
        guard let url = Bundle.main.url(forResource: "tailieu", withExtension: "khoa") else {
            print("Không tìm thấy file tailieu.khoa")
            return
        }
        
        do {
            let encryptedData = try Data(contentsOf: url)
            if let decryptedZip = CryptoManager.decryptPayload(data: encryptedData) {
                let archiveData = ArchiveManager.extractInMemory(zipData: decryptedZip)
                let myMid = MachineID.get()
                
                if archiveData.revocations.contains(myMid) {
                    self.isBanned = true
                } else {
                    self.pdfs = archiveData.pdfs
                    self.selectedPDF = archiveData.pdfs.first
                }
            }
        } catch {
            print("Lỗi đọc file bundle: \(error)")
        }
    }
}
