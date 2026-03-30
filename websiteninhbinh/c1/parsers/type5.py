from .base import BaseParser
from urllib.parse import urljoin
import re
from datetime import date
from .. import utils
import CameraObject as camob
import helpers as hp
from ..config import FROM_DATE


class Type5Parser(BaseParser):
    def parse_list(self, soup, scraper) -> bool:
        """
        Structure: section.Article-Detail-listType5 > article.item-block.detail-list-type-5
        OR section#section23.Article-Detail-listType5 > div.listType6.news-item
        """
        # Check for new structure first (user provided)
        section_new = soup.select_one("section.Article-Detail-listType5")
        if section_new:
            items = section_new.select("div.listType6.news-item")
            if items:
                print(
                    f"--> [Type5Parser] Phát hiện cấu trúc mới: Article-Detail-listType5 | {len(items)} bài"
                )
                count_new = 0

                for item in items:
                    # Title and Link
                    title_a = item.select_one("div.content-title div.news-title a")
                    if not title_a:
                        continue

                    href = title_a.get("href")
                    full_url = urljoin(scraper.base, href)
                    title = utils.clean_spaces(title_a.get("title") or title_a.get_text())
                    if not title:
                        continue

                    # Date
                    pub_date = None
                    time_span = item.select_one("span.time-news")
                    if time_span:
                        date_text = time_span.get_text().strip()
                        # Remove icon: <i class="fa fa-calendar" aria-hidden="true"></i>
                        date_text = re.sub(r'<[^>]+>', '', date_text).strip()
                        pub_date = utils.parse_vn_date_any(date_text)

                    if pub_date and pub_date < FROM_DATE:
                        print(f"   [Type5] Bỏ qua vì bài cũ ({pub_date}): {title[:40]}...")
                        continue

                    # Image
                    thumb = ""
                    img_a = item.select_one("div.images-news a")
                    if img_a:
                        img_tag = img_a.select_one("img")
                        if img_tag:
                            src = img_tag.get("src")
                            if src and not src.startswith('data:'):
                                thumb = urljoin(scraper.base, src)

                    # Description
                    intro = ""
                    brief_div = item.select_one("div.brief")
                    if brief_div and brief_div.get_text().strip():
                        intro = utils.clean_spaces(brief_div.get_text())

                    # Check duplicate
                    if not hp.check_cam_url(scraper.url_id, full_url, title):
                        print(f"   [Type5] Đã có trong DB: {title[:40]}...")
                        continue

                    # Create object
                    cam = camob.CameraObject(0, title, 0, full_url, "", scraper.cat_id)
                    cam.date_publish = pub_date
                    cam.thumb = thumb
                    cam.short = intro

                    if scraper.camlist.add_cam(cam):
                        scraper.url_links.append(full_url)
                        count_new += 1

                print(f"--> [Type5Parser] Thêm {count_new} bài (cấu trúc mới).")
                return True

        # Original structure
        items = soup.select(
            "section.Article-Detail-listType5 article.item-block.detail-list-type-5"
        )
        if not items:
            return False

        print(
            f"--> [Type5Parser] Phát hiện cấu trúc: detail-list-type-5 | {len(items)} bài"
        )
        count_new = 0

        for item in items:
            # 1. Title + Link
            # <h3 class="entry-title"> <a href="...">...</a> </h3>
            h3_a = item.select_one("h3.entry-title a")
            if not h3_a:
                continue

            href = h3_a.get("href")
            full_url = urljoin(scraper.base, href)
            title = utils.clean_spaces(h3_a.get("title") or h3_a.get_text())
            if not title:
                continue

            # 2. Date
            # Date is usually NOT in the list item for this type (only in detail),
            # OR we have to rely on parsing detail page later.
            # But let's check if there is any hidden date or we skip date check here.
            # In user example: No visible date in list item.
            pub_date = None

            # NOTE: If we cannot find date in list, we usually add it to queue and check date in Detail.
            # OR we try to find it via other means.

            # 3. Image
            thumb = ""
            img_tag = item.select_one("figure.post-image img")
            if img_tag:
                src = img_tag.get("src")
                thumb = urljoin(scraper.base, src)

            # 4. Description
            intro = ""
            desc_div = item.select_one("div.post-content")
            if desc_div:
                intro = utils.clean_spaces(desc_div.get_text())

            # Check duplicate
            if not hp.check_cam_url(scraper.url_id, full_url, title):
                continue

            # Create object
            cam = camob.CameraObject(0, title, 0, full_url, "", scraper.cat_id)
            cam.date_publish = pub_date  # None for now
            cam.thumb = thumb
            cam.short = intro

            if scraper.camlist.add_cam(cam):
                scraper.url_links.append(full_url)
                count_new += 1

        print(f"--> [Type5Parser] Thêm {count_new} bài.")
        return True

    def parse_detail(self, soup, scraper) -> bool:
        """
        Structure: article.news-detail-layout-type-2
        (Shared with Type2 but might need specific cleanup)
        """
        # The user provided detail example has id="article32" class="news-detail-layout-type-2 mb-20"
        article = soup.select_one("article.news-detail-layout-type-2")
        if not article:
            return False

        # Verify if it matches specific Type5 markers if necessary,
        # or just treat it as generic Type2 if structure is identical.
        # User requested: "loại bỏ các thông tin không cần thiết"
        # The structure is very similar to Type2, but let's be explicitly safe.

        current_cam = scraper.get_current_cam()
        if not current_cam:
            return False

        print("   -> [Type5Parser] Cấu trúc: news-detail-layout-type-2")

        # Title
        h1 = article.select_one("h1.title-detail")
        if h1:
            current_cam.name = utils.clean_spaces(h1.get_text())

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

        # Date handling
        d = utils.parse_datetime_module34(soup) or utils.parse_vn_datetime_from_soup(soup)

        # ======= QUÉT ĐÍNH KÈM =======
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
        # =============================

        # Cleanup trash
        # User input shows:
        # - div.social-connect (Facebook share etc)
        # - div#audio32
        # - div.block-core-a5 > p > a.view-gallery (images) -> KEEP images, maybe remove wrapper?
        # - div.rating
        # - div.show-article.mb-15 (Tin lien quan button)
        # - div.relatedArticles.mb-15.hidden

        for sel in [
            "div.social-connect",
            "div.block_share",
            "div.rating",
            "div.network-share",
            "div.author",  # "Lượt xem: 29"
            "div.source",
            "div.show-article",
            "div.relatedArticles",
            "div[id^='audio']",  # audio32, audio20...
            "style",
            "script",
        ]:
            for t in article.select(sel):
                t.decompose()

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

        # Process
        scraper.process_content(current_cam, tag_content, d)
        return True
