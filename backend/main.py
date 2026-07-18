# Monkey-patch SSL context and urllib3 validation for corporate/proxy setups
import ssl
import urllib3
import urllib3.connection
import urllib3.util.ssl_

urllib3.disable_warnings()

orig_create_context = urllib3.util.ssl_.create_urllib3_context
def patched_create_context(*args, **kwargs):
    context = orig_create_context(*args, **kwargs)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context
urllib3.util.ssl_.create_urllib3_context = patched_create_context

orig_https_init = urllib3.connection.HTTPSConnection.__init__
def patched_https_init(self, *args, **kwargs):
    kwargs['cert_reqs'] = ssl.CERT_NONE
    orig_https_init(self, *args, **kwargs)
urllib3.connection.HTTPSConnection.__init__ = patched_https_init

orig_create_default_context = ssl.create_default_context
def patched_create_default_context(*args, **kwargs):
    context = orig_create_default_context(*args, **kwargs)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context
ssl.create_default_context = patched_create_default_context

import os
import certifi
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timezone

from models import ReconRequest, ReconResponse, JobStatus, WebSocketEvent, WebSocketEventType, AgentMeta
from coordinator import ReconCoordinator
from agent_template import AgentRegistry
from agents.product_analyzer import ProductAnalyzer
from agents.tech_stack import TechStackDetective
from agents.competitor_finder import CompetitorFinder
from agents.social_auditor import SocialAuditor
from agents.seo_scanner import SEOScanner
from agents.sentiment_analyzer import SentimentAnalyzer
from agents.hiring_agent import HiringAgent
from cache import InvestigationCache
from telemetry import TelemetryTracker
from logger import logger

os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

dotenv_path = Path(__file__).resolve().parent.parent / ".env.local"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    logger.info(f"Loaded env from {dotenv_path}")
else:
    logger.warning(".env.local not found — API keys may be missing")


agent_registry = AgentRegistry()
cache = InvestigationCache()
telemetry = TelemetryTracker()
coordinator = ReconCoordinator(
    agent_registry=agent_registry,
    cache=cache,
    telemetry=telemetry,
)

all_agents = [
    ProductAnalyzer(),
    TechStackDetective(),
    CompetitorFinder(),
    SocialAuditor(),
    SEOScanner(),
    SentimentAnalyzer(),
    HiringAgent(),
]
for agent in all_agents:
    agent_registry.register(agent)
    coordinator.register_agent(agent)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="InstaRecon", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/agents")
async def list_agents():
    return {"agents": [m.model_dump() for m in agent_registry.list_metadata()]}


@app.get("/api/recon/{job_id}")
async def get_job_status(job_id: str):
    job = coordinator.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.job_id,
        "url": job.url,
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
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


@app.get("/api/recon/{job_id}/results")
async def get_job_results(job_id: str):
    job = coordinator.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in (JobStatus.PENDING, JobStatus.RUNNING):
        raise HTTPException(status_code=409, detail="Job is still running")
    result = {
        "job_id": job.job_id,
        "url": job.url,
        "status": job.status.value,
        "agents": [
            a.model_dump()
            for a in job.agents
        ],
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }
    extra = getattr(job, "extra", None)
    if extra and "synthesis" in extra:
        result["synthesis"] = extra["synthesis"]
    return result


@app.post("/api/recon", response_model=ReconResponse, status_code=201)
async def start_recon(request: ReconRequest):
    url = request.url.strip()
    logger.info(f"Starting investigation for URL: {url}")

    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL format. Must be a valid HTTP or HTTPS URL.",
        )

    # Check cache first
    cached = coordinator.check_cache(url)
    if cached is not None:
        logger.info(f"Cache hit for URL: {url}")
        return ReconResponse(job_id=cached.get("job_id", "cached"), status=JobStatus.COMPLETE)

    if coordinator.has_active_job_for_url(url):
        raise HTTPException(
            status_code=409,
            detail="An active investigation for this URL is already in progress.",
        )

    job_id = coordinator.create_job(url)

    asyncio.create_task(coordinator.run_job(job_id))

    return ReconResponse(job_id=job_id, status=JobStatus.PENDING)


@app.get("/api/cache/status")
async def cache_status():
    return cache.status()


@app.delete("/api/cache")
async def clear_cache():
    removed = cache.clear()
    return {"status": "cleared", "entries_removed": removed}


@app.get("/api/investigations/{job_id}/brief")
async def get_intel_brief(job_id: str):
    job = coordinator.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if job.status in (JobStatus.PENDING, JobStatus.RUNNING):
        raise HTTPException(status_code=400, detail="Investigation not yet completed")

    try:
        from pdf_generator import generate_pdf
        agent_data = {}
        for a in job.agents:
            agent_data[a.agent_id] = {
                "agent_name": a.agent_name,
                "status": a.status.value,
                "data": a.data,
                "error": a.error,
            }
        extra = getattr(job, "extra", None)
        synthesis = extra.get("synthesis") if extra else None
        pdf_bytes = await generate_pdf(job.url, agent_data, synthesis, coordinator.telemetry.get_job_telemetry(job_id))
        return Response(content=pdf_bytes, media_type="application/pdf", headers={
            "Content-Disposition": f'attachment; filename="intel-brief-{job_id[:8]}.pdf"'
        })
    except Exception as e:
        logger.error(f"PDF generation failed for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    coordinator.register_ws(job_id, websocket)

    job = coordinator.get_job(job_id)
    if job:
        for agent_report in job.agents:
            await websocket.send_text(
                WebSocketEvent(
                    type=WebSocketEventType.AGENT_UPDATE,
                    payload={
                        "agent_id": agent_report.agent_id,
                        "agent_name": agent_report.agent_name,
                        "status": agent_report.status.value,
                        "error": agent_report.error,
                    },
                ).model_dump_json()
            )
        for finding in job.findings:
            await websocket.send_text(
                WebSocketEvent(
                    type=WebSocketEventType.FINDING,
                    payload=finding.model_dump(),
                ).model_dump_json()
            )
        extra = getattr(job, "extra", None)
        if extra and "synthesis" in extra:
            await websocket.send_text(
                WebSocketEvent(
                    type=WebSocketEventType.SYNTHESIS_COMPLETED,
                    payload={"synthesis": extra["synthesis"]},
                ).model_dump_json()
            )
        if job.status in (JobStatus.COMPLETE, JobStatus.ERROR, JobStatus.TIMEOUT):
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
            if extra and "synthesis" in extra:
                payload["synthesis"] = extra["synthesis"]
            await websocket.send_text(
                WebSocketEvent(
                    type=WebSocketEventType.JOB_COMPLETE,
                    payload=payload,
                ).model_dump_json()
            )
        logger.info(f"Sent initial state for job {job_id} ({len(job.agents)} agents, {len(job.findings)} findings)")

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        coordinator.unregister_ws(job_id, websocket)
