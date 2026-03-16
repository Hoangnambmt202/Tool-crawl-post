from .base import BaseParser
from urllib.parse import urljoin
from datetime import date
import helpers as hp
from .. import utils
from ..config import FROM_DATE


class Type11Parser(BaseParser):
    def parse_list(self, soup, scraper) -> bool:
        """
        UIArticleInMenu_Default list structure.
        """
        container = soup.select_one("div.UIArticleInMenu_Default ul.ArticleList")
        if not container:
            return False

        items = container.select("li.row")
        if not items:
            return False

        print(f"--> [Type11Parser] Phát hiện cấu trúc: UIArticleInMenu_Default | {len(items)} bài")
        count_new = 0

        for item in items:
            a_tag = item.select_one("h2.Title a")
            if not a_tag:
                continue

            href = urljoin(scraper.base, a_tag.get("href"))
            title = utils.clean_spaces(a_tag.get_text())

            if not title:
                continue

            # Date
            pub_date = None
            date_div = item.select_one("div.Ngaydang")
            if date_div:
                pub_date = utils.parse_vn_date_any(date_div.get_text())

            if pub_date and FROM_DATE and pub_date < FROM_DATE:
                continue

            # Image
            thumb = ""
            img_tag = item.select_one("div.col-lg-2 img.image")
            if img_tag:
                src = img_tag.get("src")
                if src:
                    thumb = urljoin(scraper.base, src)

            # Summary
            summary = ""
            p_tag = item.find("p")
            if p_tag:
                summary = utils.clean_spaces(p_tag.get_text())

            if hp.check_cam_url(scraper.url_id, href, title):
                cam = scraper.camlist.create_cam(title, href, scraper.cat_id)
                cam.date_publish = pub_date
                cam.thumb = thumb
                cam.short = summary

                if scraper.camlist.add_cam(cam):
                    scraper.url_links.append(href)
                    count_new += 1
                else:
                    print(f"   [Type11Parser] Bỏ qua (trùng trong danh sách tạm): {title}")

        print(f"--> [Type11Parser] Thêm {count_new} bài.")
        return True

    def parse_detail(self, soup, scraper) -> bool:
        article = soup.select_one("div.ArticleDetailControl")
        if not article:
            return False

        print("   -> [Type11Parser] Cấu trúc: ArticleDetailControl")

        current_cam = scraper.get_current_cam()
        if not current_cam:
            return False

        # TITLE: lấy h1 hoặc thẻ div.ArticleHeader trước khi xóa rác
        h1 = article.select_one("div.ArticleHeader")
        if h1:
            current_cam.name = utils.clean_spaces(h1.get_text())

        # DateTime
        d = None
        date_div = article.select_one("div.PostDate")
        if date_div:
            d = utils.parse_vn_datetime_any(date_div.get_text())
        if not d:
            d = utils.parse_vn_datetime_from_soup(soup)

        # Xóa rác trước khi quét iframe/file để tránh quét nhầm plugin Zalo/Fb
        TRASH_SELECTORS = [
            "div.tool",
            "div.UISocialShare",
            "style",
            "script",
            "div.author", 
            "div.ArticleHeader",
            "div.PostDate",
            "div.ArticleSummary",
            "img.ImgDetailImage",
        ]
        
        for sel in TRASH_SELECTORS:
            for t in article.select(sel):
                t.decompose()

        # Xử lý quét đính kèm
        file_links = []
        for a_el in article.select("a.link-download, a.view-gallery, a[href$='.pdf'], a[href$='.doc'], a[href$='.docx'], a[href$='.xls'], a[href$='.xlsx']"):
            href_val = a_el.get("href", "")
            if href_val and not href_val.startswith("javascript:") and not href_val.startswith("#"):
                full_link = urljoin(scraper.base, href_val)
                text = utils.clean_spaces(a_el.get_text()) or "Tập tin đính kèm"
                if not any(existing[1] == full_link for existing in file_links):
                    file_links.append((text, full_link))

        for iframe in article.select("iframe"):
            src = iframe.get("src", "")
            if "youtube.com" in src or "youtu.be" in src:
                continue
            if "file=" in src:
                try:
                    f_link = src.split("file=")[1].split("&")[0].split("#")[0]
                    full_link = urljoin(scraper.base, f_link)
                    if not any(existing[1] == full_link for existing in file_links):
                        file_links.append(("Xem tài liệu", full_link))
                except Exception:
                    pass
            elif src.startswith("http") and not any(ext in src.lower() for ext in [".html", ".php"]):
                if not any(existing[1] == src for existing in file_links):
                    file_links.append(("Xem tài liệu", src))

        # Nội dung chính
        content_div = article.select_one("div.ArticleContent")
        if content_div:
            tag_content = content_div
        else:
            tag_content = article

        if not tag_content:
            return False

        # Thêm lại link đính kèm nếu có
        if file_links:
            p = soup.new_tag("p")
            p.string = "Tài liệu đính kèm:"
            tag_content.append(p)
            ul = soup.new_tag("ul")
            for name, link in file_links:
                li = soup.new_tag("li")
                a_tag = soup.new_tag("a", href=link, target="_blank")
                a_tag["class"] = ["link-download"]
                a_tag.string = name if name else "Tải về"
                li.append(a_tag)
                ul.append(li)
            tag_content.append(ul)

        # Đánh dấu marker để dangbai_c1.py biết trường hợp này paste trực tiếp
        marker = soup.new_string("<!-- TYPE_DIRECT_PASTE -->")
        tag_content.append(marker)

        scraper.process_content(current_cam, tag_content, d)
        return True
