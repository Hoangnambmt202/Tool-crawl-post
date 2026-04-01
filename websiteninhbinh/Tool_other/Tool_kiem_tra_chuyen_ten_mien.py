import pandas as pd
import requests
import time
import os
import sys
from urllib.parse import urlparse
import urllib3
import concurrent.futures
import threading

# Tắt cảnh báo bảo mật SSL (Do nhiều web trường học SSL bị lỗi)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =====================================================================
# 1. KHỐI CẤU HÌNH (CONFIGURATION)
# =====================================================================
class Config:
    EXCEL_PATH = r"D:\D_Document\VS Code\Python\Thuc_tap\Tool_other\DS_tool_2b.xlsx"
    
    COL_URL = "Link trường"             # Cột chứa link gốc cần kiểm tra
    COL_RESULT = "Kiểm tra chuyển hướng"  # Cột MỚI sẽ được tạo ra để ghi kết quả
    
    TIMEOUT_SECONDS = 10  # Thời gian chờ tối đa cho 1 link (giây)
    
    # SỐ LUỒNG CHẠY CÙNG LÚC (Điều chỉnh tại đây)
    # Khuyến nghị: 5 đến 10. Chạy số lượng quá lớn (VD: 50) dễ bị máy chủ của Sở GD chặn IP vì tưởng DDoS
    MAX_THREADS = 10      

# =====================================================================
# 2. KHỐI QUẢN LÝ EXCEL (EXCEL MANAGER)
# =====================================================================
class ExcelManager:
    def __init__(self, path):
        self.path = path
        self.df = None
        # Khóa Lock để đảm bảo an toàn khi nhiều luồng cùng ghi file một lúc
        self.lock = threading.Lock()

    def load_data(self):
        """Đọc Excel và tự động thêm cột kết quả nếu chưa có"""
        if not os.path.exists(self.path):
            print(f"[!] LỖI: Không tìm thấy file Excel tại: {self.path}")
            return False

        try:
            self.df = pd.read_excel(self.path, engine='openpyxl')
            
            # Nếu chưa có cột kết quả, tự động tạo mới
            if Config.COL_RESULT not in self.df.columns:
                self.df[Config.COL_RESULT] = ""
            
            # Ép kiểu dữ liệu để tránh lỗi ô trống
            self.df[Config.COL_RESULT] = self.df[Config.COL_RESULT].fillna("").astype(str)
            return True
        except Exception as e:
            print(f"[!] Lỗi khi đọc Excel: {e}")
            return False

    def update_result(self, index, status):
        """Cập nhật trạng thái vào bộ nhớ (Có khóa Lock an toàn)"""
        with self.lock:
            self.df.at[index, Config.COL_RESULT] = status

    def save_safely(self):
        """Lưu Excel an toàn, chống văng tool nếu người dùng đang mở file (Có khóa Lock)"""
        with self.lock:
            while True:
                try:
                    self.df.to_excel(self.path, index=False)
                    break
                except PermissionError:
                    print(f"\n[CẢNH BÁO] File Excel đang mở! Vui lòng đóng file để tool lưu kết quả.")
                    time.sleep(3)

# =====================================================================
# 3. KHỐI KIỂM TRA CHUYỂN HƯỚNG (REDIRECT CHECKER)
# =====================================================================
class RedirectChecker:
    def __init__(self):
        # Giả lập làm trình duyệt Chrome thật để không bị web chặn
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        }

    def _get_base_domain(self, url):
        """Hàm phụ: Trích xuất tên miền cốt lõi (Bỏ http, https, www, và đường dẫn con)"""
        url = str(url).strip().lower()
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
            
        try:
            netloc = urlparse(url).netloc
            if netloc.startswith('www.'):
                netloc = netloc[4:]
            return netloc
        except:
            return url

    def check_url(self, original_url):
        """Hàm chính: Truy cập URL và xem nó có bị đẩy sang tên miền khác không"""
        if not original_url or str(original_url).lower() == 'nan':
            return "Bỏ qua (URL trống)"

        formatted_url = original_url if original_url.startswith(('http://', 'https://')) else f"http://{original_url}"
        
        try:
            # allow_redirects=True sẽ tự động lần theo các chuyển hướng 301/302 đến trang cuối cùng
            response = requests.get(
                formatted_url, 
                headers=self.headers, 
                timeout=Config.TIMEOUT_SECONDS,
                verify=False 
            )
            
            final_url = response.url
            
            old_domain = self._get_base_domain(original_url)
            new_domain = self._get_base_domain(final_url)
            
            if old_domain != new_domain:
                return f"Đã chuyển tên miền (-> {new_domain})"
            else:
                return "Không chuyển hướng"
                
        except requests.exceptions.Timeout:
            return "Lỗi: Web tải quá lâu (Timeout)"
        except requests.exceptions.ConnectionError:
            return "Lỗi: Không thể kết nối (Web chết hoặc sai link)"
        except Exception as e:
            return f"Lỗi không xác định: {str(e)[:50]}"

# =====================================================================
# 4. LUỒNG THỰC THI CHÍNH (XỬ LÝ ĐA LUỒNG)
# =====================================================================
def process_row(index, row, total_rows, checker, excel, print_lock):
    """Hàm xử lý độc lập cho từng luồng (Thread)"""
    
    # 1. Xử lý số thứ tự (STT) để không bị lỗi nan hoặc 107.0
    stt = row.get('STT')
    if pd.isna(stt) or str(stt).strip() == "":
        stt = index + 1 # Nếu trống, tự lấy STT dựa theo index hiện tại
    else:
        try:
            stt = int(float(stt)) # Chuyển "107.0" thành 107
        except:
            pass # Nếu STT chứa chữ, giữ nguyên

    # 2. Xử lý URL
    url = row.get(Config.COL_URL, "")
    
    if pd.isna(url) or str(url).strip() == "":
        with print_lock:
            print(f"[{stt}/{total_rows}] Bỏ qua (URL trống)")
        return

    # 3. Gọi kiểm tra
    result_text = checker.check_url(url)
    
    # 4. Ghi kết quả và in ra màn hình
    # Dùng print_lock để các luồng không in chữ đè lên nhau lộn xộn
    with print_lock:
        print(f"[{stt}/{total_rows}] {url} => {result_text}")
        
    excel.update_result(index, result_text)
    excel.save_safely()


def main():
    print("="*65)
    print("   TOOL KIỂM TRA CHUYỂN HƯỚNG TÊN MIỀN HÀNG LOẠT (ĐA LUỒNG)   ")
    print("="*65)
    
    excel = ExcelManager(Config.EXCEL_PATH)
    checker = RedirectChecker()
    print_lock = threading.Lock() # Khóa để text in ra không bị vỡ dòng
    
    print("[*] Đang đọc dữ liệu từ Excel...")
    if not excel.load_data():
        return
        
    total_rows = len(excel.df)
    print(f"[*] Tìm thấy {total_rows} dòng. Bắt đầu kiểm tra với {Config.MAX_THREADS} luồng...\n")
    
    # Chạy đa luồng bằng ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=Config.MAX_THREADS) as executor:
        # Gửi từng dòng cho các luồng thợ (workers) xử lý
        futures = []
        for index, row in excel.df.iterrows():
            futures.append(
                executor.submit(process_row, index, row, total_rows, checker, excel, print_lock)
            )
            
        # Chờ tất cả hoàn thành
        concurrent.futures.wait(futures)

    print("\n✅ HOÀN THÀNH KIỂM TRA TOÀN BỘ DANH SÁCH!")

if __name__ == "__main__":
    main()