import time
import logging
from models import TelemetryRecord

logger = logging.getLogger(__name__)


class TelemetryTracker:
    def __init__(self):
        self._per_job: dict[str, dict[str, TelemetryRecord]] = {}
        self._cumulative: dict[str, TelemetryRecord] = {}

    def init_job(self, job_id: str):
        self._per_job[job_id] = {}

    def _ensure_record(self, store: dict, service: str) -> TelemetryRecord:
        if service not in store:
            store[service] = TelemetryRecord(service_name=service)
        return store[service]

    def track(self, job_id: str, service: str, duration_ms: float, success: bool, metrics: dict | None = None):
        job_store = self._per_job.get(job_id)
        if job_store is None:
            return
        rec = self._ensure_record(job_store, service)
        cum = self._ensure_record(self._cumulative, service)
        rec.calls += 1
        cum.calls += 1
        rec.total_duration_ms += duration_ms
        cum.total_duration_ms += duration_ms
        if success:
            rec.successes += 1
            cum.successes += 1
        else:
            rec.failures += 1
            cum.failures += 1
        if metrics:
            for k, v in metrics.items():
                rec.metrics[k] = rec.metrics.get(k, 0) + v
                cum.metrics[k] = cum.metrics.get(k, 0) + v

    def get_job_telemetry(self, job_id: str) -> dict[str, TelemetryRecord]:
        return self._per_job.get(job_id, {})

    def get_cumulative(self) -> dict[str, TelemetryRecord]:
        return dict(self._cumulative)

    def get_all_job_telemetry(self) -> dict[str, dict[str, TelemetryRecord]]:
        return dict(self._per_job)

    def cleanup_job(self, job_id: str):
        self._per_job.pop(job_id, None)
