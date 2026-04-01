# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  3_XOA_VANBAN.PY  —  Công cụ Xóa hàng loạt bài viết trên WordPress           ║
║                                                                              ║
║  * MỤC ĐÍCH: Dọn dẹp các bài viết đã đăng từ một ngày cụ thể trở đi.         ║
║  * TÍNH NĂNG: Đọc ngày ở giao diện, tự động Bulk Trash. Vẫn mở trình duyệt.  ║
║  * AN TOÀN: Chỉ đưa bài vào Thùng rác (Trash), không xóa vĩnh viễn.          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import sys
import time
import traceback
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

# Khai báo các thông tin cấu hình từ file config của bạn
from config_vanban import (
    CHROMEDRIVER_PATH, CHROME_BINARY, USE_PROFILE, PROFILE_DIR, 
    WP_EMAIL as EMAIL, WP_PASSWORD as PASSWORD
)

# ------------------------------------------------------------------------------
# 1. CẤU HÌNH NGÀY CẦN XÓA & LINK WEB
# ------------------------------------------------------------------------------
# Định dạng: YYYY, M, D
TARGET_DATE = datetime(2026, 3, 14)

# Danh sách các trang WordPress & Post Type bạn muốn quét để xóa
# Nếu bạn có nhiều web, hãy thêm vào danh sách này.
TARGET_SITES = [
    {"base_url": "https://thptdohuylieu.ninhbinh.edu.vn", "post_type": "van-ban"},
    # {"base_url": "https://truongkhac.edu.vn", "post_type": "van-ban"},
]

# ------------------------------------------------------------------------------
# 2. MÀU SẮC LOG
# ------------------------------------------------------------------------------
class Style:
    RESET    = '\033[0m'
    BOLD     = '\033[1m'
    RED      = '\033[91m'
    GREEN    = '\033[92m'
    YELLOW   = '\033[93m'
    CYAN     = '\033[96m'
    BBLACK   = '\033[90m'

def _enable_ansi_windows():
    if sys.platform != 'win32': return
    try:
        import ctypes, ctypes.wintypes
        kernel32 = ctypes.windll.kernel32
        handle   = kernel32.GetStdHandle(-11)
        old_mode = ctypes.wintypes.DWORD(0)
        kernel32.GetConsoleMode(handle, ctypes.byref(old_mode))
        kernel32.SetConsoleMode(handle, old_mode.value | 0x0004)
    except Exception: pass

_enable_ansi_windows()

# ------------------------------------------------------------------------------
# 3. CHỨC NĂNG XÓA BÀI CỦA BOT
# ------------------------------------------------------------------------------
class WPCleanupBot:
    def __init__(self):
        opts = Options()
        # YÊU CẦU: Vẫn mở cửa sổ trình duyệt (Không dùng headless)
        if CHROME_BINARY: 
            opts.binary_location = CHROME_BINARY
        if USE_PROFILE and PROFILE_DIR: 
            opts.add_argument(f'--user-data-dir={PROFILE_DIR}')
            
        opts.add_argument('--disable-notifications')
        opts.add_argument('--window-size=1366,768')
        opts.add_argument('--disable-blink-features=AutomationControlled')
        opts.add_experimental_option('excludeSwitches', ['enable-automation'])
        
        self.driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=opts)
        
    def close(self):
        try: self.driver.quit()
        except Exception: pass

    def login(self, base_url: str):
        print(f"\n{Style.BBLACK}Đang kiểm tra đăng nhập cho {base_url}...{Style.RESET}")
        self.driver.get(f"{base_url}/wp-admin/")
        
        if "wp-login.php" not in self.driver.current_url and self.driver.find_elements(By.ID, "wpadminbar"):
            print(f"  {Style.GREEN}✓ Đã đăng nhập sẵn!{Style.RESET}")
            return True

        self.driver.get(f"{base_url}/wp-login.php")
        try:
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "user_login"))).send_keys(EMAIL)
            self.driver.find_element(By.ID, "user_pass").send_keys(PASSWORD)
            self.driver.find_element(By.ID, "wp-submit").click()
            
            WebDriverWait(self.driver, 15).until(
                lambda d: "wp-admin" in d.current_url or d.find_elements(By.ID, "wpadminbar")
            )
            print(f"  {Style.GREEN}✓ Đăng nhập thành công!{Style.RESET}")
            return True
        except Exception as e:
            print(f"  {Style.RED}✗ Lỗi đăng nhập: {e}{Style.RESET}")
            return False

    def parse_wp_date(self, text: str) -> datetime:
        """Hàm bóc tách và chuyển đổi text hiển thị ở cột Date thành chuỗi Datetime"""
        # Thường WP hiển thị: "Published\n2026/03/14" hoặc "Đã đăng\n14/03/2026"
        # 1. Tìm định dạng YYYY/MM/DD
        match_ymd = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', text)
        if match_ymd:
            return datetime(int(match_ymd.group(1)), int(match_ymd.group(2)), int(match_ymd.group(3)))
            
        # 2. Tìm định dạng DD/MM/YYYY
        match_dmy = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', text)
        if match_dmy:
            return datetime(int(match_dmy.group(3)), int(match_dmy.group(2)), int(match_dmy.group(1)))
            
        return None

    def delete_posts_from_date(self, base_url: str, post_type: str, target_date: datetime):
        print(f"\n{Style.BOLD}▶ Bắt đầu quét các bài viết từ ngày {target_date.strftime('%d/%m/%Y')}{Style.RESET}")
        
        target_url = f"{base_url}/wp-admin/edit.php?post_type={post_type}"
        self.driver.get(target_url)
        time.sleep(2) # Chờ trang load
        
        # MỚI THÊM: Bắt lỗi "Định dạng bài viết không hợp lệ"
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            if "Định dạng bài viết không hợp lệ" in page_text or "Invalid post type" in page_text:
                print(f"  {Style.RED}✗ Lỗi: Định dạng post_type='{post_type}' không tồn tại hoặc không có quyền truy cập trên web này!{Style.RESET}")
                print(f"  {Style.BBLACK}→ Vui lòng kiểm tra lại cấu hình TARGET_SITES.{Style.RESET}")
                return
        except Exception:
            pass
        
        total_deleted = 0
        
        while True:
            time.sleep(2) # Chờ load bảng dữ liệu
            
            # Kiểm tra xem có bài viết nào không
            if self.driver.find_elements(By.CLASS_NAME, "no-items"):
                print(f"  {Style.BBLACK}Không còn bài viết nào trong danh sách.{Style.RESET}")
                break

            rows = self.driver.find_elements(By.CSS_SELECTOR, "#the-list tr")
            if not rows: break

            found_posts_to_delete = 0
            
            # Quét từng hàng trong bảng
            for row in rows:
                try:
                    # Bỏ qua các hàng không phải là post (vd: thông báo ẩn)
                    if "type-" not in row.get_attribute("class"): continue
                    
                    # Cột chứa thông tin Ngày tháng
                    date_col = row.find_element(By.CSS_SELECTOR, ".column-date").text
                    post_title = row.find_element(By.CSS_SELECTOR, ".row-title").text
                    
                    post_date = self.parse_wp_date(date_col)
                    
                    # Nếu ngày của bài viết >= ngày mốc được yêu cầu -> Tích chọn
                    if post_date and post_date >= target_date:
                        cb = row.find_element(By.CSS_SELECTOR, "th.check-column input[type='checkbox']")
                        if not cb.is_selected():
                            self.driver.execute_script("arguments[0].click();", cb)
                            
                        print(f"  {Style.YELLOW}✓ Tích chọn: {post_title} ({post_date.strftime('%d/%m/%Y')}){Style.RESET}")
                        found_posts_to_delete += 1
                        total_deleted += 1
                        
                except Exception as e:
                    # Các hàng lỗi hiển thị có thể bỏ qua
                    continue

            # Thực thi Xóa bằng Bulk Action (Thao tác hàng loạt)
            if found_posts_to_delete > 0:
                print(f"  {Style.CYAN}⇛ Đang chuyển {found_posts_to_delete} bài vào Thùng rác...{Style.RESET}")
                
                # Chọn 'Move to Trash' ở menu dropdown trên cùng
                Select(self.driver.find_element(By.ID, "bulk-action-selector-top")).select_by_value("trash")
                
                # Bấm nút Áp dụng (Apply)
                self.driver.find_element(By.ID, "doaction").click()
                
                # Chờ trang web reload sau khi xóa
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.ID, "message"))
                )
                print(f"  {Style.GREEN}✓ Đã xóa xong nhóm bài này!{Style.RESET}")
                
                # SAU KHI XÓA: Danh sách sẽ co lại, ta không chuyển trang mà tiếp tục quét LẠI trang hiện tại
                continue 
            else:
                # Nếu trang này không có bài nào khớp ngày, thử sang trang tiếp theo (Next Page)
                next_btns = self.driver.find_elements(By.CSS_SELECTOR, ".tablenav.bottom .next-page:not(.disabled)")
                if next_btns:
                    print(f"  {Style.BBLACK}Chuyển sang trang tiếp theo...{Style.RESET}")
                    next_url = next_btns[0].get_attribute("href")
                    self.driver.get(next_url)
                else:
                    print(f"  {Style.BBLACK}Đã đi đến trang cuối cùng.{Style.RESET}")
                    break
                    
        print(f"\n{Style.BOLD}{Style.GREEN}HOÀN THÀNH: Đã dọn dẹp tổng cộng {total_deleted} bài viết.{Style.RESET}")

# ------------------------------------------------------------------------------
# 4. CHẠY SCRIPT
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    print(f'\n{"=" * 72}\n  {Style.BOLD}CÔNG CỤ DỌN DẸP BÀI VIẾT TỪ {TARGET_DATE.strftime("%d/%m/%Y")}{Style.RESET}\n{"=" * 72}')
    
    bot = WPCleanupBot()
    try:
        for site in TARGET_SITES:
            b_url = site["base_url"]
            p_type = site["post_type"]
            
            if bot.login(b_url):
                bot.delete_posts_from_date(b_url, p_type, TARGET_DATE)
            else:
                print(f"  {Style.RED}Bỏ qua web {b_url} do lỗi đăng nhập.{Style.RESET}")
                
            time.sleep(2)
            
    except KeyboardInterrupt:
        print(f'\n{Style.YELLOW}⚠ Đã dừng chương trình.{Style.RESET}')
    except Exception as e:
        print(f'\n{Style.RED}🔥 Lỗi hệ thống: {e}{Style.RESET}\n{traceback.format_exc()}')
    finally:
        bot.close()
        print(f'\n{"=" * 72}\n  {Style.BOLD}ĐÃ ĐÓNG TRÌNH DUYỆT.{Style.RESET}\n{"=" * 72}')