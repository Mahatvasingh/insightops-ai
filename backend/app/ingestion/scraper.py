import os
import re
import json
import logging
import urllib.robotparser
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, Optional
import requests
from bs4 import BeautifulSoup, Comment

from app.config import settings
from app.core.cache import cache_manager

logger = logging.getLogger(__name__)

class WebScraperEngine:
    """
    Web Scraper Engine.
    Supports DEMO mode (versioned JSON fixtures) and LIVE mode (HTTP requests with robots.txt check & redirect validation).
    Stamps every payload with source and timestamp.
    Strips hidden text, zero-width characters, and HTML comments for prompt injection defense.
    """

    HEADERS = {
        "User-Agent": "InsightOpsAI-MarketBot/1.0 (+https://insightops.ai/bot; bot@insightops.ai)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

    @classmethod
    def scrape_url(cls, url: str, force_refresh: bool = False, version: str = "v1") -> Dict[str, Any]:
        """
        Scrapes a target URL using either TTL cache, demo fixtures, or live HTTP requests.
        """
        cache_key = f"{url}:{version}"
        if not force_refresh:
            cached_data = cache_manager.get("scrape_payload", cache_key)
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
        cache_manager.set("scrape_payload", cache_key, payload, ttl_seconds=settings.CACHE_TTL_SCRAPE)
        return payload

    @classmethod
    def _scrape_demo(cls, url: str, version: str = "v1") -> Dict[str, Any]:
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
            
            raw_text = cls.strip_hidden_characters(data.get("raw_text", ""))
            return {
                "url": url,
                "title": data.get("title", f"Demo Data ({filename})"),
                "raw_text": raw_text,
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
        """Parses robots.txt with timeout and explicit error logging."""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        try:
            resp = requests.get(robots_url, headers=cls.HEADERS, timeout=5)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
                user_agent = cls.HEADERS["User-Agent"]
                can_fetch = rp.can_fetch(user_agent, url)
                if not can_fetch:
                    logger.warning(f"Robots.txt at {robots_url} explicitly disallows fetching URL: {url}")
                return can_fetch
        except Exception as e:
            logger.warning(f"Could not fetch/parse robots.txt from {robots_url} (defaulting to fetch): {e}")
            return True
        return True

    @classmethod
    def _scrape_live(cls, url: str) -> Dict[str, Any]:
        """
        Performs live HTTP request with robots.txt check, step-by-step redirect SSRF validation, and DOM cleaning.
        """
        if not cls._check_robots_txt(url):
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

        from app.core.url_validator import validate_target_url

        current_url = url
        max_hops = 3
        hop = 0

        while hop <= max_hops:
            try:
                # Validate current hop against SSRF before making request
                validate_target_url(current_url)

                response = requests.get(current_url, headers=cls.HEADERS, timeout=10, allow_redirects=False)

                # Handle HTTP redirects securely
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if not location:
                        break
                    current_url = urljoin(current_url, location)
                    hop += 1
                    continue

                if response.status_code == 200:
                    cleaned = cls.clean_html(response.text, current_url)
                    cleaned["source"] = "live"
                    cleaned["scrape_time"] = datetime.now(timezone.utc).isoformat()
                    cleaned["error"] = None
                    return cleaned
                else:
                    return {
                        "url": current_url,
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
                logger.error(f"Live scraping error for {current_url}: {err}")
                return {
                    "url": current_url,
                    "title": "Scrape Error",
                    "raw_text": f"Failed to connect or validate target URL: {err}",
                    "tables": [],
                    "status_code": 500,
                    "source": "live",
                    "scrape_time": datetime.now(timezone.utc).isoformat(),
                    "cached": False,
                    "error": str(err)
                }

        return {
            "url": url,
            "title": "Too Many Redirects",
            "raw_text": f"Exceeded maximum allowed redirect hops ({max_hops})",
            "tables": [],
            "status_code": 310,
            "source": "live",
            "scrape_time": datetime.now(timezone.utc).isoformat(),
            "cached": False,
            "error": "Too many redirects"
        }

    @staticmethod
    def strip_hidden_characters(text: str) -> str:
        """Strips zero-width characters and prompt injection control codes."""
        if not text:
            return ""
        # Remove zero-width space, zero-width non-joiner, zero-width joiner, BOM
        cleaned = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
        return cleaned

    @classmethod
    def clean_html(cls, html_content: str, url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Strip HTML comments
        for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Strip hidden elements (display:none, visibility:hidden, aria-hidden="true")
        for hidden in soup.find_all(attrs={"aria-hidden": "true"}):
            hidden.decompose()

        for tag in soup.find_all(style=True):
            style_str = tag["style"].lower()
            if "display:none" in style_str.replace(" ", "") or "visibility:hidden" in style_str.replace(" ", ""):
                tag.decompose()

        # Strip non-content structural tags
        for element in soup(["script", "style", "nav", "footer", "iframe", "svg", "noscript"]):
            element.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else url
        text_lines = [line.strip() for line in soup.get_text().splitlines() if line.strip()]
        clean_text = "\n".join(text_lines[:200])
        clean_text = cls.strip_hidden_characters(clean_text)

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
