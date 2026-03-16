import requests

SITE = "https://c0nhattuu.ninhbinh.edu.vn"
USER = "adminvtk"
PASS = "Khanhkh@nh9999"
s = requests.Session()

# Bắt buộc: GET wp-login trước để nhận cookie test
s.get(f"{SITE}/wp-login.php", timeout=30)

resp = s.post(
    f"{SITE}/wp-login.php",
    data={
        "log": USER,
        "pwd": PASS,
        "wp-submit": "Log In",
        "redirect_to": f"{SITE}/wp-admin/",
        "testcookie": "1",
    },
    allow_redirects=True,
    timeout=30,
)

print("After login final URL:", resp.url)
print("Cookies keys:", list(s.cookies.get_dict().keys()))

admin = s.get(f"{SITE}/wp-admin/", allow_redirects=True, timeout=30)
print("wp-admin final URL:", admin.url)
print("wp-admin status:", admin.status_code)
print("Looks like logged in:", "wpadminbar" in admin.text.lower() or "wp-admin-bar" in admin.text.lower())
