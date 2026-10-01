import os
import json
import logging
import urllib.robotparser
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

from app.config import settings
from app.core.cache import cache_manager

logger = logging.getLogger(__name__)

class WebScraperEngine:
    """
    Robust Web Scraper Engine.
    Supports DEMO mode (versioned JSON fixtures) and LIVE mode (HTTP requests with robots.txt check).
    Stamps every payload with source and timestamp.
    """

    HEADERS = {
        "User-Agent": "InsightOpsAI-MarketBot/1.0 (+https://insightops.ai/bot; bot@insightops.ai)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

    @classmethod
    def scrape_url(cls, url: str, force_refresh: bool = False, version: str = "v2") -> Dict[str, Any]:
        """
        Scrapes a target URL using either TTL cache, demo fixtures, or live HTTP requests.
        """
        if not force_refresh:
            cached_data = cache_manager.get("scrape_payload", f"{url}:{version}")
            if cached_data:
                cached = dict(cached_data)
                cached["cached"] = True
                return cached

        mode = settings.SCRAPER_MODE.lower()
        if mode == "demo":
            payload = cls._scrape_demo(url, version=version)
        else:
            payload = cls._scrape_live(url)

        # Cache extracted payload
        cache_manager.set("scrape_payload", f"{url}:{version}", payload, ttl_seconds=settings.CACHE_TTL_SCRAPE)
        return payload

    @classmethod
    def _scrape_demo(cls, url: str, version: str = "v2") -> Dict[str, Any]:
        """Loads versioned fixture snapshot from JSON files."""
        url_lower = url.lower()
        if "saasify" in url_lower:
            filename = f"saasify_{version}.json"
        elif "datapulse" in url_lower:
            filename = f"datapulse_{version}.json"
        elif "apexscale" in url_lower:
            filename = f"apexscale_{version}.json"
        else:
            filename = "default_v1.json"

        file_path = os.path.join(cls.FIXTURE_DIR, filename)
        if not os.path.exists(file_path):
            file_path = os.path.join(cls.FIXTURE_DIR, "default_v1.json")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return {
                "url": url,
                "title": data.get("title", f"Demo Data ({filename})"),
                "raw_text": data.get("raw_text", ""),
                "tables": data.get("tables", []),
                "status_code": data.get("status_code", 200),
                "source": "demo",
                "scrape_time": datetime.now(timezone.utc).isoformat(),
                "cached": False,
                "error": None
            }
        except Exception as err:
            logger.error(f"Error reading demo fixture {file_path}: {err}")
            return {
                "url": url,
                "title": f"Demo Scrape Error: {url}",
                "raw_text": f"Error loading fixture: {err}",
                "tables": [],
                "status_code": 500,
                "source": "demo",
                "scrape_time": datetime.now(timezone.utc).isoformat(),
                "cached": False,
                "error": str(err)
            }

    @classmethod
    def _check_robots_txt(cls, url: str) -> bool:
        """Parses robots.txt to ensure web scraping is permitted."""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        try:
            rp.set_url(robots_url)
            rp.read()
            user_agent = cls.HEADERS["User-Agent"]
            return rp.can_fetch(user_agent, url)
        except Exception as e:
            logger.warning(f"Could not fetch/parse robots.txt from {robots_url}: {e}")
            return True  # Fallback to allow if robots.txt is inaccessible

    @classmethod
    def _scrape_live(cls, url: str) -> Dict[str, Any]:
        """Performs live HTTP request with robots.txt check, timeout, and DOM cleaning."""
        if not cls._check_robots_txt(url):
            logger.warning(f"Scraping disallowed by robots.txt for URL: {url}")
            return {
                "url": url,
                "title": "Access Blocked",
                "raw_text": "Scraping disallowed by website robots.txt policy.",
                "tables": [],
                "status_code": 403,
                "source": "live",
                "scrape_time": datetime.now(timezone.utc).isoformat(),
                "cached": False,
                "error": "Disallowed by robots.txt"
            }

        try:
            response = requests.get(url, headers=cls.HEADERS, timeout=10)
            if response.status_code == 200:
                cleaned = cls.clean_html(response.text, url)
                cleaned["source"] = "live"
                cleaned["scrape_time"] = datetime.now(timezone.utc).isoformat()
                cleaned["error"] = None
                return cleaned
            else:
                return {
                    "url": url,
                    "title": f"HTTP Error {response.status_code}",
                    "raw_text": f"Server responded with status code {response.status_code}",
                    "tables": [],
                    "status_code": response.status_code,
                    "source": "live",
                    "scrape_time": datetime.now(timezone.utc).isoformat(),
                    "cached": False,
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as err:
            logger.error(f"Live scraping error for {url}: {err}")
            return {
                "url": url,
                "title": "Network Error",
                "raw_text": f"Failed to connect to target URL: {err}",
                "tables": [],
                "status_code": 500,
                "source": "live",
                "scrape_time": datetime.now(timezone.utc).isoformat(),
                "cached": False,
                "error": str(err)
            }

    @classmethod
    def clean_html(cls, html_content: str, url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Strip non-content tags
        for element in soup(["script", "style", "nav", "footer", "iframe", "svg", "noscript"]):
            element.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else url
        text_lines = [line.strip() for line in soup.get_text().splitlines() if line.strip()]
        clean_text = "\n".join(text_lines[:200])

        tables_data = []
        for table in soup.find_all('table'):
            rows = []
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if cells:
                    rows.append(cells)
            if rows:
                tables_data.append(rows)

        return {
            "url": url,
            "title": title,
            "raw_text": clean_text[:4000],
            "tables": tables_data,
            "status_code": 200,
            "cached": False
        }
