from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"
    TIMEOUT = "timeout"


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class WebSocketEventType(str, Enum):
    AGENT_UPDATE = "agent_update"
    FINDING = "finding"
    JOB_COMPLETE = "job_complete"
    ERROR = "error"
    TELEMETRY_UPDATE = "telemetry.update"
    SYNTHESIS_COMPLETED = "synthesis.completed"
    EMAIL_SENT = "email.sent"
    EMAIL_FAILED = "email.failed"
    PDF_GENERATED = "pdf.generated"


class ReconRequest(BaseModel):
    url: str


class ReconResponse(BaseModel):
    job_id: str
    status: JobStatus


class AgentReport(BaseModel):
    agent_id: str
    agent_name: str
    status: AgentStatus
    data: Optional[dict] = None
    error: Optional[str] = None
    pages_found: Optional[list[str]] = None
    pages_missing: Optional[list[str]] = None
    duration: Optional[float] = None
    findings_count: Optional[int] = None
    partial_data: Optional[dict] = None


class Finding(BaseModel):
    agent_id: str
    agent_name: str
    timestamp: str
    description: str
    data: Optional[dict] = None


class WebSocketEvent(BaseModel):
    type: WebSocketEventType
    payload: dict


class AgentMeta(BaseModel):
    agent_id: str
    agent_name: str
    icon: str
    color: str
    description: str


class JobState(BaseModel):
    job_id: str
    url: str
    status: JobStatus
    agents: list[AgentReport]
    findings: list[Finding] = []
    created_at: datetime
    updated_at: datetime
    extra: Optional[dict] = None


class Review(BaseModel):
    source: str
    rating: Optional[float] = None
    text: str
    date: Optional[str] = None
    author: Optional[str] = None


class SentimentReport(BaseModel):
    overall_score: float
    distribution: dict[str, float]
    praise_themes: list[str]
    complaint_themes: list[str]
    trend: str
    sources_used: list[str]
    review_count: int


class JobListing(BaseModel):
    title: str
    department: str
    seniority: Optional[str] = None
    location: Optional[str] = None
    remote: bool = False
    posting_date: Optional[str] = None
    source: str


class StrategicInference(BaseModel):
    finding: str
    confidence: float
    evidence: list[str]


class HiringSignalReport(BaseModel):
    total_open_roles: int
    department_breakdown: dict[str, int]
    top_hiring_departments: list[str]
    strategic_inferences: list[StrategicInference]
    growth_stage: str
    sources_used: list[str]


class SynthesisItem(BaseModel):
    text: str
    supporting_agents: list[str]
    signal_type: str


class SynthesisOutput(BaseModel):
    insights: list[SynthesisItem]
    risks: list[SynthesisItem]
    opportunities: list[SynthesisItem]
    generated_at: str


class IntelBrief(BaseModel):
    company_name: str
    generated_at: str
    duration_seconds: float
    executive_summary: str
    synthesis: Optional[SynthesisOutput] = None
    agent_reports: dict[str, dict]
    sponsor_attribution: dict[str, "TelemetryRecord"]


class CacheEntry(BaseModel):
    normalized_url: str
    result: dict
    cached_at: str
    ttl_seconds: int


class TelemetryRecord(BaseModel):
    service_name: str
    calls: int = 0
    successes: int = 0
    failures: int = 0
    total_duration_ms: float = 0.0
    metrics: dict[str, float] = {}


InvestigationResultData = dict
