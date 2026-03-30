from .base import BaseParser
from urllib.parse import urljoin, urlparse, quote
import helpers as hp
from .. import utils
from ..config import FROM_DATE


class Type2Parser(BaseParser):
    def parse_list(self, soup, scraper) -> bool:
        """
        Article-Detail-listmeberpost (section#section33)
        """
        section_member = soup.select_one(
            "section.section-list.Article-Detail-listmeberpost"
        )
        if not section_member:
            return False

        items = section_member.select("article.item-block")
        print(
            f"--> [Type2Parser] Phát hiện cấu trúc: Article-Detail-listmeberpost | {len(items)} bài"
        )
        count_new = 0

        for item in items:
            a_tag = item.select_one("h2.entry-title a")
            if not a_tag:
                continue

            href = urljoin(scraper.base, a_tag.get("href"))
            title = utils.clean_spaces(a_tag.get_text())

            # Date
            pub_date = None
            time_tag = item.select_one("time.post-date")
            if time_tag:
                pub_date = utils.parse_vn_date_any(time_tag.get_text())
                if not pub_date and time_tag.get("datetime"):
                    pub_date = utils.parse_vn_date_any(time_tag.get("datetime"))

            if not pub_date:
                date_span = item.select_one("span.date")
                if date_span:
                    pub_date = utils.parse_vn_date_any(date_span.get_text())

            if pub_date and pub_date < FROM_DATE:
                continue

            # Image
            thumb = ""
            img = item.select_one("figure.post-image img")
            if img:
                thumb = urljoin(scraper.base, img.get("src"))

            # Summary
            summary = ""
            content_div = item.select_one("div.post-content")
            if content_div:
                summary = utils.clean_spaces(content_div.get_text())

            if hp.check_cam_url(scraper.url_id, href, title):
                cam = scraper.camlist.create_cam(title, href, scraper.cat_id)
                cam.date_publish = pub_date
                cam.thumb = thumb
                cam.short = summary

                if scraper.camlist.add_cam(cam):
                    scraper.url_links.append(href)
                    count_new += 1

        print(f"--> [Type2Parser] Thêm {count_new} bài.")
        return True

    def parse_detail(self, soup, scraper) -> bool:
        article = soup.select_one("article.news-detail-layout-type-2")
        if not article:
            return False

        print("   -> [Type2Parser] Cấu trúc: news-detail-layout-type-2")

        # Determine current_cam
        current_cam = scraper.get_current_cam()
        if not current_cam:
            return False

        # TITLE: lấy h1 trước khi xóa rác
        h1 = article.select_one("h1.title-detail")
        if h1:
            current_cam.name = utils.clean_spaces(h1.get_text())

        d = utils.parse_datetime_module34(soup) or utils.parse_vn_datetime_from_soup(soup)

        # ======= XỬ LÝ QUÉT ĐÍNH KÈM (FILE CÔNG KHAI) TRƯỚC KHI XÓA TRASH =======
        file_links = []
        for a_el in article.select(
            "a.link-download, a.view-gallery, a[href$='.pdf'], a[href$='.doc'], a[href$='.docx'], a[href$='.xls'], a[href$='.xlsx']"
        ):
            href_val = a_el.get("href", "")
            if (
                href_val
                and not href_val.startswith("javascript:")
                and not href_val.startswith("#")
            ):
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
            elif src.startswith("http") and not any(
                ext in src.lower() for ext in [".html", ".php"]
            ):
                if not any(existing[1] == src for existing in file_links):
                    file_links.append(("Xem tài liệu", src))
        # ==========================================================================

        # XÓA RÁC: giữ toàn bộ nội dung bài, chỉ loại các phần không liên quan
        TRASH_SELECTORS = [
            "header",  # nút chia sẻ, font size, in bài
            "div.block_share",
            "div.social-connect",  # facebook share iframe
            "div.network-share",
            "div.button-bookmark",
            "style",  # inline styles
            "div[id^='audio']",  # audio player
            "div.rating",  # đánh giá sao
            "div.author",  # lượt xem
            "div.comment", # plugin bình luận
        ]
        for sel in TRASH_SELECTORS:
            for t in article.select(sel):
                t.decompose()

        # Lấy phần content nằm trong div.brief (hoặc div.content-detail với cấu trúc mới)
        # Không thay đổi/xóa cấu trúc bên trong nó để lưu nguyên vẹn vào DB
        brief_content = article.select_one("div.brief")
        content_detail = article.select_one("div.content-detail")
        
        if brief_content:
            tag_content = brief_content
        elif content_detail:
            tag_content = content_detail
        else:
            tag_content = article

        if not tag_content:
            return False

        # Gắn file links vào cuối nếu có
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

        scraper.process_content(current_cam, tag_content, d)
        return True
