"""
Web Scraper Module for Mutual Fund FAQ Assistant (Phase 2.1 - 2.3)

This module implements the web scraping functionality to fetch and clean HTML content
from official Groww mutual fund scheme pages. It strips unwanted navigation, footer,
advertisements, and styling noise, producing clean raw text for downstream chunking
and embedding.

Tasks implemented:
- 2.1: `scrape_url(url)` using `requests` + `BeautifulSoup4`; strips nav/footer/ads.
- 2.2: `scrape_all(urls_json)` to loop over scheme URLs and save to `data/raw/<id>.txt`.
- 2.3: Graceful failure handling and logging without crashing the data pipeline.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Base project directory resolution
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_URLS_JSON = BASE_DIR / "data" / "urls.json"
DEFAULT_RAW_DIR = BASE_DIR / "data" / "raw"

# Standard User-Agent to avoid blocking by web servers
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Tags to decompose immediately
NOISE_TAGS = [
    "script",
    "style",
    "nav",
    "footer",
    "noscript",
    "iframe",
    "svg",
    "header",
    "form",
    "button",
]

# Class or ID keywords indicating non-content noise (navigation menus, popups, banners, ads)
NOISE_KEYWORDS = [
    "header",
    "footer",
    "nav",
    "sidebar",
    "menu",
    "dropdown",
    "banner",
    "popup",
    "modal",
    "cookie",
    "advertisement",
    "ad-container",
]


def _clean_html(soup: BeautifulSoup) -> str:
    """
    Cleans the BeautifulSoup DOM by removing noise tags and navigation/ad containers,
    then extracts and formats clean text.

    Args:
        soup: The BeautifulSoup object representing the HTML document.

    Returns:
        Cleaned text string with normalized whitespace.
    """
    # Decompose standard noise HTML tags
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Decompose elements with class or ID names matching noise keywords
    for element in list(soup.find_all(lambda t: getattr(t, "attrs", None) is not None and (t.get("class") or t.get("id")))):
        if getattr(element, "attrs", None) is None:
            continue
        class_val = element.get("class")
        class_str = " ".join(class_val) if isinstance(class_val, list) else str(class_val or "")
        id_str = str(element.get("id") or "")
        combined_attr = f"{class_str} {id_str}".lower()

        if any(keyword in combined_attr for keyword in NOISE_KEYWORDS):
            element.decompose()

    # Extract text with newline separator to preserve structural paragraph breaks
    raw_text = soup.get_text(separator="\n", strip=True)

    # Clean up whitespace: strip individual lines and remove excessive blank lines
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    cleaned_text = "\n".join(lines)

    # Normalize 3 or more consecutive newlines down to 2 (paragraph break)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    return cleaned_text


def scrape_url(url: str, timeout: int = 15, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
    """
    Scrapes a single URL, strips navigation, footers, advertisements, and styling,
    and returns clean readable text.

    Handles network failures and HTTP errors gracefully without raising exceptions.

    Args:
        url: The web page URL to scrape.
        timeout: Request timeout in seconds (default: 15).
        headers: Optional custom HTTP headers.

    Returns:
        The cleaned text string if scraping succeeds, or None if scraping fails.
    """
    if not url:
        logger.error("Empty URL provided to scrape_url.")
        return None

    request_headers = headers if headers is not None else DEFAULT_HEADERS

    logger.info(f"Scraping URL: {url}")
    try:
        response = requests.get(url, headers=request_headers, timeout=timeout)
        if response.status_code != 200:
            logger.warning(f"Failed to fetch {url} - Status code: {response.status_code}")
            return None

        # Parse HTML using lxml (or fallback to html.parser if needed)
        try:
            soup = BeautifulSoup(response.text, "lxml")
        except Exception as e:
            logger.debug(f"lxml parser failed ({e}), falling back to html.parser")
            soup = BeautifulSoup(response.text, "html.parser")

        cleaned_text = _clean_html(soup)

        if not cleaned_text or len(cleaned_text.strip()) < 50:
            logger.warning(f"Scraped text from {url} is suspiciously short or empty ({len(cleaned_text if cleaned_text else '')} chars).")
            return None

        logger.info(f"Successfully scraped {len(cleaned_text)} characters from {url}")
        return cleaned_text

    except requests.exceptions.Timeout:
        logger.error(f"Timeout occurred while scraping URL: {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while scraping URL {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while scraping URL {url}: {e}", exc_info=True)
        return None


def scrape_all(
    urls_json: Union[str, Path, Dict[str, Any]] = DEFAULT_URLS_JSON,
    output_dir: Union[str, Path] = DEFAULT_RAW_DIR,
    timeout: int = 15,
) -> List[Dict[str, Any]]:
    """
    Scrapes all URLs defined in the provided JSON configuration or dictionary,
    and saves the extracted raw text to individual `<id>.txt` files in `output_dir`.

    Handles failures gracefully: logs errors for individual URLs and continues
    processing the remaining corpus without crashing the pipeline.

    Args:
        urls_json: Path to `urls.json` file, or dictionary containing the corpus schema.
        output_dir: Directory path where raw text files (`<id>.txt`) will be saved.
        timeout: Request timeout in seconds for each URL.

    Returns:
        A list of dictionaries summarizing the scraping result for each scheme:
        [{ "id": int, "scheme_name": str, "url": str, "status": "success"|"failed", "filepath": str|None, "char_count": int }]
    """
    # Resolve output directory
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load corpus configuration
    corpus: List[Dict[str, Any]] = []
    if isinstance(urls_json, dict):
        corpus = urls_json.get("corpus", [])
    else:
        json_path = Path(urls_json)
        if not json_path.exists():
            logger.error(f"URLs JSON configuration file not found at: {json_path}")
            return []
        try:
            with open(json_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                corpus = data.get("corpus", [])
        except Exception as e:
            logger.error(f"Failed to read or parse JSON configuration at {json_path}: {e}")
            return []

    if not corpus:
        logger.warning("No scheme URLs found in corpus configuration.")
        return []

    logger.info(f"Starting batch scrape for {len(corpus)} scheme URLs. Output directory: {out_dir}")

    results: List[Dict[str, Any]] = []
    success_count = 0
    failure_count = 0

    for item in corpus:
        scheme_id = item.get("id")
        scheme_name = item.get("scheme_name", "Unknown Scheme")
        url = item.get("url")

        if not scheme_id or not url:
            logger.warning(f"Skipping malformed corpus entry: {item}")
            results.append({
                "id": scheme_id,
                "scheme_name": scheme_name,
                "url": url,
                "status": "failed",
                "error": "Missing id or url",
                "filepath": None,
                "char_count": 0,
            })
            failure_count += 1
            continue

        # Scrape URL with graceful failure handling (Task 2.3)
        text = scrape_url(url, timeout=timeout)

        if text is not None:
            output_file = out_dir / f"{scheme_id}.txt"
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(text)
                
                logger.info(f"Saved raw text for '{scheme_name}' (ID: {scheme_id}) -> {output_file}")
                results.append({
                    "id": scheme_id,
                    "scheme_name": scheme_name,
                    "url": url,
                    "status": "success",
                    "filepath": str(output_file),
                    "char_count": len(text),
                })
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to write file {output_file} for scheme ID {scheme_id}: {e}")
                results.append({
                    "id": scheme_id,
                    "scheme_name": scheme_name,
                    "url": url,
                    "status": "failed",
                    "error": f"File write error: {e}",
                    "filepath": None,
                    "char_count": len(text),
                })
                failure_count += 1
        else:
            logger.error(f"Scraping failed for scheme '{scheme_name}' (ID: {scheme_id}) at {url}")
            results.append({
                "id": scheme_id,
                "scheme_name": scheme_name,
                "url": url,
                "status": "failed",
                "error": "Scraping returned None or failed",
                "filepath": None,
                "char_count": 0,
            })
            failure_count += 1

    logger.info(f"Batch scraping completed. Success: {success_count}/{len(corpus)}, Failed: {failure_count}/{len(corpus)}")
    return results


if __name__ == "__main__":
    # When run as a script, execute batch scraping over data/urls.json
    print("Executing standalone batch scrape...")
    summary = scrape_all()
    print("\n--- Scraping Summary ---")
    for res in summary:
        status_icon = "OK  " if res["status"] == "success" else "FAIL"
        print(f"[{status_icon}] ID {res.get('id')}: {res.get('scheme_name')} ({res.get('char_count')} chars) -> {res.get('status')}")
