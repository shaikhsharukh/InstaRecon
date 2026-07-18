import re
import asyncio
from typing import Optional
import httpx
from bs4 import BeautifulSoup

from agent_template import BaseAgent
from models import AgentReport, AgentStatus, JobListing, HiringSignalReport, StrategicInference
from logger import logger


SSL_VERIFY = False

DEPARTMENT_KEYWORDS = {
    "Engineering": ["engineer", "developer", "software", "backend", "frontend", "fullstack", "devops", "sre", "infrastructure", "data engineer", "platform"],
    "AI/ML": ["machine learning", "ai", "data scientist", "ml engineer", "deep learning", "nlp", "computer vision", "llm"],
    "Sales": ["sales", "account executive", "business development", "sales development", "revenue"],
    "Marketing": ["marketing", "growth", "content", "seo", "brand", "communications", "pr"],
    "Operations": ["operations", "hr", "people", "finance", "legal", "admin", "office manager"],
    "Product": ["product manager", "product designer", "product", "ux", "ui", "designer"],
}

SENIORITY_KEYWORDS = {
    "entry": ["junior", "entry", "associate", "intern", "graduate"],
    "mid": ["mid", "mid-level", "ii", "iii"],
    "senior": ["senior", "sr", "staff", "principal", "lead"],
    "executive": ["vp", "vice president", "director", "head of", "chief", "cto", "cfo", "ceo"],
}


class HiringAgent(BaseAgent):
    agent_id = "hiring_agent"
    agent_name = "Hiring Signal Detector"
    icon = "💼"
    color = "#8b5cf6"
    description = "Scrapes job listings and infers hiring strategy"

    def __init__(self):
        super().__init__(self.agent_id, self.agent_name)

    async def run(self, url: str, on_finding: callable) -> AgentReport:
        domain = self._extract_domain(url)
        if not domain:
            return self.on_error("Could not extract domain from URL")

        careers_task = self._scrape_careers_page(url, domain)
        linkedin_task = self._scrape_job_board(domain, "linkedin")
        indeed_task = self._scrape_job_board(domain, "indeed")

        careers_listings, linkedin_listings, indeed_listings = await asyncio.gather(
            careers_task, linkedin_task, indeed_task, return_exceptions=True
        )

        if isinstance(careers_listings, Exception):
            careers_listings = []
        if isinstance(linkedin_listings, Exception):
            linkedin_listings = []
        if isinstance(indeed_listings, Exception):
            indeed_listings = []

        all_listings = careers_listings + linkedin_listings + indeed_listings

        if not all_listings:
            report = self.create_report(
                data={
                    "total_open_roles": 0,
                    "department_breakdown": {},
                    "top_hiring_departments": [],
                    "strategic_inferences": [],
                    "growth_stage": "unknown",
                    "sources_used": [],
                    "message": "No job listings found",
                }
            )
            return report

        report_data = self._build_hiring_report(all_listings)
        return self.create_report(data=report_data.model_dump())

    def _extract_domain(self, url: str) -> Optional[str]:
        url = url.strip().lower()
        url = re.sub(r"^https?://", "", url)
        url = re.sub(r"^www\.", "", url)
        url = url.split("/")[0]
        return url if "." in url else None

    async def _scrape_careers_page(self, url: str, domain: str) -> list[JobListing]:
        careers_urls = [f"{url.rstrip('/')}/careers", f"{url.rstrip('/')}/jobs", f"https://careers.{domain}"]
        for cu in careers_urls:
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(10.0), verify=SSL_VERIFY, follow_redirects=True) as client:
                    resp = await client.get(cu, headers={"User-Agent": "Mozilla/5.0"})
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        listings = self._parse_listings_from_html(soup, "careers_page")
                        if listings:
                            return listings
            except Exception as e:
                logger.info(f"Careers page scrape failed for {cu}: {e}")
                continue
        return []

    def _parse_listings_from_html(self, soup: BeautifulSoup, source: str) -> list[JobListing]:
        listings = []
        for link in soup.select("a[href*='job'], a[href*='career'], a[href*='position']"):
            title = link.text.strip() or link.get("title") or ""
            if title and len(title) > 5:
                href = link.get("href", "")
                listings.append(JobListing(
                    title=title,
                    department=self._classify_department(title),
                    seniority=self._classify_seniority(title),
                    location=None,
                    remote=False,
                    source=source,
                ))
        return listings[:30]

    async def _scrape_job_board(self, domain: str, board: str) -> list[JobListing]:
        company = domain.split(".")[0]
        query = f"site:{board}.com/jobs {company}" if board == "linkedin" else f"site:{board}.com {company}"
        try:
            result = await self.oxylabs_scrape(
                f"https://www.google.com/search?q={query}",
                source_type="google_search",
            )
            if not result or "content" not in result:
                return []
            soup = BeautifulSoup(str(result.get("content", "")), "html.parser")
            listings = []
            for item in soup.select("div.g, div[data-hveid]"):
                title_el = item.select_one("h3")
                if title_el:
                    title = title_el.text.strip()
                    if company.lower() in title.lower():
                        listings.append(JobListing(
                            title=title,
                            department=self._classify_department(title),
                            seniority=self._classify_seniority(title),
                            source=board,
                            remote=False,
                        ))
            return listings[:10]
        except Exception as e:
            logger.info(f"Job board scrape failed for {board} {domain}: {e}")
            return []

    def _classify_department(self, title: str) -> str:
        title_lower = title.lower()
        best_dept = "Other"
        best_score = 0
        for dept, keywords in DEPARTMENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in title_lower)
            if score > best_score:
                best_score = score
                best_dept = dept
        return best_dept

    def _classify_seniority(self, title: str) -> str:
        title_lower = title.lower()
        for level, keywords in SENIORITY_KEYWORDS.items():
            if any(kw in title_lower for kw in keywords):
                return level
        return "mid"

    def _build_hiring_report(self, listings: list[JobListing]) -> HiringSignalReport:
        dept_breakdown: dict[str, int] = {}
        for listing in listings:
            dept_breakdown[listing.department] = dept_breakdown.get(listing.department, 0) + 1

        sorted_depts = sorted(dept_breakdown.items(), key=lambda x: x[1], reverse=True)
        top_depts = [d for d, _ in sorted_depts[:3]]
        total = len(listings)

        inferences = self._generate_inferences(listings, dept_breakdown, total)

        ai_pct = dept_breakdown.get("AI/ML", 0) / total * 100 if total > 0 else 0
        sales_mktg_pct = (dept_breakdown.get("Sales", 0) + dept_breakdown.get("Marketing", 0)) / total * 100 if total > 0 else 0

        if ai_pct > 20:
            growth_stage = "scaling"
        elif sales_mktg_pct > 40:
            growth_stage = "growth"
        elif total > 20:
            growth_stage = "mature"
        elif total > 5:
            growth_stage = "early"
        elif total > 0:
            growth_stage = "stealth"
        else:
            growth_stage = "unknown"

        sources = list(set(l.source for l in listings))

        return HiringSignalReport(
            total_open_roles=total,
            department_breakdown=dept_breakdown,
            top_hiring_departments=top_depts,
            strategic_inferences=inferences,
            growth_stage=growth_stage,
            sources_used=sources,
        )

    def _generate_inferences(self, listings: list[JobListing], dept_breakdown: dict[str, int], total: int) -> list[StrategicInference]:
        inferences = []
        ai_count = dept_breakdown.get("AI/ML", 0)
        eng_count = dept_breakdown.get("Engineering", 0)
        sales_count = dept_breakdown.get("Sales", 0)
        mktg_count = dept_breakdown.get("Marketing", 0)

        if total > 0 and ai_count / total > 0.2:
            inferences.append(StrategicInference(
                finding="Heavy AI/ML hiring indicates an AI-first strategy or product pivot",
                confidence=round(ai_count / total, 2),
                evidence=[f"{ai_count} AI/ML roles out of {total} total openings"],
            ))

        if total > 0 and (sales_count + mktg_count) / total > 0.4:
            inferences.append(StrategicInference(
                finding="Go-to-market focus — company is investing heavily in sales and marketing",
                confidence=round((sales_count + mktg_count) / total, 2),
                evidence=[f"{sales_count + mktg_count} sales/marketing roles out of {total}"],
            ))

        if total > 0 and eng_count / total > 0.4:
            inferences.append(StrategicInference(
                finding="Engineering-heavy hiring suggests product expansion or platform buildout",
                confidence=round(eng_count / total, 2),
                evidence=[f"{eng_count} engineering roles out of {total}"],
            ))

        senior = sum(1 for l in listings if l.seniority in ("senior", "executive"))
        if total > 0 and senior / total > 0.5:
            inferences.append(StrategicInference(
                finding="Preference for senior/experienced hires — company values expertise over cost",
                confidence=round(senior / total, 2),
                evidence=[f"{senior} senior/executive roles out of {total}"],
            ))

        if not inferences:
            inferences.append(StrategicInference(
                finding="Limited hiring data — unable to make strong strategic inferences",
                confidence=0.3,
                evidence=[f"Only {total} roles found across {len(set(l.source for l in listings))} sources"],
            ))

        return inferences
