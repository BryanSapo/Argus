# Argus

**Reusable LLM-powered infrastructure monitoring agent + AI incident simulator.**

Argus is a full-stack observability and incident simulation platform designed for AI/ML infrastructure teams. It pairs a tick-based **AI Infrastructure Incident Simulator (AIIS)** with a pluggable **LLM-powered monitoring agent** to create a closed-loop system where synthetic infrastructure failures are generated, observed, and diagnosed — all within a single application.

### Why Argus?

Real production systems are difficult to break on purpose: failures are hard to reproduce, labeled incident datasets are scarce, and evaluating AI-based diagnosis tools requires realistic yet controllable signals. Argus solves this by providing a deterministic simulation environment that produces correlated **metrics**, **structured logs**, and **discrete events** — the same three pillars of observability used in production — and then feeds them into an LLM agent that returns structured root-cause analysis.

### What It Does

| Component               | Role                                                                                                                                                                                                                                                                                                                                                                                 |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **AIIS — Simulator**    | A tick-driven engine that generates synthetic time-series metrics (latency p50/p95, throughput, error rate, queue depth, CPU/memory utilization), rule-based structured logs (INFO / WARN / ERROR), and discrete system events (deployments, traffic spikes, dependency outages, recoveries). Users can tune system parameters in real time and inject predefined failure scenarios. |
| **Argus Agent**         | A reusable, framework-agnostic monitoring agent. It consumes observability data through a pluggable `DataSource` abstraction, builds a compact context payload, sends it to any LLM backend via a pluggable `LLMClient` interface, and returns a structured `DiagnosisReport` with severity, root cause, supporting evidence, recommendations, and affected components.              |
| **Streamlit Dashboard** | A single-page interactive UI that hosts the control panel, live Plotly charts, streaming logs, event timeline, and an AI diagnosis panel — all updating in real time.                                                                                                                                                                                                                |
| **FastAPI REST API**    | A lightweight API that exposes the simulation state (`/api/metrics`, `/api/logs`, `/api/events`, `/api/summary`, `/api/snapshot`) for external consumers, scripts, or LLM agents running out-of-process.                                                                                                                                                                             |

### Target Users

- **AI / ML engineers** building or evaluating AI-driven monitoring and alerting systems
- **SRE / reliability engineers** prototyping incident response automation
- **Backend / infrastructure engineers** testing observability pipelines
- **Researchers** working on agentic AI, anomaly detection, or root-cause analysis

---

## Tech Stack

| Layer           | Technology                                                      | Purpose                                                                         |
| --------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Language        | **Python 3.12+**                                                | Core runtime                                                                    |
| Package Manager | **[uv](https://docs.astral.sh/uv/)**                            | Fast dependency resolution and virtualenv management                            |
| Web UI          | **[Streamlit](https://streamlit.io/)**                          | Interactive dashboard with real-time controls and auto-rerun loop               |
| Charting        | **[Plotly](https://plotly.com/python/)**                        | Interactive time-series visualizations (latency, throughput, error rate, queue) |
| REST API        | **[FastAPI](https://fastapi.tiangolo.com/)**                    | Async REST endpoints for LLM agent / programmatic access                        |
| ASGI Server     | **[Uvicorn](https://www.uvicorn.org/)**                         | Serves the FastAPI app in a background thread                                   |
| Data Modeling   | **[Pydantic v2](https://docs.pydantic.dev/)**                   | Schema definitions, validation, and JSON serialization for all data records     |
| Data Handling   | **[Pandas](https://pandas.pydata.org/)**                        | DataFrame operations for metric history                                         |
| Simulation Math | **[NumPy](https://numpy.org/)**                                 | Gaussian noise, metric computation                                              |
| HTTP Client     | **[HTTPX](https://www.python-httpx.org/)**                      | LLM API calls (OpenRouter) and data source fetching                             |
| Config          | **[python-dotenv](https://github.com/theskumar/python-dotenv)** | `.env` file support for API keys                                                |
| LLM Provider    | **[OpenRouter](https://openrouter.ai/)**                        | Access to hosted LLM models (default: `nvidia/nemotron-3-super-120b-a12b:free`) |

---

## Features

- **Real-time simulation** of infrastructure metrics (latency, throughput, error rate, queue length, CPU/memory)
- **Structured log generation** (INFO / WARN / ERROR) correlated with metric anomalies
- **Discrete event system** (deployments, traffic spikes, dependency failures, recoveries)
- **4 predefined failure scenarios**: deployment regression, traffic spike, dependency failure, resource exhaustion
- **Interactive Streamlit dashboard** with live charts, log panel, and event timeline
- **REST API** (FastAPI) for programmatic / LLM agent access
- **AI diagnosis** via OpenRouter LLM — ask questions about system health and get structured reports
- **Pluggable architecture** — use the Argus agent with any data source or LLM backend

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              Streamlit UI (app.py)           │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ Controls │ │ Charts   │ │ Logs/Events  │ │
│  └──────────┘ └──────────┘ └──────────────┘ │
│                     │                        │
│         ┌───────────┴───────────┐            │
│         │   Simulation Engine   │            │
│         │  (aiis/engine.py)     │            │
│         ├───────────────────────┤            │
│         │ Metric  │ Log  │Event│            │
│         │ Gen.    │ Gen. │Gen. │            │
│         └───────────────────────┘            │
│                     │                        │
│              ┌──────┴──────┐                 │
│              │ State Store │                 │
│              └──────┬──────┘                 │
│                     │                        │
│    ┌────────────────┼────────────────┐       │
│    │ FastAPI API     │  Argus Agent  │       │
│    │ (aiis/api.py)   │ (argus/)      │       │
│    └────────────────┴────────────────┘       │
└─────────────────────────────────────────────┘
```

---

## Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** (recommended package manager)
- **OpenRouter API key** (optional, for AI diagnosis feature)

---

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/Argus.git
cd Argus

# Install dependencies with uv
uv sync
```

---

## Running

### Start the app

```bash
uv run streamlit run app.py
```

This launches the Streamlit dashboard on `http://localhost:8501` and automatically starts the FastAPI REST API on port `8502`.

### Alternative: use the entry point

```bash
uv run python main.py
```

---

## Usage

### Streamlit Dashboard

1. Open `http://localhost:8501` in your browser.
2. Use the **sidebar controls** to adjust simulation parameters:
    - Request Rate (QPS)
    - Latency Multiplier
    - Error Rate Injection
    - Queue Processing Speed
    - CPU / Memory Pressure
3. Click **▶️ Run** to start the simulation, **⏸ Pause** to stop, **🔄 Reset** to clear all state.
4. **Inject failure scenarios** from the sidebar dropdown:
    - Deployment Regression
    - Traffic Spike
    - Dependency Failure
    - Resource Exhaustion
5. **Deploy a new model version** to trigger a deployment event + regression scenario.
6. View real-time **metrics charts**, **streaming logs**, and **event timeline** in the main area.

### AI Diagnosis

1. Set your OpenRouter API key via the `OPENROUTER_API_KEY` environment variable or enter it in the UI.
2. Click **🔍 Run Diagnosis** to get a structured report with severity, root cause, evidence, and recommendations.
3. Use the **💬 Ask** text box to ask free-form questions about the current system state.

### REST API

The FastAPI server runs on `http://localhost:8502` with interactive docs at `/docs`.

| Endpoint                           | Description                                        |
| ---------------------------------- | -------------------------------------------------- |
| `GET /api/health`                  | System health & tick count                         |
| `GET /api/metrics?last=N`          | Recent metric records                              |
| `GET /api/logs?last=N&level=LEVEL` | Recent logs (optional level filter)                |
| `GET /api/events?last=N`           | Recent system events                               |
| `GET /api/snapshot`                | Full simulation snapshot (metrics + logs + events) |
| `GET /api/summary?last=N`          | Compact summary designed for LLM context windows   |

---

## Using the Argus Agent Standalone

The `argus` package is a reusable monitoring agent you can integrate into any project:

```python
from argus import MonitoringAgent, HTTPDataSource, OpenRouterClient

# Point at any API that serves metrics/logs/events
agent = MonitoringAgent(
    data_source=HTTPDataSource("http://localhost:8502/api"),
    llm=OpenRouterClient(api_key="sk-or-..."),
)

report = agent.analyze()
print(report.severity)    # "critical" | "warning" | "healthy"
print(report.summary)
print(report.root_cause)
```

Or use `DictDataSource` for in-process data:

```python
from argus import MonitoringAgent, DictDataSource, OpenRouterClient

source = DictDataSource(
    metrics=[{"latency_p50": 450, "error_rate": 0.32}],
    logs=[{"level": "ERROR", "message": "OOM killed"}],
    events=[{"event_type": "deployment", "description": "v2.0 deployed"}],
)

agent = MonitoringAgent(data_source=source, llm=OpenRouterClient(api_key="sk-or-..."))
report = agent.analyze()
```

---

## Environment Variables

| Variable             | Description                        | Required                   |
| -------------------- | ---------------------------------- | -------------------------- |
| `OPENROUTER_API_KEY` | API key for OpenRouter LLM service | No (only for AI diagnosis) |

---

## Project Structure

```
Argus/
├── app.py              # Streamlit UI + FastAPI bootstrap
├── main.py             # CLI entry point
├── pyproject.toml      # Project metadata & dependencies
├── aiis/               # AI Infrastructure Incident Simulator
│   ├── api.py          # FastAPI REST endpoints
│   ├── engine.py       # Simulation engine (tick loop)
│   ├── event_generator.py  # Scenario injection & event lifecycle
│   ├── log_generator.py    # Rule-based log generation
│   ├── metric_generator.py # Time-series metric generation
│   ├── models.py       # Pydantic data models
│   ├── shared.py       # Shared singleton state
│   └── state.py        # Central state store
└── argus/              # Reusable monitoring agent
    ├── agent.py        # MonitoringAgent + DiagnosisReport
    ├── data_source.py  # DataSource abstraction (HTTP, Dict)
    └── llm.py          # LLM client abstraction (OpenRouter)
```

---

## License

MIT
