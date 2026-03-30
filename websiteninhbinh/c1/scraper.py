from .parsers import AVAILABLE_PARSERS
import sys
import os
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from urllib.parse import urljoin, urlparse, quote

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import MenuLink as menulink
import CameraObject as camob
import helpers as hp


from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from . import config
from . import utils


class VspProducts:
    def __init__(self, base, url, cat, target):
        self.base = base
        self.cat = cat
        self.target = target
        self.camlist = camob.Listcam()

        # Monkey patch create_cam for compatibility with new parsers
        self.camlist.create_cam = self._create_cam_shim

        self.url_links = []
        self.menu_links = menulink.MenuLink()

        service = Service(config.CHROME_DRIVER_PATH)
        chrome_options = Options()
        chrome_options.binary_location = config.CHROME_BINARY_PATH
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        self.url = url
        self.cat_id = ""
        self.url_id = ""
        self.page_link = 1
        self.current_working_url = ""

    def _create_cam_shim(self, title, url, cat_id):
        # Helper to match what parsers are calling: scraper.camlist.create_cam(title, url, cat_id)
        return camob.CameraObject(0, title, 0, url, "", cat_id)

    def reset_for_row(self):
        self.url_links = []
        self.menu_links = menulink.MenuLink()
        self.camlist = camob.Listcam()
        self.camlist.create_cam = self._create_cam_shim  # Re-apply if reset re-inits
        self.page_link = 1

    def get_data(self):
        """
        Two-phase scraping:
          Phase 1: Scan all list pages, collect detail URLs into self.detail_queue.
          Phase 2: Visit each detail URL and parse content.
        """
        print("=" * 50)
        print(f">> Phase 1: Thu thập danh sách bài viết từ {self.url}")
        print("=" * 50)

        self.detail_queue = []  # Separate list for detail URLs
        self.url_links = []  # Reset (used as temp buffer by parsers)

        # Run Phase 1: collect all detail links
        self._scan_list_pages(self.url)

        print(
            f"\n>> Phase 1 xong: {len(self.detail_queue)} bài viết cần xử lý chi tiết."
        )
        print(f"{'=' * 50}")
        print(">> Phase 2: Xử lý chi tiết bài viết")
        print("=" * 50)

        # Run Phase 2: parse each detail URL
        for i, url in enumerate(self.detail_queue, 1):
            print(f"\n[{i}/{len(self.detail_queue)}] Chi tiết: {url}")
            self._parse_detail_page(url)

        print(f"\n>> Xong! Đã xử lý {len(self.detail_queue)} bài.")

    def close(self):
        try:
            self.driver.quit()
        except:
            pass

    def get_current_cam(self):
        for cam in self.camlist.camobs:
            if cam.url == self.current_working_url:
                return cam
        return None

    def process_content(self, current_cam, tag_content, d):
        # Common content cleaning and saving logic
        if not tag_content:
            return

        # 1. Date
        if d:
            comp_d = d.date() if hasattr(d, 'hour') else d
            if comp_d < config.FROM_DATE:
                print(f"Bài cũ ({d}) < {config.FROM_DATE}. Bỏ qua không xử lý.")
                return

        current_cam.date_publish = d if d else None

        # 2. Remove unnecessary UI elements
        for elem in tag_content.select("div.tool, div.UISocialShare, div.author, div.PostDate, img#ctrl_162921_22_imgImagePath"):
            elem.decompose()

        # 3. Remove authors/trash
        for t in tag_content.select("div.tac_gia_news"):
            t.decompose()

        # 4. Normalize links
        utils.normalize_download_links_in_content(tag_content)

        # 5. Fix images
        for img in tag_content.find_all("img"):
            src = img.get("src")
            if not src:
                continue
            full_src = urljoin(self.base, src)

            parsed = urlparse(full_src)
            encoded_path = quote(parsed.path)
            encoded_src = parsed._replace(path=encoded_path).geturl()

            img["src"] = encoded_src
            img["style"] = "max-width:100%;height:auto;"

        # 6. Fix other links and download documents
        import requests
        import urllib3
        import mimetypes

        # Disable SSL warnings
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        has_document = 0
        documents_to_insert = []
        doc_dir = r"D:\WORKSPACE_CODE\Projects\Web\folder\websiteninhbinh\documents"
        if not os.path.exists(doc_dir):
            try:
                os.makedirs(doc_dir)
            except Exception:
                pass

        for a in tag_content.find_all("a"):
            href = a.get("href")
            if not href:
                continue

            a_classes = a.get("class", [])
            if isinstance(a_classes, str):
                a_classes = a_classes.split()

            is_doc = False
            if (
                "/upload" in href
                or "link_download" in a_classes
                or "link-download" in a_classes
            ):
                is_doc = True

            if is_doc:
                if "http" not in href:
                    if "/upload" in href:
                        idx = href.find("/upload")
                        file_url = str(self.url_name).rstrip("/") + href[idx:]
                    else:
                        file_url = urljoin(str(self.url_name), href)
                else:
                    file_url = href

                a["href"] = file_url
                a["target"] = "_blank"

                try:
                    res = requests.get(file_url, stream=True, timeout=15, verify=False)
                    if res.status_code == 200:
                        file_size = int(res.headers.get("content-length", 0))
                        content_type = res.headers.get("content-type", "")

                        parsed = urlparse(file_url)
                        import re
                        safe_title = current_cam.name.strip()
                        safe_title = re.sub(r'\s+', '_', safe_title)
                        safe_title = re.sub(r'[\\/*?:"<>|]', '', safe_title)
                        
                        original_ext = os.path.splitext(parsed.path)[1]
                        if not original_ext:
                            original_ext = ".pdf"
                            
                        file_name = f"{safe_title}{original_ext}"
                        local_path = os.path.join(doc_dir, file_name)
                        
                        counter = 1
                        while os.path.exists(local_path):
                            file_name = f"{safe_title}_{counter}{original_ext}"
                            local_path = os.path.join(doc_dir, file_name)
                            counter += 1

                        with open(local_path, "wb") as f:
                            for chunk in res.iter_content(8192):
                                f.write(chunk)

                        documents_to_insert.append(
                            {
                                "file_name": file_name,
                                "file_path": local_path,
                                "file_type": content_type,
                                "file_size": file_size,
                                "source_url": file_url,
                            }
                        )
                        has_document = 1
                except Exception as e:
                    print(f"Lỗi tải {file_url}: {e}")
            else:
                a["href"] = urljoin(self.base, href)
                a["target"] = "_blank"

        # 7. Remove scripts/iframes
        for t in tag_content.find_all(["script", "style"]):
            t.decompose()
        for iframe in tag_content.find_all("iframe"):
            src = iframe.get("src", "")
            if (
                "youtube.com" not in src
                and "youtu.be" not in src
                and "pdfjs" not in src
            ):
                iframe.decompose()
            elif "pdfjs" in src:
                iframe["src"] = urljoin(self.base, src)

        # 8. Save
        current_cam.description = str(tag_content)
        current_cam.short = self.target

        current_cam.display_info()
        news_id = hp.save_data_cam(
            self.url_name, current_cam, has_document=has_document
        )
        if news_id and documents_to_insert:
            hp.save_documents(news_id, documents_to_insert)

        print("✅ Đã lưu bài viết và tài liệu (nếu có)")

    def _scan_list_pages(self, start_url):
        """
        Phase 1: Navigate to start_url and paginate through all list pages,
        collecting detail URLs into self.detail_queue.
        """
        try:
            self.driver.get(start_url)
            time.sleep(2)
        except Exception as e:
            print(f"Lỗi tải trang danh sách: {e}")
            return

        page_count = 1
        consecutive_empty = 0
        MAX_EMPTY_PAGES = 3

        while True:
            html = self.driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            print(f">> Đang quét danh sách bài viết (Page {page_count})...")
            before = len(self.detail_queue)

            # Use url_links as temp buffer; parsers append to it
            self.url_links = []
            handled = False
            for parser in AVAILABLE_PARSERS:
                if parser.parse_list(soup, self):
                    handled = True
                    break  # Only use the first matching parser per page

            # Move newly added links to detail_queue
            for link in self.url_links:
                if link not in self.detail_queue:
                    self.detail_queue.append(link)
            self.url_links = []

            if not handled:
                print("❌ Không tìm thấy danh sách bài viết, dừng.")
                break

            added_this_page = len(self.detail_queue) - before
            if added_this_page == 0:
                consecutive_empty += 1
                print(
                    f">> Trang {page_count}: 0 bài mới ({consecutive_empty}/{MAX_EMPTY_PAGES})"
                )
                if consecutive_empty >= MAX_EMPTY_PAGES:
                    print(
                        f">> Dừng: {MAX_EMPTY_PAGES} trang liên tiếp không có bài mới."
                    )
                    break
            else:
                consecutive_empty = 0
                print(
                    f">> Trang {page_count}: +{added_this_page} bài mới (tổng: {len(self.detail_queue)})"
                )

            if self._handle_pagination():
                page_count += 1
                time.sleep(2.5)
            else:
                break

    def _parse_detail_page(self, url):
        """
        Phase 2: Navigate to a detail URL and parse its content.
        """
        self.current_working_url = url

        # Find the cam object for this URL
        current_cam = self.get_current_cam()
        if not current_cam:
            print(f"  ⚠️ Không tìm thấy cam object cho: {url}")
            return

        try:
            self.driver.get(url)
            time.sleep(2)
        except Exception as e:
            print(f"  Lỗi tải trang chi tiết: {e}")
            return

        html = self.driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        for parser in AVAILABLE_PARSERS:
            if parser.parse_detail(soup, self):
                return

        print(f"  ❌ Không tìm thấy parser cho chi tiết: {url}")

    # Legacy method kept for backward compatibility
    def extract_data(self, o_url):
        """Deprecated: use get_data() which runs two-phase scraping."""
        self._parse_detail_page(o_url)

    def _handle_pagination(self):
        """
        Attempts to click Next button.
        Stops when 'a.next' is replaced by 'span.current.next' (last page indicator).
        Logic:
          1. Parse current HTML with BS4.
          2. If ANY pagination bar has 'span.current.next' -> last page -> stop.
          3. If 'a.next' exists and is clickable -> click -> continue.
          4. Otherwise stop.
        """
        try:
            # --- Step 1: Check from BS4 (fast, accurate) ---
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # --- Handle AJAX pagination for UIArticleInMenu_Default ---
            ui_pagination = soup.select_one("div.UIArticleInMenu_Default ul.pagination")
            if ui_pagination:
                active_li = ui_pagination.select_one("li.page-item.page-number.active")
                if active_li:
                    next_li = active_li.find_next_sibling("li", class_="page-number")
                    if next_li:
                        page = next_li.get("data-page")
                        if page:
                            print(f">> Chuyển sang trang tiếp theo (Page {page})...")
                            try:
                                wait = WebDriverWait(self.driver, 4)
                                next_btn = wait.until(
                                    EC.element_to_be_clickable(
                                        (By.XPATH, f"//div[contains(@class, 'UIArticleInMenu_Default')]//ul[contains(@class, 'pagination')]//li[contains(@class, 'page-number') and @data-page='{page}']//a[contains(@class, 'page-link')]")
                                    )
                                )
                                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_btn)
                                time.sleep(0.5)
                                try:
                                    next_btn.click()
                                except Exception:
                                    self.driver.execute_script("arguments[0].click();", next_btn)
                                time.sleep(2)  # Wait for AJAX to complete
                                return True
                            except Exception as ex:
                                print(f"Lỗi click chuyển trang (UIArticle): {ex}")
                                return False
                print(">> Không còn trang tiếp theo (UIArticle).")
                return False
            # ----------------------------------------------------------

            # Find all pagination containers
            pagination_bars = soup.select(
                "div.default-pagination, div.pagination, ul.pagination, nav.pagination, div.page"
            )

            for bar in pagination_bars:
                # 'span.current.next' means we're on last page (or 'span.next-pages' for this specific layout)
                if bar.select_one(
                    "span.current.next, span.next.current, span.next-pages"
                ):
                    print(
                        ">> Trang cuối cùng (span element cho next block). Dừng phân trang."
                    )
                    return False

                # If this bar has no 'a.next' or 'a.next-pages' at all, also stop
                if bar.select_one("a.next, a.next-pages, li.btn-next a"):
                    # Found a real next link in this bar -> proceed to click below
                    break
            else:
                # No pagination bar found OR no a.next in any bar
                # Double-check: is there any a.next or a.next-pages on the page?
                if not soup.select_one("a.next, a.next-pages, li.btn-next a"):
                    print(">> Không còn trang tiếp theo.")
                    return False

            # --- Step 2: Click the next button via Selenium ---
            next_btn = None

            # Primary specific selectors
            try:
                wait = WebDriverWait(self.driver, 4)
                next_btn = wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "a.next, a.next-pages, li.btn-next a")
                    )
                )
            except Exception:
                pass

            # Fallbacks
            if not next_btn:
                fallback_selectors = [
                    "div.default-pagination a.next",
                    "div.pagination a.next",
                    "ul.pagination a.next-pages",
                    "div.col-center a.next",
                    "div.page li.btn-next a",
                    "a.next-pages",
                    "a[rel='next']",
                ]
                for sel in fallback_selectors:
                    try:
                        els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        for el in els:
                            if el.is_displayed():
                                next_btn = el
                                break
                    except Exception:
                        pass
                    if next_btn:
                        break

            if next_btn:
                print(">> Chuyển sang trang tiếp theo (click a.next)...")
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", next_btn
                )
                time.sleep(0.5)
                try:
                    next_btn.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", next_btn)
                return True

            print(">> Không còn trang tiếp theo.")
            return False

        except Exception as ex:
            print("Lỗi phân trang:", ex)
            return False
