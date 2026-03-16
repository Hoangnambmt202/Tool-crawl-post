import time
from urllib.parse import urlparse
from datetime import datetime, date
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import helpers as hp
from bs4 import BeautifulSoup
import os
import re
import uuid
import requests
from urllib.parse import urljoin, urlparse
# =========================
# CONFIG
# =========================
CHROMEDRIVER_PATH = r"F:\soft\chromedriver-win64\chromedriver-win64\chromedriver.exe"
CHROME_BINARY     = r"F:\soft\chrome-win64\chrome-win64\chrome.exe"

EMAIL    = "adminvtk"
PASSWORD = "Khanhkh@nh9999"

# Nếu muốn giữ cookie giữa các lần chạy, bật profile:
USE_PROFILE = False
PROFILE_DIR = r"D:\selenium_profile_itcctv"



def date_to_datetime(d: date, hour=8, minute=0) -> datetime:
    return datetime(d.year, d.month, d.day, hour, minute)
def get_base(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        p = urlparse("https://" + url)
    return f"{p.scheme}://{p.netloc}/"



def normalize_img_url(src: str, base_source: str) -> str:
    src = (src or "").strip()
    if not src:
        return ""

    # //cdn... -> thêm scheme
    if src.startswith("//"):
        return "https:" + src

    # đã là absolute
    if src.startswith("http://") or src.startswith("https://"):
        return src

    # tương đối -> join với base_source
    return urljoin(base_source, src)


def download_image(img_url: str, tmp_dir: str = r"D:\tmp_wp_upload") -> str:
    os.makedirs(tmp_dir, exist_ok=True)

    # đoán extension
    ext = ".jpg"
    path_part = urlparse(img_url).path.lower()
    for e in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        if path_part.endswith(e):
            ext = e
            break

    file_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex}{ext}")

    r = requests.get(img_url, timeout=60, stream=True)
    r.raise_for_status()
    with open(file_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return file_path

def wp_media_upload_and_get_url(driver, wait, file_path: str) -> str:
    # mở modal
    wait.until(EC.element_to_be_clickable((By.ID, "insert-media-button"))).click()

    # về tab Upload (nếu có)
    try:
        wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR,
            "#menu-item-upload, .media-menu-item[data-route='upload']"
        ))).click()
    except:
        pass

    # upload file
    file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")))
    file_input.send_keys(file_path)

    # đợi danh sách attachments xuất hiện (upload xong thường sẽ tạo thumbnail)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.attachments, .attachments-browser")))

    # chọn attachment mới nhất: thường item cuối
    def select_latest_attachment():
        items = driver.find_elements(By.CSS_SELECTOR, "ul.attachments li.attachment")
        if items:
            driver.execute_script("arguments[0].click();", items[-1])
            return True
        # fallback khác
        items = driver.find_elements(By.CSS_SELECTOR, ".attachments-browser .attachment")
        if items:
            driver.execute_script("arguments[0].click();", items[-1])
            return True
        return False

    for _ in range(10):
        if select_latest_attachment():
            break
        time.sleep(0.5)

    # lấy URL theo nhiều cách (ưu tiên lấy từ preview img)
    def try_get_url():
        # 1) lấy từ ảnh preview bên phải (chi tiết tệp đính kèm)
        img_selectors = [
            ".attachment-details img",                 # nhiều bản WP
            "img.details-image",                       # nhiều bản WP
            ".media-sidebar img",                      # sidebar details
            ".thumbnail img",                          # thumbnail preview
        ]
        for sel in img_selectors:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for e in els:
                src = (e.get_attribute("src") or "").strip()
                if src.startswith("http://") or src.startswith("https://"):
                    # bỏ ảnh icon hệ thống nếu có
                    if "/wp-includes/" not in src:
                        return src

        # 2) input url field
        for sel in ["input[data-setting='url']", "input.attachment-details-copy-link", "input.urlfield"]:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                val = (els[0].get_attribute("value") or "").strip()
                if val.startswith("http://") or val.startswith("https://"):
                    return val

        # 3) textarea copy link (một số WP dùng textarea)
        for sel in ["textarea[data-setting='url']", "textarea.attachment-details-copy-link"]:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                val = (els[0].get_attribute("value") or "").strip()
                if val.startswith("http://") or val.startswith("https://"):
                    return val

        return ""

    url_value = ""
    for _ in range(40):  # tối đa ~20s
        url_value = try_get_url()
        if url_value:
            break
        time.sleep(0.5)

    # đóng modal (không cần insert)
    try:
        driver.find_element(By.CSS_SELECTOR, "button.media-modal-close").click()
    except:
        pass

    if not url_value:
        # Debug nhẹ: in ra text sidebar để bạn xem nó đang có gì
        try:
            sidebar = driver.find_element(By.CSS_SELECTOR, ".media-sidebar, .attachment-details")
            print("DEBUG SIDEBAR TEXT:", sidebar.text[:800])
        except:
            print("DEBUG: không lấy được sidebar")

        raise RuntimeError(f"Upload xong nhưng không lấy được URL media: {file_path}")

    return url_value
def wp_media_upload_and_get_url_1(driver, wait: WebDriverWait, file_path: str) -> str:
    """
    Mở modal Media, upload 1 file, lấy URL ảnh (URL thật trên site WP), rồi đóng modal.
    Trả về source_url của ảnh đã upload.
    """
    # mở modal
    add_media = wait.until(EC.element_to_be_clickable((By.ID, "insert-media-button")))
    add_media.click()

    # đảm bảo vào tab Upload Files (tuỳ WP sẽ có/không)
    try:
        upload_tab = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR,
            "#menu-item-upload, .media-menu-item[data-route='upload']"
        )))
        upload_tab.click()
    except:
        pass

    # input file
    file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']")))
    file_input.send_keys(file_path)

    # chờ phần “Attachment details” hiện ra để lấy URL
    # WordPress classic thường có input data-setting="url"
    url_value = ""

    def try_get_url():
        selectors = [
            "input[data-setting='url']",
            "input.attachment-details-copy-link",
            "#attachment-details-two-column-copy-link",
            "input.urlfield",
        ]
        for sel in selectors:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                val = (els[0].get_attribute("value") or "").strip()
                if val.startswith("http://") or val.startswith("https://"):
                    return val
        return ""

    # đợi tối đa 20s để WP upload xong và render url field
    for _ in range(40):
        url_value = try_get_url()
        if url_value:
            break
        # đôi khi cần chọn attachment vừa upload
        # thử click thumbnail đầu tiên nếu có
        try:
            thumbs = driver.find_elements(By.CSS_SELECTOR, "ul.attachments li.attachment")
            if thumbs:
                driver.execute_script("arguments[0].click();", thumbs[0])
        except:
            pass
        import time
        time.sleep(0.5)

    # đóng modal (không cần “Chèn vào bài viết” vì ta tự thay src trong HTML)
    try:
        close_btn = driver.find_element(By.CSS_SELECTOR, "button.media-modal-close")
        close_btn.click()
    except:
        # fallback ESC
        from selenium.webdriver.common.keys import Keys
        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.ESCAPE)

    if not url_value:
        raise RuntimeError(f"Upload xong nhưng không lấy được URL media: {file_path}")

    return url_value

def safe_click(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    driver.execute_script("arguments[0].click();", element)


def set_featured_image_latest(driver, wait):
    # Mở modal "Ảnh tiêu biểu"
    btn = wait.until(EC.element_to_be_clickable((By.ID, "set-post-thumbnail")))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    driver.execute_script("arguments[0].click();", btn)

    # Chờ modal
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".media-modal")))

    # Nếu có tab "Thư viện" thì click (để chắc chắn đang ở Library)
    tabs = driver.find_elements(By.CSS_SELECTOR, ".media-router .media-menu-item")
    for t in tabs:
        if "Thư viện" in (t.text or ""):
            driver.execute_script("arguments[0].click();", t)
            time.sleep(0.2)
            break

    # Chờ danh sách ảnh
    for _ in range(60):
        items = driver.find_elements(By.CSS_SELECTOR, "ul.attachments li.attachment")
        if items:
            break
        time.sleep(0.25)
    else:
        raise TimeoutException("Không thấy attachments trong modal ảnh tiêu biểu.")

    # Click item mới nhất (cuối danh sách)
    items = driver.find_elements(By.CSS_SELECTOR, "ul.attachments li.attachment")
    last = items[0]  # chú ý: WP thường render mới nhất ở đầu
    # nếu bạn thấy mới nhất nằm cuối thì đổi thành items[-1]
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", last)
    driver.execute_script("arguments[0].click();", last)

    # Chờ nút "Chọn ảnh tiêu biểu" hết disabled rồi bấm
    select_btn = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "button.media-button-select")
    ))

    # đợi enabled
    for _ in range(60):
        dis = select_btn.get_attribute("disabled")
        if not dis:
            break
        time.sleep(0.2)
    else:
        raise TimeoutException("Nút 'Chọn ảnh tiêu biểu' vẫn bị disabled, không chọn được ảnh.")

    driver.execute_script("arguments[0].click();", select_btn)

    # Chờ thumbnail xuất hiện ở metabox
    for _ in range(60):
        if driver.find_elements(By.CSS_SELECTOR, "#postimagediv img"):
            return True
        time.sleep(0.25)

    raise TimeoutException("Đã bấm 'Chọn ảnh tiêu biểu' nhưng chưa thấy thumbnail hiển thị.")

def select_category_by_name(driver, wait, cat_name: str):
    cat_name = (cat_name or "").strip()
    if not cat_name:
        return False

    # danh sách category
    wait.until(EC.presence_of_element_located((By.ID, "categorychecklist")))

    labels = driver.find_elements(By.CSS_SELECTOR, "#categorychecklist label")
    for lb in labels:
        text = (lb.text or "").strip()
        if text.lower() == cat_name.lower():
            # label thường chứa input checkbox
            cb = lb.find_element(By.TAG_NAME, "input")
            if not cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
            return True

    print("Không tìm thấy category:", cat_name)
    return False

def set_featured_image_latest(driver, wait):
    print("SET FEATURED IMAGE VIA WP MEDIA STATE")

    # 1. Mở modal Ảnh tiêu biểu
    open_btn = wait.until(EC.element_to_be_clickable((By.ID, "set-post-thumbnail")))
    driver.execute_script("arguments[0].click();", open_btn)

    # 2. Chờ modal
    modal = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".media-modal")))

    # 3. Chờ danh sách ảnh
    for _ in range(60):
        items = modal.find_elements(By.CSS_SELECTOR, "li.attachment[data-id]")
        if items:
            break
        time.sleep(0.25)
    else:
        raise TimeoutException("Không tìm thấy attachment nào")

    # 4. Lấy ảnh mới nhất (thường là item đầu)
    att = items[0]
    att_id = int(att.get_attribute("data-id"))
    print("Using attachment id:", att_id)

    # 5. JS: set selection + set featured image (CỐT LÕI)
    ok = driver.execute_script(
        """
        if (!window.wp || !wp.media) return false;

        const frame = wp.media.frame;
        if (!frame) return false;

        const selection = frame.state().get('selection');
        selection.reset();

        const attachment = wp.media.attachment(arguments[0]);
        attachment.fetch();
        selection.add(attachment);

        if (wp.media.featuredImage && wp.media.featuredImage.set) {
            wp.media.featuredImage.set(arguments[0]);
        }

        return true;
        """,
        att_id
    )

    if not ok:
        raise RuntimeError("Không thể set featured image bằng wp.media")

    # 6. Đóng modal
    try:
        close_btn = driver.find_element(By.CSS_SELECTOR, ".media-modal-close")
        driver.execute_script("arguments[0].click();", close_btn)
    except:
        pass

    # 7. Chờ thumbnail hiển thị
    for _ in range(60):
        if driver.find_elements(By.CSS_SELECTOR, "#postimagediv img"):
            print("Featured image set OK")
            return True
        time.sleep(0.25)

    raise TimeoutException("Set featured image xong nhưng không thấy thumbnail")


def set_wp_publish_datetime(driver, wait, dt):
    """
    Set ngày/giờ đăng bài cho WordPress Classic Editor.
    Không dùng clear()/send_keys() để tránh InvalidElementState.
    """
    # bấm "Chỉnh sửa" thời gian (Publish box)
    edit_links = driver.find_elements(By.CSS_SELECTOR, "a.edit-timestamp")
    if edit_links:
        driver.execute_script("arguments[0].click();", edit_links[0])
    else:
        # fallback: tìm link có chữ "Chỉnh sửa"
        for a in driver.find_elements(By.TAG_NAME, "a"):
            if "chỉnh sửa" in (a.text or "").lower():
                driver.execute_script("arguments[0].click();", a)
                break

    # chờ input xuất hiện
    wait.until(EC.presence_of_element_located((By.ID, "mm")))

    # set giá trị bằng JS
    driver.execute_script(
        """
        (function(mm,jj,aa,hh,mn){
          function setVal(id,val){
            var el=document.getElementById(id);
            if(!el) return;
            el.value = val;
            el.dispatchEvent(new Event('input',{bubbles:true}));
            el.dispatchEvent(new Event('change',{bubbles:true}));
          }
          setVal('mm', mm);
          setVal('jj', jj);
          setVal('aa', aa);
          setVal('hh', hh);
          setVal('mn', mn);
        })(arguments[0],arguments[1],arguments[2],arguments[3],arguments[4]);
        """,
        f"{dt.month:02d}",
        f"{dt.day:02d}",
        str(dt.year),
        f"{dt.hour:02d}",
        f"{dt.minute:02d}",
    )

    time.sleep(0.2)

    # bấm OK
    ok_btns = driver.find_elements(By.CSS_SELECTOR, "#timestampdiv .save-timestamp")
    if ok_btns:
        driver.execute_script("arguments[0].click();", ok_btns[0])
    else:
        # fallback: nút OK dạng input/button khác
        for b in driver.find_elements(By.CSS_SELECTOR, "#timestampdiv button, #timestampdiv input"):
            if "ok" in ((b.get_attribute("value") or "") + " " + (b.text or "")).strip().lower():
                driver.execute_script("arguments[0].click();", b)
                break


def replace_images_in_html(content_html: str, base_source: str, upload_func) -> str:
    """
    - Parse content_html
    - Với mỗi img src: normalize -> download -> upload -> replace src bằng url mới
    upload_func(img_url_abs) phải trả về url mới trên WP
    """
    soup = BeautifulSoup(content_html or "", "html.parser")
    imgs = soup.find_all("img")
    if not imgs:
        return str(soup)

    # map để tránh upload trùng nếu cùng 1 src
    mapped = {}

    for img in imgs:
        src = (img.get("src") or "").strip()
        if not src:
            continue

        src_abs = normalize_img_url(src, base_source)
        if not src_abs:
            continue

        if src_abs in mapped:
            img["src"] = mapped[src_abs]
            continue

        new_url = upload_func(src_abs)
        mapped[src_abs] = new_url
        img["src"] = new_url

    return str(soup)

class NewsPoster:
    def __init__(self):
        service = Service(CHROMEDRIVER_PATH)
        chrome_options = Options()
        chrome_options.binary_location = CHROME_BINARY

        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")

        if USE_PROFILE:
            chrome_options.add_argument(rf"--user-data-dir={PROFILE_DIR}")
            chrome_options.add_argument("--profile-directory=Default")

        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)

        # nhớ domain nào đã login rồi
        self.logged_sites = set()

    def close(self):
        try:
            self.driver.quit()
        except:
            pass

    # =========================
    # LOGIN (chỉ 1 lần / domain)
    # =========================
    def ensure_wp_login(self, base: str, login_url: str,
                    username: str, password: str) -> bool:
        # dùng self.logged_sites thay vì truyền logged_sites vào
        if base in self.logged_sites:
            return True

        self.driver.get(login_url)
        wait = WebDriverWait(self.driver, 15)

        try:
            user_el = wait.until(EC.presence_of_element_located((By.ID, "user_login")))
            pass_el = wait.until(EC.presence_of_element_located((By.ID, "user_pass")))
            btn_el  = wait.until(EC.element_to_be_clickable((By.ID, "wp-submit")))
        except TimeoutException:
            print("Không thấy form WP login:", login_url)
            return False

        user_el.clear()
        user_el.send_keys(username)

        pass_el.clear()
        pass_el.send_keys(password)

        btn_el.click()

        try:
            wait.until(lambda d: ("wp-admin" in d.current_url) or (len(d.find_elements(By.ID, "wpadminbar")) > 0))
        except TimeoutException:
            print("Login WP có thể thất bại:", base, "URL hiện tại:", self.driver.current_url)
            return False

        self.logged_sites.add(base)
        print("WP Login OK:", base)
        return True


    # =========================
    # POST (KHUNG) - bạn điền theo trang đăng bài thật
    # =========================
    def post_one(self, anew: list) -> bool:
        # 1) Map dữ liệu
        # Bạn sửa index title cho đúng dữ liệu thật
        title = (anew[2] or "").strip() if len(anew) > 2 else ""
        content_html = (anew[3] or "").strip() if len(anew) > 3 else ""
        base_source = get_base(anew[6]) if len(anew) > 6 else ""
        base_target = anew[7]
        if not title or not content_html:
            print("Thiếu title/content, bỏ qua")
            return False

        # 2) Vào trang tạo bài mới
        # base WP đích chính là base của login_url bạn đã dùng khi login
        # ở run() bạn đã có base, bạn có thể truyền base vào post_one nếu muốn.
        # Ở đây lấy từ driver.current_url sau login: an toàn nhất là dùng base_source nếu site nguồn = site wp đích
        # Nếu site đích khác site nguồn, bạn nên truyền base_wp vào.
        base_wp = base_source
        create_url = base_target + "wp-admin/post-new.php"

        self.driver.get(create_url)

        # 3) Điền tiêu đề
        title_el = self.wait.until(EC.presence_of_element_located((By.ID, "title")))
        title_el.clear()
        title_el.send_keys(title)

        # 4) Upload ảnh và thay src trong HTML
        def _upload_one_image(img_abs_url: str) -> str:
            local_path = download_image(img_abs_url)
            return wp_media_upload_and_get_url(self.driver, self.wait, local_path)

        new_html = replace_images_in_html(
            content_html=content_html,
            base_source=base_source,
            upload_func=_upload_one_image
        )

        # 5) Chuyển sang tab “Văn bản” và set HTML
        try:
            self.driver.find_element(By.ID, "content-html").click()
        except:
            pass

        content_box = self.wait.until(EC.presence_of_element_located((By.ID, "content")))
        content_box.clear()
        content_box.send_keys(new_html)


        
        # === SET NGÀY ĐĂNG THEO BÀI GỐC ===
        post_date = anew[12]  # kiểu date

        if post_date:
            dt = date_to_datetime(post_date, hour=8, minute=0)
            set_wp_publish_datetime(self.driver, self.wait, dt)
        # --- Category ---
        cat_name = (anew[9] or "").strip() if len(anew) > 9 else ""
        select_category_by_name(self.driver, self.wait, cat_name)

        # --- Featured image ---
        set_featured_image_latest(self.driver, self.wait)
        # 6) Đăng bài
        publish_btn = self.wait.until(EC.presence_of_element_located((By.ID, "publish")))
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", publish_btn)
        time.sleep(0.2)
        self.driver.execute_script("arguments[0].click();", publish_btn)

        # 7) Chờ thông báo thành công
        # WP classic thường có #message.updated
        try:
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#message.updated, #message.notice-success")))
        except:
            # không thấy message vẫn có thể đăng thành công, cứ coi là OK nếu URL có post=
            pass

        print("Đăng bài xong:", title)
        return True


    # =========================
    # MAIN LOOP
    # =========================
    def run(self):
        news = hp.read_news()
        
        for anew in news:
            anew = list(anew)

            base = get_base(anew[7])
            login_url = base + "wp-login.php"

            print("\n==============================")
            print("BASE:", base)
            print("LOGIN_URL:", login_url)

            ok = self.ensure_wp_login(
                base=base,
                login_url=login_url,
                username=EMAIL,
                password=PASSWORD
            )
            if not ok:
                continue

            self.post_one(anew)
            hp.update_upload_new(anew[0])
            time.sleep(0.5)



if __name__ == "__main__":
    bot = NewsPoster()
    try:
        bot.run()
    finally:
        bot.close()
