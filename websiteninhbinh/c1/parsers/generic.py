from .base import BaseParser
from urllib.parse import urljoin, urlparse, quote
import helpers as hp
from .. import utils
from ..config import FROM_DATE
import re


class GenericParser(BaseParser):
    def parse_list(self, soup, scraper) -> bool:
        count = 0
        handled = False

        # 1. content_news ul.media-list
        content_root = soup.select_one("div.content_news ul.media-list")
        if content_root:
            print("--> [GenericParser] content_news")
            for a in content_root.select("li.media > a.pull-left[href]"):
                href = a["href"]
                url = urljoin(scraper.base, href)
                li = a.find_parent("li", class_="media")
                title_tag = li.select_one("h4.title-content-new") if li else None
                name = (
                    utils.clean_spaces(title_tag.get_text())
                    if title_tag
                    else url.split("/")[-1]
                )

                if hp.check_cam_url(scraper.url_id, url, name):
                    cam = scraper.camlist.create_cam(name, url, scraper.cat_id)
                    if scraper.camlist.add_cam(cam):
                        scraper.url_links.append(url)
                        count += 1
            handled = True

        # 2. section-list (generic)
        section = soup.select_one("section.section-list")
        if section and not handled:
            print("--> [GenericParser] section-list")
            items = section.select("div.item-article, article.item-block")
            for item in items:
                # Prefer h2 or h3 title links
                a = item.select_one(
                    "h2.entry-title a[href], h3 a[href]"
                ) or item.select_one("a[href]")
                if not a:
                    continue
                href = urljoin(scraper.base, a["href"])
                title = utils.clean_spaces(a.get("title") or a.get_text())

                pub_date = None
                date_tag = item.select_one("time, span.date")
                if date_tag:
                    pub_date = utils.parse_vn_date_any(date_tag.get_text())

                if pub_date and pub_date < FROM_DATE:
                    continue

                if hp.check_cam_url(scraper.url_id, href, title):
                    cam = scraper.camlist.create_cam(title, href, scraper.cat_id)
                    if pub_date:
                        cam.date_publish = pub_date
                    if scraper.camlist.add_cam(cam):
                        scraper.url_links.append(href)
                        count += 1
            handled = True

        # 3. UL/LI Fallback (Case 5 in original)
        if not handled:
            main_container = soup.select_one("div#left-content-modules")
            if main_container:
                all_uls = main_container.find_all("ul")
                for ul in all_uls:
                    if ul.find("li", class_="actived") or ul.find(
                        "a", text=re.compile(r"Trang|Next|Sau", re.I)
                    ):
                        continue
                    if ul.find_parent("div", class_="page"):
                        continue

                    lis = ul.find_all("li", recursive=False)
                    if not lis:
                        continue

                    print(f"--> [GenericParser] UL list ({len(lis)} item)")
                    for li in lis:
                        a = li.find("a", href=True)
                        if not a:
                            continue
                        full_url = urljoin(scraper.base, a["href"])
                        title = utils.clean_spaces(a.get_text())

                        li_text = li.get_text(" ", strip=True)
                        remaining_text = li_text.replace(title, "")
                        pub_date = utils.parse_vn_date_any(remaining_text)
                        if pub_date and pub_date < FROM_DATE:
                            continue

                        if hp.check_cam_url(scraper.url_id, full_url, title):
                            cam = scraper.camlist.create_cam(
                                title, full_url, scraper.cat_id
                            )
                            cam.date_publish = pub_date
                            if scraper.camlist.add_cam(cam):
                                scraper.url_links.append(full_url)
                                count += 1
                    handled = True

        if handled:
            print(f"--> [GenericParser] Thêm {count} bài.")
            return True
        return False

    def parse_detail(self, soup, scraper) -> bool:
        current_cam = scraper.get_current_cam()
        if not current_cam:
            return False

        tag_content = None

        # 1. Tin tức thường
        tag_content = soup.select_one(
            "div.media.news#gioithieu_noidung"
        ) or soup.select_one("div.content_news")
        if tag_content:
            print("   -> [GenericParser] Tin tức thường")

        # 1.5 News Detail Default
        if not tag_content:
            article = soup.select_one("section.news-detail-default article")
            if article:
                print("   -> [GenericParser] news-detail-default")
                h1 = article.select_one("h1.title-news-detail")
                if h1:
                    current_cam.name = utils.clean_spaces(h1.get_text())

                content_div = article.select_one("div.content-detail")
                tag_content = content_div if content_div else article

                if tag_content:
                    trash = tag_content.select_one("div.social")
                    if trash:
                        trash.decompose()

        # 2. Project Realty
        if not tag_content:
            project_detail = soup.select_one("article.project-realty-detail")
            if project_detail:
                print("   -> [GenericParser] project-realty-detail")
                h1 = project_detail.select_one("h1.post-title")
                if h1:
                    current_cam.name = utils.clean_spaces(h1.get_text())

                content_div = project_detail.select_one(
                    "div.post-content div.content-detail"
                )
                tag_content = (
                    content_div
                    if content_div
                    else project_detail.select_one("div.post-content")
                )

                # Trash specific
                if tag_content:
                    trash = tag_content.select_one("div.content-label, div.social")
                    if trash:
                        trash.decompose()

        if tag_content:
            d = utils.parse_vn_date_from_soup(soup)
            scraper.process_content(current_cam, tag_content, d)
            return True

        return False
