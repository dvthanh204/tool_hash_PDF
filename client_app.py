import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import fitz  # PyMuPDF
import os
import sys
import subprocess
from cryptography.fernet import Fernet
import json
import base64
from datetime import datetime
import hashlib
import time
from PIL import Image, ImageTk

# Khóa Master (Cùng khóa với AdminApp)
MASTER_KEY = b'-hZzUf1Mkx1t0wM_hX2b6F4kS_J5LqZcQk9d-4S5X88='
fernet = Fernet(MASTER_KEY)

class ClientApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PDFLock Viewer - macOS")
        self.geometry("1000x800")
        ctk.set_appearance_mode("dark")
        
        self.doc = None
        self.current_page = 0
        self.license_info = None
        
        # 1. Lấy Machine ID bằng lệnh trên macOS
        self.machine_id = self.get_machine_id()
        
        # Setup UI
        self.setup_ui()
        
        # 2. Xóa Clipboard liên tục để chống Copy (chạy ngầm sau mỗi 1.5 giây)
        self.clear_clipboard()
        
        # 3. Thử ngăn chặn quay màn hình bằng hàm API hệ thống của macOS (AppKit)
        self.disable_screencapture()

        # 4. Bind các phím tắt theo chuẩn macOS (Command)
        self.bind("<Command-p>", self.cmd_print)
        self.bind("<Command-P>", self.cmd_print)
        self.bind("<Left>", self.prev_page)
        self.bind("<Right>", self.next_page)

    def get_machine_id(self):
        """ Lấy UUID phần cứng chuẩn cho máy Mac """
        try:
            # Ưu tiên dùng ioreg
            cmd = "ioreg -rd1 -c IOPlatformExpertDevice | awk '/IOPlatformUUID/ { split($0, line, \"\\\"\"); printf(\"%s\\n\", line[4]); }'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            uuid_str = result.stdout.strip()
            
            # Dự phòng bằng system_profiler
            if not uuid_str:
                cmd = "system_profiler SPHardwareDataType | grep 'Hardware UUID' | awk '{print $3}'"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                uuid_str = result.stdout.strip()
                
            if uuid_str:
                # Hash SHA256 lại cho bảo mật và định dạng hiển thị MAC-xxxx
                hash_str = hashlib.sha256(uuid_str.encode()).hexdigest()[:10].upper()
                return f"MAC-{hash_str}"
            return "UNKNOWN-MAC-ID"
        except Exception:
            return "UNKNOWN-MAC-ID"

    def clear_clipboard(self):
        """ Liên tục thực thi lệnh xóa bộ nhớ đệm (Clipboard) """
        try:
            subprocess.run('echo -n "" | pbcopy', shell=True)
        except:
            pass
        self.after(1500, self.clear_clipboard)

    def disable_screencapture(self):
        """ Dùng pyobjc can thiệp NSWindowSharingNone nhằm che giao diện khi chụp / quay màn hình """
        try:
            import objc
            from AppKit import NSApplication, NSWindow
            app = NSApplication.sharedApplication()
            for window in app.windows():
                if hasattr(window, 'setSharingType_'):
                    # NSWindowSharingNone = 0
                    window.setSharingType_(0)
        except ImportError:
            # Bỏ qua nếu ko cài pyobjc, không làm app crash
            pass
        except Exception:
            pass

    def setup_ui(self):
        self.top_frame = ctk.CTkFrame(self, height=50)
        self.top_frame.pack(fill="x", padx=10, pady=10)
        
        self.btn_open = ctk.CTkButton(self.top_frame, text="Mở File (.khoa)", command=self.open_file)
        self.btn_open.pack(side="left", padx=10)
        
        self.btn_key = ctk.CTkButton(self.top_frame, text="Nhập License Key", command=self.input_key, fg_color="orange")
        self.btn_key.pack(side="left", padx=10)
        
        self.btn_print = ctk.CTkButton(self.top_frame, text="In Bằng CUPS (Cmd+P)", command=self.cmd_print, fg_color="gray", state="disabled")
        self.btn_print.pack(side="left", padx=10)
        
        self.lbl_mid = ctk.CTkLabel(self.top_frame, text=f"Machine ID: {self.machine_id}", font=("Arial", 12, "bold"))
        self.lbl_mid.pack(side="right", padx=10)
        
        # Canvas hiển thị PDF
        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Thanh điều hướng
        self.bottom_frame = ctk.CTkFrame(self, height=40)
        self.bottom_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.btn_prev = ctk.CTkButton(self.bottom_frame, text="< Trang trước", command=self.prev_page, state="disabled")
        self.btn_prev.pack(side="left", padx=20)
        
        self.lbl_page = ctk.CTkLabel(self.bottom_frame, text="Trang: 0 / 0")
        self.lbl_page.pack(side="left", expand=True)
        
        self.btn_next = ctk.CTkButton(self.bottom_frame, text="Trang sau >", command=self.next_page, state="disabled")
        self.btn_next.pack(side="right", padx=20)

    def is_blacklisted(self):
        """ Kiểm tra xem file blacklist.json nằm chung folder có chứa máy này không """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if getattr(sys, 'frozen', False):
            # Nếu chạy bằng file execute được đóng gói thông thường (Pyinstaller)
            base_dir = os.path.dirname(sys.executable)
            
        bl_path = os.path.join(base_dir, "blacklist.json")
        if os.path.exists(bl_path):
            with open(bl_path, "r") as f:
                try:
                    bl = json.load(f)
                    if self.machine_id in bl:
                        return True
                except:
                    pass
        return False

    def input_key(self):
        if self.is_blacklisted():
            messagebox.showerror("Bị Chặn", "Máy Mác của bạn đã bị đưa vào danh sách đen (Blacklisted)!")
            sys.exit(0)
            return
            
        key_str = simpledialog.askstring("License Key", f"ID máy bạn: {self.machine_id}\nVui lòng nhập License Key được cấp:")
        if not key_str: return
        
        try:
            raw_key = base64.urlsafe_b64decode(key_str.strip())
            decrypted = fernet.decrypt(raw_key).decode('utf-8')
            license_data = json.loads(decrypted)
            
            if license_data.get("machine_id") != self.machine_id:
                messagebox.showerror("Lỗi Key", "License Key này không dành cho máy tính của bạn!")
                return
                
            expiry = license_data.get("expiry")
            if expiry != "PERMANENT":
                exp_date = datetime.strptime(expiry, "%Y-%m-%d")
                if datetime.now() > exp_date:
                    messagebox.showerror("Lỗi Key", "License Key đã hết hạn sử dụng!")
                    return
            
            self.license_info = license_data
            
            if self.license_info.get("can_print"):
                self.btn_print.configure(state="normal", fg_color="#1f538d")
                
            # Ghi lưu trữ ẩn .pdflock_key trên hệ thống user
            key_path = os.path.join(os.path.expanduser("~"), ".pdflock_key")
            with open(key_path, "w") as f:
                f.write(key_str)
                
            messagebox.showinfo("Thành công", "Kích hoạt bản quyền trên thiết bị thành công!")
        except Exception as e:
            messagebox.showerror("Lỗi", "License Key không hợp lệ hoặc bị hỏng!")

    def load_saved_key(self):
        key_path = os.path.join(os.path.expanduser("~"), ".pdflock_key")
        if os.path.exists(key_path):
            with open(key_path, "r") as f:
                saved_key = f.read().strip()
            try:
                raw_key = base64.urlsafe_b64decode(saved_key)
                decrypted = fernet.decrypt(raw_key).decode('utf-8')
                li = json.loads(decrypted)
                
                if li.get("machine_id") == self.machine_id:
                    expiry = li.get("expiry")
                    is_valid = True
                    if expiry != "PERMANENT":
                        exp_date = datetime.strptime(expiry, "%Y-%m-%d")
                        if datetime.now() > exp_date: is_valid = False
                    
                    if is_valid and not self.is_blacklisted():
                        self.license_info = li
                        if self.license_info.get("can_print"):
                            self.btn_print.configure(state="normal", fg_color="#1f538d")
            except Exception:
                pass

    def open_file(self):
        self.load_saved_key()
                
        if not self.license_info:
            messagebox.showwarning("Yêu cầu", "Vui lòng nhập License Key hợp lệ trước khi mở bất kỳ file nào.")
            return
            
        path = filedialog.askopenfilename(filetypes=[("PDFLock Files", "*.khoa")])
        if not path: return
        
        try:
            with open(path, "rb") as f:
                encrypted_data = f.read()
            decrypted_pdf_bytes = fernet.decrypt(encrypted_data)
            
            # Render hoàn toàn trong RAM
            self.doc = fitz.open(stream=decrypted_pdf_bytes, filetype="pdf")
            self.current_page = 0
            self.render_page()
            
            self.btn_next.configure(state="normal" if len(self.doc)>1 else "disabled")
            self.btn_prev.configure(state="disabled")
            
        except Exception as e:
            messagebox.showerror("Lỗi Mở File", "Không thể giải mã file. Tập tin có thể bị hỏng hoặc chưa được cấp quyền đúng.")

    def render_page(self):
        if not self.doc: return
        page = self.doc.load_page(self.current_page)
        
        # Việc render thành image sẽ chống bôi đen text khi xem
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Độ phân giải x2 cho rõ nét
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        
        # Chỉ mục giữa màn hình
        self.canvas.create_image(
            self.canvas.winfo_width()//2, 
            self.canvas.winfo_height()//2, 
            anchor="center", image=self.tk_img
        )
        self.lbl_page.configure(text=f"Trang: {self.current_page + 1} / {len(self.doc)}")

    def next_page(self, event=None):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.render_page()
            self.btn_prev.configure(state="normal")
            if self.current_page == len(self.doc) - 1:
                self.btn_next.configure(state="disabled")

    def prev_page(self, event=None):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.render_page()
            self.btn_next.configure(state="normal")
            if self.current_page == 0:
                self.btn_prev.configure(state="disabled")
                
    # --- Xử lý in ấn macOS an toàn (loại bỏ win32print/win32ui) ---

    def get_printers_macos(self):
        """ Lấy danh sách máy in, loại trừ ổ PDF ảo và Preview """
        try:
            cmd = "lpstat -p | awk '{print $2}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            printers = result.stdout.strip().split('\n')
            
            invalid_keywords = ["PDF", "Preview", "WebEx", "virtual"]
            valid_printers = []
            for p in printers:
                p_lower = p.lower()
                if p and not any(kw.lower() in p_lower for kw in invalid_keywords):
                    valid_printers.append(p)
            return valid_printers
        except Exception:
            return []

    def cmd_print(self, event=None):
        if not self.doc or not self.license_info: return
        if not self.license_info.get("can_print"):
            messagebox.showerror("Lỗi Phân Quyền", "Quyền cấp phép không cho phép bạn In tài liệu này!")
            return
            
        printers = self.get_printers_macos()
        if not printers:
            messagebox.showerror("Lỗi", "Không tìm thấy máy in thật nào trên hệ thống.")
            return
            
        # Modal chọn máy in
        print_window = tk.Toplevel(self)
        print_window.title("Chọn Máy In")
        print_window.geometry("350x200")
        # Đưa Toplevel lên trước
        print_window.attributes('-topmost', True)
        
        lbl = ctk.CTkLabel(print_window, text="Chọn máy in để tiếp tục:")
        lbl.pack(pady=10)
        
        printer_var = tk.StringVar(value=printers[0])
        opt_printers = ctk.CTkOptionMenu(print_window, values=printers, variable=printer_var)
        opt_printers.pack(pady=10)
        
        def do_print_job():
            selected = printer_var.get()
            print_window.destroy()
            self.execute_print(selected)
            
        btn = ctk.CTkButton(print_window, text="Xác nhận IN", command=do_print_job)
        btn.pack(pady=20)

    def execute_print(self, printer_name):
        # Trích xuất PDF dạng hình ảnh ngầm ra /tmp để gửi CUPS để tránh việc bị trích xuất nội dung vector (Text)
        tmp_name = f"/tmp/print_{int(time.time())}_{hashlib.md5(str(os.getpid()).encode()).hexdigest()[:6]}.pdf"
        try:
            # Tạo 1 file PDF sạch mới cứng
            img_pdf = fitz.open()
            
            # Từng trang biến thành Ảnh, sau đó chèn luôn vào trang của PDF tạm
            for i in range(len(self.doc)):
                page = self.doc.load_page(i)
                pix = page.get_pixmap(dpi=150) # DPI 150 đủ cho máy in cơ bản, tránh file quá nặng
                # Tạo trang trắng cùng kích thước
                new_page = img_pdf.new_page(width=page.rect.width, height=page.rect.height)
                # Dán ảnh (không hề chứa text vector) vào trang đó
                new_page.insert_image(new_page.rect, stream=pix.tobytes("png"))
                
            img_pdf.save(tmp_name)
            img_pdf.close()
            
            # Đẩy lệnh cho CUPS (hệ thống in ấn chuẩn của Unix/Mac)
            subprocess.run(["lp", "-d", printer_name, tmp_name])
            messagebox.showinfo("In Ấn", f"Đã gửi tài liệu ngầm tới máy in: {printer_name}\nLệnh in đã được chuyển đi thành công.")
        except Exception as e:
            messagebox.showerror("Lỗi In", f"Có lỗi xảy ra trong quá trình in ấn: {str(e)}")
        finally:
            # Sạch sẽ: Xóa tận gốc file tạm vừa tạo ra
            if os.path.exists(tmp_name):
                os.remove(tmp_name)

if __name__ == "__main__":
    app = ClientApp()
    app.mainloop()
