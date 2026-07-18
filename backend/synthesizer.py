import re
from datetime import datetime, timezone
from typing import Optional

from models import SynthesisOutput, SynthesisItem
from logger import logger


AGENT_NAMES = {
    "product_analyzer": "Product Analyzer",
    "competitor_finder": "Competitor Finder",
    "tech_stack": "Tech Stack Detective",
    "seo_scanner": "SEO Scanner",
    "social_auditor": "Social Auditor",
    "sentiment_analyzer": "Sentiment Analyzer",
    "hiring_agent": "Hiring Signal Detector",
}


class Synthesizer:
    async def synthesize(self, agent_data: dict[str, dict]) -> SynthesisOutput:
        insights = []
        risks = []
        opportunities = []

        available = {aid: ad for aid, ad in agent_data.items() if ad.get("status") == "done" and ad.get("data")}

        if not available:
            return SynthesisOutput(
                insights=[SynthesisItem(text="No agent data available for synthesis", supporting_agents=[], signal_type="single_agent_anomaly")],
                risks=[],
                opportunities=[],
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        # Agreement signals
        insights.extend(self._detect_agreements(available))

        # Conflict signals  
        conflicts = self._detect_conflicts(available)
        risks.extend(conflicts)

        # Single-agent anomalies
        anomalies = self._detect_anomalies(available)
        insights.extend(anomalies)

        opportunities.extend(self._find_opportunities(available))

        # Fallback if no signals found
        if not insights and not risks and not opportunities:
            insights.append(SynthesisItem(
                text="All agents completed successfully — no contradictory or anomalous signals detected",
                supporting_agents=list(available.keys()),
                signal_type="agreement",
            ))

        return SynthesisOutput(
            insights=insights[:6],
            risks=risks[:4],
            opportunities=opportunities[:4],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _detect_agreements(self, available: dict) -> list[SynthesisItem]:
        items = []

        # Check if multiple agents mention the same company
        companies = set()
        for aid, ad in available.items():
            data = ad.get("data", {})
            if isinstance(data, dict):
                name = data.get("company_name") or data.get("name") or ""
                if name:
                    companies.add(name.lower())
        if len(companies) == 1:
            company = list(companies)[0]
            supporting = [aid for aid, ad in available.items() if (ad.get("data", {}).get("company_name") or ad.get("data", {}).get("name") or "").lower() == company]
            if len(supporting) >= 2:
                items.append(SynthesisItem(
                    text=f"Multiple agents confirm the target is {company.title()}",
                    supporting_agents=[AGENT_NAMES.get(s, s) for s in supporting],
                    signal_type="agreement",
                ))

        return items

    def _detect_conflicts(self, available: dict) -> list[SynthesisItem]:
        items = []

        # Sentiment vs Social engagement
        sentiment = available.get("sentiment_analyzer", {}).get("data", {})
        social = available.get("social_auditor", {}).get("data", {})
        if sentiment and social:
            score = sentiment.get("overall_score")
            social_mentions = social.get("total_mentions", 0) if isinstance(social, dict) else 0
            if isinstance(score, (int, float)) and score > 70 and social_mentions == 0:
                items.append(SynthesisItem(
                    text="High sentiment score but no social media presence — reviews may be from incentivized sources",
                    supporting_agents=["Sentiment Analyzer", "Social Auditor"],
                    signal_type="conflict",
                ))
            elif isinstance(score, (int, float)) and score < 30 and social_mentions > 100:
                items.append(SynthesisItem(
                    text="Poor reviews despite strong social engagement — possible reputation management issue",
                    supporting_agents=["Sentiment Analyzer", "Social Auditor"],
                    signal_type="conflict",
                ))

        return items

    def _detect_anomalies(self, available: dict) -> list[SynthesisItem]:
        items = []

        # Hiring agent found roles but product analyzer says small company
        hiring = available.get("hiring_agent", {}).get("data", {})
        product = available.get("product_analyzer", {}).get("data", {})
        if hiring and product:
            total_roles = hiring.get("total_open_roles", 0) if isinstance(hiring, dict) else 0
            company_size = None
            if isinstance(product, dict):
                size = product.get("company_size") or product.get("size") or ""
                if isinstance(size, str):
                    match = re.search(r"(\d+)", size)
                    if match:
                        company_size = int(match.group(1))
            if isinstance(total_roles, (int, float)) and total_roles > 20 and company_size and company_size < 50:
                items.append(SynthesisItem(
                    text=f"Company with {company_size} employees is hiring {total_roles}+ roles — aggressive growth signal",
                    supporting_agents=["Hiring Signal Detector", "Product Analyzer"],
                    signal_type="single_agent_anomaly",
                ))

        # Tech stack mentions AI but no AI hiring
        tech = available.get("tech_stack", {}).get("data", {})
        if tech and hiring:
            tech_data = tech if isinstance(tech, dict) else {}
            has_ai = any("ai" in str(v).lower() or "machine learning" in str(v).lower() for v in tech_data.values())
            ai_hiring = hiring.get("department_breakdown", {}).get("AI/ML", 0) if isinstance(hiring, dict) else 0
            if has_ai and ai_hiring == 0:
                items.append(SynthesisItem(
                    text="AI/ML in tech stack but no AI hiring — could indicate existing AI team or reliance on third-party AI tools",
                    supporting_agents=["Tech Stack Detective", "Hiring Signal Detector"],
                    signal_type="single_agent_anomaly",
                ))

        return items

    def _find_opportunities(self, available: dict) -> list[SynthesisItem]:
        items = []

        # Poor SEO + strong tech = opportunity
        seo = available.get("seo_scanner", {}).get("data", {})
        tech = available.get("tech_stack", {}).get("data", {})
        if seo and tech:
            seo_score = seo.get("score") if isinstance(seo, dict) else None
            if isinstance(seo_score, (int, float)) and seo_score < 50:
                items.append(SynthesisItem(
                    text="Low SEO score combined with modern tech stack — significant quick-win optimization opportunity",
                    supporting_agents=["SEO Scanner", "Tech Stack Detective"],
                    signal_type="single_agent_anomaly",
                ))

        # Good reviews + weak competitors
        sentiment = available.get("sentiment_analyzer", {}).get("data", {})
        comp = available.get("competitor_finder", {}).get("data", {})
        if sentiment and comp:
            score = sentiment.get("overall_score", 0) if isinstance(sentiment, dict) else 0
            if isinstance(score, (int, float)) and score > 60 and comp:
                items.append(SynthesisItem(
                    text="Strong customer sentiment in a competitive market — leverage reviews as social proof",
                    supporting_agents=["Sentiment Analyzer", "Competitor Finder"],
                    signal_type="single_agent_anomaly",
                ))

        return items
