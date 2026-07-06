"""
Unit Tests for Web Scraper Module (Phase 2.1 - 2.3)

Tests:
- 2.1: `scrape_url` strips nav/footer/ads and returns clean text.
- 2.2: `scrape_all` processes URL corpus and saves text files.
- 2.3: Graceful error handling on HTTP failures, timeouts, and network exceptions.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import requests
from bs4 import BeautifulSoup

from src.ingestion.scraper import _clean_html, scrape_all, scrape_url


@pytest.fixture
def sample_html():
    return """
    <html>
      <head><title>Test Fund Page</title></head>
      <body>
        <nav class="navbar">Home | About | Contact</nav>
        <header id="main-header">Welcome to Groww</header>
        <div class="banner-ad">Buy stocks now with zero fees!</div>
        <div class="content">
            <h1>HDFC NIFTY 50 Index Fund Direct Growth</h1>
            <p>NAV: ₹237.03 as of 03 Jul '26.</p>
            <p>Expense ratio: 0.31%</p>
        </div>
        <div class="popup-modal">Sign up for notifications</div>
        <footer>Copyright 2026 Groww. All rights reserved.</footer>
        <script>console.log("analytics"); </script>
        <style>body { color: red; }</style>
      </body>
    </html>
    """


def test_clean_html_strips_noise(sample_html):
    """Test that _clean_html removes nav, footer, scripts, styles, and ad/modal classes."""
    soup = BeautifulSoup(sample_html, "html.parser")
    cleaned = _clean_html(soup)

    # Ensure noise content is removed
    assert "Home | About" not in cleaned
    assert "Welcome to Groww" not in cleaned
    assert "Buy stocks now" not in cleaned
    assert "Sign up for notifications" not in cleaned
    assert "Copyright 2026" not in cleaned
    assert "analytics" not in cleaned
    assert "color: red" not in cleaned

    # Ensure core content is preserved
    assert "HDFC NIFTY 50 Index Fund Direct Growth" in cleaned
    assert "NAV: ₹237.03" in cleaned
    assert "Expense ratio: 0.31%" in cleaned


@patch("src.ingestion.scraper.requests.get")
def test_scrape_url_success(mock_get, sample_html):
    """Test scrape_url on successful HTTP 200 response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = sample_html
    mock_get.return_value = mock_resp

    result = scrape_url("https://groww.in/test-fund")
    assert result is not None
    assert "HDFC NIFTY 50 Index Fund Direct Growth" in result
    mock_get.assert_called_once()


@patch("src.ingestion.scraper.requests.get")
def test_scrape_url_http_error(mock_get):
    """Test scrape_url returns None on HTTP 404 error without crashing."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp

    result = scrape_url("https://groww.in/not-found")
    assert result is None


@patch("src.ingestion.scraper.requests.get")
def test_scrape_url_timeout_graceful(mock_get):
    """Test scrape_url handles timeout exception gracefully without crashing (Task 2.3)."""
    mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

    result = scrape_url("https://groww.in/timeout")
    assert result is None


@patch("src.ingestion.scraper.requests.get")
def test_scrape_all_graceful_failures(mock_get, tmp_path):
    """Test scrape_all processes a corpus where one URL fails and another succeeds without crashing."""
    # Create temporary corpus JSON
    corpus_data = {
        "corpus": [
            {"id": 1, "scheme_name": "Success Fund", "url": "https://groww.in/success"},
            {"id": 2, "scheme_name": "Fail Fund", "url": "https://groww.in/fail"},
        ]
    }
    json_path = tmp_path / "urls.json"
    raw_dir = tmp_path / "raw"
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(corpus_data, f)

    def side_effect(url, **kwargs):
        mock_resp = MagicMock()
        if "success" in url:
            mock_resp.status_code = 200
            mock_resp.text = "<html><body><h1>Success Fund</h1><p>This is a valid fund description text with sufficient length for validation.</p></body></html>"
        else:
            mock_resp.status_code = 500
        return mock_resp

    mock_get.side_effect = side_effect

    results = scrape_all(urls_json=json_path, output_dir=raw_dir)

    assert len(results) == 2
    assert results[0]["status"] == "success"
    assert results[0]["id"] == 1
    assert (raw_dir / "1.txt").exists()
    assert "Success Fund" in (raw_dir / "1.txt").read_text(encoding="utf-8")

    assert results[1]["status"] == "failed"
    assert results[1]["id"] == 2
    assert not (raw_dir / "2.txt").exists()
