import asyncio
import json
import os
import time
from abc import ABC, abstractmethod
from typing import Optional
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

    async def oxylabs_scrape(self, url: str, source_type: str = "universal") -> Optional[dict]:
        username = os.getenv("OXYLABS_USERNAME")
        password = os.getenv("OXYLABS_PASSWORD")
        if not username or not password:
            logger.warning(f"{self.agent_id}: Oxylabs credentials not configured")
            return None

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
                    elapsed = time.monotonic() - start
                    logger.info(
                        f"{self.agent_id}: oxylabs_scrape attempt {attempt + 1}/3 "
                        f"for {url} -> {resp.status_code} ({elapsed:.2f}s)"
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results = data.get("results", [])
                        if results:
                            return results[0]
                    return None
            except Exception as e:
                elapsed = time.monotonic() - start
                logger.warning(
                    f"{self.agent_id}: oxylabs_scrape attempt {attempt + 1}/3 failed "
                    f"({elapsed:.2f}s): {e}"
                )
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
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
                elapsed = time.monotonic() - start
                logger.info(
                    f"{self.agent_id}: kimi_analyze attempt {attempt + 1}/3 "
                    f"responded ({elapsed:.2f}s)"
                )
                content = response.choices[0].message.content
                if content:
                    json_match = content[content.find("{") : content.rfind("}") + 1]
                    return json.loads(json_match)
                logger.warning(f"{self.agent_id}: Kimi returned empty content")
                return None
            except Exception as e:
                elapsed = time.monotonic() - start
                logger.warning(
                    f"{self.agent_id}: kimi_analyze attempt {attempt + 1}/3 failed "
                    f"({elapsed:.2f}s): {e}"
                )
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
