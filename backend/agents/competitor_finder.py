import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Optional

from agent_template import BaseAgent
from models import AgentReport, AgentStatus, Finding
from logger import logger


SSL_VERIFY: bool = False


class CompetitorFinder(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="competitor_finder",
            agent_name="Competitor Finder",
        )
        self.icon = "🏆"
        self.color = "#EF4444"
        self.description = "Discovers top competitors and builds comparison matrix"
        self._product_category: Optional[str] = None
        self._company_name: Optional[str] = None

    async def run(self, url: str, on_finding: callable) -> AgentReport:
        start_time = time.monotonic()
        finding_count = 0
        sandbox = None
        sandbox_start = time.monotonic()

        try:
            await on_finding(
                Finding(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    description="Starting competitor research for " + url,
                )
            )
            finding_count += 1

            # Daytona sandbox setup
            sandbox = await self.create_daytona_sandbox()
            if sandbox:
                await on_finding(
                    Finding(
                        agent_id=self.agent_id,
                        agent_name=self.agent_name,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        description=f"Spun up Daytona sandbox (ID: {sandbox.id})",
                    )
                )
                res = await asyncio.to_thread(sandbox.process.exec, "uname -a")
                await on_finding(
                    Finding(
                        agent_id=self.agent_id,
                        agent_name=self.agent_name,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        description=f"Daytona sandbox verified: {res.result.strip()}",
                    )
                )

            if not self._company_name:
                await on_finding(
                    Finding(
                        agent_id=self.agent_id,
                        agent_name=self.agent_name,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        description="Waiting for Product Analyzer to determine company name",
                    )
                )
                finding_count += 1
                return AgentReport(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    status=AgentStatus.ERROR,
                    error="Company name not provided by Product Analyzer",
                    duration=time.monotonic() - start_time,
                )

            category_part = f" {self._product_category}" if self._product_category else ""
            query = f"{self._company_name}{category_part} competitors alternative"
            serp_results = await self._search_competitors(query, on_finding)
            if serp_results is None:
                serp_results = []
            finding_count += len(serp_results)

            if not serp_results:
                await on_finding(
                    Finding(
                        agent_id=self.agent_id,
                        agent_name=self.agent_name,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        description="No competitors found via search",
                    )
                )
                finding_count += 1
                return self.create_report(data={})

            competitors = serp_results[:10]
            comparison = await self._build_comparison(url, competitors, on_finding)
            if comparison:
                finding_count += 1

            return AgentReport(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.DONE,
                data={
                    "competitors": competitors,
                    "comparison_matrix": (comparison or {}).get("comparison_matrix", []),
                    "pricing_comparison": (comparison or {}).get("pricing_comparison", ""),
                    "market_positioning": (comparison or {}).get("market_positioning", ""),
                    "advantage": (comparison or {}).get("advantage", ""),
                },
                duration=time.monotonic() - start_time,
                findings_count=finding_count,
            )

        except asyncio.TimeoutError:
            return AgentReport(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.ERROR,
                error="Competitor finding timed out",
                duration=time.monotonic() - start_time,
            )
        except Exception as exc:
            return AgentReport(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.ERROR,
                error=str(exc),
                duration=time.monotonic() - start_time,
            )
        finally:
            if sandbox:
                await self.destroy_daytona_sandbox(sandbox, sandbox_start)

    async def _search_competitors(self, query: str, on_finding: callable):
        result = await self.oxylabs_scrape(
            f"https://www.google.com/search?q={query.replace(' ', '+')}",
            source_type="google_search",
        )
        if result and "content" in result:
            await on_finding(
                Finding(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    description=f"SERP search returned results for '{query}'",
                )
            )
            return self._parse_serp(result.get("content", ""))
        return []

    def _parse_serp(self, html: str) -> list[dict]:
        import re
        competitors = []
        links = re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*>([^<]+)</a>', html)
        seen = set()
        for url, text in links:
            domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
            if domain and domain not in seen and text.strip():
                seen.add(domain)
                competitors.append({
                    "name": text.strip(),
                    "url": url,
                    "snippet": "",
                })
        return competitors

    async def _build_comparison(self, target_url: str, competitors: list, on_finding: callable):
        await on_finding(
            Finding(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                timestamp=datetime.now(timezone.utc).isoformat(),
                description="Building competitive comparison matrix",
            )
        )

        comp_list = "\n".join(
            f"- {c['name']} ({c['url']})" for c in competitors[:5]
        )

        space = f' in the "{self._product_category}" space' if self._product_category else ""
        prompt = f"""Compare the target company ({self._company_name}, {target_url}){space} with these potential competitors:

{comp_list}

Return a JSON object with:
- comparison_matrix: array of {{"feature": string, "target": string|bool, "competitor_N": string|bool}} — compare key features
- pricing_comparison: string — how target pricing compares to competitors
- market_positioning: string — where the target sits in the market
- advantage: string — the target's key competitive advantage"""

        return await self.kimi_analyze(
            prompt,
            system_prompt="You are a competitive intelligence analyst. Compare companies objectively.",
        )
