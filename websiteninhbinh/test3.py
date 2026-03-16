import re, requests
SITE="https://c0nhattuu.ninhbinh.edu.vn"
USER = "adminvtk"
PASS = "Khanhkh@nh9999"
s=requests.Session()
s.get(f"{SITE}/wp-login.php")
s.post(f"{SITE}/wp-login.php", data={"log":USER,"pwd":PASS,"wp-submit":"Log In","redirect_to":f"{SITE}/wp-admin/","testcookie":"1"}, allow_redirects=True)
html=s.get(f"{SITE}/wp-admin/").text
print("has wp-rest-nonce meta:", bool(re.search(r'wp-rest-nonce', html)))
print("has _wpUtilSettings:", bool(re.search(r'_wpUtilSettings', html)))
print("has wpApiSettings:", bool(re.search(r'wpApiSettings', html)))