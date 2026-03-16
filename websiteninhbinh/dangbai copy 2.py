import os
import re
import time
import uuid
import requests
from datetime import datetime, date
from urllib.parse import urljoin, urlparse, quote_plus

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

import helpers as hp


# =========================
# CONFIG
# =========================
CHROMEDRIVER_PATH = r"F:\soft\chromedriver-win64\chromedriver-win64\chromedriver.exe"
CHROME_BINARY     = r"F:\soft\chrome-win64\chrome-win64\chrome.exe"

EMAIL    = "adminvtk"
PASSWORD = "Khanhkh@nh9999"

USE_PROFILE = False
PROFILE_DIR = r"D:\selenium_profile_itcctv"

TMP_DIR = r"D:\tmp_wp_upload"
DEFAULT_PUBLISH_HOUR = 8
DEFAULT_PUBLISH_MINUTE = 0


# =========================
# BASIC HELPERS
# =========================
def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def safe_js_click(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    driver.execute_script("arguments[0].click();", element)

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
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("http://") or src.startswith("https://"):
        return src
    return urljoin(base_source, src)

def guess_ext_from_url(img_url: str) -> str:
    ext = ".jpg"
    path_part = urlparse(img_url).path.lower()
    for e in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        if path_part.endswith(e):
            return e
    return ext

def _safe_filename_from_url(img_url: str) -> str:
    p = urlparse(img_url)
    name = os.path.basename(p.path) or "image.jpg"
    name = name.split("?")[0].split("#")[0]
    name = re.sub(r"[^a-zA-Z0-9._-]+", "-", name).strip("-")
    if not name:
        name = f"image-{uuid.uuid4().hex}.jpg"
    return name

def download_image(img_url: str, tmp_dir: str = TMP_DIR) -> str:
    ensure_dir(tmp_dir)

    filename = _safe_filename_from_url(img_url)
    stem, ext = os.path.splitext(filename)
    if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        ext = guess_ext_from_url(img_url)

    # thêm suffix để stem khác nhau -> tìm aria-label ổn định
    filename2 = f"{stem}-{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(tmp_dir, filename2)

    r = requests.get(img_url, timeout=60, stream=True)
    r.raise_for_status()
    with open(file_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return file_path


# =========================
# WORDPRESS: EDITOR HELPERS
# =========================
def wp_editor_focus_end(driver):
    driver.execute_script("""
    try {
      if (window.tinymce && tinymce.get('content')) {
        const ed = tinymce.get('content');
        ed.focus();
        ed.selection.select(ed.getBody(), true);
        ed.selection.collapse(false);
        return true;
      }
    } catch(e) {}
    return false;
    """)

def wp_editor_insert_html(driver, html: str):
    html = html or ""
    driver.execute_script("""
    const html = arguments[0];
    try {
      if (window.tinymce && tinymce.get('content')) {
        const ed = tinymce.get('content');
        ed.execCommand('mceInsertContent', false, html);
        ed.save();
        return 'tinymce';
      }
    } catch(e) {}
    const ta = document.getElementById('content');
    if (ta) {
      ta.value = (ta.value || '') + html;
      return 'textarea';
    }
    return 'none';
    """, html)


# =========================
# WORDPRESS: MEDIA MODAL (CÁCH B)
# =========================
def wp_open_add_media_modal(driver, wait: WebDriverWait):
    btn = wait.until(EC.element_to_be_clickable((By.ID, "insert-media-button")))
    safe_js_click(driver, btn)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".media-modal")))

    # chuyển sang tab Upload Files nếu có
    try:
        upload_tab = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR,
            "#menu-item-upload, .media-menu-item[data-route='upload']"
        )))
        safe_js_click(driver, upload_tab)
        time.sleep(0.2)
    except:
        pass

def wp_media_clear_selection(driver):
    driver.execute_script("""
    try {
      // reset selection trong wp.media.editor (Classic Editor)
      if (window.wp && wp.media && wp.media.editor && wp.media.editor.get) {
        const fr = wp.media.editor.get();
        if (fr && fr.state) {
          const st = fr.state();
          if (st && st.get) {
            const sel = st.get('selection');
            if (sel && sel.reset) sel.reset();
          }
        }
      }

      // reset selection trong wp.media.frame (fallback)
      if (window.wp && wp.media && wp.media.frame) {
        const fr2 = wp.media.frame;
        if (fr2 && fr2.state) {
          const st2 = fr2.state();
          if (st2 && st2.get) {
            const sel2 = st2.get('selection');
            if (sel2 && sel2.reset) sel2.reset();
          }
        }
      }

      // dọn tick xanh UI
      document.querySelectorAll('li.attachment[aria-checked="true"]').forEach(el=>{
        el.setAttribute('aria-checked','false');
        el.classList.remove('selected','details');
      });
    } catch(e) {}
    """)

def _get_modal_file_input(driver):
    # ưu tiên input file nằm trong modal
    inputs = driver.find_elements(By.CSS_SELECTOR, ".media-modal input[type='file']")
    if inputs:
        return inputs[0]
    # fallback
    inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
    if inputs:
        return inputs[0]
    return None
def wp_media_upload_pick_insert2(driver, wait, file_path: str) -> int:
    """
    Upload 1 ảnh:
    - WP site này tự chèn ảnh ngay sau upload
    - KHÔNG có nút 'Chèn'
    - Chỉ cần: upload → xác định attachment → đợi modal đóng
    """
    wp_media_clear_selection(driver)

    # input file
    file_input = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, ".media-modal input[type='file'], input[type='file']")
    ))
    file_input.send_keys(file_path)

    # chờ attachments xuất hiện
    wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "ul.attachments, .attachments-browser")
    ))

    stem = os.path.splitext(os.path.basename(file_path))[0]
    att_id = None

    # tìm đúng attachment theo aria-label
    for _ in range(120):
        items = driver.find_elements(
            By.CSS_SELECTOR,
            f"li.attachment[data-id][aria-label*='{stem}']"
        )
        if items:
            item = items[0]
            safe_js_click(driver, item)
            att_id = int(item.get_attribute("data-id"))
            break
        time.sleep(0.25)

    if not att_id:
        # fallback: item đang selected
        sel = driver.find_elements(
            By.CSS_SELECTOR,
            "li.attachment.selected[data-id], li.attachment[aria-checked='true'][data-id]"
        )
        if sel:
            safe_js_click(driver, sel[0])
            att_id = int(sel[0].get_attribute("data-id"))

    if not att_id:
        raise RuntimeError(f"Không xác định được attachment vừa upload: {file_path}")

    # 🔥 ĐIỂM QUAN TRỌNG 🔥
    # Site này tự chèn ảnh → chỉ cần đợi modal đóng
    wait.until(EC.invisibility_of_element_located(
        (By.CSS_SELECTOR, ".media-modal")
    ))

    return att_id

def wp_media_upload_pick_insert(driver, wait: WebDriverWait, file_path: str) -> int:
    """
    Upload 1 file trong modal Add Media và bấm 'Chèn vào bài viết' luôn.
    Mỗi lần chỉ chọn đúng 1 ảnh vừa upload (clear selection trước đó).
    """
    wp_media_clear_selection(driver)

    file_input = _get_modal_file_input(driver)
    if not file_input:
        raise RuntimeError("Không tìm thấy input[type=file] trong Media Modal")

    file_input.send_keys(file_path)

    # chờ danh sách attachments có
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.attachments, .attachments-browser")))

    stem = os.path.splitext(os.path.basename(file_path))[0]
    att_id = None

    # 1) tìm đúng item theo aria-label chứa stem
    for _ in range(220):  # ~55s
        try:
            items = driver.find_elements(By.CSS_SELECTOR, "li.attachment[data-id][aria-label]")
            for it in items:
                al = (it.get_attribute("aria-label") or "")
                if stem in al:
                    safe_js_click(driver, it)
                    att_id = int(it.get_attribute("data-id"))
                    break
            if att_id:
                break
        except StaleElementReferenceException:
            pass
        time.sleep(0.25)

    # 2) fallback: item đang selected
    if not att_id:
        sel = driver.find_elements(By.CSS_SELECTOR, "li.attachment.selected[data-id], li.attachment[aria-checked='true'][data-id]")
        if sel:
            safe_js_click(driver, sel[0])
            att_id = int(sel[0].get_attribute("data-id"))

    if not att_id:
        raise RuntimeError(f"Không xác định được attachment vừa upload: {file_path}")

    # 3) ép selection chỉ còn đúng 1 ảnh vừa upload (cực quan trọng)
    ok = driver.execute_script("""
    try {
      const id = arguments[0];
      if (!window.wp || !wp.media) return false;

      let fr = null;
      if (wp.media.editor && wp.media.editor.get) fr = wp.media.editor.get();
      if (!fr && wp.media.frame) fr = wp.media.frame;
      if (!fr || !fr.state) return false;

      const st = fr.state();
      const sel = st.get('selection');
      sel.reset();

      const att = wp.media.attachment(id);
      att.fetch();
      sel.add(att);

      const btn = document.querySelector('button.media-button-insert');
      if (btn) btn.disabled = false;

      return true;
    } catch(e) { return false; }
    """, int(att_id))

    if not ok:
        raise RuntimeError("Không set selection được bằng wp.media/editor")

    # 4) bấm "Chèn vào bài viết"
    def _find_clickable_insert_button(driver):
        # Ưu tiên các class phổ biến của WP
        candidates = driver.find_elements(
            By.CSS_SELECTOR,
            ".media-modal button.media-button-insert, "
            ".media-modal button.media-button-select, "
            ".media-modal .media-toolbar button.media-button, "
            ".media-modal .media-toolbar-primary button.button-primary"
        )

        # lọc theo text (VN/EN) + trạng thái enabled
        for b in candidates:
            try:
                if not b.is_displayed():
                    continue
                if b.get_attribute("disabled"):
                    continue
                txt = ((b.text or "") + " " + (b.get_attribute("value") or "")).strip().lower()
                # các nhãn hay gặp
                if ("chèn" in txt) or ("insert" in txt) or ("select" in txt) or ("choose" in txt):
                    return b
            except:
                pass

        # fallback: nút primary cuối toolbar
        try:
            b = driver.find_element(By.CSS_SELECTOR, ".media-modal .media-toolbar-primary button")
            if b.is_displayed() and not b.get_attribute("disabled"):
                return b
        except:
            pass

        return None


    # --- bấm nút chèn ---
    deadline = time.time() + 20  # tối đa 20s
    insert_btn = None
    while time.time() < deadline:
        insert_btn = _find_clickable_insert_button(driver)
        if insert_btn:
            break
        time.sleep(0.25)

    if not insert_btn:
        # debug để bạn nhìn đúng trạng thái modal đang ở đâu
        try:
            toolbar = driver.find_element(By.CSS_SELECTOR, ".media-modal .media-toolbar")
            print("DEBUG TOOLBAR:", toolbar.text[:400])
        except:
            print("DEBUG TOOLBAR: cannot read")
        # raise TimeoutException("Không tìm thấy nút 'Chèn vào bài viết/Chọn' trong media modal")
    else:
        safe_js_click(driver, insert_btn)

    # đợi modal đóng
    wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".media-modal")))

    return att_id


# =========================
# WORDPRESS: FEATURED IMAGE
# =========================
def _wait_media_modal_open(wait: WebDriverWait):
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".media-modal")))

def _close_media_modal(driver):
    try:
        btn = driver.find_element(By.CSS_SELECTOR, "button.media-modal-close")
        driver.execute_script("arguments[0].click();", btn)
    except:
        pass
def set_featured_image_by_id(driver, wait: WebDriverWait, attachment_id: int) -> bool:
    """
    Classic Editor: set featured image đúng attachment_id.
    - Mở modal #set-post-thumbnail
    - Dùng wp.media.featuredImage.frame() (đúng frame)
    - Reset selection rồi add attachment(id)
    - Bấm nút primary (Set featured image / Đặt ảnh đại diện / Chọn ảnh tiêu biểu...)
    """

    # 1) mở modal ảnh tiêu biểu
    open_btn = wait.until(EC.element_to_be_clickable((By.ID, "set-post-thumbnail")))
    safe_js_click(driver, open_btn)

    # chờ modal
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".media-modal, .media-frame")))

    # 2) set selection bằng featuredImage frame
    ok = driver.execute_script("""
    try {
      const id = arguments[0];
      if (!window.wp || !wp.media) return {ok:false, why:'no-wp-media'};

      // featured frame (classic)
      let frame = null;
      if (wp.media.featuredImage && wp.media.featuredImage.frame) {
        frame = wp.media.featuredImage.frame();
      }
      // fallback nếu site custom
      if (!frame && wp.media.frame) frame = wp.media.frame;
      if (!frame || !frame.state) return {ok:false, why:'no-frame'};

      const st = frame.state();
      if (!st || !st.get) return {ok:false, why:'no-state'};

      const sel = st.get('selection');
      if (sel && sel.reset) sel.reset();

      const att = wp.media.attachment(id);
      att.fetch();

      // add đúng 1 attachment
      if (sel && sel.add) sel.add(att);

      // bật nút primary (đừng phụ thuộc class cố định)
      document.querySelectorAll('.media-modal button, .media-frame button').forEach(b=>{
        try {
          const t = (b.innerText || b.value || '').toLowerCase();
          if (
            t.includes('set featured') ||
            t.includes('featured image') ||
            t.includes('đặt ảnh') ||
            t.includes('ảnh đại diện') ||
            t.includes('chọn ảnh') ||
            t.includes('select') ||
            t.includes('choose')
          ) b.disabled = false;
        } catch(e) {}
      });

      return {ok:true, why:'ok'};
    } catch(e) {
      return {ok:false, why:String(e)};
    }
    """, int(attachment_id))

    if not ok or not ok.get("ok"):
        # đóng modal cho sạch trạng thái
        try:
            _close_media_modal(driver)
        except:
            pass
        raise RuntimeError(f"Không thể set selection featured image. Debug: {ok}")

    # 3) tìm nút xác nhận theo text (VN/EN) + button-primary
    def find_feature_button():
        candidates = driver.find_elements(By.CSS_SELECTOR,
            ".media-modal .media-toolbar-primary button, "
            ".media-frame .media-toolbar-primary button, "
            ".media-modal button.button-primary, "
            ".media-frame button.button-primary, "
            ".media-modal button.media-button, "
            ".media-frame button.media-button"
        )
        for b in candidates:
            try:
                if not b.is_displayed():
                    continue
                if b.get_attribute("disabled"):
                    continue
                txt = ((b.text or "") + " " + (b.get_attribute("value") or "")).strip().lower()

                # các nhãn thường gặp
                if (
                    "set featured" in txt or
                    "featured image" in txt or
                    "đặt ảnh" in txt or
                    "ảnh đại diện" in txt or
                    "chọn ảnh" in txt or
                    "select" in txt or
                    "choose" in txt
                ):
                    return b

                # fallback: nếu là button-primary và đang hiển thị thì lấy luôn
                cls = (b.get_attribute("class") or "").lower()
                if "button-primary" in cls:
                    return b
            except StaleElementReferenceException:
                continue
            except:
                continue
        return None

    deadline = time.time() + 20
    btn = None
    while time.time() < deadline:
        btn = find_feature_button()
        if btn:
            break
        time.sleep(0.25)

    if not btn:
        # debug toolbar text để bạn nhìn trạng thái
        try:
            tb = driver.find_element(By.CSS_SELECTOR, ".media-modal .media-toolbar, .media-frame .media-toolbar")
            print("DEBUG FEATURE TOOLBAR:", (tb.text or "")[:500])
        except:
            print("DEBUG FEATURE TOOLBAR: cannot read")
        raise TimeoutException("Không tìm thấy nút 'Đặt ảnh đại diện/Set featured image' trong modal.")

    safe_js_click(driver, btn)

    # 4) chờ thumbnail hiện
    for _ in range(120):
        if driver.find_elements(By.CSS_SELECTOR, "#postimagediv img"):
            return True
        time.sleep(0.25)

    raise TimeoutException("Đã bấm đặt ảnh tiêu biểu nhưng chưa thấy thumbnail hiển thị.")
def set_featured_image_by_id2(driver, wait: WebDriverWait, attachment_id: int) -> bool:
    open_btn = wait.until(EC.element_to_be_clickable((By.ID, "set-post-thumbnail")))
    safe_js_click(driver, open_btn)
    _wait_media_modal_open(wait)

    ok = driver.execute_script("""
        try {
        const id = arguments[0];
        if (!window.wp || !wp.media) return false;

        // ưu tiên editor frame
        let fr = null;
        if (wp.media.editor && wp.media.editor.get) fr = wp.media.editor.get();
        if (!fr && wp.media.frame) fr = wp.media.frame;
        if (!fr || !fr.state) return false;

        const st = fr.state();
        const sel = st.get('selection');
        sel.reset();

        const att = wp.media.attachment(id);
        att.fetch();
        sel.add(att);

        // cố gắng bật nút primary
        document.querySelectorAll('.media-modal button').forEach(b=>{
            const t = (b.innerText||'').toLowerCase();
            if (t.includes('chèn') || t.includes('insert') || t.includes('select') || t.includes('choose')) {
            b.disabled = false;
            }
        });

        return true;
        } catch(e) { return false; }
        """, int(attachment_id))

    if not ok:
        _close_media_modal(driver)
        raise RuntimeError("Không thể set featured image bằng wp.media")

    select_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.media-button-select")))
    safe_js_click(driver, select_btn)

    for _ in range(80):
        if driver.find_elements(By.CSS_SELECTOR, "#postimagediv img"):
            return True
        time.sleep(0.25)

    raise TimeoutException("Đã chọn ảnh tiêu biểu nhưng chưa thấy thumbnail hiển thị.")


# =========================
# CATEGORY + PUBLISH DATE (Classic)
# =========================
def select_category_by_name(driver, wait: WebDriverWait, cat_name: str) -> bool:
    cat_name = (cat_name or "").strip()
    if not cat_name:
        return False

    wait.until(EC.presence_of_element_located((By.ID, "categorychecklist")))
    labels = driver.find_elements(By.CSS_SELECTOR, "#categorychecklist label")
    for lb in labels:
        if (lb.text or "").strip().lower() == cat_name.lower():
            cb = lb.find_element(By.TAG_NAME, "input")
            if not cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
            return True

    print("Không tìm thấy category:", cat_name)
    return False

def set_wp_publish_datetime(driver, wait: WebDriverWait, dt: datetime):
    edit_links = driver.find_elements(By.CSS_SELECTOR, "a.edit-timestamp")
    if edit_links:
        safe_js_click(driver, edit_links[0])
    wait.until(EC.presence_of_element_located((By.ID, "mm")))

    driver.execute_script("""
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
    """, f"{dt.month:02d}", f"{dt.day:02d}", str(dt.year), f"{dt.hour:02d}", f"{dt.minute:02d}")

    time.sleep(0.2)
    ok_btns = driver.find_elements(By.CSS_SELECTOR, "#timestampdiv .save-timestamp")
    if ok_btns:
        safe_js_click(driver, ok_btns[0])


# =========================
# CONTENT: CHÈN THEO THỨ TỰ + IMG THÌ UPLOAD&INSERT
# =========================
def wp_insert_content_with_images(driver, wait, content_html: str, base_source: str) -> list[int]:
    """
    Duyệt tuyến tính theo thứ tự trong HTML:
    - gặp img: upload & insert ngay
    - gặp tag khác: insert HTML nguyên khối
    Return: list attachment_id (theo thứ tự xuất hiện)
    """
    soup = BeautifulSoup(content_html or "", "html.parser")
    root = soup.body if soup.body else soup

    inserted_ids = []
    wp_editor_focus_end(driver)

    # duyệt toàn bộ nodes con cấp 1; nếu nguồn hay bọc div lớn, vẫn insert cả div
    # và để chắc chắn img nào cũng đi qua, ta “tách” img ra khỏi khối bằng cách duyệt descendants theo thứ tự.
    # Cách làm: duyệt theo .contents của root, nhưng nếu gặp tag có img bên trong, ta xử lý recursive.
    def walk(node):
        for child in list(getattr(node, "children", [])):
            if getattr(child, "name", None) is None:
                txt = str(child).strip()
                if txt:
                    wp_editor_insert_html(driver, txt)
                continue
            # print (1)
            if child.name.lower() == "img":
                src = (child.get("src") or "").strip()
                if not src:
                    continue

                img_abs = normalize_img_url(src, base_source)
                local_path = ""
                try:
                    local_path = download_image(img_abs)
                    # print (2)
                    wp_open_add_media_modal(driver, wait)
                    att_id = wp_media_upload_pick_insert(driver, wait, local_path)
                    inserted_ids.append(int(att_id))
                    # print (3)
                    wp_editor_focus_end(driver)
                finally:
                    try:
                        if local_path and os.path.isfile(local_path):
                            os.remove(local_path)
                        # print (4)

                    except:
                        pass
            else:
                # nếu bên trong có img, đi sâu để giữ đúng thứ tự
                if child.find("img"):
                    # trước khi đi sâu: nếu tag này có text trước img, vẫn giữ thứ tự
                    walk(child)
                    # print (5)

                else:
                    # insert nguyên khối
                    # print (6)
                    wp_editor_insert_html(driver, str(child))

    walk(root)
    return inserted_ids


# =========================
# DUPLICATE TITLE GUARD
# =========================
def wp_post_exists_by_title(driver, wait: WebDriverWait, base: str, title: str) -> bool:
    title = (title or "").strip()
    if not title:
        return False

    search_url = base + "wp-admin/edit.php?post_type=post&post_status=all&s=" + quote_plus(title)
    driver.get(search_url)
    wait.until(EC.presence_of_element_located((By.ID, "the-list")))

    rows = driver.find_elements(By.CSS_SELECTOR, "#the-list tr")
    for r in rows:
        els = r.find_elements(By.CSS_SELECTOR, "a.row-title")
        if not els:
            continue
        t = (els[0].text or "").strip()
        if t.lower() == title.lower():
            return True
    return False


# =========================
# MAIN BOT
# =========================
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
        self.wait = WebDriverWait(self.driver, 20)
        self.logged_sites = set()

    def close(self):
        try:
            self.driver.quit()
        except:
            pass

    def ensure_wp_login(self, base: str, login_url: str, username: str, password: str) -> bool:
        if base in self.logged_sites:
            return True

        self.driver.get(login_url)
        wait = WebDriverWait(self.driver, 20)

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

    def post_one(self, anew: list) -> bool:
        title = (anew[2] or "").strip() if len(anew) > 2 else ""
        content_html = (anew[3] or "").strip() if len(anew) > 3 else ""
        base_source = get_base(anew[6]) if len(anew) > 6 else ""
        base_target = (anew[7] or "").strip() if len(anew) > 7 else ""

        if not title or not content_html or not base_target:
            print("Thiếu title/content/base_target, bỏ qua")
            return False

        base = get_base(base_target)

        # chống trùng
        try:
            if wp_post_exists_by_title(self.driver, self.wait, base, title):
                print("Đã tồn tại bài cùng tiêu đề, bỏ qua:", title)
                return False
        except Exception as e:
            print("Cảnh báo: không kiểm tra được trùng tiêu đề:", e)

        create_url = base + "wp-admin/post-new.php"
        self.driver.get(create_url)

        # tiêu đề
        title_el = self.wait.until(EC.presence_of_element_located((By.ID, "title")))
        title_el.clear()
        title_el.send_keys(title)

        # xoá nội dung cũ
        self.driver.execute_script("""
        try {
          if (window.tinymce && tinymce.get('content')) {
            tinymce.get('content').setContent('');
            tinymce.get('content').save();
          } else {
            const ta = document.getElementById('content');
            if (ta) ta.value = '';
          }
        } catch(e) {}
        """)

        # chèn nội dung + upload&insert từng ảnh
        uploaded_attachment_ids = wp_insert_content_with_images(
            driver=self.driver,
            wait=self.wait,
            content_html=content_html,
            base_source=base_source
        )
        print(uploaded_attachment_ids)
        # ngày đăng
        post_date = anew[12] if len(anew) > 12 else None
        if post_date:
            dt = date_to_datetime(post_date, hour=DEFAULT_PUBLISH_HOUR, minute=DEFAULT_PUBLISH_MINUTE)
            set_wp_publish_datetime(self.driver, self.wait, dt)

        # category
        cat_name = (anew[9] or "").strip() if len(anew) > 9 else ""
        if cat_name:
            select_category_by_name(self.driver, self.wait, cat_name)

        # featured: lấy ảnh đầu tiên đã insert
        if uploaded_attachment_ids:
            try:
                print('set feature')
                print(uploaded_attachment_ids[0])
                set_featured_image_by_id(self.driver, self.wait, uploaded_attachment_ids[0])
            except Exception as e:
                print("Cảnh báo: set ảnh tiêu biểu thất bại:", e)

        # Publish
        try:
            publish_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "publish")))
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", publish_btn)
            time.sleep(0.2)
            safe_js_click(self.driver, publish_btn)
        except Exception as e:
            print("Không bấm được nút Đăng/Cập nhật:", e)
            return False

        # message success
        try:
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#message.updated, #message.notice-success")))
        except:
            pass

        print("Đăng bài xong:", title)
        return True

    def run(self):
        news = hp.read_news()
        for anew in news:
            anew = list(anew)

            base = get_base(anew[7])
            login_url = base + "wp-login.php"

            print("\n==============================")
            print("BASE:", base)
            print("LOGIN_URL:", login_url)

            ok = self.ensure_wp_login(base, login_url, EMAIL, PASSWORD)
            if not ok:
                continue

            posted = self.post_one(anew)

            # bạn tuỳ quyết định: chỉ update khi posted True
            try:
                hp.update_upload_new(anew[0])
            except:
                pass

            time.sleep(0.5)
            # test 1 bài thì break
            # break


if __name__ == "__main__":
    bot = NewsPoster()
    try:
        bot.run()
    finally:
        bot.close()
