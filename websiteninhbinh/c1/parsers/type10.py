from .base import BaseParser
from urllib.parse import urljoin
import re
from datetime import date
from .. import utils
import CameraObject as camob
import helpers as hp


class Type10Parser(BaseParser):
    def parse_list(self, soup, scraper) -> bool:
        """
        news-listType10 structure.
        """
        type10_items = soup.select(
            "section.Article-Detail-listType10 div.news-listType10"
        )
        if not type10_items:
            type10_items = soup.select("div.news-listType10")

        if not type10_items:
            return False

        print(
            f"--> [Type10Parser] Phát hiện cấu trúc: news-listType10 | {len(type10_items)} bài"
        )
        count_new = 0

        for item in type10_items:
            h2_a = item.select_one("div.title-news-listType10 h2 a")
            if not h2_a:
                continue

            href = h2_a.get("href")
            full_url = urljoin(scraper.base, href)
            title = utils.clean_spaces(h2_a.get("title") or h2_a.get_text())

            if not title:
                continue

            # Date
            pub_date = None
            time_span = item.select_one("span.time-news")
            if time_span:
                txt_time = utils.clean_spaces(time_span.get_text())
                m = re.search(
                    r"(\d{1,2})[/-](\d{1,2})[/-](\d{2})", txt_time
                )  # 2 digit year
                if m:
                    d, mo, y_short = map(int, m.groups())
                    y = 2000 + y_short
                    try:
                        pub_date = date(y, mo, d)
                    except:
                        pass
                else:
                    pub_date = utils.parse_vn_date_any(txt_time)

            # Image
            thumb = ""
            img_tag = item.select_one("div.images-news img")
            if img_tag:
                src = img_tag.get("data-original") or img_tag.get("src")
                thumb = urljoin(scraper.base, src)

            # Summary
            excerpt = ""
            brief = item.select_one("div.brief-news")
            if brief:
                excerpt = utils.clean_spaces(brief.get_text())

            if not hp.check_cam_url(scraper.url_id, full_url, title):
                print(f"   [Type10Parser] Bỏ qua (đã có trong DB): {title}")
                continue

            cam = camob.CameraObject(0, title, 0, full_url, "", scraper.cat_id)
            cam.date_publish = pub_date
            cam.thumb = thumb
            cam.short = excerpt

            if scraper.camlist.add_cam(cam):
                scraper.url_links.append(full_url)
                count_new += 1
            else:
                print(f"   [Type10Parser] Bỏ qua (trùng trong danh sách tạm): {title}")

        print(f"--> [Type10Parser] Thêm {count_new} bài.")
        return True

    def parse_detail(self, soup, scraper) -> bool:
        # Currently Type10 list often leads to generic or type2 details,
        # but if there is a specific DetailType10, add here.
        return False
