import asyncio
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, List
from email.utils import parsedate_to_datetime

import feedparser
from bs4 import BeautifulSoup

from .base_crawler import BaseCrawler, RawArticle

logger = logging.getLogger(__name__)

RSS_SOURCES: List[Dict] = [
    # ── Global / General ─────────────────────────────────────────────────────
    {"name": "BBC News", "url": "http://feeds.bbci.co.uk/news/rss.xml", "region": "GB", "priority": 1},
    {"name": "BBC World", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "region": "GB", "priority": 1},
    {"name": "Reuters Top News", "url": "https://feeds.reuters.com/reuters/topNews", "region": "US", "priority": 1},
    {"name": "Reuters World", "url": "https://feeds.reuters.com/Reuters/worldNews", "region": "US", "priority": 1},
    {"name": "AP Top News", "url": "https://feeds.apnews.com/rss/apf-topnews", "region": "US", "priority": 1},
    {"name": "AP World", "url": "https://feeds.apnews.com/rss/apf-WorldNews", "region": "US", "priority": 1},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "region": "QA", "priority": 2},
    {"name": "The Guardian World", "url": "https://www.theguardian.com/world/rss", "region": "GB", "priority": 2},
    {"name": "The Guardian US", "url": "https://www.theguardian.com/us-news/rss", "region": "US", "priority": 2},
    {"name": "NPR News", "url": "https://feeds.npr.org/1001/rss.xml", "region": "US", "priority": 2},
    {"name": "NPR World", "url": "https://feeds.npr.org/1004/rss.xml", "region": "US", "priority": 2},
    {"name": "PBS NewsHour", "url": "https://www.pbs.org/newshour/feeds/rss/headlines", "region": "US", "priority": 2},
    {"name": "VOA News", "url": "https://www.voanews.com/api/zkvvqeoiyk", "region": "US", "priority": 2},
    {"name": "CBC Canada", "url": "https://www.cbc.ca/cmlink/rss-topstories", "region": "CA", "priority": 2},
    {"name": "ABC News AU", "url": "https://www.abc.net.au/news/feed/51120/rss.xml", "region": "AU", "priority": 3},
    {"name": "Sky News", "url": "https://feeds.skynews.com/feeds/rss/world.xml", "region": "GB", "priority": 2},
    {"name": "Independent", "url": "https://www.independent.co.uk/news/rss", "region": "GB", "priority": 3},
    {"name": "Euronews", "url": "https://feeds.feedburner.com/euronews/en/news/", "region": "EU", "priority": 2},

    # ── US News ───────────────────────────────────────────────────────────────
    {"name": "ABC News US", "url": "https://abcnews.go.com/abcnews/topstories", "region": "US", "priority": 2},
    {"name": "NBC News", "url": "https://feeds.nbcnews.com/nbcnews/public/news", "region": "US", "priority": 2},
    {"name": "CBS News", "url": "https://www.cbsnews.com/latest/rss/main", "region": "US", "priority": 2},
    {"name": "Politico", "url": "https://www.politico.com/rss/politicopicks.xml", "region": "US", "priority": 2},
    {"name": "The Hill", "url": "https://thehill.com/news/feed/", "region": "US", "priority": 2},
    {"name": "ProPublica", "url": "https://feeds.propublica.org/propublica/main", "region": "US", "priority": 3},
    {"name": "The Atlantic", "url": "https://www.theatlantic.com/feed/all/", "region": "US", "priority": 3},
    {"name": "Axios", "url": "https://api.axios.com/feed/", "region": "US", "priority": 2},

    # ── Finance / Economy ────────────────────────────────────────────────────
    {"name": "Reuters Finance", "url": "https://feeds.reuters.com/reuters/businessNews", "region": "US", "priority": 1},
    {"name": "CNBC Finance", "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html", "region": "US", "priority": 1},
    {"name": "CNBC Markets", "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html", "region": "US", "priority": 1},
    {"name": "Bloomberg Markets", "url": "https://feeds.bloomberg.com/markets/news.rss", "region": "US", "priority": 1},
    {"name": "Bloomberg Economics", "url": "https://feeds.bloomberg.com/economics/news.rss", "region": "US", "priority": 1},
    {"name": "FT Markets", "url": "https://www.ft.com/rss/home/uk", "region": "GB", "priority": 2},
    {"name": "Seeking Alpha", "url": "https://seekingalpha.com/feed.xml", "region": "US", "priority": 3},
    {"name": "MarketWatch", "url": "https://feeds.marketwatch.com/marketwatch/topstories", "region": "US", "priority": 2},
    {"name": "Investopedia", "url": "https://www.investopedia.com/feedbuilder/feed/getfeed/?feedName=rss_headline", "region": "US", "priority": 3},

    # ── Crypto / Web3 ────────────────────────────────────────────────────────
    {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "region": "US", "priority": 2},
    {"name": "CoinTelegraph", "url": "https://cointelegraph.com/rss", "region": "US", "priority": 2},
    {"name": "Decrypt", "url": "https://decrypt.co/feed", "region": "US", "priority": 3},
    {"name": "The Block", "url": "https://www.theblock.co/rss.xml", "region": "US", "priority": 3},

    # ── Technology / AI ──────────────────────────────────────────────────────
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "region": "US", "priority": 2},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "region": "US", "priority": 1},
    {"name": "Ars Technica", "url": "http://feeds.arstechnica.com/arstechnica/index", "region": "US", "priority": 2},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss", "region": "US", "priority": 3},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "region": "US", "priority": 3},
    {"name": "Hacker News Best", "url": "https://hnrss.org/best", "region": "US", "priority": 2},
    {"name": "Hacker News Front", "url": "https://hnrss.org/frontpage", "region": "US", "priority": 2},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "region": "US", "priority": 2},
    {"name": "VentureBeat", "url": "https://venturebeat.com/feed/", "region": "US", "priority": 3},
    {"name": "ZDNet", "url": "https://www.zdnet.com/news/rss.xml", "region": "US", "priority": 3},
    {"name": "Slashdot", "url": "https://rss.slashdot.org/Slashdot/slashdotMain", "region": "US", "priority": 3},

    # ── Science / Health ─────────────────────────────────────────────────────
    {"name": "Nature News", "url": "https://www.nature.com/nature.rss", "region": None, "priority": 2},
    {"name": "Science AAAS", "url": "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science", "region": None, "priority": 2},
    {"name": "New Scientist", "url": "https://www.newscientist.com/feed/home/", "region": None, "priority": 3},
    {"name": "ScienceDaily", "url": "https://www.sciencedaily.com/rss/all.xml", "region": None, "priority": 3},
    {"name": "WHO News", "url": "https://www.who.int/rss-feeds/news-english.xml", "region": None, "priority": 2},
    {"name": "CDC Newsroom", "url": "https://tools.cdc.gov/api/v2/resources/media/316422.rss", "region": "US", "priority": 2},

    # ── Geopolitics / Defense ────────────────────────────────────────────────
    {"name": "Foreign Affairs", "url": "https://www.foreignaffairs.com/rss.xml", "region": "US", "priority": 2},
    {"name": "Defense News", "url": "https://www.defensenews.com/arc/outboundfeeds/rss/", "region": "US", "priority": 2},
    {"name": "The Diplomat", "url": "https://thediplomat.com/feed/", "region": None, "priority": 2},
    {"name": "War on the Rocks", "url": "https://warontherocks.com/feed/", "region": "US", "priority": 3},
    {"name": "Bellingcat", "url": "https://www.bellingcat.com/feed/", "region": None, "priority": 2},

    # ── Climate / Energy ─────────────────────────────────────────────────────
    {"name": "Carbon Brief", "url": "https://www.carbonbrief.org/feed/", "region": None, "priority": 2},
    {"name": "CleanTechnica", "url": "https://cleantechnica.com/feed/", "region": "US", "priority": 3},
    {"name": "Reuters Environment", "url": "https://feeds.reuters.com/reuters/environment", "region": "US", "priority": 2},

    # ── Asia-Pacific ─────────────────────────────────────────────────────────
    {"name": "Xinhua World", "url": "http://www.xinhuanet.com/english/rss/worldrss.xml", "region": "CN", "priority": 3},
    {"name": "Times of India", "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "region": "IN", "priority": 3},
    {"name": "The Hindu", "url": "https://www.thehindu.com/news/international/?service=rss", "region": "IN", "priority": 3},
    {"name": "NHK World", "url": "https://www3.nhk.or.jp/rss/news/cat0.xml", "region": "JP", "priority": 3},
    {"name": "SCMP", "url": "https://www.scmp.com/rss/91/feed", "region": "HK", "priority": 2},
    {"name": "Straits Times", "url": "https://www.straitstimes.com/news/world/rss.xml", "region": "SG", "priority": 3},

    # ── Europe / Middle East / Africa ────────────────────────────────────────
    {"name": "Deutsche Welle", "url": "https://rss.dw.com/rdf/rss-en-all", "region": "DE", "priority": 3},
    {"name": "Der Spiegel Int", "url": "https://www.spiegel.de/international/index.rss", "region": "DE", "priority": 3},
    {"name": "Le Monde EN", "url": "https://www.lemonde.fr/en/rss/une.xml", "region": "FR", "priority": 3},
    {"name": "France 24", "url": "https://www.france24.com/en/rss", "region": "FR", "priority": 2},
    {"name": "The Local EU", "url": "https://feeds.thelocal.com/rss/en", "region": "EU", "priority": 3},
    {"name": "Arab News", "url": "https://www.arabnews.com/rss.xml", "region": "SA", "priority": 3},
    {"name": "Haaretz EN", "url": "https://www.haaretz.com/srv/haaretz-en.rss", "region": "IL", "priority": 3},
    {"name": "Daily Maverick ZA", "url": "https://www.dailymaverick.co.za/feed/", "region": "ZA", "priority": 3},

    # ── Latin America ────────────────────────────────────────────────────────
    {"name": "Reuters LatAm", "url": "https://feeds.reuters.com/reuters/latamNews", "region": "LATAM", "priority": 3},
    {"name": "BBC Mundo", "url": "https://feeds.bbci.co.uk/mundo/rss.xml", "region": "LATAM", "priority": 3},
]


class RSSCrawler(BaseCrawler):
    def __init__(self, source_config: Dict):
        super().__init__(source_config)
        self.feed_url = source_config["url"]

    async def crawl(self) -> AsyncGenerator[RawArticle, None]:
        html = await self._fetch(self.feed_url)
        if not html:
            return

        feed = feedparser.parse(html)
        for entry in feed.entries:
            try:
                title = entry.get("title", "").strip()
                url = entry.get("link", "").strip()
                if not title or not url:
                    continue

                # Extract content
                content = ""
                if hasattr(entry, "content"):
                    content = BeautifulSoup(entry.content[0].value, "lxml").get_text(separator=" ")
                elif hasattr(entry, "summary"):
                    content = BeautifulSoup(entry.summary, "lxml").get_text(separator=" ")
                elif hasattr(entry, "description"):
                    content = BeautifulSoup(entry.description, "lxml").get_text(separator=" ")

                # Parse date
                published_at = None
                if hasattr(entry, "published"):
                    try:
                        published_at = parsedate_to_datetime(entry.published)
                    except Exception:
                        pass
                if published_at is None and hasattr(entry, "updated"):
                    try:
                        published_at = parsedate_to_datetime(entry.updated)
                    except Exception:
                        pass

                author = entry.get("author", None)

                yield RawArticle(
                    url=url,
                    title=title,
                    content=content,
                    source=self.name,
                    source_type="rss",
                    published_at=published_at or datetime.utcnow(),
                    author=author,
                    region=self.source_config.get("region"),
                    metadata={"feed_url": self.feed_url},
                )
            except Exception as e:
                logger.warning("RSS entry parse error [%s]: %s", self.name, e)
                continue


class RSSCrawlerPool:
    def __init__(self, sources: List[Dict] = None):
        self.sources = sources or RSS_SOURCES

    async def crawl_all(self) -> AsyncGenerator[RawArticle, None]:
        semaphore = asyncio.Semaphore(50)

        async def crawl_one(source):
            async with semaphore:
                crawler = RSSCrawler(source)
                async for article in crawler.run():
                    yield article

        tasks = [crawl_one(src) for src in self.sources]
        for coro in asyncio.as_completed([self._collect(t) for t in tasks]):
            articles = await coro
            for article in articles:
                yield article

    async def _collect(self, gen) -> List[RawArticle]:
        results = []
        async for item in gen:
            results.append(item)
        return results
