import asyncio
import httpx
import json
import os
import re
from datetime import datetime, timezone
from typing import Optional
from openai import OpenAI

from agent_template import BaseAgent
from models import AgentReport, AgentStatus, Finding
from logger import logger


SSL_VERIFY: bool = False

SCRAPE_TIMEOUT = 15
ANALYSIS_TIMEOUT = 10

EXPECTED_PAGES = ["homepage", "about", "pricing", "features"]

URL_PATHS = {
    "homepage": "",
    "about": "about",
    "pricing": "pricing",
    "features": "features",
}


def _normalize_url(base: str, path: str) -> str:
    base = base.rstrip("/")
    return f"{base}/{path}" if path else base


class ProductAnalyzer(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="product_analyzer",
            agent_name="Product Analyzer",
        )

    async def run(
        self, url: str, on_finding: callable
    ) -> AgentReport:
        try:
            await on_finding(
                Finding(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    description=f"Starting analysis of {url}",
                )
            )

            scraped = await self._scrape_pages(url, on_finding)

            if not scraped:
                return AgentReport(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    status=AgentStatus.ERROR,
                    error="Could not scrape any pages from this URL.",
                    pages_found=[],
                    pages_missing=EXPECTED_PAGES,
                )

            pages_found = list(scraped.keys())
            pages_missing = [p for p in EXPECTED_PAGES if p not in scraped]

            await on_finding(
                Finding(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    description=f"Scraped {len(pages_found)}/{len(EXPECTED_PAGES)} pages",
                )
            )

            analysis = await self._analyze(url, scraped, on_finding)

            return AgentReport(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.DONE,
                data=analysis,
                pages_found=pages_found,
                pages_missing=pages_missing,
            )

        except asyncio.TimeoutError:
            return AgentReport(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.ERROR,
                error="Investigation timed out.",
            )
        except Exception as exc:
            return AgentReport(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.ERROR,
                error=str(exc),
            )

    async def _scrape_pages(
        self, url: str, on_finding: callable
    ) -> dict[str, str]:
        scraped: dict[str, str] = {}

        logger.info(f"ProductAnalyzer: scraping {url}")

        async with httpx.AsyncClient(timeout=SCRAPE_TIMEOUT, verify=SSL_VERIFY) as client:
            tasks = []
            for page_name, path in URL_PATHS.items():
                page_url = _normalize_url(url, path)
                logger.info(f"ProductAnalyzer: queueing {page_url}")
                tasks.append(self._try_scrape(client, page_name, page_url))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("ProductAnalyzer: scraping complete")

        for page_name, result in zip(EXPECTED_PAGES, results):
            if isinstance(result, Exception):
                await on_finding(
                    Finding(
                        agent_id=self.agent_id,
                        agent_name=self.agent_name,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        description=f"Could not scrape {page_name} page: {result}",
                    )
                )
            elif result:
                scraped[page_name] = result
                snippet = result[:100].replace("\n", " ")
                await on_finding(
                    Finding(
                        agent_id=self.agent_id,
                        agent_name=self.agent_name,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        description=f"Scraped {page_name} page",
                    )
                )

        return scraped

    async def _try_scrape(
        self, client: httpx.AsyncClient, page_name: str, page_url: str
    ) -> Optional[str]:
        try:
            resp = await client.get(page_url, follow_redirects=True, timeout=SCRAPE_TIMEOUT)
            logger.info(f"ProductAnalyzer: {page_url} -> {resp.status_code} ({len(resp.text)} bytes)")
            if resp.status_code == 200 and len(resp.text) > 100:
                return resp.text
            return None
        except Exception as e:
            logger.warning(f"ProductAnalyzer: {page_url} failed: {e}")
            return None

    async def _analyze(
        self,
        url: str,
        scraped_pages: dict[str, str],
        on_finding: callable,
    ) -> dict:
        await on_finding(
            Finding(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                timestamp=datetime.now(timezone.utc).isoformat(),
                description="Analyzing scraped content...",
            )
        )

        sample_pages = {}
        for page_name, html in scraped_pages.items():
            sample_pages[page_name] = self._extract_text(html)

        if os.getenv("KIMI_API_KEY"):
            return await self._analyze_with_kimi(url, sample_pages)
        else:
            return self._analyze_fallback(url, sample_pages)

    def _extract_text(self, html: str) -> str:
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:5000]

    async def _analyze_with_kimi(
        self, url: str, pages: dict[str, str]
    ) -> dict:
        prompt = self._build_prompt(url, pages)
        logger.info("ProductAnalyzer: calling Kimi API via aiand.com")

        def _call_kimi() -> dict:
            _http_client = httpx.Client(
                verify=SSL_VERIFY, timeout=httpx.Timeout(30.0)
            )
            client = OpenAI(
                base_url="https://api.aiand.com/v1",
                api_key=os.getenv("KIMI_API_KEY"),
                http_client=_http_client,
                max_retries=0,
            )
            response = client.chat.completions.create(
                model="deepseek-ai/deepseek-v4-flash",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a product analyst. Extract structured information from the provided web pages.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            content = response.choices[0].message.content
            logger.info(f"ProductAnalyzer: Kimi API responded (finish_reason={response.choices[0].finish_reason})")
            if content:
                json_match = content[content.find("{") : content.rfind("}") + 1]
                return json.loads(json_match)
            logger.warning("ProductAnalyzer: Kimi returned empty content, using fallback")
            return self._analyze_fallback(url, pages)

        try:
            return await asyncio.to_thread(_call_kimi)
        except Exception as e:
            logger.error(f"ProductAnalyzer: Kimi API error: {e}")
            return self._analyze_fallback(url, pages)

    def _build_prompt(self, url: str, pages: dict[str, str]) -> str:
        sections = []
        for page_name, text in pages.items():
            sections.append(f"--- {page_name.upper()} ---\n{text[:3000]}")

        return f"""Analyze the following web pages from {url}.

{sections}

Return a JSON object with these keys:
- company_name (string)
- description (string)
- target_market (string)
- key_features (array of strings)
- pricing (object with "model" string and optional "tiers" array)
- value_proposition (string)
- differentiators (array of strings)
- pages_analyzed (array of strings)
- pages_missing (array of strings)"""

    def _analyze_fallback(self, url: str, pages: dict[str, str]) -> dict:
        combined = " ".join(pages.values())

        company_match = re.search(r"(?:about|company|brand)\s*[-–:]\s*([^.]*\.)", combined, re.IGNORECASE)
        description_match = re.search(r"(?:we\s+are|our\s+mission|our\s+platform)\s+([^.]*\.)", combined, re.IGNORECASE)
        price_match = re.search(r"(?:\$[\d,]+\.?\d*|starting\s+at|plans?\s+(?:start|begin))", combined, re.IGNORECASE)

        return {
            "company_name": company_match.group(1).strip() if company_match else None,
            "description": description_match.group(1).strip() if description_match else None,
            "target_market": None,
            "key_features": [],
            "pricing": {"model": "pricing mentioned" if price_match else None, "tiers": None},
            "value_proposition": None,
            "differentiators": [],
            "pages_analyzed": list(pages.keys()),
            "pages_missing": [p for p in EXPECTED_PAGES if p not in pages],
        }

