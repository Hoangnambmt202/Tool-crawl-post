import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import os

# ================= CẤU HÌNH ĐƯỜNG DẪN =================
BASE_DIR = r"D:\D_Document\VS Code\Python\Thuc_tap"
CHROMEDRIVER_PATH = rf"{BASE_DIR}\chromedriver-win64\chromedriver-win64\chromedriver.exe"
CHROME_BINARY = rf"{BASE_DIR}\chrome-win64\chrome-win64\chrome.exe"

EXCEL_PATH = r"D:\D_Document\VS Code\Python\Thuc_tap\DS_tool_2.xlsx"

FILE_HEADER = r"D:\D_Document\VS Code\Python\Thuc_tap\File\header.php"
FILE_TAX = r"D:\D_Document\VS Code\Python\Thuc_tap\File\taxonomy-phong-ban.php"
FILE_GVIEW = r"D:\D_Document\VS Code\Python\Thuc_tap\File\gview.php"

DA_LOGIN_URL = "https://sv1126.viettechkey.com:2222"

# ================= TÙY CHỌN TÍNH NĂNG =================
SKIP_DONE_ROWS         = True   # Bỏ qua các trường đã ghi "Thành công"
USE_SMART_DOMAIN       = True   # Tự động đổi c3->thpt, c2->thcs...
CHECK_HOMEPAGE_DOMAINS = True   # Đọc danh sách domain thực tế trên trang chủ DirectAdmin
TRY_FALLBACK_DOMAINS   = True   # Nếu lỗi domain chính, thử tiếp domain dự phòng
AUTO_LOGOUT            = True   # Tự động đăng xuất sau khi xong mỗi trường
HEADLESS_MODE          = False  # Đổi thành True nếu muốn Chrome chạy ngầm (không hiện UI)

# Kiểm tra file local có tồn tại không trước khi chạy
for file_path in [FILE_HEADER, FILE_TAX, FILE_GVIEW]:
    if not os.path.exists(file_path):
        print(f"LỖI: Không tìm thấy file cần upload tại: {file_path}")
        print("Vui lòng kiểm tra lại đường dẫn file!")
        exit()

# ================= HÀM HỖ TRỢ =================
def get_target_domain(excel_domain):
    """
    Chuyển đổi tiền tố domain theo luật ưu tiên:
    c3 -> thpt, c2 -> thcs, c1 -> th, c0 -> mn
    """
    domain = str(excel_domain).strip().lower()
    if domain.startswith('c3'):
        return domain.replace('c3', 'thpt', 1)
    elif domain.startswith('c2'):
        return domain.replace('c2', 'thcs', 1)
    elif domain.startswith('c1'):
        return domain.replace('c1', 'th', 1)
    elif domain.startswith('c0'):
        return domain.replace('c0', 'mn', 1)
    return domain

def setup_driver():
    """Khởi tạo trình duyệt Chrome với các tùy chọn an toàn"""
    chrome_options = Options()
    chrome_options.binary_location = CHROME_BINARY
    chrome_options.add_argument("--ignore-certificate-errors") # Bỏ qua lỗi SSL (Your connection is not private)
    if HEADLESS_MODE:
        chrome_options.add_argument("--headless=new") # Chạy ngầm
    else:
        chrome_options.add_argument("--start-maximized")
    
    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# ================= LUỒNG CHÍNH =================
def main():
    print("Đang đọc dữ liệu từ file Excel...")
    try:
        df = pd.read_excel(EXCEL_PATH)
        
        # Sửa lỗi cảnh báo dtype (FutureWarning) của Pandas
        if 'Kết quả' not in df.columns:
            df['Kết quả'] = ""
        df['Kết quả'] = df['Kết quả'].fillna("").astype(str)

        # Thêm cột 'Domain đã dùng' (Cột F) nếu chưa có
        if 'Domain đã dùng' not in df.columns:
            df['Domain đã dùng'] = ""
        df['Domain đã dùng'] = df['Domain đã dùng'].fillna("").astype(str)
        
    except Exception as e:
        print(f"Không thể đọc file Excel. Lỗi: {e}")
        print("Hãy đảm bảo bạn đã đóng file Excel trước khi chạy tool!")
        return

    # Khởi tạo trình duyệt
    driver = setup_driver()
    wait = WebDriverWait(driver, 15) # Thời gian chờ tối đa 15s cho các element xuất hiện

    for index, row in df.iterrows():
        stt = row.get('STT', index + 1)
        domain_goc = str(row['Link trường']).strip().lower()
        user = row['User']
        password = row['Pass']
        
        # Chuẩn hóa chuỗi kết quả: chuyển thành chữ thường và xóa khoảng trắng 2 đầu để so sánh chính xác tuyệt đối
        ket_qua = str(row.get('Kết quả', '')).strip().lower()

        # [TÙY CHỌN] Bỏ qua nếu đã tải thành công trước đó
        if SKIP_DONE_ROWS and "thành công" in ket_qua:
            print(f"[{stt}] Bỏ qua {domain_goc} vì đã thành công trước đó.")
            continue

        # [TÙY CHỌN] Xử lý domain thông minh
        if USE_SMART_DOMAIN:
            target_domain = get_target_domain(domain_goc)
        else:
            target_domain = domain_goc
            
        print(f"\n[{stt}] Đang xử lý: {domain_goc}")

        try:
            # 1. Xóa cookie cũ và truy cập trang đăng nhập
            driver.delete_all_cookies()
            driver.get(DA_LOGIN_URL)

            # Điền tài khoản (Sử dụng XPath chỉ định rõ thẻ input, tránh nhầm với thẻ div của Vue.js)
            user_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@name='username']")))
            pass_input = driver.find_element(By.XPATH, "//input[@name='password']")
            
            user_input.clear()
            user_input.send_keys(user)
            
            pass_input.clear()
            pass_input.send_keys(password)
            pass_input.send_keys(Keys.RETURN) # Nhấn phím Enter để đăng nhập thay vì .submit()

            # Chờ trang chủ DirectAdmin tải xong bằng cách tìm nút Logout
            wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'CMD_LOGOUT')]")))
            print("  -> Đăng nhập thành công.")

            # -------------------------------------------------------------------
            # ĐỌC TRANG CHỦ & TẠO DANH SÁCH TÊN MIỀN CẦN THỬ NGHIỆM
            # -------------------------------------------------------------------
            available_domains = []
            
            # [TÙY CHỌN] Đọc domain từ trang chủ
            if CHECK_HOMEPAGE_DOMAINS:
                domain_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/CMD_SHOW_DOMAIN?domain=')]")
                available_domains = [el.text.strip().lower() for el in domain_elements]
                print(f"  -> Các tên miền có sẵn trên host: {available_domains}")
            
            domains_to_try = []
            
            # Xây dựng danh sách domain sẽ đưa vào vòng lặp tải lên
            if target_domain in available_domains or not CHECK_HOMEPAGE_DOMAINS:
                domains_to_try.append(target_domain)
            
            # [TÙY CHỌN] Fallback (Nếu bật fallback, thêm domain gốc vào để thử nếu target_domain thất bại)
            if TRY_FALLBACK_DOMAINS:
                if domain_goc in available_domains or not CHECK_HOMEPAGE_DOMAINS:
                    if domain_goc not in domains_to_try:
                        domains_to_try.append(domain_goc)
                
            # Nếu danh sách vẫn trống (cực hiếm), ép nó thử target_domain
            if not domains_to_try:
                domains_to_try = [target_domain]
                
            print(f"  -> Sẽ thử lần lượt các tên miền: {domains_to_try}")

            success_for_this_row = False
            last_error_msg = ""

            # -------------------------------------------------------------------
            # VÒNG LẶP THỬ NGHIỆM TỪNG TÊN MIỀN
            # -------------------------------------------------------------------
            for attempt_domain in domains_to_try:
                print(f"  -> Đang thử vào thư mục của tên miền: {attempt_domain}")
                try:
                    # -- NHIỆM VỤ 1 --
                    dir_1_url = f"{DA_LOGIN_URL}/CMD_FILE_MANAGER/domains/{attempt_domain}/public_html/wp-content/themes/vtkEduSchool"
                    driver.get(dir_1_url)
                    
                    # Cố gắng tìm nút Upload trong vòng 8 giây (để nếu sai thư mục thì thoát ra nhanh)
                    btn_upload_dir = WebDriverWait(driver, 8).until(
                        EC.element_to_be_clickable((By.XPATH, "//input[@value='Upload files to current directory']"))
                    )
                    btn_upload_dir.click()

                    # Upload 2 file
                    file1_input = wait.until(EC.presence_of_element_located((By.NAME, "file1")))
                    file2_input = driver.find_element(By.NAME, "file2")
                    file1_input.send_keys(FILE_HEADER)
                    file2_input.send_keys(FILE_TAX)
                    
                    btn_submit_upload = driver.find_element(By.XPATH, "//input[@value='Upload Files']")
                    btn_submit_upload.click()

                    wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Upload successful')]")))
                    print("    -> Upload Nhóm 1 (header, taxonomy) thành công.")

                    # -- NHIỆM VỤ 2 --
                    dir_2_url = f"{DA_LOGIN_URL}/CMD_FILE_MANAGER/domains/{attempt_domain}/public_html/wp-content/themes/vtkEduSchool/DDevFramework/functions"
                    driver.get(dir_2_url)
                    
                    btn_upload_dir = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='Upload files to current directory']")))
                    btn_upload_dir.click()

                    # Upload 1 file
                    file1_input = wait.until(EC.presence_of_element_located((By.NAME, "file1")))
                    file1_input.send_keys(FILE_GVIEW)
                    
                    btn_submit_upload = driver.find_element(By.XPATH, "//input[@value='Upload Files']")
                    btn_submit_upload.click()

                    wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Upload successful')]")))
                    print("    -> Upload Nhóm 2 (gview) thành công.")

                    # NẾU ĐẾN ĐÂY KHÔNG LỖI -> ĐÃ TẢI LÊN XONG, CHỐT VÀ KẾT THÚC VÒNG LẶP
                    df.at[index, 'Domain đã dùng'] = attempt_domain
                    df.at[index, 'Kết quả'] = "Thành công"
                    success_for_this_row = True
                    break # Thoát khỏi vòng lặp thử nghiệm tên miền

                except Exception as e:
                    # Nếu văng lỗi ở bất kỳ bước nào, lưu lại lỗi và để vòng lặp chạy tiếp tên miền thứ 2
                    last_error_msg = str(e).split('\n')[0]
                    print(f"    -> Bỏ qua {attempt_domain} do lỗi: {last_error_msg}")
            
            # Kiểm tra xem sau khi thử hết các tên miền có thành công không
            if not success_for_this_row:
                print("  -> LỖI TỔNG HỢP: Đã thử hết các tên miền nhưng không thành công.")
                df.at[index, 'Kết quả'] = f"Lỗi: {last_error_msg}"

        except Exception as global_e:
            # Bắt các lỗi xảy ra ngay từ lúc đăng nhập
            global_error_msg = str(global_e).split('\n')[0]
            print(f"  -> LỖI HỆ THỐNG: {global_error_msg}")
            df.at[index, 'Kết quả'] = f"Lỗi: {global_error_msg}"
        
        finally:
            # [TÙY CHỌN] Đăng xuất khỏi tài khoản sau khi xử lý xong (dù thành công hay lỗi)
            if AUTO_LOGOUT:
                try:
                    driver.get(f"{DA_LOGIN_URL}/CMD_LOGOUT")
                    print("  -> Đã đăng xuất an toàn.")
                except Exception:
                    pass

            # Lưu lại file Excel ngay lập tức sau mỗi trường
            try:
                df.to_excel(EXCEL_PATH, index=False)
            except Exception as e:
                print("LỖI LƯU EXCEL: Vui lòng đóng file Excel nếu bạn đang mở nó!")
            
            time.sleep(1) # Nghỉ 1 giây trước khi sang trường tiếp theo

    # Đóng trình duyệt khi xong tất cả
    driver.quit()
    print("\nHOÀN THÀNH QUÁ TRÌNH UPLOAD!")

if __name__ == "__main__":
    main()