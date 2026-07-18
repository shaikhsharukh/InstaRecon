import re
import asyncio
from typing import Optional
import httpx
from bs4 import BeautifulSoup

from agent_template import BaseAgent
from models import AgentReport, AgentStatus, Review, SentimentReport
from logger import logger


SSL_VERIFY = False


class SentimentAnalyzer(BaseAgent):
    agent_id = "sentiment_analyzer"
    agent_name = "Sentiment Analyzer"
    icon = "💬"
    color = "#f59e0b"
    description = "Collects reviews from Trustpilot, Google, Reddit and analyzes sentiment"

    def __init__(self):
        super().__init__(self.agent_id, self.agent_name)

    async def run(self, url: str, on_finding: callable) -> AgentReport:
        domain = self._extract_domain(url)
        if not domain:
            return self.on_error("Could not extract domain from URL")

        trustpilot_task = self._scrape_trustpilot(domain)
        google_task = self._scrape_google(domain)
        reddit_task = self._scrape_reddit(domain)

        trustpilot_reviews, google_reviews, reddit_reviews = await asyncio.gather(
            trustpilot_task, google_task, reddit_task, return_exceptions=True
        )

        if isinstance(trustpilot_reviews, Exception):
            trustpilot_reviews = []
        if isinstance(google_reviews, Exception):
            google_reviews = []
        if isinstance(reddit_reviews, Exception):
            reddit_reviews = []

        all_reviews = trustpilot_reviews + google_reviews + reddit_reviews
        if not all_reviews:
            report = self.create_report(
                data={
                    "overall_score": None,
                    "distribution": {},
                    "praise_themes": [],
                    "complaint_themes": [],
                    "trend": "insufficient_data",
                    "sources_used": [],
                    "review_count": 0,
                    "message": "No reviews found for this company",
                }
            )
            return report

        report_data = self._build_sentiment_report(all_reviews)
        return self.create_report(data=report_data.model_dump())

    def _extract_domain(self, url: str) -> Optional[str]:
        url = url.strip().lower()
        url = re.sub(r"^https?://", "", url)
        url = re.sub(r"^www\.", "", url)
        url = url.split("/")[0]
        return url if "." in url else None

    async def _scrape_trustpilot(self, domain: str) -> list[Review]:
        url = f"https://www.trustpilot.com/review/{domain}"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(15.0), verify=SSL_VERIFY) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    logger.info(f"Trustpilot returned {resp.status_code} for {domain}")
                    return []
                soup = BeautifulSoup(resp.text, "html.parser")
                reviews = []
                for card in soup.select('[data-service-review-card]'):
                    try:
                        rating_el = card.select_one('[data-rating]')
                        rating = float(rating_el["data-rating"]) if rating_el else None
                        text_el = card.select_one('[data-service-review-text]')
                        text = text_el.text.strip() if text_el else ""
                        author_el = card.select_one('[data-consumer-name]')
                        author = author_el.text.strip() if author_el else None
                        reviews.append(Review(
                            source="trustpilot",
                            rating=rating,
                            text=text,
                            author=author,
                        ))
                    except Exception:
                        continue
                return reviews
        except Exception as e:
            logger.info(f"Trustpilot scrape failed for {domain}: {e}")
            return []

    async def _scrape_google(self, domain: str) -> list[Review]:
        try:
            result = await self.oxylabs_scrape(
                f"https://www.google.com/search?q={domain}+reviews",
                source_type="google_search",
            )
            if not result or "content" not in result:
                return []
            soup = BeautifulSoup(str(result.get("content", "")), "html.parser")
            reviews = []
            for item in soup.select('[data-attrid="review"]') or soup.select('.review'):
                text = item.text.strip()
                if text:
                    reviews.append(Review(source="google", rating=None, text=text))
            return reviews
        except Exception as e:
            logger.info(f"Google reviews scrape failed for {domain}: {e}")
            return []

    async def _scrape_reddit(self, domain: str) -> list[Review]:
        company_name = domain.split(".")[0]
        url = f"https://old.reddit.com/r/all/search?q={company_name}&restrict_sr=on&sort=relevance&t=year"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(15.0), verify=SSL_VERIFY) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    return []
                soup = BeautifulSoup(resp.text, "html.parser")
                reviews = []
                for link in soup.select("a.search-title") or soup.select("a.may-blank"):
                    title = link.text.strip()
                    if title and len(title) > 10:
                        reviews.append(Review(source="reddit", rating=None, text=title))
                        if len(reviews) >= 10:
                            break
                return reviews
        except Exception as e:
            logger.info(f"Reddit scrape failed for {domain}: {e}")
            return []

    def _classify_sentiment(self, text: str) -> str:
        positive_words = ["great", "excellent", "amazing", "love", "best", "awesome", "fantastic", "good", "happy", "recommend"]
        negative_words = ["terrible", "awful", "worst", "bad", "hate", "poor", "horrible", "disappointed", "scam", "avoid"]
        text_lower = text.lower()
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"

    def _extract_themes(self, reviews: list[Review]) -> tuple[list[str], list[str]]:
        praise_themes = set()
        complaint_themes = set()
        praise_keywords = ["easy", "fast", "reliable", "support", "quality", "price", "intuitive", "responsive"]
        complaint_keywords = ["slow", "broken", "crash", "bug", "expensive", "support", "confusing", "buggy"]
        for review in reviews:
            text_lower = review.text.lower()
            for kw in praise_keywords:
                if kw in text_lower:
                    praise_themes.add(kw.capitalize())
            for kw in complaint_keywords:
                if kw in text_lower:
                    complaint_themes.add(kw.capitalize())
        return list(praise_themes), list(complaint_themes)

    def _build_sentiment_report(self, reviews: list[Review]) -> SentimentReport:
        classifications = [self._classify_sentiment(r.text) for r in reviews]
        pos = classifications.count("positive")
        neg = classifications.count("negative")
        neu = classifications.count("neutral")
        total = len(classifications)
        overall = round((pos / total) * 100) if total > 0 else 0
        praise_themes, complaint_themes = self._extract_themes(reviews)
        sources = list(set(r.source for r in reviews))

        if pos > neg * 1.5:
            trend = "improving"
        elif neg > pos * 1.5:
            trend = "declining"
        else:
            trend = "stable"

        return SentimentReport(
            overall_score=overall,
            distribution={"positive": round(pos / total * 100, 1), "negative": round(neg / total * 100, 1), "neutral": round(neu / total * 100, 1)},
            praise_themes=praise_themes,
            complaint_themes=complaint_themes,
            trend=trend,
            sources_used=sources,
            review_count=total,
        )
