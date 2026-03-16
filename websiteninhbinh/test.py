import requests

SITE = "https://c0nhattuu.ninhbinh.edu.vn"
USER = "adminvtk"
PASS = "Khanhkh@nh9999"

s = requests.Session()

# đăng nhập wp-admin để lấy cookie
login = s.post(
    f"{SITE}/wp-login.php",
    data={
        "log": USER,
        "pwd": PASS,
        "wp-submit": "Log In",
        "redirect_to": f"{SITE}/wp-admin/",
        "testcookie": "1",
    },
    timeout=30
)

# thử tạo bài nháp qua REST
r = s.post(
    f"{SITE}/wp-json/wp/v2/posts",
    json={"title": "Test from Python", "content": "Hello", "status": "draft"},
    timeout=30
)
print(r.status_code)
print(r.text[:300])
