"""FastAPI REST API for LLM agent consumption."""

from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .models import LogLevel
from .shared import get_shared_state

app = FastAPI(
    title="AIIS API",
    description="AI Infrastructure Incident Simulator - REST API for LLM agents",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    state = get_shared_state()
    return {
        "status": "ok",
        "tick": state.tick,
        "model_version": state.params.model_version,
        "active_effects": list(state.active_effects.keys()),
    }


@app.get("/api/metrics")
def get_metrics(last: int = Query(default=50, ge=1, le=5000)):
    """Return the most recent N metric records."""
    state = get_shared_state()
    records = state.metrics[-last:]
    return {"count": len(records), "metrics": [r.model_dump(mode="json") for r in records]}


@app.get("/api/logs")
def get_logs(
    last: int = Query(default=50, ge=1, le=5000),
    level: LogLevel | None = Query(default=None),
):
    """Return the most recent N log records, optionally filtered by level."""
    state = get_shared_state()
    logs = state.logs[-last:]
    if level is not None:
        logs = [l for l in logs if l.level == level]
    return {"count": len(logs), "logs": [l.model_dump(mode="json") for l in logs]}


@app.get("/api/events")
def get_events(last: int = Query(default=30, ge=1, le=5000)):
    """Return the most recent N event records."""
    state = get_shared_state()
    events = state.events[-last:]
    return {"count": len(events), "events": [e.model_dump(mode="json") for e in events]}


@app.get("/api/snapshot")
def get_snapshot():
    """Full simulation snapshot -- metrics + logs + events. Useful as LLM context."""
    state = get_shared_state()
    return {
        "tick": state.tick,
        "params": state.params.model_dump(),
        "active_effects": dict(state.active_effects),
        "metrics": [m.model_dump(mode="json") for m in state.metrics],
        "logs": [l.model_dump(mode="json") for l in state.logs],
        "events": [e.model_dump(mode="json") for e in state.events],
    }


@app.get("/api/summary")
def get_summary(last: int = Query(default=20, ge=1, le=500)):
    """Compact summary designed for LLM context windows.

    Returns only the last N ticks worth of data plus current system status.
    """
    state = get_shared_state()
    recent_metrics = state.metrics[-last:]
    recent_logs = state.logs[-last * 3 :]  # logs are denser
    recent_events = state.events[-last:]

    error_logs = [l for l in recent_logs if l.level == LogLevel.ERROR]
    warn_logs = [l for l in recent_logs if l.level == LogLevel.WARN]

    avg_latency = 0.0
    avg_error_rate = 0.0
    avg_throughput = 0.0
    if recent_metrics:
        avg_latency = sum(m.latency_p50 for m in recent_metrics) / len(recent_metrics)
        avg_error_rate = sum(m.error_rate for m in recent_metrics) / len(recent_metrics)
        avg_throughput = sum(m.throughput for m in recent_metrics) / len(recent_metrics)

    return {
        "tick": state.tick,
        "model_version": state.params.model_version,
        "active_effects": dict(state.active_effects),
        "window_size": last,
        "stats": {
            "avg_latency_p50_ms": round(avg_latency, 2),
            "avg_error_rate": round(avg_error_rate, 4),
            "avg_throughput_qps": round(avg_throughput, 2),
            "error_log_count": len(error_logs),
            "warn_log_count": len(warn_logs),
            "event_count": len(recent_events),
        },
        "recent_errors": [l.model_dump(mode="json") for l in error_logs[-10:]],
        "recent_events": [e.model_dump(mode="json") for e in recent_events[-10:]],
    }
