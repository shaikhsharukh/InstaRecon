import asyncio
import re
import time
from datetime import datetime, timezone

import httpx

from agent_template import BaseAgent
from models import AgentReport, AgentStatus, Finding
from logger import logger


SSL_VERIFY: bool = False
SCRAPE_TIMEOUT = 15


TECH_PATTERNS = [
    ("React", [r"__NEXT_DATA__", r"react\.js", r"react-dom", r"data-reactroot"]),
    ("Vue.js", [r"data-v-", r"vue\.js", r"__VUE__"]),
    ("Angular", [r"ng-version", r"ng-app", r"angular\.js"]),
    ("Svelte", [r"svelte\.js", r"__SVELTE__"]),
    ("Next.js", [r"__NEXT_DATA__", r"/_next/static"]),
    ("Nuxt.js", [r"__NUXT__"]),
    ("Gatsby", [r"gatsby\.js", r"___gatsby"]),
    ("Astro", [r"astro\.js", r"data-astro"]),
    ("Remix", [r"remix-run", r"__remix"]),
    ("Solid.js", [r"solid\.js", r"__SOLID__"]),
    ("Tailwind CSS", [r"tailwindcss", r"tw-", r"dark:"]),
    ("Bootstrap", [r"bootstrap\.min\.css", r"bootstrap\.js", r"col-md-"]),
    ("jQuery", [r"jquery\.js", r"jquery-"]),
]


CMS_PATTERNS = [
    ("WordPress", [r"wp-content", r"wp-includes", r"wordpress"]),
    ("Shopify", [r"shopify\.com", r"myshopify\.com", r"Shopify\.sdk"]),
    ("Wix", [r"wix\.com", r"WIX"]),
    ("Squarespace", [r"squarespace\.com", r"static1\.squarespace"]),
    ("Drupal", [r"drupal\.js", r"Drupal\.settings"]),
    ("Joomla", [r"joomla", r"option=com_"]),
    ("Webflow", [r"webflow\.js", r"data-wf-"]),
]


CDN_PATTERNS = [
    ("Cloudflare", [r"cloudflare", r"__cfduid", r"cf-ray"]),
    ("Akamai", [r"akamai", r"akamaized"]),
    ("Fastly", [r"fastly", r"fastly-tls"]),
    ("CloudFront", [r"cloudfront\.net"]),
    ("Cloudflare R2", [r"r2\.cloudflarestorage"]),
    ("jsDelivr", [r"cdn\.jsdelivr\.net"]),
    ("unpkg", [r"unpkg\.com"]),
    ("cdnjs", [r"cdnjs\.cloudflare\.com"]),
]


HOSTING_SIGNALS = {
    "Vercel": [r"vercel\.com", r"x-vercel-id", r"x-vercel-cache"],
    "Netlify": [r"netlify\.com", r"x-nf-request-id"],
    "AWS": [r"awseb", r"amazonaws\.com", r"x-amz-"],
    "Cloudflare Pages": [r"__cf", r"_cfduid"],
    "GitHub Pages": [r"github\.io"],
    "Firebase": [r"firebaseapp\.com", r"web\.app"],
    "Railway": [r"railway\.app"],
    "Render": [r"onrender\.com"],
    "Heroku": [r"herokuapp\.com", r"heroku"],
    "DigitalOcean": [r"digitalocean\.com", r"do-"],
}


class TechStackDetective(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="tech_stack",
            agent_name="Tech Stack Detective",
        )
        self.icon = "⚙️"
        self.color = "#8B5CF6"
        self.description = "Identifies frameworks, CMS, CDN, and hosting infrastructure"

    async def run(self, url: str, on_finding: callable) -> AgentReport:
        start_time = time.monotonic()
        finding_count = 0

        try:
            await on_finding(
                Finding(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    description="Scanning tech stack for " + url,
                )
            )
            finding_count += 1

            html, headers = await self._fetch_page(url, on_finding)

            if not html:
                return AgentReport(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    status=AgentStatus.ERROR,
                    error="Could not fetch page for tech analysis",
                    duration=time.monotonic() - start_time,
                )

            await on_finding(
                Finding(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    description=f"Fetched {len(html)} bytes from " + url,
                )
            )
            finding_count += 1

            frameworks = self._detect_frameworks(html)
            cms = self._detect_cms(html)
            cdn = self._detect_cdn(headers, html)
            hosting = self._detect_hosting(headers, html)

            signals = {
                "frameworks": frameworks,
                "cms": cms,
                "cdn": cdn,
                "hosting": hosting,
                "http_headers": {
                    "server": headers.get("server", ""),
                    "x-powered-by": headers.get("x-powered-by", ""),
                    "x-generator": headers.get("x-generator", ""),
                },
            }

            kimi_result = await self.kimi_analyze(
                self._build_prompt(url, signals, html[:5000]),
                system_prompt="You are a technology detection expert. Analyze the detected tech signals and return a JSON object with confidence scores.",
            )

            if kimi_result:
                await on_finding(
                    Finding(
                        agent_id=self.agent_id,
                        agent_name=self.agent_name,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        description="AI confidence scoring complete for tech stack",
                    )
                )
                finding_count += 1
                signals["ai_analysis"] = kimi_result

            return AgentReport(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.DONE,
                data=signals,
                duration=time.monotonic() - start_time,
                findings_count=finding_count,
                partial_data=None,
            )

        except asyncio.TimeoutError:
            return AgentReport(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                status=AgentStatus.ERROR,
                error="Tech analysis timed out",
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
                    description=f"Failed to fetch page: {e}",
                )
            )
            return None, {}

    def _detect_frameworks(self, html: str) -> list[dict]:
        detected = []
        for name, patterns in TECH_PATTERNS:
            matches = sum(1 for p in patterns if re.search(p, html, re.IGNORECASE))
            if matches > 0:
                confidence = min(0.5 + (matches / len(patterns)) * 0.5, 0.99)
                detected.append({"name": name, "confidence": round(confidence, 2)})
        return detected

    def _detect_cms(self, html: str) -> list[dict]:
        detected = []
        for name, patterns in CMS_PATTERNS:
            matches = sum(1 for p in patterns if re.search(p, html, re.IGNORECASE))
            if matches > 0:
                confidence = min(0.5 + (matches / len(patterns)) * 0.5, 0.99)
                detected.append({"name": name, "confidence": round(confidence, 2)})
        return detected

    def _detect_cdn(self, headers: dict, html: str) -> list[dict]:
        detected = []
        combined = str(headers) + " " + html
        for name, patterns in CDN_PATTERNS:
            if any(re.search(p, combined, re.IGNORECASE) for p in patterns):
                detected.append({"name": name, "confidence": 0.9})
        return detected

    def _detect_hosting(self, headers: dict, html: str) -> list[dict]:
        detected = []
        combined = str(headers) + " " + html
        for name, patterns in HOSTING_SIGNALS.items():
            if any(re.search(p, combined, re.IGNORECASE) for p in patterns):
                detected.append({"name": name, "confidence": 0.7})
        return detected

    def _build_prompt(self, url: str, signals: dict, html_sample: str) -> str:
        import json
        return f"""Analyze the detected technology signals for {url}.

Raw signals:
{json.dumps(signals, indent=2)}

HTML sample (first 5000 chars):
{html_sample[:5000]}

Return a JSON object with:
- frameworks: array of {{"name": string, "confidence": float}} — cross-referenced and re-scored
- cms: array of {{"name": string, "confidence": float}}
- cdn: array of {{"name": string, "confidence": float}}
- hosting: array of {{"name": string, "confidence": float}}
- assessment: string — one sentence summary of the tech stack
- estimated_stack_age: string — "modern", "recent", "legacy", or "unknown"

Only include technologies you have reasonable evidence for."""
