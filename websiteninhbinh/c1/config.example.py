from datetime import date
import os

# Đường dẫn Chrome (update these paths for your system)
CHROME_DRIVER_PATH = r"path/to/chromedriver.exe"  # e.g., r"chromedriver-win64/chromedriver.exe"
CHROME_BINARY_PATH = r"path/to/chrome.exe"  # e.g., r"chrome-win64/chrome.exe"

# Cấu hình ngày tháng
FROM_DATE = date(2017, 1, 1)  # chỉ lấy bài từ mốc này trở về sau
DETAIL_DATE_CSS = "span.post-date"

# Timeout default
WAIT_TIMEOUT = 10