import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from models import (
    JobState,
    JobStatus,
    AgentReport,
    AgentStatus,
    Finding,
    WebSocketEvent,
    WebSocketEventType,
)
from agent_template import BaseAgent, AgentRegistry
from cache import InvestigationCache
from telemetry import TelemetryTracker
from logger import logger


AGENT_TIMEOUT = 45.0
JOB_TIMEOUT = 60.0


class ReconCoordinator:
    def __init__(
        self,
        agent_registry: AgentRegistry = None,
        cache: InvestigationCache = None,
        telemetry: TelemetryTracker = None,
    ):
        self.jobs: dict[str, JobState] = {}
        self.agents: dict[str, BaseAgent] = {}
        self.ws_connections: dict[str, set] = {}
        self.agent_registry = agent_registry or AgentRegistry()
        self.cache = cache or InvestigationCache()
        self.telemetry = telemetry or TelemetryTracker()

    def register_agent(self, agent: BaseAgent):
        self.agents[agent.agent_id] = agent

    def create_job(self, url: str) -> str:
        job_id = str(uuid.uuid4())
        job = JobState(
            job_id=job_id,
            url=url,
            status=JobStatus.PENDING,
            agents=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.jobs[job_id] = job
        self.telemetry.init_job(job_id)
        return job_id

    def track_telemetry(self, job_id: str, service: str, duration_ms: float, success: bool, metrics: dict | None = None):
        self.telemetry.track(job_id, service, duration_ms, success, metrics)
        job_telemetry = self.telemetry.get_job_telemetry(job_id)
        service_telemetry = job_telemetry.get(service)
        if service_telemetry:
            asyncio.create_task(self.emit_event(
                job_id,
                WebSocketEvent(
                    type=WebSocketEventType.TELEMETRY_UPDATE,
                    payload={
                        "job_id": job_id,
                        "service": service,
                        "data": service_telemetry.model_dump()
                    }
                )
            ))

    def check_cache(self, url: str) -> Optional[dict]:
        cached = self.cache.get(url)
        if cached is not None:
            cached["cached"] = True
            return cached
        return None

    def register_ws(self, job_id: str, ws):
        if job_id not in self.ws_connections:
            self.ws_connections[job_id] = set()
        self.ws_connections[job_id].add(ws)

    def unregister_ws(self, job_id: str, ws):
        if job_id in self.ws_connections:
            self.ws_connections[job_id].discard(ws)

    async def emit_event(self, job_id: str, event: WebSocketEvent):
        connections = self.ws_connections.get(job_id, set())
        for ws in connections:
            try:
                await ws.send_text(event.model_dump_json())
            except Exception:
                pass

    async def _run_single_agent(
        self,
        job_id: str,
        agent: BaseAgent,
        url: str,
    ) -> AgentReport:
        agent.job_id = job_id
        agent.track_telemetry = lambda service, duration, success, metrics=None: self.track_telemetry(job_id, service, duration, success, metrics)

        report = AgentReport(
            agent_id=agent.agent_id,
            agent_name=agent.agent_name,
            status=AgentStatus.PENDING,
        )
        start_time = time.monotonic()

        try:
            await self.emit_event(
                job_id,
                WebSocketEvent(
                    type=WebSocketEventType.AGENT_UPDATE,
                    payload={
                        "agent_id": agent.agent_id,
                        "agent_name": agent.agent_name,
                        "status": AgentStatus.RUNNING.value,
                    },
                ),
            )

            result = await asyncio.wait_for(
                agent.run(url, on_finding=lambda f: self._handle_finding(job_id, f)),
                timeout=AGENT_TIMEOUT,
            )

            elapsed = time.monotonic() - start_time
            result.duration = round(elapsed, 2)

            status_val = (
                AgentStatus.DONE.value
                if result.status == AgentStatus.DONE
                else AgentStatus.ERROR.value
            )

            payload = {
                "agent_id": agent.agent_id,
                "agent_name": agent.agent_name,
                "status": status_val,
                "duration": result.duration,
            }
            if result.error:
                payload["error"] = result.error

            await self.emit_event(
                job_id,
                WebSocketEvent(
                    type=WebSocketEventType.AGENT_UPDATE,
                    payload=payload,
                ),
            )

            return result

        except asyncio.TimeoutError:
            elapsed = time.monotonic() - start_time
            report = AgentReport(
                agent_id=agent.agent_id,
                agent_name=agent.agent_name,
                status=AgentStatus.ERROR,
                error="Agent timed out after 45 seconds",
                duration=round(elapsed, 2),
            )
            await self.emit_event(
                job_id,
                WebSocketEvent(
                    type=WebSocketEventType.AGENT_UPDATE,
                    payload={
                        "agent_id": agent.agent_id,
                        "agent_name": agent.agent_name,
                        "status": AgentStatus.ERROR.value,
                        "error": "Agent timed out after 45 seconds",
                        "duration": round(elapsed, 2),
                    },
                ),
            )
            return report

        except Exception as exc:
            elapsed = time.monotonic() - start_time
            error_msg = str(exc)
            report = AgentReport(
                agent_id=agent.agent_id,
                agent_name=agent.agent_name,
                status=AgentStatus.ERROR,
                error=error_msg,
                duration=round(elapsed, 2),
            )
            await self.emit_event(
                job_id,
                WebSocketEvent(
                    type=WebSocketEventType.AGENT_UPDATE,
                    payload={
                        "agent_id": agent.agent_id,
                        "agent_name": agent.agent_name,
                        "status": AgentStatus.ERROR.value,
                        "error": error_msg,
                        "duration": round(elapsed, 2),
                    },
                ),
            )
            return report

    async def run_job(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            return

        job.status = JobStatus.RUNNING
        job.updated_at = datetime.now(timezone.utc)
        logger.info(f"Job {job_id} started for URL: {job.url}")

        agent_list = self.agent_registry.list_agents()
        if not agent_list:
            logger.error(f"Job {job_id}: no agents registered")
            job.status = JobStatus.ERROR
            job.updated_at = datetime.now(timezone.utc)
            return

        for a in agent_list:
            job.agents.append(
                AgentReport(
                    agent_id=a.agent_id,
                    agent_name=a.agent_name,
                    status=AgentStatus.PENDING,
                )
            )

        agent_map = {a.agent_id: a for a in agent_list}

        async def run_agent_1():
            agent = agent_map.get("product_analyzer")
            if not agent:
                return AgentReport(
                    agent_id="product_analyzer",
                    agent_name="Product Analyzer",
                    status=AgentStatus.ERROR,
                    error="Agent not found",
                )
            return await self._run_single_agent(job_id, agent, job.url)

        async def run_agent_2(agent_1_future: asyncio.Future):
            agent = agent_map.get("competitor_finder")
            if not agent:
                return AgentReport(
                    agent_id="competitor_finder",
                    agent_name="Competitor Finder",
                    status=AgentStatus.ERROR,
                    error="Agent not found",
                )

            await self.emit_event(
                job_id,
                WebSocketEvent(
                    type=WebSocketEventType.AGENT_UPDATE,
                    payload={
                        "agent_id": agent.agent_id,
                        "agent_name": agent.agent_name,
                        "status": AgentStatus.PENDING.value,
                        "error": "Waiting for Product Analyzer to determine company and category",
                    },
                ),
            )
            logger.info(f"Job {job_id}: Agent 2 (competitor_finder) waiting for Agent 1 (product_analyzer)")

            agent_1_report = await agent_1_future

            product_category = None
            company_name = None
            if agent_1_report.data:
                product_category = (
                    agent_1_report.data.get("product_category")
                    or agent_1_report.data.get("category")
                    or agent_1_report.data.get("target_market")
                )
                company_name = agent_1_report.data.get("company_name")

            if not company_name:
                report = AgentReport(
                    agent_id=agent.agent_id,
                    agent_name=agent.agent_name,
                    status=AgentStatus.ERROR,
                    error="Product Analyzer did not determine company/category",
                )
                await self.emit_event(
                    job_id,
                    WebSocketEvent(
                        type=WebSocketEventType.AGENT_UPDATE,
                        payload={
                            "agent_id": agent.agent_id,
                            "agent_name": agent.agent_name,
                            "status": AgentStatus.ERROR.value,
                            "error": "Product Analyzer did not determine company/category",
                        },
                    ),
                )
                return report

            agent._company_name = company_name
            agent._product_category = product_category

            return await self._run_single_agent(job_id, agent, job.url)

        async def run_independent_agent(agent_id: str):
            agent = agent_map.get(agent_id)
            if not agent:
                return AgentReport(
                    agent_id=agent_id,
                    agent_name=agent_id,
                    status=AgentStatus.ERROR,
                    error="Agent not found",
                )
            return await self._run_single_agent(job_id, agent, job.url)

        agent_1_future = asyncio.get_event_loop().create_future()

        async def wrap_agent_1():
            result = await run_agent_1()
            agent_1_future.set_result(result)
            return result

        independent_ids = ["tech_stack", "seo_scanner", "social_auditor", "sentiment_analyzer", "hiring_agent"]
        independent_tasks = [
            asyncio.create_task(run_independent_agent(aid))
            for aid in independent_ids
        ]
        agent_1_task = asyncio.create_task(wrap_agent_1())
        agent_2_task = asyncio.create_task(run_agent_2(agent_1_future))

        try:
            all_reports = await asyncio.wait_for(
                asyncio.gather(
                    agent_1_task,
                    agent_2_task,
                    *independent_tasks,
                    return_exceptions=True,
                ),
                timeout=JOB_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Job {job_id} exceeded {JOB_TIMEOUT}s overall timeout")
            job.status = JobStatus.TIMEOUT
            job.updated_at = datetime.now(timezone.utc)

            for a in job.agents:
                if a.status not in (AgentStatus.DONE, AgentStatus.ERROR):
                    a.status = AgentStatus.ERROR
                    a.error = "Job timed out"
                    a.duration = JOB_TIMEOUT

            await self._emit_job_complete(job_id, job)
            return

        reports_flat = []
        for r in all_reports:
            if isinstance(r, Exception):
                logger.warning(f"Job {job_id}: task raised exception: {r}")
                continue
            if isinstance(r, AgentReport):
                reports_flat.append(r)

        agent_ids = ["product_analyzer", "competitor_finder", "tech_stack", "seo_scanner", "social_auditor", "sentiment_analyzer", "hiring_agent"]

        if reports_flat:
            report_map = {r.agent_id: r for r in reports_flat}
            for i, a in enumerate(job.agents):
                if a.agent_id in report_map:
                    job.agents[i] = report_map[a.agent_id]

        job.status = (
            JobStatus.COMPLETE
            if any(a.status == AgentStatus.DONE for a in job.agents)
            else JobStatus.ERROR
        )
        job.updated_at = datetime.now(timezone.utc)

        # Run synthesis if not errored
        if job.status == JobStatus.COMPLETE:
            await self._run_synthesis(job_id, job)

        # Cache the result
        self.cache.set(job.url, self._build_result_dict(job))

        await self._emit_job_complete(job_id, job)

    def _build_result_dict(self, job: JobState) -> dict:
        return {
            "job_id": job.job_id,
            "url": job.url,
            "status": job.status.value,
            "agents": [a.model_dump() for a in job.agents],
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
        }

    async def _run_synthesis(self, job_id: str, job: JobState):
        try:
            from synthesizer import Synthesizer
            synth = Synthesizer()
            agent_data = {}
            for a in job.agents:
                agent_data[a.agent_id] = {
                    "agent_name": a.agent_name,
                    "status": a.status.value,
                    "data": a.data,
                    "error": a.error,
                }
            synthesis = await synth.synthesize(agent_data)
            await self.emit_event(
                job_id,
                WebSocketEvent(
                    type=WebSocketEventType.SYNTHESIS_COMPLETED,
                    payload={"synthesis": synthesis.model_dump()},
                ),
            )
            # Store synthesis in job state for later retrieval
            job.extra = job.extra or {}
            job.extra["synthesis"] = synthesis.model_dump()
            logger.info(f"Job {job_id}: synthesis completed with {len(synthesis.insights)} insights")
        except Exception as e:
            logger.warning(f"Job {job_id}: synthesis failed: {e}")

    async def _emit_job_complete(self, job_id: str, job: JobState):
        payload = {
            "job_id": job_id,
            "status": job.status.value,
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "agent_name": a.agent_name,
                    "status": a.status.value,
                    "duration": a.duration,
                    "error": a.error,
                }
                for a in job.agents
            ],
        }
        extra = getattr(job, "extra", None)
        if extra and "synthesis" in extra:
            payload["synthesis"] = extra["synthesis"]
        await self.emit_event(
            job_id,
            WebSocketEvent(
                type=WebSocketEventType.JOB_COMPLETE,
                payload=payload,
            ),
        )

    async def _handle_finding(self, job_id: str, finding: Finding):
        job = self.jobs.get(job_id)
        if job:
            job.findings.append(finding)
        await self.emit_event(
            job_id,
            WebSocketEvent(
                type=WebSocketEventType.FINDING,
                payload=finding.model_dump(),
            ),
        )

    def get_job(self, job_id: str) -> Optional[JobState]:
        return self.jobs.get(job_id)

    def has_active_job_for_url(self, url: str) -> bool:
        return any(
            j.url == url and j.status in (JobStatus.PENDING, JobStatus.RUNNING)
            for j in self.jobs.values()
        )
