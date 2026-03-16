from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def parse_list(self, soup, scraper) -> bool:
        """
        Parse danh sách bài viết từ soup.
        Trả về True nếu parser này đã xử lý (tìm thấy cấu trúc phù hợp), False nếu không.
        """
        pass

    @abstractmethod
    def parse_detail(self, soup, scraper) -> bool:
        """
        Parse chi tiết bài viết từ soup.
        Trả về True nếu parser này đã xử lý, False nếu không.
        """
        pass
