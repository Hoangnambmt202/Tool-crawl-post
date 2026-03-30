from .base import BaseParser
from urllib.parse import urljoin
import helpers as hp
from .. import utils
from ..config import FROM_DATE
import re


class HanamParser(BaseParser):
    def parse_list(self, soup, scraper) -> bool:
        """
        Handles several Hanam list structures:
        1. list-item
        2. action-news
        3. list-news-content
        """
        handled = False
        count = 0

        # 1. list-item
        list_root = soup.select("div#left-content-modules div.list-item")
        if list_root:
            print(f"--> [HanamParser] list-item | {len(list_root)} bài")
            for item in list_root:
                a_tag = item.select_one(".news-item-name a[href]")
                if not a_tag:
                    continue

                href = urljoin(scraper.base, a_tag.get("href"))
                title = utils.clean_spaces(a_tag.get_text())
                if not title:
                    continue

                date_tag = item.select_one("span.text-color")
                pub_date = utils.parse_vn_date_any(
                    date_tag.get_text() if date_tag else ""
                )

                img_tag = item.select_one("div.col-xs-4 img[src]")
                thumb = urljoin(scraper.base, img_tag["src"]) if img_tag else ""

                desc_tag = item.select_one("div.col-xs-8 div p span")
                excerpt = utils.clean_spaces(desc_tag.get_text()) if desc_tag else ""

                author_tag = item.select_one("p.text-right")
                author = utils.clean_spaces(author_tag.get_text()) if author_tag else ""

                if hp.check_cam_url(scraper.url_id, href, title):
                    cam = scraper.camlist.create_cam(title, href, scraper.cat_id)
                    cam.date_publish = pub_date
                    cam.short = excerpt
                    cam.thumb = thumb
                    cam.author = author
                    if scraper.camlist.add_cam(cam):
                        scraper.url_links.append(href)
                        count += 1
            handled = True

        # 2. action-news
        action_items = soup.select("div#left-content-modules div.action-news")
        if action_items:
            print(f"--> [HanamParser] action-news | {len(action_items)} bài")
            for item in action_items:
                a_tag = item.select_one("a[href] p.title")
                if not a_tag:
                    continue
                a = a_tag.find_parent("a")
                href = urljoin(scraper.base, a.get("href"))
                title = utils.clean_spaces(a_tag.get_text())

                time_tag = item.select_one("p.time")
                pub_date = utils.parse_vn_date_any(
                    time_tag.get_text() if time_tag else ""
                )

                img_tag = item.select_one("img[src]")
                thumb = urljoin(scraper.base, img_tag["src"]) if img_tag else ""

                desc_tag = item.select_one("p.text-content")
                excerpt = utils.clean_spaces(desc_tag.get_text()) if desc_tag else ""

                if hp.check_cam_url(scraper.url_id, href, title):
                    cam = scraper.camlist.create_cam(title, href, scraper.cat_id)
                    cam.date_publish = pub_date
                    cam.short = excerpt
                    cam.thumb = thumb
                    if scraper.camlist.add_cam(cam):
                        scraper.url_links.append(href)
                        count += 1
            handled = True

        # 3. list-news-content
        list_root_2 = soup.select_one("div.row.list-news-content")
        if list_root_2:
            items = list_root_2.select("div.new-content")
            print(f"--> [HanamParser] list-news-content | {len(items)} bài")
            for item in items:
                a = item.select_one("a.title[href]")
                if not a:
                    continue
                href = urljoin(scraper.base, a["href"])
                title = utils.clean_spaces(a.get_text())

                p_desc = item.find("p")
                desc = utils.clean_spaces(p_desc.get_text()) if p_desc else ""

                if hp.check_cam_url(scraper.url_id, href, title):
                    cam = scraper.camlist.create_cam(title, href, scraper.cat_id)
                    cam.short = desc
                    if scraper.camlist.add_cam(cam):
                        scraper.url_links.append(href)
                        count += 1
            handled = True

        # 4. content_news
        content_news = soup.select("div.content_news aside.content-new ul.media-list li.media")
        if content_news:
            print(f"--> [HanamParser] content_news | {len(content_news)} bài")
            for item in content_news:
                a_tag = item.select_one("a.pull-left[href]")
                if not a_tag:
                    a_tag = item.select_one("a[href]")
                if not a_tag:
                    continue

                href = urljoin(scraper.base, a_tag.get("href"))
                
                title_tag = item.select_one("div.media-body h4.media-heading.title-content-new")
                title = utils.clean_spaces(title_tag.get_text()) if title_tag else utils.clean_spaces(a_tag.get_text())
                if not title:
                    continue

                img_tag = item.select_one("img.media-object[src]")
                thumb = urljoin(scraper.base, img_tag["src"]) if img_tag else ""

                excerpt = ""
                media_body = item.select_one("div.media-body")
                if media_body:
                    for tag_to_remove in ["h4", "div"]:
                        for t in media_body.find_all(tag_to_remove):
                            t.decompose()
                    excerpt = utils.clean_spaces(media_body.get_text())

                if hp.check_cam_url(scraper.url_id, href, title):
                    cam = scraper.camlist.create_cam(title, href, scraper.cat_id)
                    cam.short = excerpt
                    cam.thumb = thumb
                    if scraper.camlist.add_cam(cam):
                        scraper.url_links.append(href)
                        count += 1
            handled = True

        if handled:
            print(f"--> [HanamParser] Thêm {count} bài.")
            return True
        return False

    def parse_detail(self, soup, scraper) -> bool:
        # Case 3: Tin tức hoạt động (Hanam)
        root = soup.select_one("#left-content-modules div.action-news")
        tag_content = None
        current_cam = scraper.get_current_cam()
        if not current_cam:
            return False

        if root:
            print("   -> [HanamParser] Cấu trúc: Tin tức hoạt động")
            title_tag = root.select_one("a > p.title")
            if title_tag:
                current_cam.name = utils.clean_spaces(title_tag.get_text())
            view_img = root.select_one("div.view_img")
            if view_img:
                tag_content = view_img

        # Case 2.5: news-detail
        if not tag_content:
            detail = soup.select_one("div.news-detail")
            if detail:
                print("   -> [HanamParser] Cấu trúc: news-detail")
                h4 = detail.find("h4")
                if h4:
                    current_cam.name = utils.clean_spaces(h4.get_text())
                tag_content = detail

        # Case 4: content_news detail
        if not tag_content:
            detail = soup.select_one("div.content_news")
            if detail:
                print("   -> [HanamParser] Cấu trúc: content_news")
                title_tag = detail.select_one("div.title_news")
                if title_tag:
                    current_cam.name = utils.clean_spaces(title_tag.get_text())
                
                media_news = detail.select_one("div.media.news")
                if media_news:
                    tag_content = media_news
                else:
                    tag_content = detail

                # Process attachments from the entire detail block
                file_links = []
                for a_el in detail.select("a[href$='.pdf'], a[href$='.doc'], a[href$='.docx'], a[href$='.xls'], a[href$='.xlsx'], a[href$='.rar'], a[href$='.zip']"):
                    href_val = a_el.get("href", "")
                    if href_val:
                        full_link = urljoin(scraper.base, href_val)
                        text = utils.clean_spaces(a_el.get_text()) or "Tập tin đính kèm"
                        if not any(existing[1] == full_link for existing in file_links):
                            file_links.append((text, full_link))
                
                if file_links:
                    p = soup.new_tag("p")
                    p.string = "Tài liệu đính kèm:"
                    tag_content.append(p)
                    ul = soup.new_tag("ul")
                    for name, link in file_links:
                        li = soup.new_tag("li")
                        a_a = soup.new_tag("a", href=link, target="_blank")
                        a_a.string = name
                        li.append(a_a)
                        ul.append(li)
                    tag_content.append(ul)

        if tag_content:
            d = utils.parse_vn_date_from_soup(soup)
            scraper.process_content(current_cam, tag_content, d)
            return True

        return False
