from .base import BaseParser
from urllib.parse import urljoin
import helpers as hp
from .. import utils
from ..config import FROM_DATE


class TypeDefaultParser(BaseParser):
    def parse_list(self, soup, scraper) -> bool:
        """
        Structure: section.Article-Detail-default > article.detailType2.Article-News
        Extracts: h4.entry-title a, time.post-date, figure.post-image img, div.post-content
        """
        section = soup.select_one("section.section-list.Article-Detail-default")
        if not section:
            return False

        items = section.select("article.detailType2.Article-News")
        if not items:
            return False

        print(
            f"--> [TypeDefaultParser] Phát hiện cấu trúc: Article-Detail-default | {len(items)} bài"
        )
        count_new = 0

        for item in items:
            # 1. Title + Link
            # <h4 class="entry-title"> <a href="...">...</a> </h4>
            a_tag = item.select_one("h4.entry-title a")
            if not a_tag:
                # Fallback: any a tag inside post-title
                a_tag = item.select_one("div.post-title a")
            if not a_tag:
                continue

            href = urljoin(scraper.base, a_tag.get("href"))
            title = utils.clean_spaces(a_tag.get("title") or a_tag.get_text())
            if not title:
                continue

            # 2. Date
            # <time class="post-date updated" datetime="2025-10-30T10:31:51+07:00">30/10/2025</time>
            pub_date = None
            time_tag = item.select_one("time.post-date")
            if time_tag:
                # Try text first (dd/mm/yyyy format)
                pub_date = utils.parse_vn_date_any(time_tag.get_text())
                # Fallback: datetime attribute (ISO format)
                if not pub_date and time_tag.get("datetime"):
                    pub_date = utils.parse_vn_date_any(time_tag.get("datetime"))

            # Also check span.date if time tag not found
            if not pub_date:
                date_span = item.select_one("span.date")
                if date_span:
                    pub_date = utils.parse_vn_date_any(date_span.get_text())

            # 3. Image
            thumb = ""
            img = item.select_one("figure.post-image img")
            if img:
                # Prefer data-original (lazy load) over src (often placeholder)
                src = img.get("data-original") or img.get("src")
                if src and "no-image" not in src:
                    thumb = urljoin(scraper.base, src)

            # 4. Summary
            summary = ""
            content_div = item.select_one("div.post-content")
            if content_div:
                summary = utils.clean_spaces(content_div.get_text())

            # Check duplicate
            if hp.check_cam_url(scraper.url_id, href, title):
                cam = scraper.camlist.create_cam(title, href, scraper.cat_id)
                cam.date_publish = pub_date
                cam.thumb = thumb
                cam.short = summary

                if scraper.camlist.add_cam(cam):
                    scraper.url_links.append(href)
                    count_new += 1
            else:
                print(f"   [Trùng DB] {title[:60]}")

        print(f"--> [TypeDefaultParser] Thêm {count_new} bài.")
        return True

    def parse_detail(self, soup, scraper) -> bool:
        """
        Structure: article.news-detail-layout-type-2
        Note: This is shared with Type2Parser/Type5Parser,
        but here we handle it specifically for Article-Detail-default context.
        """
        article = soup.select_one("article.news-detail-layout-type-2")
        if not article:
            return False

        current_cam = scraper.get_current_cam()
        if not current_cam:
            return False

        print("   -> [TypeDefaultParser] Cấu trúc: news-detail-layout-type-2")

        # TITLE
        # <h1 class="title-detail">...</h1>
        h1 = article.select_one("h1.title-detail")
        if h1:
            current_cam.name = utils.clean_spaces(h1.get_text())

        # DATE
        # <span class="post-date left">Thứ năm, 30/10/2025<span class="drash"> | </span>10:31</span>
        d = None
        date_span = article.select_one("span.post-date")
        if date_span:
            d = utils.parse_vn_datetime_any(date_span.get_text())

        if not d:
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

        # CONTENT
        # Primary: div.brief
        # Fallback: article
        brief_content = article.select_one("div.brief")
        if brief_content:
            tag_content = brief_content
        else:
            tag_content = article

        if not tag_content:
            return False

        # CLEANUP
        for sel in [
            "div.social-connect",
            "div.block_share",
            "div.rating",
            "div.network-share",
            "div.author",
            "div.source",
            "div.show-article",
            "div.relatedArticles",
            "div[id^='audio']",
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
