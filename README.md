# Website Ninh Bình Scraper - Tự Động Hóa Đăng Bài Lên WordPress

Dự án này là một công cụ cào dữ liệu (web scraper) kết hợp tự động đăng bài được phát triển bằng Python. Dự án được thiết kế để tự động hóa việc lấy các bài viết, tin tức từ các trang mạng giáo dục tại Ninh Bình, sau đó tự động đăng tải (publish) chúng lên một hệ thống nội dung WordPress.

## Mục đích của dự án
- **Tiết kiệm thời gian & Tự động hóa**: Thay vì phải copy - paste nội dung, tải ảnh và upload từng bài một cách thủ công lên WordPress, tool sẽ tự động bóc tách mã nguồn, trích xuất dữ liệu bài viết (tiêu đề, nội dung, hình ảnh, file đính kèm, danh mục) và đăng hoàn chỉnh trong một thao tác.
- **Đảm bảo tính toàn vẹn nội dung**: Tải và nhúng toàn bộ file tài liệu, hình ảnh vào đúng định dạng và vị trí của bài viết như nguồn gốc.
- **Kiểm soát & Quản lý dữ liệu**: Tự động kiểm tra trùng lặp (duplicate check) từ tệp log (và WordPress search), xuất báo cáo chi tiết quá trình làm việc qua tệp log Excel giúp người quản trị dễ dàng theo dõi.

## Kết quả đạt được
- Hệ thống hỗ trợ khả năng phân tích và lấy dữ liệu thành công từ nhiều dạng giao diện website giáo dục khác nhau (Mầm non, Tiểu học, v.v).
- **Vượt qua các giới hạn tự động hóa**: Nhận dạng, tương tác thành công và ổn định với DOM của Media Modal WP, xử lý được các nút bấm có text thay đổi hoặc ẩn dựa vào fallback thông qua HTML classes.
- Quản lý tải và upload đúng tệp tin (File & Image), format URL chuẩn xác, không bị lỗi khi làm việc với file tên tiếng Việt hoặc tên quá dài.
- Giảm thiểu tối đa (hơn 90%) thời gian, công sức cho nhân sự biên tập nội dung.

## Công nghệ sử dụng
- **Ngôn ngữ lập trình:** Python (3.x)
- **Cào dữ liệu & Phân tích (Web Scraping / Parsing):**
  - `BeautifulSoup4`: Bóc tách và xử lý mã HTML của các mẫu tin tức, làm sạch dữ liệu và bảo lưu thẻ `img`, `a` cần thiết.
  - `Requests`: Xử lý kết nối tải bài, tải định dạng file, tải hình ảnh. Sử dụng `HTTPAdapter` và `Retry` từ `urllib3` để thêm bộ đệm phục hồi lỗi cho các request network gặp sự cố.
- **Tự động hóa trình duyệt (Browser Automation):**
  - `Selenium WebDriver`: Điều khiển trình duyệt Chrome mô phỏng tương tác người dùng, xử lý các form đăng nhập WP, thao tác trực tiếp với iframe của bộ soạn thảo TinyMCE hay kích hoạt click các tệp tin đính kèm trong hộp thoại Media bằng JavaScript execution.
- **Xử lý Dữ liệu & Báo cáo:**
  - `openpyxl`: Tạo và cập nhật module tệp dữ liệu Excel (`log_posted.xlsx`) sử dụng cho mục đích logging nhật ký từng phiên cào/đăng tin. 
  - `SQLite` (hoặc CSDL thông qua file `helpers.py`): Quản lý queue hàng đợi của các tin cần đăng và check duplicate nội dung.

## Cấu trúc thư mục (Project Structure)

```text
folder/
├── websiteninhbinh/
│   ├── c1/
│   │   ├── config.py          # Cấu hình cài đặt (URLs, thông tin đăng nhập, thư mục Chrome...)
│   │   ├── dangbai_c1.py      # Script chính chạy quy trình tự động đăng bài lên WordPress
│   │   ├── main.py            # Entry point để chạy ứng dụng scraper
│   │   ├── scraper.py         # Logic cào dữ liệu tổng hợp
│   │   ├── utils.py           # Các hàm hỗ trợ dùng chung
│   │   └── parsers/           # Thư mục xử lý class bóc tách riêng biệt cho từng dạng cấu trúc HTML
│   │       ├── base.py
│   │       ├── type11.py
│   │       └── ...
├── chrome-win64/              # Chứa Portable Chrome chạy riêng cho Selenium
├── chromedriver-win64/        # Chrome driver cho Selenium
├── tmp_wp_upload/             # Thư mục chờ lưu trữ ảnh/file tạm thời
├── log_posted.xlsx            # File logs tiến trình
└── README.md
```

## Các Tính Năng Kỹ Thuật Nổi Bật (Features)
1. **Tương tác TinyMCE nâng cao**: Thay vì đăng bài qua REST API (không giữ được thẻ tải lên), tool sử dụng logic JS qua Selenium để chèn thẳng khối HTML có thứ tự vào TinyMCE iframe, cho phép can thiệp trực tiếp vị trí hình ảnh.
2. **Xử lý Media Modal cực Ổn Định**: Tính năng chọn, upload file qua Media Browser của WP được tối ưu nâng cao. Bao gồm việc fallback ưu tiên sử dụng `media-button-insert`, `media-button-select` class cho các tình huống element text (Chèn vào bài viết / Select) hiển thị sai, không đầy đủ.
3. **Smart Check Duplicate**: Cơ chế check title bài nếu trùng lặp trên DB local hoặc trên giao diện list post WP Admin để tự bỏ qua.
4. **Auto Date & Category**: Chuẩn hoá String tên category (có dấu tiếng Việt) để mapping và tick tự động checkboxes danh mục ứng với WP. Thiết lập ngày/giờ publish chuẩn chỉ qua các thao tác điền form timestamp.
5. **Robust Image & File Processing (Luồng xử lý Media độc lập)**: Trình xử lý ảnh tải xuống tệp vào máy nhánh cục bộ, đổi tên an toàn loại bỏ ký tự lạ kết hợp md5 hash suffix (chống trùng lặp tên file). Hỗ trợ cơ chế bắt lỗi ngoại lệ cô lập (Isolated Exception Handling): Nếu một thẻ `img` hoặc `a` bị lỗi (do chứng chỉ SSL, mạng chậm hoặc do file WebP không được WP hỗ trợ), hệ thống sẽ catch lỗi, tự động đóng hộp thoại Media và tiếp tục đăng phần còn lại của bài viết nhằm đảm bảo không làm gián đoạn/hủy bỏ toàn bộ quá trình tải.

## Hướng dẫn cài đặt (Installation)

1. Sao chép project về thư mục local.
2. Cài đặt các thư viện Python theo yêu cầu:
   ```bash
   pip install -r requirements.txt
   ```
   (Hoặc: `pip install requests beautifulsoup4 selenium openpyxl urllib3`)
3. Thực hiện cấu hình file config (có thể sao chép từ example):
   ```bash
   cp websiteninhbinh/c1/config.example.py websiteninhbinh/c1/config.py
   ```
4. Thiết lập đường dẫn Chrome Core và ChromeDriver trong tệp cấu hình (`config.py` và `dangbai_c1.py`) tới folder `chrome-win64` và `chromedriver-win64` được cung cấp.

## Cách sử dụng (Usage)

1. Mở terminal / command line, chạy script cào và đăng bài qua thư mục gốc:
   ```bash
   python websiteninhbinh/c1/main.py
   ```
   Nếu chỉ muốn test phần đăng WP trên queue sẵn có:
   ```bash
   python websiteninhbinh/c1/dangbai_c1.py
   ```
2. Theo dõi terminal log. Nếu tool hoàn thành đăng tải, nó sẽ report success/fail chi tiết.

## Khắc phục sự cố (Troubleshooting)
- **Lỗi không đăng được ảnh (Missing insert button):** Tool đã được cập nhật để khắc phục tình trạng này (fallback tìm các phần tử JS có class `.media-button-insert|select`). Nếu vẫn báo lỗi upload Timeout, hãy kiểm tra lại tốc độ kết nối băng thông tải file temporary.
- **Có lỗi khi đăng ảnh (WebP không hỗ trợ, Timeout, Mất kết nối):** Trường hợp ảnh tải lên WP gặp sự cố, tính năng catch exception sẽ kích hoạt. Ảnh bị lỗi sẽ được bỏ qua và tiến trình đăng bài vẫn tiếp tục. Bạn có thể kiểm tra console log `⚠️ SKIP IMG...` để đối chiếu URL ảnh bị lỗi. 
- **Chrome bị crash hoặc outdated driver:** Cần đảm bảo phiên bản `chromedriver.exe` đồng bộ với `chrome.exe` dùng trong thư mục.
- **Lỗi Duplicate không mong đợi:** Xóa/làm trống bảng log queue nếu bạn cần đăng tải lại tin bài đã được quét trong cơ sở dữ liệu. Theo dõi `log_posted.xlsx` để chẩn đoán.

## Lịch sử cập nhật (Version History)

### [2026-03-27] - Update v1.2: Bảo mật & Tối ưu hóa Media
- **Sửa lỗi Upload Media**: Khắc phục lỗi không tìm thấy nút "Insert/Select" trong Media Modal bằng cơ chế fallback nhận diện HTML ID/Class thay vì chỉ dùng Text.
- **Xử lý Emoji thông minh**: Tự động nhận diện và nhúng link trực tiếp (direct link) cho các biểu tượng cảm xúc từ Facebook/WP CDN. Không tải về local giúp giảm rác Media và tăng tốc độ đăng bài 5-10 lần cho các bài nhiều icon.
- **Cơ chế Isolated Exception**: Bọc mã nguồn trong khối try-except tại luồng xử lý ảnh. Nếu 1 ảnh lỗi (404, WebP không hỗ trợ), bài viết vẫn tiếp tục được đăng thay vì bị dừng hoàn toàn.

### [2026-03-27] - Update v1.1: Quản lý Trùng lặp nâng cao
- **Smart Duplicate Cleanup**: Cấu hình tính năng kiểm tra bài viết tồn tại. Nếu phát hiện có nhiều bài trùng tiêu đề (>1), tự động sử dụng WP Bulk Action để chuyển các bài dư thừa vào Thùng rác (Trash) và giữ lại duy nhất 1 bản ghi sạch.
- **Chuẩn hóa so khớp**: Cải thiện Regex bóc tách `stem_words` hỗ trợ cả khoảng trắng (spaces) giúp việc tìm và chọn ảnh trong thư viện WordPress chính xác tuyệt đối.

### [2026-03-27] - Update v1.0: Khởi tạo & Tiêu chuẩn hóa
- Hoàn thiện luồng đăng bài tự động (Auto-Poster) qua Selenium.
- Hỗ trợ đăng bài kèm File đính kèm (PDF, DOCX, XLSX...).
- Tự động map Chuyên mục và đặt lịch ngày đăng (Publish Date) theo dữ liệu cào.
- Xuất báo cáo Log chi tiết qua file Excel.
