"""Pydantic models for AIIS data structures."""

from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class LogLevel(str, enum.Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class ScenarioType(str, enum.Enum):
    DEPLOYMENT_REGRESSION = "deployment_regression"
    TRAFFIC_SPIKE = "traffic_spike"
    DEPENDENCY_FAILURE = "dependency_failure"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


# ---------------------------------------------------------------------------
# Data records
# ---------------------------------------------------------------------------

class MetricRecord(BaseModel):
    timestamp: datetime
    latency_p50: float
    latency_p95: float
    throughput: float
    error_rate: float
    queue_length: float
    cpu_usage: float
    memory_usage: float


class LogRecord(BaseModel):
    timestamp: datetime
    level: LogLevel
    message: str
    source: str = "simulator"


class EventRecord(BaseModel):
    timestamp: datetime
    event_type: str
    description: str


# ---------------------------------------------------------------------------
# Simulation parameters (controllable by user)
# ---------------------------------------------------------------------------

class SimulationParams(BaseModel):
    qps: float = Field(default=100.0, ge=0, le=10000, description="Requests per second")
    latency_multiplier: float = Field(default=1.0, ge=0.1, le=20.0)
    error_rate_injection: float = Field(default=0.0, ge=0.0, le=1.0)
    queue_speed: float = Field(default=1.0, ge=0.1, le=5.0, description="Queue processing speed multiplier")
    cpu_pressure: float = Field(default=0.3, ge=0.0, le=1.0)
    memory_pressure: float = Field(default=0.3, ge=0.0, le=1.0)
    model_version: str = Field(default="v1.0")


# ---------------------------------------------------------------------------
# Snapshot export
# ---------------------------------------------------------------------------

class SimulationSnapshot(BaseModel):
    metrics: list[MetricRecord]
    logs: list[LogRecord]
    events: list[EventRecord]
