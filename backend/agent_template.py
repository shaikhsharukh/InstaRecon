import asyncio
import json
import os
import time
from abc import ABC, abstractmethod
from typing import Optional, Any
import httpx
from openai import OpenAI

from models import AgentReport, AgentStatus, AgentMeta
from logger import logger


SSL_VERIFY: bool = False


class BaseAgent(ABC):
    agent_id: str
    agent_name: str
    icon: str = ""
    color: str = ""
    description: str = ""

    def __init__(self, agent_id: str, agent_name: str):
        self.agent_id = agent_id
        self.agent_name = agent_name

    @abstractmethod
    async def run(self, url: str, on_finding: callable) -> AgentReport:
        pass

    def on_error(self, error: str) -> AgentReport:
        return AgentReport(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status=AgentStatus.ERROR,
            error=error,
        )

    def create_report(
        self,
        data: Optional[dict] = None,
        pages_found: Optional[list[str]] = None,
        pages_missing: Optional[list[str]] = None,
    ) -> AgentReport:
        return AgentReport(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status=AgentStatus.DONE,
            data=data,
            pages_found=pages_found,
            pages_missing=pages_missing,
        )

    def get_meta(self) -> AgentMeta:
        return AgentMeta(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            icon=self.icon,
            color=self.color,
            description=self.description,
        )

    def _do_track(self, service: str, duration_ms: float, success: bool, metrics: dict | None = None):
        track_fn = getattr(self, "track_telemetry", None)
        if track_fn:
            try:
                track_fn(service, duration_ms, success, metrics)
            except Exception as e:
                logger.warning(f"Error calling track_telemetry: {e}")

    def _create_sandbox_sync(self):
        from daytona import Daytona, DaytonaConfig
        api_key = os.getenv("DAYTONA_API_KEY")
        if not api_key:
            logger.warning("DAYTONA_API_KEY not configured")
            return None
        config = DaytonaConfig(api_key=api_key)
        daytona = Daytona(config=config)
        return daytona.create()

    async def create_daytona_sandbox(self) -> Optional[Any]:
        start = time.monotonic()
        try:
            logger.info(f"{self.agent_id}: Creating Daytona sandbox...")
            sandbox = await asyncio.to_thread(self._create_sandbox_sync)
            elapsed_ms = (time.monotonic() - start) * 1000.0
            if sandbox:
                logger.info(f"{self.agent_id}: Daytona sandbox created successfully (ID: {sandbox.id}) in {elapsed_ms/1000.0:.2f}s")
                self._do_track(
                    "daytona",
                    elapsed_ms,
                    success=True,
                    metrics={
                        "sandbox_count": 1,
                        "avg_spin_up_ms": elapsed_ms,
                        "cumulative_runtime_s": 0.0,
                    }
                )
                return sandbox
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000.0
            logger.error(f"{self.agent_id}: Failed to create Daytona sandbox: {e}")
            self._do_track(
                "daytona",
                elapsed_ms,
                success=False,
                metrics={
                    "sandbox_count": 1,
                    "avg_spin_up_ms": elapsed_ms,
                }
            )
        return None

    async def destroy_daytona_sandbox(self, sandbox, start_time: float):
        if not sandbox:
            return
        runtime_s = time.monotonic() - start_time
        try:
            logger.info(f"{self.agent_id}: Deleting Daytona sandbox {sandbox.id}...")
            await asyncio.to_thread(sandbox.delete)
            logger.info(f"{self.agent_id}: Daytona sandbox deleted successfully.")
            self._do_track(
                "daytona",
                0.0,
                success=True,
                metrics={
                    "cumulative_runtime_s": round(runtime_s, 2),
                }
            )
        except Exception as e:
            logger.error(f"{self.agent_id}: Failed to delete Daytona sandbox: {e}")

    async def oxylabs_scrape(self, url: str, source_type: str = "universal") -> Optional[dict]:
        username = os.getenv("OXYLABS_USERNAME")
        password = os.getenv("OXYLABS_PASSWORD")
        is_serp = "serp" in source_type.lower() or "google" in source_type.lower()
        
        # Track type (web scrape vs. SERP)
        metrics = {
            "web_scrape_count": 0 if is_serp else 1,
            "serp_count": 1 if is_serp else 0,
            "data_volume_kb": 0.0,
        }

        # Attempt Oxylabs first
        if username and password:
            payload = {
                "source": source_type,
                "url": url,
                "parse": True,
            }
            for attempt in range(3):
                start = time.monotonic()
                try:
                    async with httpx.AsyncClient(
                        timeout=httpx.Timeout(30.0), verify=SSL_VERIFY
                    ) as client:
                        resp = await client.post(
                            "https://realtime.oxylabs.io/v1/queries",
                            json=payload,
                            auth=(username, password),
                        )
                        elapsed = (time.monotonic() - start) * 1000.0
                        logger.info(
                            f"{self.agent_id}: oxylabs_scrape attempt {attempt + 1}/3 "
                            f"for {url} -> {resp.status_code} ({elapsed/1000.0:.2f}s)"
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            results = data.get("results", [])
                            if results:
                                data_len = len(resp.content)
                                metrics["data_volume_kb"] = round(data_len / 1024.0, 2)
                                self._do_track("oxylabs", elapsed, success=True, metrics=metrics)
                                return results[0]
                        self._do_track("oxylabs", elapsed, success=False, metrics=metrics)
                except Exception as e:
                    elapsed = (time.monotonic() - start) * 1000.0
                    logger.warning(
                        f"{self.agent_id}: oxylabs_scrape attempt {attempt + 1}/3 failed "
                        f"({elapsed/1000.0:.2f}s): {e}"
                    )
                    self._do_track("oxylabs", elapsed, success=False, metrics=metrics)
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)

        # Fallback if Oxylabs is missing or failed (e.g. 401/403)
        logger.info(f"{self.agent_id}: Oxylabs failed/missing. Using free inline search/scrape fallback for {url}")
        
        if is_serp:
            # SERP (Google search) fallback using Tavily Search API
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed.query)
            query = query_params.get("q", [""])[0] or url
            
            tavily_key = os.getenv("TAVILY_API_KEY") or "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"
            
            start = time.monotonic()
            try:
                headers = {"Content-Type": "application/json"}
                payload = {
                    "api_key": tavily_key,
                    "query": query,
                    "search_depth": "basic"
                }
                async with httpx.AsyncClient(timeout=15.0, verify=SSL_VERIFY) as client:
                    resp = await client.post("https://api.tavily.com/search", json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        google_results_html = []
                        for item in data.get("results", []):
                            title = item.get("title", "")
                            href = item.get("url", "")
                            snippet = item.get("content", "")
                            google_results_html.append(f"""
                            <div class="g" data-hveid="1">
                                <h3><a href="{href}">{title}</a></h3>
                                <span class="st">{snippet}</span>
                                <div class="review">{snippet}</div>
                            </div>
                            """)
                        mock_html = "<html><body>" + "".join(google_results_html) + "</body></html>"
                        elapsed = (time.monotonic() - start) * 1000.0
                        self._do_track("oxylabs", elapsed, success=True, metrics=metrics)
                        return {"content": mock_html}
                    else:
                        logger.warning(f"{self.agent_id}: Tavily API returned status {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.warning(f"{self.agent_id}: Tavily fallback search failed: {e}")
        else:
            # Universal scrape fallback using direct HTTP GET
            start = time.monotonic()
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                async with httpx.AsyncClient(timeout=httpx.Timeout(15.0), verify=SSL_VERIFY) as client:
                    resp = await client.get(url, headers=headers)
                    elapsed = (time.monotonic() - start) * 1000.0
                    if resp.status_code == 200:
                        self._do_track("oxylabs", elapsed, success=True, metrics=metrics)
                        return {"content": resp.text}
            except Exception as e:
                logger.warning(f"{self.agent_id}: Direct scrape fallback failed for {url}: {e}")

        return None

    async def kimi_analyze(self, prompt: str, system_prompt: str = None) -> Optional[dict]:
        api_key = os.getenv("KIMI_API_KEY")
        if not api_key:
            logger.warning(f"{self.agent_id}: KIMI_API_KEY not configured")
            return None

        if system_prompt is None:
            system_prompt = "You are a business analysis AI. Extract structured information and return valid JSON."

        for attempt in range(3):
            start = time.monotonic()
            try:
                _http_client = httpx.Client(
                    verify=SSL_VERIFY, timeout=httpx.Timeout(30.0)
                )
                client = OpenAI(
                    base_url="https://api.aiand.com/v1",
                    api_key=api_key,
                    http_client=_http_client,
                    max_retries=0,
                )
                response = await asyncio.to_thread(
                    client.chat.completions.create,
                    model="deepseek-ai/deepseek-v4-flash",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                )
                elapsed = (time.monotonic() - start) * 1000.0
                logger.info(
                    f"{self.agent_id}: kimi_analyze attempt {attempt + 1}/3 "
                    f"responded ({elapsed/1000.0:.2f}s)"
                )
                
                usage = getattr(response, "usage", None)
                tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
                tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0
                est_cost = (tokens_in * 0.15 + tokens_out * 0.60) / 1_000_000.0
                metrics = {
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "estimated_cost_usd": round(est_cost, 6)
                }

                content = response.choices[0].message.content
                if content:
                    json_match = content[content.find("{") : content.rfind("}") + 1]
                    self._do_track("kimi", elapsed, success=True, metrics=metrics)
                    return json.loads(json_match)
                logger.warning(f"{self.agent_id}: Kimi returned empty content")
                self._do_track("kimi", elapsed, success=False, metrics=metrics)
                return None
            except Exception as e:
                elapsed = (time.monotonic() - start) * 1000.0
                logger.warning(
                    f"{self.agent_id}: kimi_analyze attempt {attempt + 1}/3 failed "
                    f"({elapsed/1000.0:.2f}s): {e}"
                )
                self._do_track("kimi", elapsed, success=False)
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        return None

    async def run_with_timeout(self, coro, timeout: float = 45.0):
        return await asyncio.wait_for(coro, timeout=timeout)


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent):
        self._agents[agent.agent_id] = agent

    def get(self, agent_id: str) -> Optional[BaseAgent]:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[BaseAgent]:
        return list(self._agents.values())

    def list_metadata(self) -> list[AgentMeta]:
        return [agent.get_meta() for agent in self._agents.values()]
