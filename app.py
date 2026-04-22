"""AIIS – AI Infrastructure Incident Simulator (Streamlit UI)."""

from __future__ import annotations

import json
import os
import threading
import time

import httpx
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
import plotly.graph_objects as go
import streamlit as st
import uvicorn

from aiis.api import app as fastapi_app
from aiis.engine import export_snapshot, tick
from aiis.event_generator import emit_deployment_event, inject_scenario
from aiis.models import LogLevel, ScenarioType, SimulationParams
from aiis.shared import get_shared_state, set_shared_state
from aiis.state import StateStore
from argus import MonitoringAgent, OpenRouterClient
from argus.data_source import DataSource

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Argus",
    page_icon="🔥",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session state initialisation – use shared singleton
# ---------------------------------------------------------------------------
if "state" not in st.session_state:
    st.session_state.state = get_shared_state()
if "running" not in st.session_state:
    st.session_state.running = False
if "speed" not in st.session_state:
    st.session_state.speed = 0.5  # seconds between ticks

state: StateStore = st.session_state.state
set_shared_state(state)

# ---------------------------------------------------------------------------
# Start FastAPI in a background thread (once per Streamlit process)
# ---------------------------------------------------------------------------
API_PORT = 8502

if "api_started" not in st.session_state:

    def _run_api() -> None:
        uvicorn.run(fastapi_app, host="0.0.0.0", port=API_PORT, log_level="warning")

    threading.Thread(target=_run_api, daemon=True).start()
    st.session_state.api_started = True

# ---------------------------------------------------------------------------
# Sidebar – Control Panel
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Control Panel")

    st.subheader("System Parameters")
    qps = st.slider("Request Rate (QPS)", 10, 5000, int(state.params.qps), step=10)
    latency_mult = st.slider("Latency Multiplier", 0.1, 10.0, state.params.latency_multiplier, step=0.1)
    err_inject = st.slider("Error Rate Injection", 0.0, 1.0, state.params.error_rate_injection, step=0.01)
    queue_speed = st.slider("Queue Processing Speed", 0.1, 5.0, state.params.queue_speed, step=0.1)
    cpu_pressure = st.slider("CPU Pressure", 0.0, 1.0, state.params.cpu_pressure, step=0.05)
    mem_pressure = st.slider("Memory Pressure", 0.0, 1.0, state.params.memory_pressure, step=0.05)

    # Update params
    state.params = SimulationParams(
        qps=qps,
        latency_multiplier=latency_mult,
        error_rate_injection=err_inject,
        queue_speed=queue_speed,
        cpu_pressure=cpu_pressure,
        memory_pressure=mem_pressure,
        model_version=state.params.model_version,
    )

    st.divider()
    st.subheader("Scenario Injection")
    scenario_choice = st.selectbox(
        "Select Scenario",
        options=[s.value for s in ScenarioType],
        format_func=lambda x: x.replace("_", " ").title(),
    )
    if st.button("🔥 Inject Scenario"):
        inject_scenario(state, ScenarioType(scenario_choice))

    st.divider()
    st.subheader("Deployment")
    new_version = st.text_input("New Model Version", value="v2.0")
    if st.button("🚀 Deploy New Version"):
        emit_deployment_event(state, new_version)
        inject_scenario(state, ScenarioType.DEPLOYMENT_REGRESSION)

    st.divider()
    st.subheader("Simulation Control")
    speed = st.slider("Tick Interval (seconds)", 0.1, 2.0, st.session_state.speed, step=0.1)
    st.session_state.speed = speed

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("▶️ Run", use_container_width=True):
            st.session_state.running = True
    with col_b:
        if st.button("⏸ Pause", use_container_width=True):
            st.session_state.running = False
    with col_c:
        if st.button("🔄 Reset", use_container_width=True):
            state.reset()
            st.session_state.running = False
            st.rerun()

    # Active effects display
    if state.active_effects:
        st.divider()
        st.subheader("Active Effects")
        for eff, remaining in state.active_effects.items():
            st.warning(f"**{eff.replace('_', ' ').title()}** — {remaining} ticks remaining")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("Argus - Infrastructure Incident Simulator")
st.caption(
    f"Tick: {state.tick}  |  Model: {state.params.model_version}  "
    f"|  Status: {'🟢 Running' if st.session_state.running else '🔴 Paused'}  "
    f"|  API: http://localhost:{API_PORT}/docs"
)

# ---------------------------------------------------------------------------
# Helper: run a single tick
# ---------------------------------------------------------------------------
if st.session_state.running:
    tick(state)

# ---------------------------------------------------------------------------
# Metrics Dashboard
# ---------------------------------------------------------------------------
st.subheader("📊 Metrics Dashboard")

if len(state.metrics) > 1:
    df = pd.DataFrame([m.model_dump() for m in state.metrics])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["latency_p50"], name="p50", line=dict(color="#636EFA")))
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["latency_p95"], name="p95", line=dict(color="#EF553B")))
        fig.update_layout(title="Latency (ms)", height=280, margin=dict(t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["throughput"], name="QPS", fill="tozeroy", line=dict(color="#00CC96")))
        fig.update_layout(title="Throughput (QPS)", height=280, margin=dict(t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col3:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["error_rate"], name="Error Rate", fill="tozeroy", line=dict(color="#EF553B")))
        fig.update_layout(title="Error Rate", height=280, margin=dict(t=30, b=20), yaxis=dict(range=[0, 1]))
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["queue_length"], name="Queue", fill="tozeroy", line=dict(color="#AB63FA")))
        fig.update_layout(title="Queue Length", height=280, margin=dict(t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Press ▶️ Run in the sidebar to start the simulation.")

# ---------------------------------------------------------------------------
# Logs & Events columns
# ---------------------------------------------------------------------------
log_col, event_col = st.columns(2)

with log_col:
    st.subheader("📝 Logs")
    log_filter = st.multiselect(
        "Filter by level",
        options=[l.value for l in LogLevel],
        default=[l.value for l in LogLevel],
    )
    recent_logs = state.recent_logs(80)
    filtered = [l for l in recent_logs if l.level.value in log_filter]

    with st.container(height=400):
        if filtered:
            for log in reversed(filtered[-30:]):
                colour = {"INFO": "blue", "WARN": "orange", "ERROR": "red"}[log.level.value]
                st.markdown(
                    f"<span style='color:{colour};font-weight:600'>[{log.level.value}]</span> "
                    f"<span style='color:gray;font-size:0.85em'>{log.timestamp.strftime('%H:%M:%S')} · {log.source}</span><br/>"
                    f"{log.message}",
                    unsafe_allow_html=True,
                )
                st.markdown("---")
        else:
            st.caption("No logs yet.")

with event_col:
    st.subheader("🗓️ Event Timeline")
    recent_events = state.recent_events(30)
    with st.container(height=400):
        if recent_events:
            for evt in reversed(recent_events):
                icon = {
                    "deployment": "🚀",
                    "deployment_regression": "⚠️",
                    "traffic_spike": "📈",
                    "dependency_failure": "🔌",
                    "resource_exhaustion": "💾",
                    "recovery": "✅",
                }.get(evt.event_type, "📌")
                st.markdown(
                    f"{icon} **{evt.event_type.replace('_', ' ').title()}** "
                    f"<span style='color:gray;font-size:0.85em'>({evt.timestamp.strftime('%H:%M:%S')})</span><br/>"
                    f"{evt.description}",
                    unsafe_allow_html=True,
                )
                st.markdown("---")
        else:
            st.caption("No events yet.")

# ---------------------------------------------------------------------------
# AI Diagnosis (Argus Agent)
# ---------------------------------------------------------------------------
st.divider()
st.subheader("🤖 Argus AI Diagnosis")

api_key = os.environ.get("OPENROUTER_API_KEY", "")
if not api_key:
    api_key = st.text_input("OpenRouter API Key", type="password", help="Set OPENROUTER_API_KEY env var or enter here")

if api_key:
    # Build a DataSource that reads directly from the in-process StateStore
    class _StateStoreSource(DataSource):
        """Reads from the live StateStore — no HTTP hop needed."""

        def fetch_metrics(self, last: int = 20) -> list[dict]:
            return [m.model_dump(mode="json") for m in state.metrics[-last:]]

        def fetch_logs(self, last: int = 60, level: str | None = None) -> list[dict]:
            logs = state.logs[-last:]
            if level:
                logs = [l for l in logs if l.level.value == level]
            return [l.model_dump(mode="json") for l in logs]

        def fetch_events(self, last: int = 20) -> list[dict]:
            return [e.model_dump(mode="json") for e in state.events[-last:]]

        def fetch_summary(self) -> dict:
            recent_m = state.metrics[-20:]
            error_logs = [l for l in state.logs[-60:] if l.level.value == "ERROR"]
            warn_logs = [l for l in state.logs[-60:] if l.level.value == "WARN"]
            recent_events = state.events[-20:]
            avg_lat = sum(m.latency_p50 for m in recent_m) / len(recent_m) if recent_m else 0
            avg_err = sum(m.error_rate for m in recent_m) / len(recent_m) if recent_m else 0
            avg_thr = sum(m.throughput for m in recent_m) / len(recent_m) if recent_m else 0
            return {
                "tick": state.tick,
                "active_effects": dict(state.active_effects),
                "stats": {
                    "avg_latency_p50_ms": round(avg_lat, 2),
                    "avg_error_rate": round(avg_err, 4),
                    "avg_throughput_qps": round(avg_thr, 2),
                    "error_log_count": len(error_logs),
                    "warn_log_count": len(warn_logs),
                    "event_count": len(recent_events),
                },
                "recent_errors": [l.model_dump(mode="json") for l in error_logs[-10:]],
                "recent_events": [e.model_dump(mode="json") for e in recent_events[-10:]],
            }

    if "agent" not in st.session_state or st.session_state.get("agent_api_key") != api_key:
        llm = OpenRouterClient(api_key=api_key)
        st.session_state.agent = MonitoringAgent(data_source=_StateStoreSource(), llm=llm)
        st.session_state.agent_api_key = api_key

    agent: MonitoringAgent = st.session_state.agent

    diag_col1, diag_col2 = st.columns([1, 2])

    with diag_col1:
        if st.button("🔍 Run Diagnosis", use_container_width=True, disabled=len(state.metrics) < 2):
            with st.spinner("Analyzing system state..."):
                try:
                    report = agent.analyze()
                    st.session_state.last_report = report
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401:
                        st.error("Invalid API key. Please check your OpenRouter API key and try again.")
                        del st.session_state["agent"]
                    else:
                        st.error(f"API error: {e.response.status_code} — {e.response.text[:200]}")
                except Exception as e:
                    st.error(f"Error: {e}")

        user_question = st.text_area("Ask about the system", placeholder="Why is latency spiking?")
        if st.button("💬 Ask", use_container_width=True) and user_question:
            with st.spinner("Thinking..."):
                try:
                    answer = agent.analyze_with_question(user_question)
                    st.session_state.last_answer = answer
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401:
                        st.error("Invalid API key.")
                        del st.session_state["agent"]
                    else:
                        st.error(f"API error: {e.response.status_code}")
                except Exception as e:
                    st.error(f"Error: {e}")

    with diag_col2:
        if "last_report" in st.session_state:
            report = st.session_state.last_report
            severity_colors = {"critical": "🔴", "warning": "🟡", "healthy": "🟢"}
            icon = severity_colors.get(report.severity, "⚪")

            st.markdown(f"### {icon} Severity: **{report.severity.upper()}**")
            st.markdown(f"**Summary:** {report.summary}")
            st.markdown(f"**Root Cause:** {report.root_cause}")

            if report.evidence:
                with st.expander("Evidence", expanded=True):
                    for e in report.evidence:
                        st.markdown(f"- {e}")

            if report.recommendations:
                with st.expander("Recommendations", expanded=True):
                    for i, r in enumerate(report.recommendations, 1):
                        st.markdown(f"{i}. {r}")

            if report.affected_components:
                st.markdown(f"**Affected:** {', '.join(report.affected_components)}")

        if "last_answer" in st.session_state:
            st.divider()
            st.markdown("**Agent Response:**")
            st.markdown(st.session_state.last_answer)
else:
    st.info("Enter your OpenRouter API key to enable AI diagnosis.")

# ---------------------------------------------------------------------------
# Data Export
# ---------------------------------------------------------------------------
with st.expander("📦 Export Simulation Data (JSON)"):
    if st.button("Generate Snapshot"):
        snapshot = export_snapshot(state)
        json_str = snapshot.model_dump_json(indent=2)
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name="aiis_snapshot.json",
            mime="application/json",
        )
        st.json(json.loads(json_str)["metrics"][:3] if state.metrics else [])

# ---------------------------------------------------------------------------
# Auto-rerun loop
# ---------------------------------------------------------------------------
if st.session_state.running:
    time.sleep(st.session_state.speed)
    st.rerun()
