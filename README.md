# InsightOps AI — Autonomous Market Intelligence & Competitor War-Room Backend

InsightOps AI is an autonomous, multi-agent market intelligence platform built with **FastAPI** and **LangGraph**. It continually extracts, analyzes, verifies, and reports competitive market movements (pricing shifts, feature deprecations, SLA changes) using stateful multi-agent workflows with human-in-the-loop (HITL) breakpoints.

*Note: The React frontend application was provided separately and integrated with this backend API without modifying frontend component contracts or response shapes.*

---

## 📊 Feature & Implementation Status

| Component | Status | Details |
| :--- | :--- | :--- |
| **Multi-Agent Workflow** | **Implemented** | Stateful cyclical graph built with LangGraph (`Supervisor` -> `Researcher` -> `Analyst` -> `Fact-Checker` -> `Human Review` / `Writer`). |
| **Human-in-the-Loop (HITL)** | **Implemented** | Pauses execution via `langgraph.types.interrupt()`. Resumes cleanly with `Command(resume={"approved": ..., "feedback": ...})`. |
| **Persistent Checkpointer** | **Implemented** | State persistence across server restarts using `SqliteSaver` (`checkpointer.db`). |
| **SSRF Protection** | **Implemented** | Restricts target URLs to exact domain/subdomain and blocks private, loopback, link-local, or reserved IP ranges. |
| **DuckDB Snapshot Diffing** | **Implemented** | Quantitative FULL OUTER JOIN diffing of parsed snapshot records using DuckDB SQL; computes numeric `pct_change` and derives threat severity. |
| **Adversarial Fact-Checking** | **Implemented** | Programmatically verifies supporting quotes and numerical evidence against raw scraped text; anti-dilution confidence score (0.0 - 1.0). |
| **Prompt-Injection Defense** | **Implemented** | Strips hidden DOM text, zero-width characters, and instruction override tags; delimits scraped text in system-instructed blocks. |
| **Auth & RBAC** | **Implemented** | `pbkdf2_sha256` password hashing, JWT authentication with live DB user status verification, public signup restricted to `Viewer`, and admin-only user endpoints. |
| **Rate Limiting** | **Implemented** | SlowAPI rate limits on auth and agent endpoints with client IP resolution. |
| **Scraper Engine** | **Demo-mode** | Dual-mode: `DEMO` mode with versioned JSON fixtures (`v1`/`v2`) and `LIVE` mode with `robots.txt` compliance, User-Agent, and redirect hop validation. |
| **LLM Provider & Cost Control**| **Demo-mode** | Abstract `LLMClient` returning labeled `MockLLMClient` by default, with configurable OpenAI provider support, per-run token budgets, and content hash change detection (0 LLM calls when unchanged). |
| **Automated Scheduler** | **Implemented** | APScheduler background service enforcing competitor `scraping_cadence` (Hourly, Daily, Weekly) with worker thread dispatching. |
| **Telemetry & Analytics** | **Implemented** | Database metrics and in-memory `TTLCache` hit/miss telemetry with single `GROUP BY` query optimization. |
| **Distributed SSE Streaming** | **Roadmap** | Single-worker in-memory SSE stream buffer active; Redis Pub/Sub recommended for multi-worker scale. |

---

## 🏗 System Architecture

```
                                    +-----------------------+
                                    |   Supervisor Node     |
                                    +-----------+-----------+
                                                |
                                                v
                                    +-----------------------+
                                    |    Researcher Node    | <----------------------+
                                    +-----------+-----------+                        |
                                                |                                    |
                                                v                                    | (Self-Correction Loop)
                                    +-----------------------+                        | (score < 0.85 & rev < 2)
                                    |  Quantitative Analyst |                        |
                                    +-----------+-----------+                        |
                                                |                                    |
                                                v                                    |
                                    +-----------------------+                        |
                                    | Adversarial Checker   | -----------------------+
                                    +-----------+-----------+
                                                |
                          +---------------------+---------------------+
                          | (hitl_required = True)                    | (Confidence >= 0.85 & Low Threat)
                          v                                           v
             +-------------------------+                 +-------------------------+
             |   Human Review (HITL)   |                 |     Executive Writer    |
             |  [interrupt() paused]   |                 +------------+------------+
             +------------+------------+                              |
                          |                                           v
            +-------------+-------------+                          [ END ]
            |                           |
  (approved = True)            (approved = False)
            |                           |
            v                           v
  +-------------------+              [ END ]
  |  Executive Writer |          (status: "rejected")
  +---------+---------+          (no report created)
            |
            v
         [ END ]
```

---

## 📁 Repository Layout

```
insightops-ai/
├── .github/workflows/
│   └── test.yml                 # GitHub Actions CI workflow (Pytest on clean checkout)
├── backend/
│   ├── app/
│   │   ├── api/                 # FastAPI router endpoints (auth, agent, competitors, reports, analytics)
│   │   ├── core/                # Security, URL validator (SSRF), cache, rate limiter
│   │   ├── db/                  # Database models, async engine, seed script
│   │   ├── inference/           # LangGraph workflow, agents (researcher, analyst, fact_checker, writer, supervisor), LLM client
│   │   ├── ingestion/           # Scraper engine (demo fixtures & live), parser
│   │   ├── config.py            # Pydantic Settings configuration
│   │   ├── main.py              # FastAPI main application
│   │   └── scheduler.py         # APScheduler background cadence runner
│   ├── tests/                   # Pytest unit & integration test suite
│   ├── .dockerignore
│   ├── Dockerfile               # Multi-stage production container build (non-root user)
│   ├── pytest.ini
│   └── requirements.txt         # Pinned python dependencies
├── frontend/                    # Pre-built React frontend application
├── docker-compose.yml           # Docker Compose orchestrator (persistent /app/data volume)
├── .gitignore
└── README.md
```

---

## 🚀 Quickstart & Setup

### Prerequisites
* **Python 3.11+**
* **Docker & Docker Compose** (Optional for containerized run)

### 1. Environment Variables Configuration

The backend relies on `pydantic-settings` to load configuration from `.env`. Copy `.env.example` to `.env`:

```bash
cd backend
cp .env.example .env
```

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DEMO_MODE` | `false` | Enables seed credentials and fixture fallbacks when set to `true`. |
| `SCRAPER_MODE` | `demo` | `demo` uses versioned JSON fixtures; `live` executes HTTP scraping. |
| `LLM_PROVIDER` | `mock` | `mock` uses labeled MockLLMClient; `openai` uses OpenAI API. |
| `SECRET_KEY` | *(Required)* | JWT signing key. Must be explicitly set outside demo mode. |
| `DATABASE_URL` | `sqlite+aiosqlite:///./insightops.db` | Async SQLAlchemy database URL. |
| `SQLITE_CHECKPOINT_DB` | `./checkpointer.db` | SQLite database for LangGraph state persistence. |
| `ALLOWED_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | Configured CORS allowed origins list. |

### 2. Local Environment Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI development server
uvicorn app.main:app --reload --port 8000
```

### 3. Running with Docker Compose

```bash
# From project root directory
docker-compose up --build
```
The backend API will be available at `http://localhost:8000`. Interactive API Documentation is hosted at `http://localhost:8000/docs`.

---

## 🎮 Demo Workflow Walkthrough (HITL & Change Detection)

1. **Login**:
   - `POST /api/v1/auth/login` with `username="analyst@insightops.ai"`, `password="analyst123"` to obtain JWT bearer token.
2. **Initiate Agent Run**:
   - `POST /api/v1/agent/run` with `{"competitor_id": "<ID>", "target_url": "https://saasify.cloud/pricing"}`.
   - On the initial run, the Researcher captures `v1` as the baseline.
3. **HITL Review Inbox**:
   - On subsequent runs (loading `v2` fixture with a 20% price cut anomaly), threat severity triggers a HITL interrupt.
   - `GET /api/v1/agent/pending` lists paused runs with status `awaiting_hitl`.
4. **Resume Run**:
   - `POST /api/v1/agent/resume/{thread_id}` with `{"approved": true, "feedback": "Approved by Lead Analyst"}` to resume graph execution and generate executive report.
5. **Change Detection**:
   - Running the agent again for an unchanged target detects identical `content_hash` and short-circuits execution with status `unchanged` (0 LLM calls).

---

## 🧪 Testing

The backend includes a comprehensive pytest suite covering auth RBAC, SSRF protection, price parsing, DuckDB snapshot diffing, fact-checker evidence verification, cache telemetry, scheduler cadence, and end-to-end graph interrupts/resumes.

```bash
cd backend
pytest -v
```

---

## 🔑 Key API Endpoints

### Authentication & Users
* `POST /api/v1/auth/login`: Authenticate and obtain JWT bearer token.
* `POST /api/v1/auth/register`: Public user signup (always assigns `Viewer` role).
* `POST /api/v1/auth/users`: Admin-only endpoint to create users with explicit roles (`Admin`, `Analyst`, `Viewer`).
* `PUT /api/v1/auth/users/{user_id}/role`: Admin-only endpoint to promote user roles.

### Agent Workflow & HITL
* `POST /api/v1/agent/run`: Trigger multi-agent competitive analysis. Accepts `competitor_id`, `target_url`, `user_query`.
* `POST /api/v1/agent/stream-token/{thread_id}`: Issue short-lived (60s) stream token for SSE authentication.
* `GET /api/v1/agent/stream/{job_id}?token=...`: Real-time Server-Sent Events (SSE) telemetry log stream.
* `GET /api/v1/agent/pending`: Inbox returning paused agent runs awaiting Human-in-the-Loop review.
* `POST /api/v1/agent/resume/{thread_id}`: Resume paused graph run with `approved: true/false` and analyst feedback.

### Analytics & System Health
* `GET /api/v1/analytics/overview`: Dynamic metrics summary and competitor anomaly bar chart.
* `GET /api/v1/health`: System health status (DB connection, cache telemetry, LLM provider, scheduler state).

---

## ⚠️ Known Limitations

1. **In-Memory SSE Stream Buffer**: Real-time event buffers are stored in-memory per process with a thread-safe lock. In multi-worker production deployments behind a load balancer, event streaming should use Redis Pub/Sub.
2. **SQLite Concurrency & Volume Persistence**: SQLite operates with single-writer lock semantics. Docker Compose maps `/app/data` to a persistent named volume (`insightops-data`) to preserve database and checkpointer state across container restarts.
