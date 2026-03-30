from .base import BaseParser
from urllib.parse import urljoin
import helpers as hp
from .. import utils
from ..config import FROM_DATE


class CongKhaiParser(BaseParser):
    def parse_list(self, soup, scraper) -> bool:
        """
        Handles:
        1. div.bancanbiet
        2. aside.content-new ul.media-list
        """
        count = 0
        handled = False

        # 1. bancanbiet
        bancanbiet_root = soup.select_one("div.bancanbiet")
        if bancanbiet_root:
            print("--> [CongKhaiParser] Công khai / Bạn cần biết")
            items = bancanbiet_root.select("div.bancanbiet-item")
            for item in items:
                a_tag = item.select_one(
                    "div.col-xs-8 p.text-left a"
                ) or item.select_one("a[href]")
                if not a_tag:
                    continue
                href = urljoin(scraper.base, a_tag.get("href"))
                title = utils.clean_spaces(a_tag.get("title") or a_tag.get_text())

                if hp.check_cam_url(scraper.url_id, href, title):
                    cam = scraper.camlist.create_cam(title, href, scraper.cat_id)
                    if scraper.camlist.add_cam(cam):
                        scraper.url_links.append(href)
                        count += 1
            handled = True

        # 2. media-list (Công khai)
        aside = soup.select_one("aside.content-new ul.media-list")
        if aside:
            print("--> [CongKhaiParser] Công khai media-list")
            items = aside.select("li.media")
            for li in items:
                a = li.select_one("h4 a[href]")
                if not a:
                    continue
                href = urljoin(scraper.base, a["href"])
                title = utils.clean_spaces(a.get_text())

                pub_date = None
                date_tag = li.select_one("em.date-time")
                if date_tag:
                    pub_date = utils.parse_vn_date_any(date_tag.get_text())

                if pub_date and pub_date < FROM_DATE:
                    continue

                if hp.check_cam_url(scraper.url_id, href, title):
                    cam = scraper.camlist.create_cam(title, href, scraper.cat_id)
                    cam.date_publish = pub_date
                    if scraper.camlist.add_cam(cam):
                        scraper.url_links.append(href)
                        count += 1
            handled = True

        # 3. list-pdf-table (Công khai dạng bảng)
        # Structure: div.ModuleWrapper > div.list-pdf-table table tr
        pdf_table = soup.select_one("div.list-pdf-table table")
        if pdf_table:
            print("--> [CongKhaiParser] Công khai dạng bảng (list-pdf-table)")
            rows = pdf_table.select("tbody tr")
            for row in rows:
                cols = row.select("td")
                if len(cols) < 2:
                    continue

                a_tag = row.select_one("a[href]")
                if not a_tag:
                    continue

                href = urljoin(scraper.base, a_tag.get("href"))
                title = utils.clean_spaces(a_tag.get("title") or a_tag.get_text())

                pub_date = None
                for cell in row.select("td"):
                    d = utils.parse_vn_date_any(cell.get_text())
                    if d:
                        pub_date = d
                        break

                if pub_date and pub_date < FROM_DATE:
                    continue

                if hp.check_cam_url(scraper.url_id, href, title):
                    cam = scraper.camlist.create_cam(title, href, scraper.cat_id)
                    cam.date_publish = pub_date
                    if scraper.camlist.add_cam(cam):
                        scraper.url_links.append(href)
                        count += 1
            handled = True

        # 4. list-legal-document-table (Công khai văn bản pháp lý dạng bảng)
        # Structure: div.list-legal-document-table table
        # Columns: STT | Tên văn bản | Nơi nhận | Số hiệu | Ngày ban hành | File đính kèm
        legal_table = soup.select_one("div.list-legal-document-table table")
        if legal_table:
            print("--> [CongKhaiParser] Công khai dạng bảng (list-legal-document-table)")
            rows = legal_table.select("tbody tr")
            for row in rows:
                cols = row.select("td")
                if len(cols) < 2:
                    continue

                # Title link: td.tg-yw4l > a[href] (column "Tên văn bản")
                title_td = row.select_one("td.tg-yw4l")
                a_tag = title_td.select_one("a[href]") if title_td else None
                if not a_tag:
                    # Fallback: first a[href] in the row
                    a_tag = row.select_one("a[href]")
                if not a_tag:
                    continue

                href_raw = a_tag.get("href", "")
                # Skip direct download links (we want detail page links)
                if href_raw.startswith("javascript:"):
                    continue
                href = urljoin(scraper.base, href_raw)
                title = utils.clean_spaces(a_tag.get("title") or a_tag.get_text())
                if not title:
                    continue

                # Date: look for date pattern in all cells
                pub_date = None
                for cell in cols:
                    d = utils.parse_vn_date_any(cell.get_text())
                    if d:
                        pub_date = d
                        break

                if hp.check_cam_url(scraper.url_id, href, title):
                    cam = scraper.camlist.create_cam(title, href, scraper.cat_id)
                    cam.date_publish = pub_date
                    if scraper.camlist.add_cam(cam):
                        scraper.url_links.append(href)
                        count += 1
                else:
                    print(f"   [Trùng DB] {title[:60]}")
            handled = True

        if handled:
            print(f"--> [CongKhaiParser] Thêm {count} bài.")
            return True
        return False

    def parse_detail(self, soup, scraper) -> bool:
        # CASE: CÔNG KHAI – content_news + gioithieu_noidung
        if not scraper.get_current_cam():
            return False

        # Check title/content split common in public info
        title_tag = soup.select_one("p.title")
        public_content = soup.select_one("div.media.news")

        current_cam = scraper.get_current_cam()
        tag_content = None

        if title_tag and public_content:
            print("   -> [CongKhaiParser] Thông báo / Công khai")
            current_cam.name = utils.clean_spaces(title_tag.get_text())
            tag_content = public_content
        else:
            container = soup.select_one("div.content_news")
            content = soup.select_one("div#gioithieu_noidung")
            if container and content:
                print("   -> [CongKhaiParser] Công khai (content_news)")
                t = container.select_one("div.title_news")
                if t:
                    current_cam.name = utils.clean_spaces(t.get_text())
                tag_content = content

        if tag_content:
            # Clean extra file links outside content
            for a in soup.select("a[href*='.pdf'], a[href*='.doc'], a[href*='.xls']"):
                if not tag_content.find(a):
                    a.decompose()

            d = utils.parse_public_media_date(soup) or utils.parse_vn_date_from_soup(
                soup
            )
            scraper.process_content(current_cam, tag_content, d)
            return True

        # CASE: PDF Detail (pdf-detail-layout-default)
        pdf_detail = soup.select_one("article.pdf-detail-layout-default")
        if pdf_detail:
            print("   -> [CongKhaiParser] PDF Detail Layout")

            # Title
            h1 = pdf_detail.select_one("h1.doc-name")
            if h1:
                current_cam.name = utils.clean_spaces(h1.get_text())

            # Date (div.news-date)
            date_div = pdf_detail.select_one("div.news-date")
            d = None
            if date_div:
                d = utils.parse_vn_date_any(date_div.get_text())

            # Content: iframe with PDF viewer
            iframe = pdf_detail.select_one("div.wrap-view-ducument iframe")
            pdf_link = None
            if iframe:
                src = iframe.get("src", "")
                if "file=" in src:
                    try:
                        pdf_link = src.split("file=")[1].split("&")[0]
                    except Exception:
                        pass

            if pdf_link:
                full_pdf = urljoin(scraper.base, pdf_link)
                tag_content = soup.new_tag("div")
                p = soup.new_tag("p")
                p.string = "Tài liệu công khai: "
                a = soup.new_tag(
                    "a", href=full_pdf, target="_blank", **{"class": "link-download"}
                )
                a.string = "Tải về PDF"
                p.append(a)
                tag_content.append(p)

                scraper.process_content(current_cam, tag_content, d)
                return True

        # CASE: Legal Document Detail (legal-document-detailLayout-default)
        # Structure: div.legal-document-detailLayout-default > table with metadata rows
        legal_detail = soup.select_one("div.legal-document-detailLayout-default")
        if legal_detail:
            print("   -> [CongKhaiParser] Legal Document Detail Layout")

            # Title: <td class="title">...</td>
            td_title = legal_detail.select_one("td.title")
            if td_title:
                current_cam.name = utils.clean_spaces(td_title.get_text())

            # Date: Find "Ngày ban hành" label, then grab the next td
            d = None
            for td in legal_detail.select("td.td-title, th.td-title"):
                if "Ngày ban hành" in td.get_text():
                    # The date is in the next sibling td
                    next_td = td.find_next_sibling("td")
                    if next_td:
                        d = utils.parse_vn_date_any(next_td.get_text())
                    break

            # If no date from label, try any td with date pattern
            if not d:
                for td in legal_detail.select("td"):
                    parsed = utils.parse_vn_date_any(td.get_text())
                    if parsed:
                        d = parsed
                        break

            # Extract file links
            file_links = []
            valid_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar']

            # 1. From table: download links and "Tải xuống" / "Tải về" links
            for a_el in legal_detail.select("table a[href]"):
                href_val = a_el.get("href", "")
                # Skip javascript links
                if href_val.startswith("javascript:"):
                    continue
                # Check if onclick has downloadFile with a path
                onclick = a_el.get("onclick", "")
                if "downloadFile" in onclick:
                    # Extract path from onclick: downloadFile('id', '/upload/...')
                    try:
                        parts = onclick.split("'")  # split by single quotes
                        for part in parts:
                            if "/upload/" in part or any(ext in part.lower() for ext in valid_exts):
                                href_val = part
                                break
                    except Exception:
                        pass
                if any(ext in href_val.lower() for ext in valid_exts):
                    full_link = urljoin(scraper.base, href_val)
                    text = utils.clean_spaces(a_el.get_text())
                    if not any(existing[1] == full_link for existing in file_links):
                        file_links.append((text or "Tải về", full_link))

            # 2. From iframes (PDF viewer)
            for iframe in legal_detail.select("iframe"):
                src = iframe.get("src", "")
                # Direct PDF in src (not pdfjs viewer)
                if any(ext in src.lower() for ext in ['.pdf']):
                    # Could be: /upload/.../file.pdf#zoom=100
                    clean_src = src.split("#")[0]  # Remove #zoom etc.
                    full_link = urljoin(scraper.base, clean_src)
                    if not any(existing[1] == full_link for existing in file_links):
                        file_links.append(("Xem tài liệu", full_link))
                elif "file=" in src:
                    # pdfjs viewer: /3rdparty/pdfjs/web/viewer.html?file=/upload/...
                    try:
                        f_link = src.split("file=")[1].split("&")[0].split("#")[0]
                        full_link = urljoin(scraper.base, f_link)
                        if not any(existing[1] == full_link for existing in file_links):
                            file_links.append(("Xem tài liệu", full_link))
                    except Exception:
                        pass

            # Build content HTML and JSON for custom fields
            metadata = {
                "so_ky_hieu": "",
                "nguoi_ky": "",
                "co_quan_ban_hanh": "",
                "file_links": []
            }
            
            for tr in legal_detail.select("tr"):
                cells = tr.select("td, th")
                for td_idx, td in enumerate(cells):
                    text = td.get_text().strip()
                    if text == "Số hiệu" and td_idx + 1 < len(cells):
                        metadata["so_ky_hieu"] = cells[td_idx + 1].get_text().strip()
                    elif text == "Người ký" and td_idx + 1 < len(cells):
                        metadata["nguoi_ky"] = cells[td_idx + 1].get_text().strip()
                    elif text == "Cơ quan ban hành" and td_idx + 1 < len(cells):
                        metadata["co_quan_ban_hanh"] = cells[td_idx + 1].get_text().strip()

            tag_content = soup.new_tag("div")

            if file_links:
                p = soup.new_tag("p")
                p.string = "Tài liệu công khai:"
                tag_content.append(p)

                ul = soup.new_tag("ul")
                for name, link in file_links:
                    li = soup.new_tag("li")
                    a_el = soup.new_tag("a", href=link, target="_blank")
                    a_el.string = name if name else "Tải về"
                    li.append(a_el)
                    ul.append(li)
                    metadata["file_links"].append(link)
                tag_content.append(ul)
            else:
                # Fallback: grab the detail-content div entirely
                content_div = legal_detail.select_one("div.detail-content")
                if content_div:
                    tag_content = content_div
            
            import json
            from bs4 import Comment
            json_str = json.dumps(metadata, ensure_ascii=False)
            tag_content.append(Comment(f" VANBAN_META: {json_str} "))

            scraper.process_content(current_cam, tag_content, d)
            return True

        return False
