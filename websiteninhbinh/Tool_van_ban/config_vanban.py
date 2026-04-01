# config.py  —  Cấu hình chung cho 1_Lay_bai.py và 2_Dang_bai.py. Đặt file này cùng thư mục với 2 script trên.
# Chỉ cần chỉnh sửa file này — không cần động vào code chính.

from datetime import date

#  THƯ MỤC GỐC -> Thay đổi duy nhất cần thiết khi chuyển máy hoặc chuyển ổ đĩa. Tất cả đường dẫn bên dưới đều dựa vào biến này.
BASE_DIR = r"D:\D_Document\VS Code\Python\Thuc_tap"

#  CHROME / SELENIUM  (dùng chung cho cả 2 script)
CHROMEDRIVER_PATH = rf"{BASE_DIR}\chromedriver-win64\chromedriver-win64\chromedriver.exe"
CHROME_BINARY     = rf"{BASE_DIR}\chrome-win64\chrome-win64\chrome.exe"

# Dùng profile Chrome đã đăng nhập sẵn để tránh nhập mật khẩu mỗi lần.
# True = dùng profile tại PROFILE_DIR | False = mở Chrome mới (phiên ẩn danh)
USE_PROFILE = False
PROFILE_DIR = rf"{BASE_DIR}\selenium_profile_itcctv"

#  FILE & THƯ MỤC DỮ LIỆU
EXCEL_PATH = rf"{BASE_DIR}\Tool_van_ban\DS_vb.xlsx" # file Excel chứa danh sách URL cần scrape (1_Lay_bai.py)
TMP_DIR = rf"{BASE_DIR}\tmp_wp_upload" # Thư mục tạm lưu ảnh/file tải về trước khi upload
ERROR_LOG_FILE = rf"{BASE_DIR}\log_lay_van_ban.log" # log lỗi scraper (1_Lay_vanban.py) — để None hoặc "" để chỉ log ra console
LOG_XLSX = rf"{BASE_DIR}\log_dang_van_ban.xlsx" # kết quả đăng bài

#  WORDPRESS  (2_Dang_bai.py)
# Tài khoản WordPress — dùng cho cả REST API lẫn Selenium
WP_EMAIL    = "adminvtk"
WP_PASSWORD = "Khanhkh@nh9999"
# Giờ publish mặc định khi bài không có ngày (HH:MM)
DEFAULT_PUBLISH_HOUR   = 8
DEFAULT_PUBLISH_MINUTE = 0

# Xử lý bài trùng khi đăng:
#   0 = Không lọc  — cứ đăng kể cả trùng
#   1 = Bỏ qua     — bài đã tồn tại thì bỏ, không đăng lại
#   2 = Xóa nháp   — xóa bản nháp trùng, giữ bài đã publish
#   3 = Xóa public — xóa bài đã publish trùng, giữ nháp
#   4 = Xóa tất cả — xóa mọi bài trùng (cả nháp lẫn đã đăng)
DUPLICATE_MODE = 4

# True  = xóa file tạm ngay sau khi upload lên WP (tiết kiệm ổ đĩa)
# False = giữ lại trong TMP_DIR (upload lại nhanh nếu chạy lại, xóa tay sau)
XOA_FILE_SAU_KHI_DANG = True

#  REST API  (2_Dang_bai.py — primary, nhanh hơn Selenium ~10x)
USE_REST_API            = True   # False → dùng Selenium hoàn toàn
REST_DOMAIN_CONCURRENCY = 3      # Request đồng thời tối đa / domain (anti-ban)
REST_DELAY_MIN          = 0.3    # Delay ngẫu nhiên tối thiểu giữa các bài (giây)
REST_DELAY_MAX          = 1.2    # Delay ngẫu nhiên tối đa (giây)
REST_UPLOAD_WORKERS     = 4      # Luồng song song upload ảnh/file per-article
MAX_CONCURRENT_WORKERS  = 1     # Tổng luồng REST (không phải Chrome) -> số luồng tối đa cho tất cả

#  SELENIUM FALLBACK  (2_Dang_bai.py — khi REST không khả dụng)
PAUSE_TIME      = 0.2    # Polling nhanh (giây)
STABILITY_PAUSE = 1.0    # Chờ UI ổn định sau thao tác (giây)
UPLOAD_TIMEOUT  = 120    # Timeout tối đa khi upload file lớn (giây)

MAX_RETRIES_PER_POST = 3   # Thử lại tối đa nếu 1 bài bị lỗi
MAX_THREADS_PER_SITE = 1   # Luồng Selenium tối đa mỗi trường -> số luồng tối đa cho mỗi trường

#  SCRAPER  (1_Lay_bai.py)
# ══════════════════════════════════════════════════════════════════════════════
# Chỉ lấy bài đăng từ ngày này trở đi
FROM_DATE = date(2000, 7, 1)

# CSS selector lấy ngày đăng trên trang chi tiết bài viết
DETAIL_DATE_CSS = "span.post-date"

# Số trang listing tối đa mỗi URL — chặn CMS tạo nút phân trang vô hạn
# Tăng lên nếu biết chắc có site thực sự có nhiều hơn 50 trang
MAX_LIST_PAGES = 100

# True  = hiện cửa sổ Chrome (có thể bấm vào xem)
# False = thu nhỏ ngay khi mở (chạy ngầm, tiết kiệm màn hình)
SHOW_CHROME_WINDOW = True
