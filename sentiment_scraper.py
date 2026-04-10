"""
Sentiment Scraper — Scrapes Malaysian stock forum discussions,
extracts stock mentions, computes sentiment scores, and provides
aggregated sentiment data for the signal engine.

Sources:
- KLSE Screener (klsescreener.com)
- i3investor (klse.i3investor.com)
- Reddit (r/Bursa_Malaysia, r/MalaysianPF)
- MalaysiaStock.Biz (malaysiastock.biz)
- Lowyat Forum (forum.lowyat.net/StockExchange)
"""

import os
import re
import time
import json
import logging
import hashlib
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional

import requests
from bs4 import BeautifulSoup

from stock_aliases import build_alias_map
from sentiment_config import (
    FORUM_SOURCES,
    SENTIMENT_PARAMS,
    SENTIMENT_CACHE_FILE,
    BULLISH_EN, BEARISH_EN,
    BULLISH_MS, BEARISH_MS,
    EVENT_KEYWORDS,
    LLM_ENABLED,
    LLM_CONFIG,
    LLM_PROMPT_TEMPLATE,
    LLM_COST_LIMIT_DAILY,
)

logger = logging.getLogger("sentiment")


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class ForumPost:
    source: str
    text: str
    timestamp: float
    stock_mentions: list[str] = field(default_factory=list)
    raw_sentiment: float = 0.0
    author: str = ""
    url: str = ""
    # LLM classification fields
    llm_label: str = ""            # "POSITIVE", "NEGATIVE", "NOISE", or "" if not classified
    llm_confidence: float = 0.0    # 0.0-1.0 confidence from LLM
    llm_reason: str = ""           # brief LLM reasoning


@dataclass
class StockSentiment:
    stock_key: str
    mention_count: int = 0
    sentiment_score: float = 50.0   # 0-100 scale (same as signal sub-scores)
    buzz_score: float = 0.0         # 0-100, percentile-based
    mention_trend: float = 0.0      # % change vs prior period
    bullish_count: int = 0
    bearish_count: int = 0
    neutral_count: int = 0
    top_sources: list[str] = field(default_factory=list)
    last_updated: float = 0.0
    recent_posts: list[dict] = field(default_factory=list)
    # Event detection fields
    events: list[dict] = field(default_factory=list)  # detected company events
    event_impact: float = 0.0       # net event impact on sentiment (-1 to +1)
    has_catalyst: bool = False       # True if significant event detected
    # LLM classification aggregates
    llm_positive_pct: float = 0.0   # % of posts classified POSITIVE by LLM
    llm_negative_pct: float = 0.0   # % of posts classified NEGATIVE by LLM
    llm_noise_pct: float = 0.0      # % of posts classified NOISE by LLM
    llm_classified_count: int = 0   # how many posts had LLM classification
    llm_consensus: str = ""         # "POSITIVE", "NEGATIVE", "MIXED", "NOISE"

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# SENTIMENT ANALYZER — Keyword-based scoring
# ============================================================

class SentimentAnalyzer:
    """Extracts stock mentions and computes sentiment from text."""

    def __init__(self):
        self.alias_map = build_alias_map()
        # Pre-compile sorted aliases (longest first for greedy matching)
        self._sorted_aliases = sorted(
            self.alias_map.keys(), key=len, reverse=True
        )
        # Combine all keyword dicts
        self._bullish = {**BULLISH_EN, **BULLISH_MS}
        self._bearish = {**BEARISH_EN, **BEARISH_MS}
        # Pre-compile keyword patterns (longest first)
        self._bullish_patterns = sorted(
            self._bullish.keys(), key=len, reverse=True
        )
        self._bearish_patterns = sorted(
            self._bearish.keys(), key=len, reverse=True
        )

    def extract_stock_mentions(self, text: str) -> list[str]:
        """Find all stock references in text. Returns list of stock keys."""
        text_lower = text.lower()
        found = set()
        for alias in self._sorted_aliases:
            if len(alias) <= 2:
                # Short aliases need word boundary matching
                pattern = r'\b' + re.escape(alias) + r'\b'
                if re.search(pattern, text_lower):
                    found.add(self.alias_map[alias])
            else:
                if alias in text_lower:
                    found.add(self.alias_map[alias])
        return list(found)

    def analyze_text(self, text: str) -> float:
        """
        Compute sentiment score from text.
        Returns raw score in range [-1.0, +1.0].
        Positive = bullish, negative = bearish.
        """
        text_lower = text.lower()
        bullish_sum = 0.0
        bearish_sum = 0.0

        for kw in self._bullish_patterns:
            if kw in text_lower:
                bullish_sum += self._bullish[kw]

        for kw in self._bearish_patterns:
            if kw in text_lower:
                bearish_sum += self._bearish[kw]

        total = bullish_sum + bearish_sum
        if total == 0:
            return 0.0

        raw = (bullish_sum - bearish_sum) / total
        return max(-1.0, min(1.0, raw))

    def detect_events(self, text: str) -> list[dict]:
        """
        Detect company-specific events in text that could impact stock price.
        Returns list of detected events with type, impact direction, and weight.

        Checks for: new contracts, terminations, legal issues, earnings,
        management changes, M&A, regulatory, analyst rating changes.
        """
        text_lower = text.lower()
        detected = []

        for event_type, cfg in EVENT_KEYWORDS.items():
            for keyword in cfg["keywords"]:
                if keyword.lower() in text_lower:
                    detected.append({
                        "type": event_type,
                        "keyword": keyword,
                        "impact": cfg["impact"],
                        "weight": cfg["weight"],
                    })
                    break  # one match per event type is enough

        return detected

    @staticmethod
    def raw_to_score(raw: float) -> float:
        """Convert raw sentiment [-1, +1] to 0-100 score."""
        return 50.0 + raw * 50.0


# ============================================================
# LLM SENTIMENT CLASSIFIER — Anthropic Claude Sonnet
# ============================================================

class LLMSentimentClassifier:
    """
    Uses Anthropic Claude Sonnet to classify forum posts as
    POSITIVE, NEGATIVE, or NOISE. Processes posts in batches
    for efficiency. Falls back to keyword scoring on failure.
    """

    def __init__(self):
        self._client = None
        self._available = False
        self._daily_calls = 0
        self._daily_reset = time.time()
        self._cache: dict[str, tuple[str, float, str]] = {}  # text_hash -> (label, confidence, reason)
        self._cache_timestamps: dict[str, float] = {}
        self._lock = threading.Lock()

        if not LLM_ENABLED:
            logger.info("LLM sentiment classification disabled")
            return

        try:
            import anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                logger.warning("ANTHROPIC_API_KEY not set — LLM classification disabled")
                return
            self._client = anthropic.Anthropic(api_key=api_key)
            self._available = True
            logger.info("LLM sentiment classifier initialized (Claude Sonnet)")
        except ImportError:
            logger.warning("anthropic package not installed — LLM classification disabled")
        except Exception as e:
            logger.warning(f"Failed to initialize Anthropic client: {e}")

    @property
    def is_available(self) -> bool:
        return self._available and self._client is not None

    def classify_posts(self, posts: list[ForumPost]) -> list[ForumPost]:
        """
        Classify a list of ForumPost objects using Claude Sonnet.
        Updates each post's llm_label, llm_confidence, llm_reason in-place.
        Returns the same list (mutated).
        """
        if not self.is_available:
            return posts

        # Reset daily counter if needed
        now = time.time()
        with self._lock:
            if now - self._daily_reset > 86400:
                self._daily_calls = 0
                self._daily_reset = now

        # Filter posts worth classifying
        classifiable = [
            p for p in posts
            if len(p.text.strip()) >= LLM_CONFIG["min_text_length"]
            and not self._check_cache(p.text)
        ]

        # Apply cached results to posts that have them
        for p in posts:
            cached = self._get_cache(p.text)
            if cached:
                p.llm_label, p.llm_confidence, p.llm_reason = cached

        if not classifiable:
            return posts

        # Batch process
        batch_size = LLM_CONFIG["batch_size"]
        max_calls = LLM_CONFIG["max_calls_per_cycle"]
        calls_made = 0

        for i in range(0, len(classifiable), batch_size):
            if calls_made >= max_calls:
                logger.info(f"LLM call limit reached ({max_calls}), remaining posts use keyword scoring")
                break

            with self._lock:
                if self._daily_calls >= (LLM_COST_LIMIT_DAILY / 0.01):
                    logger.warning("LLM daily cost limit reached, skipping")
                    break

            batch = classifiable[i:i + batch_size]
            try:
                results = self._classify_batch(batch)
                for post, result in zip(batch, results):
                    post.llm_label = result[0]
                    post.llm_confidence = result[1]
                    post.llm_reason = result[2]
                    self._set_cache(post.text, result)
                calls_made += 1
                with self._lock:
                    self._daily_calls += 1
            except Exception as e:
                logger.error(f"LLM batch classification failed: {e}")
                if not LLM_CONFIG["fallback_on_error"]:
                    break
                # Posts in this batch keep default empty llm_label

        classified = sum(1 for p in posts if p.llm_label)
        logger.info(f"LLM classified {classified}/{len(posts)} posts ({calls_made} API calls)")
        return posts

    def _classify_batch(self, batch: list[ForumPost]) -> list[tuple[str, float, str]]:
        """Send a batch of posts to Claude Sonnet and parse results."""
        # Format posts for the prompt
        posts_text = ""
        for idx, post in enumerate(batch, 1):
            # Truncate to save tokens
            text = post.text[:300].replace("\n", " ").strip()
            posts_text += f"\n{idx}. [{post.source}] {text}"

        prompt = LLM_PROMPT_TEMPLATE.format(posts=posts_text)

        response = self._client.messages.create(
            model=LLM_CONFIG["model"],
            max_tokens=LLM_CONFIG["max_tokens"],
            temperature=LLM_CONFIG["temperature"],
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response
        response_text = response.content[0].text.strip()
        results = self._parse_response(response_text, len(batch))
        return results

    def _parse_response(self, text: str, expected_count: int) -> list[tuple[str, float, str]]:
        """Parse LLM response into (label, confidence, reason) tuples."""
        results = []
        valid_labels = {"POSITIVE", "NEGATIVE", "NOISE"}

        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = line.split("|", 3)
            if len(parts) < 3:
                continue

            try:
                label = parts[1].strip().upper()
                if label not in valid_labels:
                    label = "NOISE"
                confidence = float(parts[2].strip())
                confidence = max(0.0, min(1.0, confidence))
                reason = parts[3].strip() if len(parts) > 3 else ""
                results.append((label, confidence, reason))
            except (ValueError, IndexError):
                results.append(("NOISE", 0.3, "parse error"))

        # Pad if we got fewer results than expected
        while len(results) < expected_count:
            results.append(("NOISE", 0.0, "no response"))

        return results[:expected_count]

    def _check_cache(self, text: str) -> bool:
        """Check if text has a cached LLM result."""
        key = self._cache_key(text)
        with self._lock:
            if key in self._cache:
                ts = self._cache_timestamps.get(key, 0)
                if time.time() - ts < LLM_CONFIG["cache_ttl"]:
                    return True
                # Expired
                del self._cache[key]
                del self._cache_timestamps[key]
        return False

    def _get_cache(self, text: str) -> Optional[tuple[str, float, str]]:
        """Get cached LLM result for text."""
        key = self._cache_key(text)
        with self._lock:
            if key in self._cache:
                ts = self._cache_timestamps.get(key, 0)
                if time.time() - ts < LLM_CONFIG["cache_ttl"]:
                    return self._cache[key]
        return None

    def _set_cache(self, text: str, result: tuple[str, float, str]):
        """Cache an LLM result."""
        key = self._cache_key(text)
        with self._lock:
            self._cache[key] = result
            self._cache_timestamps[key] = time.time()
            # Prune cache if too large (keep last 2000 entries)
            if len(self._cache) > 2000:
                oldest_keys = sorted(
                    self._cache_timestamps, key=self._cache_timestamps.get
                )[:500]
                for k in oldest_keys:
                    self._cache.pop(k, None)
                    self._cache_timestamps.pop(k, None)

    @staticmethod
    def _cache_key(text: str) -> str:
        """Generate a short hash key for text."""
        return hashlib.md5(text[:300].encode("utf-8", errors="ignore")).hexdigest()


# ============================================================
# BASE SCRAPER
# ============================================================

class BaseScraper:
    """Base class for forum scrapers with rate limiting and caching."""

    def __init__(self, source_name: str, rate_limit: float = 5.0):
        self.source_name = source_name
        self._rate_limit = rate_limit
        self._last_request_time = 0.0
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def _wait_rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit:
            time.sleep(self._rate_limit - elapsed)
        self._last_request_time = time.time()

    def _get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Rate-limited GET request with error handling."""
        self._wait_rate_limit()
        try:
            resp = self._session.get(url, timeout=15, **kwargs)
            if resp.status_code == 200:
                return resp
            logger.warning(f"[{self.source_name}] HTTP {resp.status_code} for {url}")
            return None
        except Exception as e:
            logger.error(f"[{self.source_name}] Request error for {url}: {e}")
            return None

    def fetch_posts(self) -> list[ForumPost]:
        """Override in subclass. Returns list of ForumPost."""
        raise NotImplementedError


# ============================================================
# KLSE SCREENER SCRAPER
# ============================================================

class KLSEScreenerScraper(BaseScraper):
    """Scrapes discussion pages from klsescreener.com"""

    def __init__(self):
        cfg = FORUM_SOURCES["klsescreener"]
        super().__init__("klsescreener", cfg.get("rate_limit", 5.0))
        self.base_url = cfg["base_url"]
        self.max_pages = cfg.get("max_pages", 3)

    def fetch_posts(self) -> list[ForumPost]:
        posts = []
        for page in range(1, self.max_pages + 1):
            url = f"{self.base_url}/v2/discussion/index/{page}"
            resp = self._get(url)
            if not resp:
                continue

            try:
                soup = BeautifulSoup(resp.text, "html.parser")
                # Find discussion entries
                for card in soup.select(".card-container, .comment, .message, .discussion-item"):
                    text = card.get_text(strip=True, separator=" ")
                    if len(text) < 5:
                        continue

                    # Try to extract stock code from links
                    stock_link = card.select_one("a[href*='/v2/stocks/view/']")
                    url_str = ""
                    if stock_link:
                        url_str = self.base_url + stock_link.get("href", "")

                    posts.append(ForumPost(
                        source=self.source_name,
                        text=text[:500],  # cap text length
                        timestamp=time.time(),  # approximate
                        url=url_str,
                    ))
            except Exception as e:
                logger.error(f"[klsescreener] Parse error page {page}: {e}")

        logger.info(f"[klsescreener] Fetched {len(posts)} posts from {self.max_pages} pages")
        return posts


# ============================================================
# REDDIT SCRAPER
# ============================================================

class RedditScraper(BaseScraper):
    """Scrapes posts from Reddit subreddits via JSON API."""

    def __init__(self):
        super().__init__("reddit", 2.0)
        self._subreddits = []
        if FORUM_SOURCES.get("reddit_bursa", {}).get("enabled"):
            self._subreddits.append(FORUM_SOURCES["reddit_bursa"]["url"])
        if FORUM_SOURCES.get("reddit_mypf", {}).get("enabled"):
            self._subreddits.append(FORUM_SOURCES["reddit_mypf"]["url"])

    def fetch_posts(self) -> list[ForumPost]:
        posts = []
        for url in self._subreddits:
            resp = self._get(url)
            if not resp:
                continue

            try:
                data = resp.json()
                children = data.get("data", {}).get("children", [])
                for child in children:
                    post_data = child.get("data", {})
                    title = post_data.get("title", "")
                    selftext = post_data.get("selftext", "")
                    text = f"{title} {selftext}".strip()
                    if len(text) < 5:
                        continue

                    created = post_data.get("created_utc", time.time())
                    author = post_data.get("author", "")
                    permalink = post_data.get("permalink", "")

                    posts.append(ForumPost(
                        source="reddit",
                        text=text[:500],
                        timestamp=created,
                        author=author,
                        url=f"https://www.reddit.com{permalink}" if permalink else "",
                    ))
            except Exception as e:
                logger.error(f"[reddit] Parse error: {e}")

        logger.info(f"[reddit] Fetched {len(posts)} posts from {len(self._subreddits)} subreddits")
        return posts


# ============================================================
# I3INVESTOR SCRAPER
# ============================================================

class I3InvestorScraper(BaseScraper):
    """Scrapes discussion pages from klse.i3investor.com"""

    def __init__(self):
        cfg = FORUM_SOURCES["i3investor"]
        super().__init__("i3investor", cfg.get("rate_limit", 5.0))
        self.base_url = cfg["base_url"]

    def fetch_posts(self) -> list[ForumPost]:
        posts = []
        # Scrape the main blog/discussion hub page
        url = f"{self.base_url}/web/blog/stock-market-pair"
        resp = self._get(url)
        if not resp:
            return posts

        try:
            soup = BeautifulSoup(resp.text, "html.parser")

            # 1) Blog entries from widget-data-row (news/blog posts)
            for row in soup.select(".widget-data-row"):
                text = row.get_text(strip=True, separator=" ")
                if len(text) < 15:
                    continue
                link = row.select_one("a[href]")
                url_str = ""
                if link:
                    href = link.get("href", "")
                    if href.startswith("/"):
                        url_str = self.base_url + href
                    elif href.startswith("http"):
                        url_str = href
                posts.append(ForumPost(
                    source=self.source_name,
                    text=text[:500],
                    timestamp=time.time(),
                    url=url_str,
                ))

            # 2) Stock discussion links from db-mod-card sections
            for card in soup.select(".db-mod-card"):
                for link in card.select("a[href]"):
                    href = link.get("href", "")
                    text = link.get_text(strip=True)
                    if len(text) < 5 or "/forum/" not in href:
                        continue
                    url_str = self.base_url + href if href.startswith("/") else href
                    posts.append(ForumPost(
                        source=self.source_name,
                        text=text[:500],
                        timestamp=time.time(),
                        url=url_str,
                    ))
        except Exception as e:
            logger.error(f"[i3investor] Parse error: {e}")

        logger.info(f"[i3investor] Fetched {len(posts)} posts")
        return posts


# ============================================================
# MALAYSIASTOCK.BIZ SCRAPER
# ============================================================

class MalaysiaStockBizScraper(BaseScraper):
    """Scrapes forum from malaysiastock.biz"""

    def __init__(self):
        cfg = FORUM_SOURCES["malaysiastockbiz"]
        super().__init__("malaysiastockbiz", cfg.get("rate_limit", 5.0))
        self.base_url = cfg["base_url"]

    def fetch_posts(self) -> list[ForumPost]:
        posts = []
        url = f"{self.base_url}/Forum/Main.aspx"
        resp = self._get(url)
        if not resp:
            return posts

        try:
            soup = BeautifulSoup(resp.text, "html.parser")
            # Forum typically has thread titles and discussion snippets
            for item in soup.select(".forumTopic, .thread, tr, .post, .topic-row, .discussion-item"):
                text = item.get_text(strip=True, separator=" ")
                if len(text) < 10:
                    continue

                link = item.select_one("a[href]")
                url_str = ""
                if link:
                    href = link.get("href", "")
                    if href.startswith("/"):
                        url_str = self.base_url + href

                posts.append(ForumPost(
                    source=self.source_name,
                    text=text[:500],
                    timestamp=time.time(),
                    url=url_str,
                ))
        except Exception as e:
            logger.error(f"[malaysiastockbiz] Parse error: {e}")

        logger.info(f"[malaysiastockbiz] Fetched {len(posts)} posts")
        return posts


# ============================================================
# LOWYAT SCRAPER
# ============================================================

class LowyatScraper(BaseScraper):
    """Scrapes Stock Exchange subforum from forum.lowyat.net"""

    def __init__(self):
        cfg = FORUM_SOURCES["lowyat"]
        super().__init__("lowyat", cfg.get("rate_limit", 5.0))
        self.base_url = cfg["base_url"]
        self.max_pages = cfg.get("max_pages", 2)

    def fetch_posts(self) -> list[ForumPost]:
        posts = []
        for page in range(1, self.max_pages + 1):
            if page == 1:
                url = f"{self.base_url}/StockExchange"
            else:
                url = f"{self.base_url}/StockExchange/{page}"

            resp = self._get(url)
            if not resp:
                continue

            try:
                soup = BeautifulSoup(resp.text, "html.parser")
                # Lowyat forum uses table rows for topics
                for row in soup.select(".threadbit, tr.topic, .topic-row, tr"):
                    title_el = row.select_one("a.title, a.topictitle, td a")
                    if not title_el:
                        continue

                    text = title_el.get_text(strip=True)
                    if len(text) < 5:
                        continue

                    href = title_el.get("href", "")
                    url_str = ""
                    if href.startswith("/"):
                        url_str = self.base_url + href
                    elif href.startswith("http"):
                        url_str = href

                    posts.append(ForumPost(
                        source=self.source_name,
                        text=text[:500],
                        timestamp=time.time(),
                        url=url_str,
                    ))
            except Exception as e:
                logger.error(f"[lowyat] Parse error page {page}: {e}")

        logger.info(f"[lowyat] Fetched {len(posts)} posts from {self.max_pages} pages")
        return posts


# ============================================================
# THE EDGE MALAYSIA SCRAPER
# ============================================================

class TheEdgeScraper(BaseScraper):
    """Scrapes news headlines from theedgemalaysia.com via __NEXT_DATA__."""

    def __init__(self):
        cfg = FORUM_SOURCES["theedge"]
        super().__init__("theedge", cfg.get("rate_limit", 5.0))
        self.base_url = cfg["base_url"]

    def fetch_posts(self) -> list[ForumPost]:
        posts = []
        resp = self._get(self.base_url)
        if not resp:
            return posts

        try:
            import re as _re
            import json as _json
            match = _re.search(
                r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                resp.text, _re.DOTALL,
            )
            if not match:
                logger.warning("[theedge] No __NEXT_DATA__ found")
                return posts

            data = _json.loads(match.group(1))
            pp = data.get("props", {}).get("pageProps", {})

            # Extract articles from multiple sections
            for section in ["homeData", "malaysiaNews", "wealthData"]:
                for item in pp.get(section, []):
                    if not isinstance(item, dict):
                        continue
                    title = item.get("title", "")
                    if not title or len(title) < 10:
                        continue
                    nid = item.get("nid", "")
                    url_str = f"{self.base_url}/node/{nid}" if nid else ""
                    posts.append(ForumPost(
                        source=self.source_name,
                        text=title[:500],
                        timestamp=time.time(),
                        url=url_str,
                    ))
        except Exception as e:
            logger.error(f"[theedge] Parse error: {e}")

        logger.info(f"[theedge] Fetched {len(posts)} posts")
        return posts


# ============================================================
# THE STAR BUSINESS SCRAPER
# ============================================================

class TheStarScraper(BaseScraper):
    """Scrapes business headlines from thestar.com.my/business."""

    def __init__(self):
        cfg = FORUM_SOURCES["thestar"]
        super().__init__("thestar", cfg.get("rate_limit", 5.0))
        self.base_url = cfg["base_url"]

    def fetch_posts(self) -> list[ForumPost]:
        posts = []
        url = f"{self.base_url}/business"
        resp = self._get(url)
        if not resp:
            return posts

        try:
            soup = BeautifulSoup(resp.text, "html.parser")
            seen_texts = set()

            # Collect all links pointing to /business/ articles
            for link in soup.select('a[href*="/business/"]'):
                text = link.get_text(strip=True)
                href = link.get("href", "")
                if len(text) < 15 or text in seen_texts:
                    continue
                # Skip nav/section links
                if href.endswith("/business") or href.endswith("/business/"):
                    continue
                seen_texts.add(text)

                url_str = href
                if href.startswith("/"):
                    url_str = self.base_url + href

                posts.append(ForumPost(
                    source=self.source_name,
                    text=text[:500],
                    timestamp=time.time(),
                    url=url_str,
                ))
        except Exception as e:
            logger.error(f"[thestar] Parse error: {e}")

        logger.info(f"[thestar] Fetched {len(posts)} posts")
        return posts


# ============================================================
# SENTIMENT AGGREGATOR
# ============================================================

class SentimentAggregator:
    """
    Orchestrates forum scraping, sentiment analysis, and per-stock aggregation.
    Thread-safe for use with Flask background thread.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.analyzer = SentimentAnalyzer()
        self.llm_classifier = LLMSentimentClassifier()

        # Initialize enabled scrapers
        self.scrapers: list[BaseScraper] = []
        if FORUM_SOURCES.get("klsescreener", {}).get("enabled"):
            self.scrapers.append(KLSEScreenerScraper())
        if FORUM_SOURCES.get("reddit_bursa", {}).get("enabled") or \
           FORUM_SOURCES.get("reddit_mypf", {}).get("enabled"):
            self.scrapers.append(RedditScraper())
        if FORUM_SOURCES.get("i3investor", {}).get("enabled"):
            self.scrapers.append(I3InvestorScraper())
        if FORUM_SOURCES.get("malaysiastockbiz", {}).get("enabled"):
            self.scrapers.append(MalaysiaStockBizScraper())
        if FORUM_SOURCES.get("lowyat", {}).get("enabled"):
            self.scrapers.append(LowyatScraper())
        if FORUM_SOURCES.get("theedge", {}).get("enabled"):
            self.scrapers.append(TheEdgeScraper())
        if FORUM_SOURCES.get("thestar", {}).get("enabled"):
            self.scrapers.append(TheStarScraper())

        # State
        self._sentiments: dict[str, StockSentiment] = {}
        self._all_posts: list[ForumPost] = []         # rolling 10-day window
        self._prior_posts: list[ForumPost] = []       # previous 3-day window for trend
        self._trending: list[dict] = []
        self._last_update: float = 0.0
        self._active_sources: int = 0
        self._total_mentions_24h: int = 0

        # Load cache
        self._load_cache()

    def update(self):
        """Run all scrapers and recompute sentiment. Called by background thread."""
        new_posts: list[ForumPost] = []
        active_sources = 0

        for scraper in self.scrapers:
            try:
                posts = scraper.fetch_posts()
                if posts:
                    active_sources += 1
                    # Analyze each post
                    for post in posts:
                        post.stock_mentions = self.analyzer.extract_stock_mentions(post.text)
                        post.raw_sentiment = self.analyzer.analyze_text(post.text)
                        # Detect events and boost sentiment accordingly
                        events = self.analyzer.detect_events(post.text)
                        if events:
                            event_boost = 0.0
                            for ev in events:
                                if ev["impact"] == "bullish":
                                    event_boost += 0.3 * ev["weight"]
                                elif ev["impact"] == "bearish":
                                    event_boost -= 0.3 * ev["weight"]
                            # Blend event boost into raw sentiment
                            post.raw_sentiment = max(-1.0, min(1.0,
                                post.raw_sentiment + event_boost * 0.5))
                    new_posts.extend(posts)
            except Exception as e:
                logger.error(f"Scraper {scraper.source_name} failed: {e}")

        # --- LLM Classification ---
        # Classify new posts with Claude Sonnet (only posts with stock mentions)
        if self.llm_classifier.is_available and new_posts:
            posts_with_mentions = [p for p in new_posts if p.stock_mentions]
            if posts_with_mentions:
                try:
                    self.llm_classifier.classify_posts(posts_with_mentions)
                    # Blend LLM label into raw_sentiment for classified posts
                    for post in posts_with_mentions:
                        if post.llm_label and post.llm_confidence > 0.3:
                            llm_raw = _llm_label_to_raw(post.llm_label, post.llm_confidence)
                            # Blend: 60% LLM, 40% keyword (LLM gets more weight when confident)
                            blend_weight = min(post.llm_confidence, 0.8)
                            post.raw_sentiment = (
                                post.raw_sentiment * (1 - blend_weight)
                                + llm_raw * blend_weight
                            )
                            post.raw_sentiment = max(-1.0, min(1.0, post.raw_sentiment))
                except Exception as e:
                    logger.error(f"LLM classification pipeline error: {e}")

        # Update rolling windows
        now = time.time()
        cutoff_decay = now - (SENTIMENT_PARAMS["decay_hours"] * 3600)  # 10 days
        cutoff_recent = now - (72 * 3600)  # 3 days = "recent" window

        with self._lock:
            # Prior posts: older than 3 days but within 10-day window (for trend calc)
            self._prior_posts = [
                p for p in self._all_posts
                if p.timestamp < cutoff_recent and p.timestamp >= cutoff_decay
            ]
            # Keep posts within 10-day window + add new ones
            self._all_posts = [
                p for p in self._all_posts if p.timestamp >= cutoff_decay
            ] + new_posts

            # Recompute per-stock sentiment
            self._compute_sentiments()
            self._active_sources = active_sources
            self._last_update = now

        # Persist cache
        self._save_cache()
        llm_status = f", LLM active" if self.llm_classifier.is_available else ""
        logger.info(
            f"Sentiment update: {active_sources} sources, "
            f"{len(new_posts)} new posts, "
            f"{len(self._sentiments)} stocks with mentions{llm_status}"
        )

    def _compute_sentiments(self):
        """Recompute all per-stock sentiment data. Must hold lock."""
        now = time.time()
        decay_hours = SENTIMENT_PARAMS["decay_hours"]
        cutoff_24h = now - (24 * 3600)

        # Group posts by stock
        stock_posts: dict[str, list[ForumPost]] = {}
        for post in self._all_posts:
            for stock_key in post.stock_mentions:
                if stock_key not in stock_posts:
                    stock_posts[stock_key] = []
                stock_posts[stock_key].append(post)

        # Group prior posts by stock (for trend calc)
        prior_counts: dict[str, int] = {}
        for post in self._prior_posts:
            for stock_key in post.stock_mentions:
                prior_counts[stock_key] = prior_counts.get(stock_key, 0) + 1

        # Compute mention counts for buzz scoring
        mention_counts = {k: len(v) for k, v in stock_posts.items()}

        # Compute buzz scores (percentile-based)
        buzz_scores = self._compute_buzz_scores(mention_counts)

        # Build StockSentiment for each stock
        sentiments = {}
        total_mentions = 0
        for stock_key, posts in stock_posts.items():
            # Weighted sentiment (time decay)
            weighted_sentiments = []
            bullish = 0
            bearish = 0
            neutral = 0
            sources = set()

            # Event detection aggregation
            all_events = []
            event_impact_sum = 0.0

            for post in posts:
                weight = self._time_decay_weight(post.timestamp, decay_hours)
                weighted_sentiments.append(post.raw_sentiment * weight)
                sources.add(post.source)

                if post.raw_sentiment > 0.1:
                    bullish += 1
                elif post.raw_sentiment < -0.1:
                    bearish += 1
                else:
                    neutral += 1

                # Detect events in each post
                events = self.analyzer.detect_events(post.text)
                for ev in events:
                    ev["stock_key"] = stock_key
                    ev["post_time"] = post.timestamp
                    ev["source"] = post.source
                    all_events.append(ev)
                    if ev["impact"] == "bullish":
                        event_impact_sum += ev["weight"]
                    elif ev["impact"] == "bearish":
                        event_impact_sum -= ev["weight"]

            # Average weighted sentiment
            if weighted_sentiments:
                avg_raw = sum(weighted_sentiments) / len(weighted_sentiments)
            else:
                avg_raw = 0.0

            # Normalize event impact to -1 to +1
            if all_events:
                event_impact = max(-1.0, min(1.0, event_impact_sum / len(all_events)))
                # Boost sentiment score by event impact (20% weight)
                avg_raw = avg_raw * 0.8 + event_impact * 0.2
                avg_raw = max(-1.0, min(1.0, avg_raw))
            else:
                event_impact = 0.0

            # Recent posts within 24h
            recent_24h = [p for p in posts if p.timestamp >= cutoff_24h]
            count_24h = len(recent_24h)
            total_mentions += count_24h

            # Mention trend
            prior_count = prior_counts.get(stock_key, 0)
            if prior_count > 0:
                trend = (count_24h - prior_count) / prior_count
            else:
                trend = 1.0 if count_24h > 0 else 0.0

            # Recent posts for display (last 5)
            sorted_posts = sorted(posts, key=lambda p: p.timestamp, reverse=True)[:5]
            recent_display = [
                {
                    "source": p.source,
                    "text": p.text[:200],
                    "sentiment": round(p.raw_sentiment, 2),
                    "time": p.timestamp,
                    "llm_label": p.llm_label,
                    "llm_confidence": round(p.llm_confidence, 2),
                    "llm_reason": p.llm_reason,
                }
                for p in sorted_posts
            ]

            # Deduplicate events by type (keep most recent per type)
            unique_events = {}
            for ev in sorted(all_events, key=lambda e: e.get("post_time", 0), reverse=True):
                if ev["type"] not in unique_events:
                    unique_events[ev["type"]] = {
                        "type": ev["type"],
                        "keyword": ev["keyword"],
                        "impact": ev["impact"],
                        "source": ev.get("source", ""),
                        "time": ev.get("post_time", 0),
                    }
            event_list = list(unique_events.values())

            # LLM classification aggregates
            llm_classified = [p for p in posts if p.llm_label]
            llm_count = len(llm_classified)
            llm_pos = sum(1 for p in llm_classified if p.llm_label == "POSITIVE")
            llm_neg = sum(1 for p in llm_classified if p.llm_label == "NEGATIVE")
            llm_noise = sum(1 for p in llm_classified if p.llm_label == "NOISE")
            llm_pos_pct = round(llm_pos / llm_count * 100, 1) if llm_count else 0.0
            llm_neg_pct = round(llm_neg / llm_count * 100, 1) if llm_count else 0.0
            llm_noise_pct = round(llm_noise / llm_count * 100, 1) if llm_count else 0.0

            # Determine LLM consensus
            if llm_count == 0:
                llm_consensus = ""
            elif llm_pos_pct >= 60:
                llm_consensus = "POSITIVE"
            elif llm_neg_pct >= 60:
                llm_consensus = "NEGATIVE"
            elif llm_noise_pct >= 60:
                llm_consensus = "NOISE"
            else:
                llm_consensus = "MIXED"

            sentiments[stock_key] = StockSentiment(
                stock_key=stock_key,
                mention_count=len(posts),
                sentiment_score=round(self.analyzer.raw_to_score(avg_raw), 1),
                buzz_score=buzz_scores.get(stock_key, 0.0),
                mention_trend=round(trend, 2),
                bullish_count=bullish,
                bearish_count=bearish,
                neutral_count=neutral,
                top_sources=sorted(sources),
                last_updated=now,
                recent_posts=recent_display,
                events=event_list,
                event_impact=round(event_impact, 2),
                has_catalyst=len(event_list) > 0,
                llm_positive_pct=llm_pos_pct,
                llm_negative_pct=llm_neg_pct,
                llm_noise_pct=llm_noise_pct,
                llm_classified_count=llm_count,
                llm_consensus=llm_consensus,
            )

        self._sentiments = sentiments
        self._total_mentions_24h = total_mentions

        # Compute trending (top 10 by mention count)
        sorted_stocks = sorted(
            sentiments.values(),
            key=lambda s: s.mention_count,
            reverse=True,
        )[:10]
        self._trending = [
            {
                "stock_key": s.stock_key,
                "mentions": s.mention_count,
                "sentiment_score": s.sentiment_score,
                "buzz_score": s.buzz_score,
                "trend": s.mention_trend,
            }
            for s in sorted_stocks
        ]

    @staticmethod
    def _compute_buzz_scores(mention_counts: dict[str, int]) -> dict[str, float]:
        if not mention_counts:
            return {}
        sorted_counts = sorted(mention_counts.values())
        n = len(sorted_counts)
        result = {}
        for key, count in mention_counts.items():
            percentile = sum(1 for c in sorted_counts if c <= count) / n
            result[key] = round(percentile * 100, 1)
        return result

    @staticmethod
    def _time_decay_weight(post_timestamp: float, decay_hours: float = 48.0) -> float:
        age_hours = (time.time() - post_timestamp) / 3600
        if age_hours <= 0:
            return 1.0
        return max(0.1, 1.0 - (age_hours / decay_hours))

    # ---- Public API (thread-safe) ----

    def get_sentiment(self, stock_key: str) -> Optional[StockSentiment]:
        with self._lock:
            return self._sentiments.get(stock_key)

    def get_all_sentiments(self) -> dict[str, "StockSentiment"]:
        with self._lock:
            # Return copies of StockSentiment objects (not dicts)
            return dict(self._sentiments)

    def get_trending(self) -> list[dict]:
        with self._lock:
            return list(self._trending)

    def get_recent_forum_posts(self, limit: int = 20) -> list[dict]:
        with self._lock:
            sorted_posts = sorted(
                self._all_posts,
                key=lambda p: p.timestamp,
                reverse=True,
            )[:limit]
            return [
                {
                    "source": p.source,
                    "text": p.text[:200],
                    "stock_mentions": p.stock_mentions,
                    "sentiment": round(p.raw_sentiment, 2),
                    "time": p.timestamp,
                    "author": p.author,
                    "url": p.url,
                    "llm_label": p.llm_label,
                    "llm_confidence": round(p.llm_confidence, 2),
                    "llm_reason": p.llm_reason,
                }
                for p in sorted_posts
            ]

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "active_sources": self._active_sources,
                "total_sources": len(self.scrapers),
                "total_mentions_24h": self._total_mentions_24h,
                "stocks_with_mentions": len(self._sentiments),
                "last_update": self._last_update,
                "most_bullish": self._get_extreme("bullish"),
                "most_bearish": self._get_extreme("bearish"),
                "llm_active": self.llm_classifier.is_available,
            }

    def _get_extreme(self, direction: str) -> Optional[dict]:
        """Get most bullish or bearish stock."""
        if not self._sentiments:
            return None
        if direction == "bullish":
            best = max(
                self._sentiments.values(),
                key=lambda s: s.sentiment_score if s.mention_count >= SENTIMENT_PARAMS["min_mentions"] else 50.0,
            )
            if best.sentiment_score > 55:
                return {"stock_key": best.stock_key, "score": best.sentiment_score, "mentions": best.mention_count}
        else:
            worst = min(
                self._sentiments.values(),
                key=lambda s: s.sentiment_score if s.mention_count >= SENTIMENT_PARAMS["min_mentions"] else 50.0,
            )
            if worst.sentiment_score < 45:
                return {"stock_key": worst.stock_key, "score": worst.sentiment_score, "mentions": worst.mention_count}
        return None

    # ---- Persistence ----

    def _save_cache(self):
        try:
            data = {
                "sentiments": {k: v.to_dict() for k, v in self._sentiments.items()},
                "trending": self._trending,
                "last_update": self._last_update,
                "active_sources": self._active_sources,
                "total_mentions_24h": self._total_mentions_24h,
            }
            with open(SENTIMENT_CACHE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sentiment cache: {e}")

    def _load_cache(self):
        try:
            with open(SENTIMENT_CACHE_FILE, "r") as f:
                data = json.load(f)
            # Restore sentiments
            for k, v in data.get("sentiments", {}).items():
                self._sentiments[k] = StockSentiment(**v)
            self._trending = data.get("trending", [])
            self._last_update = data.get("last_update", 0.0)
            self._active_sources = data.get("active_sources", 0)
            self._total_mentions_24h = data.get("total_mentions_24h", 0)
            logger.info(f"Loaded sentiment cache: {len(self._sentiments)} stocks")
        except FileNotFoundError:
            logger.info("No sentiment cache found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load sentiment cache: {e}")


# ============================================================
# UTILITY
# ============================================================

def _llm_label_to_raw(label: str, confidence: float) -> float:
    """Convert LLM label + confidence to raw sentiment [-1, +1]."""
    if label == "POSITIVE":
        return confidence * 0.8   # max +0.8
    elif label == "NEGATIVE":
        return -confidence * 0.8  # max -0.8
    else:  # NOISE
        return 0.0
