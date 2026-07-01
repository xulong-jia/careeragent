from __future__ import annotations

from time import monotonic
from threading import Lock
from typing import Any


_started_at = monotonic()
_lock = Lock()
_http_requests_total = 0
_http_status_classes: dict[str, int] = {}
_http_duration_ms_sum = 0
_http_duration_ms_max = 0
_domain_events: dict[str, int] = {}


def record_http_request(status_code: int, duration_ms: int) -> None:
    global _http_duration_ms_max, _http_duration_ms_sum, _http_requests_total
    status_class = f"{status_code // 100}xx"
    with _lock:
        _http_requests_total += 1
        _http_status_classes[status_class] = _http_status_classes.get(status_class, 0) + 1
        _http_duration_ms_sum += duration_ms
        _http_duration_ms_max = max(_http_duration_ms_max, duration_ms)


def record_domain_event(name: str) -> None:
    with _lock:
        _domain_events[name] = _domain_events.get(name, 0) + 1


def metrics_snapshot() -> dict[str, Any]:
    with _lock:
        average_ms = (
            round(_http_duration_ms_sum / _http_requests_total, 2)
            if _http_requests_total
            else 0
        )
        return {
            "uptime_seconds": round(monotonic() - _started_at, 2),
            "http": {
                "requests_total": _http_requests_total,
                "status_classes": dict(_http_status_classes),
                "duration_ms_avg": average_ms,
                "duration_ms_max": _http_duration_ms_max,
            },
            "domain_events": dict(_domain_events),
        }
