"""
Web intelligence service: fetches live news via Serper API and newsapi.ai,
then scrapes full article bodies with BeautifulSoup for richer persona context.
"""
import time
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from urllib.parse import urlparse
from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('phoring.web_intelligence')

FINANCIAL_SOURCES = [
    "site:economictimes.indiatimes.com",
    "site:livemint.com",
    "site:moneycontrol.com",
    "site:business-standard.com",
    "site:reuters.com",
    "site:ndtvprofit.com",
]
GLOBAL_SOURCES = [
    "site:reuters.com",
    "site:bloomberg.com",
    "site:ft.com",
    "site:bbc.com",
    "site:theguardian.com",
]
# Social media sources — track real posts from public platforms
SOCIAL_MEDIA_SOURCES = [
    "site:reddit.com",           # Reddit discussions & posts
    "site:twitter.com",          # Twitter/X public tweets
    "site:x.com",                # Twitter/X (new domain)
    "site:facebook.com",         # Facebook public posts (via search engines)
    "site:instagram.com",        # Instagram public posts (limited, depends on indexing)
    "site:linkedin.com",         # LinkedIn articles & posts
    "site:tiktok.com",           # TikTok video descriptions
]

FINANCIAL_ENTITY_TYPES = {
    "company", "stock", "fund", "bank", "exchange",
    "sector", "index", "commodity", "currency", "investor",
}
DOMAIN_SELECTORS = {
    "economictimes.indiatimes.com": ["div.artText", "div.article_full_section"],
    "livemint.com": ["div.mainArea", "div.contentSec"],
    "moneycontrol.com": ["div.article_wrap", "div#article-main"],
    "business-standard.com": ["div.storycards", "span.p-content"],
    "reuters.com": ["article", "div[class*='article-body']"],
    "ndtvprofit.com": ["div.sp-cn", "article"],
    "bloomberg.com": ["div[class*='body-content']", "article"],
    "ft.com": ["div.article__content-body"],
    "bbc.com": ["article"],
    "theguardian.com": ["div.article-body-commercial-selector"],
    # Social media domain selectors
    "reddit.com": ["div[class*='post-container']", "div[data-test-id='post']", "p"],
    "twitter.com": ["article", "div[role='article']", "span.twitter-text"],
    "x.com": ["article", "div[role='article']", "span"],
    "facebook.com": ["div[data-testid='post']", "div[role='article']"],
    "instagram.com": ["article", "div[role='presentation']"],
    "linkedin.com": ["div.share-update-container", "article"],
    "tiktok.com": ["div.video-desc", "h1"],
}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class NewsScraperService:
    SERPER_URL = "https://google.serper.dev/news"
    SERPER_SEARCH_URL = "https://google.serper.dev/search"
    NEWS_API_URL = "https://eventregistry.org/api/v1/article/getArticles"

    def __init__(self):
        self.api_key = Config.SERPER_API_KEY
        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.warning("SERPER_API_KEY not configured — web intelligence disabled")
        else:
            logger.info("NewsScraperService initialized with SERPER_API_KEY")

    # ---- Search query construction ------------------------------------------------

    @staticmethod
    def _extract_key_phrases(text: str, max_phrases: int = 6) -> List[str]:
        """Extract the most search-relevant noun phrases and named entities from text.

        Uses simple heuristics (capitalised runs, quoted phrases, domain keywords)
        rather than NLP libraries so we stay dependency-light.
        """
        import re as _re

        phrases: List[str] = []

        # 1. Quoted phrases — the user explicitly marked these as important
        for m in _re.finditer(r'"([^"]{3,60})"', text):
            phrases.append(m.group(1).strip())

        # 2. Capitalised multi-word runs (likely proper nouns / entities)
        for m in _re.finditer(r'(?:[A-Z][a-z]+(?:\s+(?:of|the|and|for|in|on)\s+)?){2,5}[A-Z][a-z]+', text):
            candidate = m.group(0).strip()
            if len(candidate) > 5:
                phrases.append(candidate)

        # 3. Words with special financial/policy significance
        domain_markers = [
            "tariff", "sanction", "inflation", "gdp", "rate cut", "rate hike",
            "monetary policy", "fiscal", "trade", "subsidy", "regulation",
            "merger", "acquisition", "ipo", "earnings", "profit", "revenue",
            "crude oil", "commodity", "currency", "forex", "bond", "yield",
            "election", "referendum", "coup", "war", "conflict", "ceasefire",
            "semiconductor", "supply chain", "shortage", "disruption",
        ]
        text_lower = text.lower()
        for marker in domain_markers:
            if marker in text_lower:
                phrases.append(marker)

        # Deduplicate while preserving order
        seen = set()
        unique: List[str] = []
        for p in phrases:
            key = p.lower().strip()
            if key not in seen and len(key) > 2:
                seen.add(key)
                unique.append(p.strip())
        return unique[:max_phrases]

    def _build_search_query(
        self, entity_name: str, entity_type: str, context: str
    ) -> str:
        """Build a high-precision search query from the entity name and full context.

        Strategy:
        - Use the full entity_name (up to 300 chars, not 80)
        - Extract key named entities, quoted terms, and domain markers from context
        - Combine into a search-engine-ready query ≤ 400 chars
        """
        # Start with the entity/scenario name — keep much more than 80 chars
        base = entity_name[:300].strip()

        if not context:
            return base

        key_phrases = self._extract_key_phrases(context)
        if not key_phrases:
            # Fallback: first 25 words from context (better than old 12)
            fallback_keywords = " ".join(context.split()[:25])
            combined = f"{base} {fallback_keywords}".strip()
            return combined[:400]

        # Combine base + extracted phrases, respecting length budget
        additions = " ".join(key_phrases)
        combined = f"{base} {additions}".strip()
        return combined[:400]

    # ---- News search APIs ---------------------------------------------------------

    def search_news(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        days_back: int = 7,
        max_results: int = 5,
    ) -> List[Dict]:
        """Call Serper news API. Returns list of {title, url, snippet, source}."""
        if not self.enabled:
            return []
        site_filter = " OR ".join(sources) if sources else ""
        full_query = f"{query} {site_filter}".strip() if site_filter else query
        # Use day-level recency for fresh results: d1=24h, d3=3days, d7=week
        if days_back <= 1:
            tbs = "qdr:d"
        elif days_back <= 7:
            tbs = f"qdr:d{days_back}"
        elif days_back <= 30:
            tbs = "qdr:m"
        else:
            months = max(1, days_back // 30)
            tbs = f"qdr:m{months}"
        payload = {"q": full_query, "num": max_results, "tbs": tbs}
        logger.info(f"Serper news search: query='{full_query[:80]}', tbs={tbs}, num={max_results}")
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        try:
            resp = requests.post(self.SERPER_URL, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            results = [
                {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": item.get("source", ""),
                }
                for item in data.get("news", [])
            ]
            logger.info(f"Serper returned {len(results)} news results for '{query[:60]}'")
            return results
        except Exception as e:
            logger.warning(f"Serper search failed for '{query[:60]}': {e}")
            return []

    def search_newsapi(self, query: str, max_results: int = 5) -> List[Dict]:
        """Fetch headlines + body text from newsapi.ai as a secondary source.

        Returns empty list on DNS/connection errors without raising so the
        primary Serper pipeline can continue uninterrupted.
        """
        api_key = Config.NEWS_API_KEY
        if not api_key:
            return []
        try:
            params = {
                "action": "getArticles",
                "keyword": query,
                "lang": "eng",
                "resultType": "articles",
                "articlesSortBy": "date",
                "articlesCount": max_results,
                "apiKey": api_key,
            }
            resp = requests.get(self.NEWS_API_URL, params=params, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            articles = data.get("articles", {}).get("results", [])
            return [
                {
                    "title": a.get("title", ""),
                    "url": a.get("url", ""),
                    # newsapi.ai provides full body — use it directly, no scraping needed
                    "snippet": (a.get("body", "") or a.get("summary", ""))[:1000],
                    "source": a.get("source", {}).get("title", ""),
                }
                for a in articles
                if a.get("title") and "[Removed]" not in a.get("title", "")
            ]
        except requests.exceptions.ConnectionError as e:
            logger.info(f"newsapi.ai unreachable (DNS/network): {e}")
            return []
        except Exception as e:
            logger.warning(f"newsapi.ai search failed for '{query}': {e}")
            return []

    # Maximum characters scraped per individual article body.
    # Matches the marketing claim: "up to 4,000 characters of real-world context per entity".
    ARTICLE_BODY_LIMIT = 4000

    def scrape_article(self, url: str) -> str:
        """
        Scrape article body from a URL using domain-specific CSS selectors
        with a generic <p> fallback. Returns at most ARTICLE_BODY_LIMIT characters.
        """
        domain = urlparse(url).netloc.replace("www.", "")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for selector in DOMAIN_SELECTORS.get(domain, []):
                elements = soup.select(selector)
                if elements:
                    text = " ".join(
                        el.get_text(separator=" ", strip=True) for el in elements
                    )
                    if len(text) > 200:
                        return text[:self.ARTICLE_BODY_LIMIT]
            container = soup.find("article") or soup.find("main") or soup.find("body")
            if container:
                paragraphs = container.find_all("p")
                text = " ".join(
                    p.get_text(strip=True)
                    for p in paragraphs
                    if len(p.get_text(strip=True)) > 50
                )
                return text[:self.ARTICLE_BODY_LIMIT] if text else ""
        except Exception as e:
            logger.debug(f"Failed to scrape {url}: {e}")
        return ""

    def gather_for_entity(
        self,
        entity_name: str,
        entity_type: str,
        max_articles: int = 3,
        context: str = "",
    ) -> Dict:
        """
        Full pipeline: Serper (news + social) → scrape → merge newsapi.ai → combine.
        Returns {'articles': [...], 'combined_text': str, 'social_media_posts': [...]}.

        Args:
            context: Optional scenario/requirement text to refine the search query.
        """
        if not self.enabled:
            return {"articles": [], "combined_text": "", "social_media_posts": []}

        is_financial = entity_type.lower() in FINANCIAL_ENTITY_TYPES
        sources = FINANCIAL_SOURCES if is_financial else GLOBAL_SOURCES

        # Build a contextualised search query from the full scenario context
        search_query = self._build_search_query(entity_name, entity_type, context)

        # Primary: Serper (targeted trusted sources, full scraping)
        results = self.search_news(
            query=search_query,
            sources=sources,
            days_back=7,
            max_results=max_articles + 2,
        )

        # NEW: Social media sources — fetch real posts from Reddit, Twitter/X, Facebook, Instagram
        social_posts = self.search_social_media(
            query=search_query,
            max_results=max_articles,
        )

        # Secondary: newsapi.ai fills gaps when Serper returns too few results
        if len(results) < max_articles:
            newsapi_results = self.search_newsapi(
                query=search_query, max_results=max_articles
            )
            existing_urls = {r["url"] for r in results}
            for r in newsapi_results:
                if r["url"] not in existing_urls:
                    results.append(r)
                    existing_urls.add(r["url"])

            # Tertiary fallback: if still short (e.g. newsapi.ai DNS fails), run an
            # unrestricted Serper /news query without site: filters to supplement
            if len(results) < max_articles and self.api_key:
                try:
                    headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
                    payload = {"q": search_query, "num": max_articles - len(results) + 2}
                    resp = requests.post(self.SERPER_URL, json=payload, headers=headers, timeout=10)
                    resp.raise_for_status()
                    data = resp.json()
                    existing_urls = {r["url"] for r in results}
                    pre_count = len(results)
                    for item in data.get("news", data.get("organic", [])):
                        url = item.get("link", item.get("url", ""))
                        if url and url not in existing_urls:
                            results.append({
                                "title": item.get("title", ""),
                                "url": url,
                                "snippet": item.get("snippet", ""),
                                "source": item.get("source", urlparse(url).netloc),
                            })
                            existing_urls.add(url)
                    added = len(results) - pre_count
                    if added > 0:
                        logger.info(f"Serper fallback: added {added} extra results for '{search_query[:60]}'")
                except Exception as e:
                    logger.debug(f"Serper tertiary fallback failed: {e}")

        articles = []
        for item in results:
            if len(articles) >= max_articles:
                break
            url = item.get("url", "")
            if not url:
                continue
            # If snippet is already rich (newsapi.ai body), skip scraping
            snippet = item.get("snippet", "")
            body = snippet if len(snippet) > 200 else self.scrape_article(url)
            text = body if body else snippet
            if text:
                articles.append({
                    "title": item["title"],
                    "source": item["source"],
                    "url": url,
                    "text": text[:self.ARTICLE_BODY_LIMIT],
                    "type": "news",
                })
            time.sleep(0.3)

        # Process social media posts
        for post in social_posts:
            articles.append({
                "title": post.get("title", post.get("snippet", "")[:80]),
                "source": post["source"],
                "url": post.get("url", ""),
                "text": post.get("snippet", "")[:1000],
                "type": "social_media",
            })

        if not articles:
            return {"articles": [], "combined_text": "", "social_media_posts": social_posts}

        parts = [f"[{a['source']}] {a['title']}\n{a['text']}" for a in articles]
        # Combined budget: 3 articles × 4,000 chars each + separators ≈ 12,500 chars
        return {
            "articles": articles,
            "combined_text": "\n\n---\n\n".join(parts)[:12000],
            "social_media_posts": social_posts,
        }

    def search_geopolitical_news(
        self,
        simulation_requirement: str,
        entities: Optional[List] = None,
        max_articles: int = 5,
    ) -> Dict:
        """Dedicated geopolitical news fetcher with focused, short queries.

        Instead of dumping the full simulation requirement as a search query,
        this builds 2-3 targeted searches:
        1. Sector/topic + "latest news today"
        2. Top entity names + "news"
        3. Event Registry as a secondary source

        Returns same structure as gather_for_entity().
        """
        if not self.enabled:
            logger.warning("Geopolitical news search skipped — SERPER_API_KEY not set")
            return {"articles": [], "combined_text": "", "headlines": []}

        logger.info("Starting geopolitical news search for simulation grounding")

        # Build focused queries from the requirement text
        key_phrases = self._extract_key_phrases(simulation_requirement, max_phrases=4)
        entity_names = []
        if entities:
            entity_names = [
                getattr(e, 'name', str(e))[:50]
                for e in entities[:6]
                if hasattr(e, 'name')
            ]

        queries = []
        # Query 1: Key topic phrases + "latest news"
        if key_phrases:
            topic_query = " ".join(key_phrases[:3]) + " latest news today"
            queries.append(topic_query)
        else:
            # Fallback: first 8 meaningful words from requirement
            words = [w for w in simulation_requirement.split() if len(w) > 3][:8]
            queries.append(" ".join(words) + " news today")

        # Query 2: Top entity names + breaking news
        if entity_names:
            entity_query = " ".join(entity_names[:3]) + " breaking news"
            queries.append(entity_query)

        # Query 3: Sector-specific search if financial entities detected
        sector_words = [
            p for p in key_phrases
            if any(kw in p.lower() for kw in [
                "stock", "market", "bank", "trade", "tariff", "economy",
                "oil", "crypto", "currency", "commodity", "inflation",
                "interest rate", "monetary", "fiscal", "regulation",
            ])
        ]
        if sector_words:
            queries.append(f"{' '.join(sector_words[:2])} policy regulation news this week")

        all_results = []
        seen_urls = set()
        for q in queries[:3]:
            # Use GLOBAL_SOURCES for geopolitical news (Reuters, BBC, Bloomberg, etc.)
            results = self.search_news(
                query=q,
                sources=GLOBAL_SOURCES,
                days_back=7,
                max_results=max_articles,
            )
            for r in results:
                if r["url"] not in seen_urls:
                    all_results.append(r)
                    seen_urls.add(r["url"])

            # Also run unrestricted search to catch non-mainstream sources
            unrestricted = self.search_news(
                query=q,
                sources=None,
                days_back=7,
                max_results=3,
            )
            for r in unrestricted:
                if r["url"] not in seen_urls:
                    all_results.append(r)
                    seen_urls.add(r["url"])

        # Secondary: Event Registry fills gaps
        if len(all_results) < max_articles:
            er_query = " ".join(key_phrases[:3]) if key_phrases else simulation_requirement[:100]
            newsapi_results = self.search_newsapi(query=er_query, max_results=max_articles)
            for r in newsapi_results:
                if r["url"] not in seen_urls:
                    all_results.append(r)
                    seen_urls.add(r["url"])

        # Scrape article bodies and build output
        articles = []
        headlines = []
        for item in all_results:
            if len(articles) >= max_articles:
                break
            url = item.get("url", "")
            if not url:
                continue
            title = item.get("title", "")
            source = item.get("source", "")
            headlines.append(f"[{source}] {title}")
            snippet = item.get("snippet", "")
            body = snippet if len(snippet) > 200 else self.scrape_article(url)
            text = body if body else snippet
            if text:
                articles.append({
                    "title": title,
                    "source": source,
                    "url": url,
                    "text": text[:self.ARTICLE_BODY_LIMIT],
                    "type": "news",
                })
            time.sleep(0.3)

        logger.info(
            f"Geopolitical news search complete: {len(articles)} articles, "
            f"{len(headlines)} headlines from {len(queries)} queries"
        )

        if not articles:
            return {"articles": [], "combined_text": "", "headlines": headlines}

        parts = [f"[{a['source']}] {a['title']}\n{a['text']}" for a in articles]
        return {
            "articles": articles,
            "combined_text": "\n\n---\n\n".join(parts)[:12000],
            "headlines": headlines,
        }

    def search_social_media(
        self,
        query: str,
        max_results: int = 3,
    ) -> List[Dict]:
        """
        Search social media platforms (Reddit, Twitter/X, Facebook, Instagram, LinkedIn, TikTok)
        via Serper regular search (not news). Returns posts from public discussions.
        
        Returns list of {title, url, snippet, source}.
        """
        if not self.enabled:
            return []
        
        social_results = []
        
        # Batch social platforms into fewer queries for efficiency
        # Group 1: Discussion platforms (Reddit + LinkedIn)
        # Group 2: Micro-blogging (Twitter/X)
        # Group 3: Visual/other (Facebook + Instagram + TikTok)
        platform_groups = [
            ["site:reddit.com", "site:linkedin.com"],
            ["site:twitter.com", "site:x.com"],
            ["site:facebook.com", "site:instagram.com", "site:tiktok.com"],
        ]
        
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        
        for group in platform_groups:
            try:
                site_filter = " OR ".join(group)
                full_query = f"{query} ({site_filter})"
                payload = {"q": full_query, "num": max_results}
                resp = requests.post(
                    self.SERPER_SEARCH_URL,
                    json=payload,
                    headers=headers,
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("organic", []):
                    social_results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "source": item.get("source", urlparse(item.get("link", "")).netloc),
                    })
                time.sleep(0.3)
            except Exception as e:
                logger.debug(f"Social media search failed for {group}: {e}")
        
        # Deduplicate & limit to max_results
        seen_urls = set()
        deduped = []
        for post in social_results:
            url = post.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduped.append(post)
                if len(deduped) >= max_results:
                    break
        
        # Tag posts by platform for better context
        for post in deduped:
            url = post.get("url", "")
            if "reddit.com" in url:
                post["platform"] = "Reddit"
            elif "twitter.com" in url or "x.com" in url:
                post["platform"] = "Twitter/X"
            elif "facebook.com" in url:
                post["platform"] = "Facebook"
            elif "instagram.com" in url:
                post["platform"] = "Instagram"
            elif "linkedin.com" in url:
                post["platform"] = "LinkedIn"
            elif "tiktok.com" in url:
                post["platform"] = "TikTok"
            else:
                post["platform"] = "Social Media"
        
        logger.info(f"Social media search for '{query}' returned {len(deduped)} posts from {len(platform_groups)} platform groups")
        return deduped
