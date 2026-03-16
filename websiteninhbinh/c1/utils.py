import re
from datetime import date, datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup

def clean_spaces(s: str) -> str:
    return " ".join((s or "").split()).strip()

def to_int(text, default=None):
    s = (text or "").strip()
    m = re.search(r"\d+", s)
    if not m:
        return default
    return int(m.group())

def get_base(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        p = urlparse("https://" + url)
    return f"{p.scheme}://{p.netloc}/"

def parse_vn_datetime_any(text: str) -> datetime | None:
    """
    Bắt ngày, giờ trong chuỗi, trả về datetime.datetime
    """
    if not text:
        return None
    text = clean_spaces(text)
    
    # Try ISO
    m_iso = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})T(\d{1,2}):(\d{2}):(\d{2})", text)
    if m_iso:
        y, mo, d, h, m, s = map(int, m_iso.groups())
        try:
            return datetime(y, mo, d, h, m, s)
        except:
            pass
            
    # Try DD/MM/YYYY HH:MM
    m2 = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4}).*?(\d{1,2}):(\d{2})(?::(\d{2}))?", text)
    if m2:
        d, mo, y, h, m, s = m2.groups()
        d, mo, y, h, m = map(int, [d, mo, y, h, m])
        s = int(s) if s else 0
        if y < 100:
            y += 2000
        try:
            return datetime(y, mo, d, h, m, s)
        except:
            pass

    # Fallback to date
    tmp = parse_vn_date_any(text)
    if tmp:
        return datetime(tmp.year, tmp.month, tmp.day)
    return None

def parse_vn_date_any(text: str) -> date | None:
    """
    Bắt ngày kiểu dd/mm/yyyy hoặc dd-mm-yyyy trong một chuỗi bất kỳ.
    """
    if not text:
        return None
    text = clean_spaces(text)
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", text)
    if not m:
        return None

    d, mo, y = map(int, m.groups())

    # Xử lý năm 2 chữ số (ví dụ: 26 -> 2026)
    if y < 100:
        y += 2000

    try:
        return date(y, mo, d)
    except:
        return None

def parse_date_from_meta(soup: BeautifulSoup) -> date | None:
    """
    Fallback: lấy ngày từ meta.
    """
    if not soup:
        return None

    candidates = []

    # 1) itemprop
    for itemprop in ["dateCreated", "datePublished", "dateModified"]:
        tag = soup.find("meta", attrs={"itemprop": itemprop})
        if tag and tag.get("content"):
            candidates.append(tag["content"])

    # 2) Open Graph / Article
    for prop in ["article:published_time", "article:modified_time"]:
        tag = soup.find("meta", attrs={"property": prop})
        if tag and tag.get("content"):
            candidates.append(tag["content"])

    # 3) name=
    for name in [
        "pubdate",
        "publishdate",
        "date",
        "dc.date",
        "dc.date.issued",
        "dcterms.created",
        "dcterms.modified",
    ]:
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            candidates.append(tag["content"])

    for s in candidates:
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
        if m:
            y, mo, d = map(int, m.groups())
            try:
                return date(y, mo, d)
            except:
                pass

        d_obj = parse_vn_date_any(s)
        if d_obj:
            return d_obj

    return None

def parse_public_date_from_uicongkhai(soup: BeautifulSoup) -> date | None:
    root = soup.find("div", class_="UICongKhaiNganSach_Default")
    if not root:
        return None

    for tr in root.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) >= 2:
            label = clean_spaces(tds[0].get_text(" ", strip=True)).lower()
            if "ngày công bố" in label:
                return parse_vn_date_any(tds[1].get_text(" ", strip=True))
    return None

def parse_issue_date_from_module34(soup: BeautifulSoup) -> date | None:
    """
    Tìm 'Ngày ban hành' trong bảng thuộc #module34.
    """
    module = soup.find("div", id="module34")
    if not module:
        return None

    label_cells = module.find_all(["th", "td"], string=True)
    for cell in label_cells:
        label = clean_spaces(cell.get_text(" ", strip=True)).lower()
        if "ngày ban hành" in label:
            nxt = cell.find_next(["td", "th"])
            if nxt:
                d = parse_vn_date_any(nxt.get_text(" ", strip=True))
                if d:
                    return d

            tr = cell.find_parent("tr")
            if tr:
                d = parse_vn_date_any(tr.get_text(" ", strip=True))
                if d:
                    return d

    return parse_vn_date_any(module.get_text(" ", strip=True))

def parse_datetime_module34(soup):
    span = soup.select_one("article.news-detail-layout-type-2 span.post-date")
    if not span:
        return None
    return parse_vn_datetime_any(span.get_text())

def parse_date_module34(soup):
    span = soup.select_one("article.news-detail-layout-type-2 span.post-date")
    if not span:
        return None  # Return None explicit

    text = clean_spaces(span.get_text())
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        d, mth, y = map(int, m.groups())
        try:
            return date(y, mth, d)
        except:
            pass
    return None

def parse_public_media_date(soup):
    em = soup.select_one("em.date-time")
    if em:
        return parse_vn_date_any(em.get_text())
    return None

def parse_vn_datetime_from_soup1(soup: BeautifulSoup) -> datetime | None:
    candidates = [
        soup.find("span", class_="post-date"),
        soup.find("div", class_="PostDate"),
        soup.find("span", class_="date"),
        soup.find("p", class_="date"),
        soup.find("div", class_="creat_date"),
    ]

    for el in candidates:
        if el:
            text = clean_spaces(el.get_text(" ", strip=True))
            dt = parse_vn_datetime_any(text)
            if dt:
                return dt
    return None

def parse_vn_datetime_from_soup(soup: BeautifulSoup) -> datetime | None:
    d = parse_vn_datetime_from_soup1(soup)
    if d is None:
        title_tag = soup.find("div", class_="title_news")
        if title_tag:
            d = parse_vn_datetime_any(title_tag.get_text())
    if d is None:
        content_tag = soup.find("div", class_="media news")
        if content_tag:
            first_text = content_tag.get_text(strip=True)[:200]
            d = parse_vn_datetime_any(first_text)
    if d is None:
        fallback_date = parse_vn_date_from_soup(soup)
        if fallback_date:
            return datetime(fallback_date.year, fallback_date.month, fallback_date.day)
    return d

def parse_vn_date_from_soup1(soup: BeautifulSoup) -> date | None:
    candidates = [
        soup.find("span", class_="post-date"),
        soup.find("div", class_="PostDate"),
        soup.find("span", class_="date"),
        soup.find("p", class_="date"),
        soup.find("div", class_="creat_date"),
    ]

    for el in candidates:
        if el:
            text = clean_spaces(el.get_text(" ", strip=True))
            return parse_vn_date_any(text)
    return None

def parse_vn_date_from_soup(soup: BeautifulSoup) -> date | None:
    # 1. Tìm trong thẻ date hiển thị
    d = parse_vn_date_from_soup1(soup)

    # 2. Nếu không thấy, tìm trong div.title_news
    if d is None:
        title_tag = soup.find("div", class_="title_news")
        if title_tag:
            d = parse_vn_date_any(title_tag.get_text())

    # 3. Nếu vẫn không thấy, tìm dòng text đầu tiên trong nội dung bài viết
    if d is None:
        content_tag = soup.find("div", class_="media news")
        if content_tag:
            first_text = content_tag.get_text(strip=True)[:200]
            d = parse_vn_date_any(first_text)

    # 4. Fallback các meta tag cũ
    if d is None:
        d = parse_issue_date_from_module34(soup)
    if d is None:
        d = parse_public_date_from_uicongkhai(soup)
    if d is None:
        d = parse_date_from_meta(soup)

    return d

def normalize_download_links_in_content(tag_content):
    """
    Chuyển <a onclick="downloadFile..."> thành <a href="...">
    """
    if not tag_content:
        return

    for a in tag_content.find_all("a"):
        onclick = (a.get("onclick") or "").strip()
        if not onclick:
            continue

        m = re.search(
            r"downloadFile\s*\(\s*(['\"]).*?\1\s*,\s*(['\"])\s*(/upload/[^'\"\)\s]+)\s*\2\s*\)",
            onclick,
            flags=re.IGNORECASE,
        )
        if not m:
            continue

        file_path = m.group(3).strip()
        a.attrs.pop("onclick", None)
        a["href"] = file_path
        a["target"] = "_blank"

        cls = a.get("class", [])
        if isinstance(cls, str):
            cls = cls.split()
        if "link-download" not in cls:
            cls.append("link-download")
        a["class"] = cls
        a.attrs.pop("style", None)

def pick_detail_links(soup):
    links = []
    links += soup.select("td.tg-yw4l a[href]")
    links += soup.select("td a[title*='Xem chi tiết công khai'][href]")
    return links
