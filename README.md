# Website Ninh Bình Scraper

A Python-based web scraper for extracting and posting articles from Ninh Bình educational websites to WordPress.

## Features

- Scrapes articles from various Ninh Bình educational sites
- Supports multiple page formats and parsers
- Automatically downloads and embeds images
- Posts content to WordPress with proper formatting
- Handles duplicate detection
- Logs all operations

## Project Structure

```
folder/
├── websiteninhbinh/
│   ├── c1/
│   │   ├── config.py          # Configuration settings
│   │   ├── dangbai_c1.py      # Main posting script
│   │   ├── main.py            # Entry point
│   │   ├── scraper.py         # Core scraper logic
│   │   ├── utils.py           # Utility functions
│   │   └── parsers/           # Page-specific parsers
│   │       ├── base.py        # Base parser class
│   │       ├── type11.py      # Parser for type 11 pages
│   │       └── ...            # Other parsers
├── chrome-win64/              # Chrome browser for Selenium
├── chromedriver-win64/        # Chrome driver
├── tmp_wp_upload/             # Temporary upload directory
├── log_posted.xlsx            # Posting logs
└── README.md
```

## Supported Formats

### Form 4 c1
#### List Page Structure
```html
<h4 class="media-heading title-content-new">
   Hướng dẫn kỹ năng lái xe an toàn
</h4>

aside.content-new ul.media-list > li.media
```

#### Detail Page Structure
```html
div.media.news#gioithieu_noidung
```

## Installation

1. Clone or download the project
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy configuration template:
   ```bash
   cp websiteninhbinh/c1/config.example.py websiteninhbinh/c1/config.py
   ```
4. Edit `websiteninhbinh/c1/config.py` to set correct paths for Chrome browser and driver
5. Ensure Chrome browser and chromedriver are available in the specified paths

## Usage

1. Activate virtual environment (if using one)
2. Run the main script:
   ```bash
   python websiteninhbinh/c1/main.py
   ```

## Configuration

Edit `websiteninhbinh/c1/config.py` to set:
- Target WordPress site URL
- Login credentials
- Scraping parameters
- Date filters

## Dependencies

- requests
- beautifulsoup4
- selenium
- openpyxl
- urllib3

## Notes

- The scraper uses Selenium for browser automation
- Images are downloaded and uploaded to WordPress media library
- Duplicate articles are automatically skipped
- All operations are logged to Excel file

## Troubleshooting

- Ensure Chrome and chromedriver versions match
- Check network connectivity for image downloads
- Verify WordPress credentials and permissions
- Review logs in `log_posted.xlsx` for errors  
