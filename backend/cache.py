import os
import time
import logging
from datetime import datetime
from models import CacheEntry

logger = logging.getLogger(__name__)

DEFAULT_TTL = int(os.getenv("CACHE_TTL_SECONDS", "3600"))


def normalize_url(url: str) -> str | None:
    url = url.strip().lower()
    if url.startswith("http://"):
        url = url[7:]
    elif url.startswith("https://"):
        url = url[8:]
    if url.startswith("www."):
        url = url[4:]
    url = url.rstrip("/")
    if not url or " " in url or "." not in url:
        return None
    return url


class InvestigationCache:
    def __init__(self, ttl: int = DEFAULT_TTL):
        self._entries: dict[str, CacheEntry] = {}
        self._ttl = ttl
        self._hits = 0
        self._misses = 0

    def get(self, url: str) -> dict | None:
        key = normalize_url(url)
        if key is None:
            self._misses += 1
            return None
        entry = self._entries.get(key)
        if entry is None:
            self._misses += 1
            return None
        age = time.time() - self._entry_timestamp(key)
        if age > entry.ttl_seconds:
            del self._entries[key]
            self._misses += 1
            return None
        self._hits += 1
        return entry.result

    def set(self, url: str, result: dict) -> str | None:
        key = normalize_url(url)
        if key is None:
            return None
        self._entries[key] = CacheEntry(
            normalized_url=key,
            result=result,
            cached_at=datetime.utcnow().isoformat() + "Z",
            ttl_seconds=self._ttl,
        )
        return key

    def _entry_timestamp(self, key: str) -> float:
        entry = self._entries.get(key)
        if entry is None:
            return 0
        try:
            dt = datetime.fromisoformat(entry.cached_at.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            return 0

    def status(self) -> dict:
        now = time.time()
        ages = []
        for e in self._entries.values():
            ts = self._entry_timestamp(e.normalized_url)
            ages.append(now - ts)
        return {
            "hits": self._hits,
            "misses": self._misses,
            "entries": len(self._entries),
            "oldest_entry_age_seconds": round(max(ages)) if ages else 0,
            "newest_entry_age_seconds": round(min(ages)) if ages else 0,
        }

    def clear(self) -> int:
        count = len(self._entries)
        self._entries.clear()
        return count

    def has(self, url: str) -> bool:
        return self.get(url) is not None
