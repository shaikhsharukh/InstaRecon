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


class SEOScanner(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="seo_scanner",
            agent_name="SEO Scanner",
        )
        self.icon = "🔍"
        self.color = "#F97316"
        self.description = "Audits SEO health including meta tags, structure, and performance"

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
                    description="Starting SEO audit for " + url,
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

            html, headers = await self._fetch_page(url, on_finding)
            if html is None:
                return AgentReport(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    status=AgentStatus.ERROR,
                    error="Could not fetch page for SEO scan",
                    duration=time.monotonic() - start_time,
                )

            await on_finding(
                Finding(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    description=f"Fetched {len(html)} bytes for SEO analysis",
                )
            )
            finding_count += 1

            details = self._analyze_seo(html, headers, url)

            await on_finding(
                Finding(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    description=f"Basic SEO check complete — score: {details.get('score', 0)}/100",
                )
            )
            finding_count += 1

            infrastructure = await self._check_infrastructure(url, on_finding)
            if infrastructure:
                details.update(infrastructure)
                finding_count += 1

            issues = self._generate_issues(details)

            kimi_review = await self.kimi_analyze(
                self._build_prompt(url, details, issues),
                system_prompt="You are an SEO expert. Review the audit data and provide recommendations.",
            )

            if kimi_review:
                details["ai_recommendations"] = kimi_review.get("recommendations", [])
                finding_count += 1

            score = self._compute_score(details)

            return AgentReport(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.DONE,
                data={
                    "score": score,
                    "issues": issues,
                    "details": details,
                },
                duration=time.monotonic() - start_time,
                findings_count=finding_count,
            )

        except asyncio.TimeoutError:
            return AgentReport(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.ERROR,
                error="SEO scan timed out",
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

    async def _fetch_page(self, url: str, on_finding: callable):
        try:
            async with httpx.AsyncClient(timeout=SCRAPE_TIMEOUT, verify=SSL_VERIFY) as client:
                resp = await client.get(url, follow_redirects=True)
                return resp.text, dict(resp.headers)
        except Exception as e:
            await on_finding(
                Finding(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    description=f"Failed to fetch page for SEO: {e}",
                )
            )
            return None, {}

    def _analyze_seo(self, html: str, headers: dict, url: str) -> dict:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""

        meta_desc_match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
            html, re.IGNORECASE,
        )
        if not meta_desc_match:
            meta_desc_match = re.search(
                r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']',
                html, re.IGNORECASE,
            )
        meta_description = meta_desc_match.group(1).strip() if meta_desc_match else ""

        h1_tags = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)

        h2_tags = re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.IGNORECASE | re.DOTALL)
        h3_tags = re.findall(r"<h3[^>]*>(.*?)</h3>", html, re.IGNORECASE | re.DOTALL)

        og_tags = re.findall(r'<meta[^>]+property=["\'](og:[^"\']+)["\'][^>]+content=["\'](.*?)["\']', html, re.IGNORECASE)
        if not og_tags:
            og_tags = re.findall(r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\'](og:[^"\']+)["\']', html, re.IGNORECASE)
            og_tags = [(prop, content) for content, prop in og_tags]

        twitter_card = re.search(r'<meta[^>]+name=["\']twitter:card["\'][^>]+content=["\'](.*?)["\']', html, re.IGNORECASE)
        canonical = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\'](.*?)["\']', html, re.IGNORECASE)

        structured_data = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html, re.IGNORECASE | re.DOTALL,
        )
        structured_types = set()
        for sd in structured_data:
            for t in re.findall(r'"@type"\s*:\s*"([^"]+)"', sd):
                structured_types.add(t)

        viewport = re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.IGNORECASE)
        hsts = headers.get("strict-transport-security", "")

        https_valid = url.startswith("https://")

        return {
            "title": {
                "content": title,
                "length": len(title),
                "has_keywords": bool(title and len(title) > 10),
            },
            "meta_description": {
                "content": meta_description,
                "length": len(meta_description),
                "has_cta": bool(re.search(r"(sign up|get started|learn more|try|join|start)", meta_description, re.IGNORECASE)),
            },
            "h1_count": len(h1_tags),
            "h2_count": len(h2_tags),
            "h3_count": len(h3_tags),
            "heading_hierarchy_ok": len(h1_tags) >= 1 and len(h1_tags) <= 3,
            "og_tags_present": [tag[0] for tag in og_tags],
            "twitter_card_present": bool(twitter_card),
            "canonical_present": bool(canonical),
            "structured_data_types": list(structured_types),
            "https_valid": https_valid,
            "hsts_present": bool(hsts),
            "mobile_viewport_ok": bool(viewport),
        }

    async def _check_infrastructure(self, url: str, on_finding: callable) -> dict:
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        result = {}

        async with httpx.AsyncClient(timeout=SCRAPE_TIMEOUT, verify=SSL_VERIFY) as client:
            try:
                resp = await client.get(f"{base}/robots.txt", follow_redirects=True)
                result["robots_txt_exists"] = resp.status_code == 200
                result["robots_txt_content"] = resp.text[:2000] if resp.status_code == 200 else ""
            except Exception:
                result["robots_txt_exists"] = False
                result["robots_txt_content"] = ""

            try:
                resp = await client.get(f"{base}/sitemap.xml", follow_redirects=True)
                result["sitemap_exists"] = resp.status_code == 200
            except Exception:
                result["sitemap_exists"] = False

        await on_finding(
            Finding(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                timestamp=datetime.now(timezone.utc).isoformat(),
                description=f"robots.txt: {'found' if result.get('robots_txt_exists') else 'missing'} | sitemap.xml: {'found' if result.get('sitemap_exists') else 'missing'}",
            )
        )

        return result

    def _generate_issues(self, details: dict) -> list[dict]:
        issues = []

        if not details.get("title", {}).get("content"):
            issues.append({
                "severity": "critical",
                "description": "Missing page title",
                "recommendation": "Add a descriptive title tag (50-60 characters)",
            })
        elif details["title"]["length"] > 60:
            issues.append({
                "severity": "major",
                "description": f"Title too long ({details['title']['length']} chars)",
                "recommendation": "Keep title under 60 characters",
            })

        if not details.get("meta_description", {}).get("content"):
            issues.append({
                "severity": "critical",
                "description": "Missing meta description",
                "recommendation": "Add a compelling meta description (150-160 characters)",
            })
        elif details["meta_description"]["length"] > 160:
            issues.append({
                "severity": "major",
                "description": f"Meta description too long ({details['meta_description']['length']} chars)",
                "recommendation": "Keep meta description under 160 characters",
            })

        h1_count = details.get("h1_count", 0)
        if h1_count == 0:
            issues.append({
                "severity": "critical",
                "description": "No H1 heading found",
                "recommendation": "Add exactly one H1 heading per page",
            })
        elif h1_count > 1:
            issues.append({
                "severity": "major",
                "description": f"Multiple H1 headings ({h1_count})",
                "recommendation": "Use only one H1 per page",
            })

        if not details.get("og_tags_present"):
            issues.append({
                "severity": "major",
                "description": "No Open Graph tags",
                "recommendation": "Add og:title, og:description, and og:image tags",
            })

        if not details.get("https_valid"):
            issues.append({
                "severity": "critical",
                "description": "HTTPS not enabled",
                "recommendation": "Enable HTTPS with a valid SSL certificate",
            })

        if not details.get("mobile_viewport_ok"):
            issues.append({
                "severity": "major",
                "description": "No viewport meta tag",
                "recommendation": "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
            })

        if not details.get("robots_txt_exists"):
            issues.append({
                "severity": "minor",
                "description": "Missing robots.txt",
                "recommendation": "Create a robots.txt file to guide crawlers",
            })

        if not details.get("sitemap_exists"):
            issues.append({
                "severity": "minor",
                "description": "Missing sitemap.xml",
                "recommendation": "Create an XML sitemap for better indexing",
            })

        if not details.get("canonical_present"):
            issues.append({
                "severity": "minor",
                "description": "No canonical URL specified",
                "recommendation": "Add a canonical tag to prevent duplicate content issues",
            })

        return issues

    def _compute_score(self, details: dict) -> int:
        score = 100

        if not details.get("title", {}).get("content"):
            score -= 15
        elif details["title"]["length"] > 60:
            score -= 5

        if not details.get("meta_description", {}).get("content"):
            score -= 15
        elif details["meta_description"]["length"] > 160:
            score -= 5

        if details.get("h1_count", 0) == 0:
            score -= 15
        elif details.get("h1_count", 0) > 1:
            score -= 5

        if not details.get("og_tags_present"):
            score -= 10

        if not details.get("https_valid"):
            score -= 20

        if not details.get("mobile_viewport_ok"):
            score -= 10

        if not details.get("robots_txt_exists"):
            score -= 5

        if not details.get("sitemap_exists"):
            score -= 5

        if not details.get("canonical_present"):
            score -= 5

        return max(0, score)

    def _build_prompt(self, url: str, details: dict, issues: list) -> str:
        import json
        return f"""Review the SEO audit for {url}.

Audit details:
{json.dumps(details, indent=2)}

Issues found:
{json.dumps(issues, indent=2)}

Return a JSON object with:
- recommendations: array of strings — prioritized list of actionable SEO improvements
- overall_assessment: string — one paragraph summary of SEO health
- quick_wins: array of strings — changes that would have the most impact with least effort"""
