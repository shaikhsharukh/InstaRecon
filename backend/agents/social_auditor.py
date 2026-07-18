import asyncio
import re
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from agent_template import BaseAgent
from models import AgentReport, AgentStatus, Finding
from logger import logger


SSL_VERIFY: bool = False
SCRAPE_TIMEOUT = 15


SOCIAL_DOMAINS = {
    "twitter.com": "Twitter/X",
    "x.com": "Twitter/X",
    "linkedin.com": "LinkedIn",
    "facebook.com": "Facebook",
    "instagram.com": "Instagram",
    "youtube.com": "YouTube",
    "github.com": "GitHub",
    "tiktok.com": "TikTok",
    "medium.com": "Medium",
    "crunchbase.com": "Crunchbase",
    "angel.co": "AngelList",
    "wellfound.com": "AngelList",
}


class SocialAuditor(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="social_auditor",
            agent_name="Social Auditor",
        )
        self.icon = "📱"
        self.color = "#10B981"
        self.description = "Discovers social media profiles and assesses presence"

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
                    description="Scanning for social media profiles",
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

            social_links = await self._find_social_links(url, on_finding)
            if social_links is None:
                social_links = []

            await on_finding(
                Finding(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    description=f"Found {len(social_links)} social profile links",
                )
            )
            finding_count += 1

            platforms = []
            for link in social_links:
                platform_data = await self._scrape_profile(link, on_finding)
                if platform_data:
                    platforms.append(platform_data)
                    finding_count += 1

            assessment = await self._assess_presence(platforms, on_finding)
            if assessment:
                finding_count += 1

            return AgentReport(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.DONE,
                data={
                    "platforms": platforms,
                    "assessment": assessment or {
                        "activity_level": "unknown",
                        "engagement_quality": "unknown",
                        "growth_trend": "unknown",
                        "overall_score": 0,
                    },
                },
                duration=time.monotonic() - start_time,
                findings_count=finding_count,
            )

        except asyncio.TimeoutError:
            return AgentReport(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.ERROR,
                error="Social audit timed out",
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

    async def _find_social_links(self, url: str, on_finding: callable) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=SCRAPE_TIMEOUT, verify=SSL_VERIFY) as client:
                resp = await client.get(url, follow_redirects=True)
                html = resp.text
        except Exception as e:
            await on_finding(
                Finding(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    description=f"Failed to fetch homepage for social scan: {e}",
                )
            )
            return []

        links = re.findall(r'href="(https?://[^"]*)"', html, re.IGNORECASE)
        social_links = []
        for link in links:
            for domain in SOCIAL_DOMAINS:
                if domain in link.lower():
                    social_links.append(link)
                    break
        return list(set(social_links))

    async def _scrape_profile(self, profile_url: str, on_finding: callable) -> Optional[dict]:
        domain = self._extract_domain(profile_url)
        platform = SOCIAL_DOMAINS.get(domain, domain)

        await on_finding(
            Finding(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                timestamp=datetime.now(timezone.utc).isoformat(),
                description=f"Scraping {platform} profile: {profile_url[:60]}",
            )
        )

        for attempt in range(3):
            try:
                result = await self.oxylabs_scrape(profile_url, source_type="universal")
                if result:
                    return {
                        "platform": platform,
                        "profile_url": profile_url,
                        "metrics": {"followers": None, "posts": None},
                        "status": "scraped",
                    }
            except Exception:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)

        return {
            "platform": platform,
            "profile_url": profile_url,
            "metrics": None,
            "status": "unavailable",
        }

    def _extract_domain(self, url: str) -> str:
        match = re.search(r"https?://(?:www\.)?([^/]+)", url)
        return match.group(1) if match else ""

    async def _assess_presence(self, platforms: list, on_finding: callable) -> Optional[dict]:
        if not platforms:
            return None

        await on_finding(
            Finding(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                timestamp=datetime.now(timezone.utc).isoformat(),
                description="Analyzing social media presence",
            )
        )

        platforms_summary = "\n".join(
            f"- {p['platform']}: {p['status']}" for p in platforms
        )

        prompt = f"""Assess the social media presence based on these discovered platforms:

{platforms_summary}

Return a JSON object with:
- activity_level: "daily" | "weekly" | "sporadic" | "dormant" | "unknown"
- engagement_quality: "high" | "medium" | "low" | "unknown"
- growth_trend: "growing" | "stable" | "declining" | "unknown"
- overall_score: integer 0-100
- recommendation: string — brief advice for improving social presence"""

        return await self.kimi_analyze(
            prompt,
            system_prompt="You are a social media analyst. Assess brand presence objectively.",
        )
