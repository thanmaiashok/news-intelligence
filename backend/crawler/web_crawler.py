import asyncio
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, BrowserContext

from .base_crawler import BaseCrawler, RawArticle

logger = logging.getLogger(__name__)

WEB_SOURCES: List[Dict] = [
    {
        "name": "Reuters",
        "base_url": "https://www.reuters.com",
        "index_urls": ["https://www.reuters.com/news/archive/worldnews"],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": ".article-body__content",
        "js_required": False,
        "region": "US",
        "priority": 1,
    },
    {
        "name": "CNN",
        "base_url": "https://edition.cnn.com",
        "index_urls": ["https://edition.cnn.com/world"],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": ".article__content",
        "js_required": True,
        "region": "US",
        "priority": 1,
    },
    {
        "name": "The Guardian",
        "base_url": "https://www.theguardian.com",
        "index_urls": ["https://www.theguardian.com/world"],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": ".article-body-commercial-selector",
        "js_required": False,
        "region": "GB",
        "priority": 2,
    },
]


class PlaywrightCrawler(BaseCrawler):
    """JS-rendered page crawler using Playwright headless browser."""

    def __init__(self, source_config: Dict):
        super().__init__(source_config)
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._playwright = None

    async def setup(self):
        await super().setup()
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        self._context = await self._browser.new_context(
            user_agent=self._random_user_agent(),
            viewport={"width": 1920, "height": 1080},
        )

    async def teardown(self):
        await super().teardown()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def _fetch_js(self, url: str) -> Optional[str]:
        try:
            page = await self._context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            content = await page.content()
            await page.close()
            return content
        except Exception as e:
            logger.warning("Playwright fetch error %s: %s", url, e)
            return None

    async def _discover_article_urls(self, index_url: str) -> List[str]:
        html = await self._fetch_js(index_url)
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        base = self.source_config["base_url"]
        urls = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(base, href)
            parsed = urlparse(full_url)
            if parsed.netloc == urlparse(base).netloc and len(parsed.path) > 20:
                urls.add(full_url)

        return list(urls)[:50]  # limit per cycle

    async def _parse_article(self, url: str) -> Optional[RawArticle]:
        html = await self._fetch_js(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        title_el = soup.select_one(self.source_config.get("title_selector", "h1"))
        content_el = soup.select_one(
            self.source_config.get("content_selector", "article")
        )

        title = title_el.get_text(strip=True) if title_el else ""
        content = content_el.get_text(separator=" ", strip=True) if content_el else ""

        if not title or len(content) < 100:
            return None

        meta_date = soup.find("meta", {"property": "article:published_time"})
        published_at = None
        if meta_date and meta_date.get("content"):
            try:
                from dateutil.parser import parse as parse_date
                published_at = parse_date(meta_date["content"])
            except Exception:
                pass

        return RawArticle(
            url=url,
            title=title,
            content=content,
            source=self.name,
            source_type="web",
            published_at=published_at or datetime.utcnow(),
            region=self.source_config.get("region"),
            raw_html=html[:50000],
        )

    async def crawl(self) -> AsyncGenerator[RawArticle, None]:
        semaphore = asyncio.Semaphore(5)  # concurrent articles per source

        for index_url in self.source_config.get("index_urls", []):
            urls = await self._discover_article_urls(index_url)
            tasks = []
            for url in urls:
                tasks.append(self._parse_article_safe(url, semaphore))

            results = await asyncio.gather(*tasks)
            for article in results:
                if article:
                    yield article

    async def _parse_article_safe(
        self, url: str, semaphore: asyncio.Semaphore
    ) -> Optional[RawArticle]:
        async with semaphore:
            return await self._parse_article(url)


class StaticWebCrawler(BaseCrawler):
    """Fast crawler for non-JS pages via aiohttp."""

    async def crawl(self) -> AsyncGenerator[RawArticle, None]:
        for index_url in self.source_config.get("index_urls", []):
            html = await self._fetch(index_url)
            if not html:
                continue

            urls = self._discover_links(html, self.source_config["base_url"])
            for url in urls[:30]:
                article = await self._parse_article(url)
                if article:
                    yield article

    def _discover_links(self, html: str, base_url: str) -> List[str]:
        soup = BeautifulSoup(html, "lxml")
        base_netloc = urlparse(base_url).netloc
        urls = []
        for a in soup.find_all("a", href=True):
            full_url = urljoin(base_url, a["href"])
            if urlparse(full_url).netloc == base_netloc:
                urls.append(full_url)
        return list(dict.fromkeys(urls))  # dedup preserving order

    async def _parse_article(self, url: str) -> Optional[RawArticle]:
        html = await self._fetch(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        title_el = soup.select_one(self.source_config.get("title_selector", "h1"))
        content_el = soup.select_one(
            self.source_config.get("content_selector", "article")
        )

        title = title_el.get_text(strip=True) if title_el else ""
        content = content_el.get_text(separator=" ", strip=True) if content_el else ""

        if not title or len(content) < 100:
            return None

        return RawArticle(
            url=url,
            title=title,
            content=content,
            source=self.name,
            source_type="web",
            published_at=datetime.utcnow(),
            region=self.source_config.get("region"),
        )


def build_web_crawler(source_config: Dict) -> BaseCrawler:
    if source_config.get("js_required", False):
        return PlaywrightCrawler(source_config)
    return StaticWebCrawler(source_config)
