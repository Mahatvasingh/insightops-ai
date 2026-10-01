# InsightOps AI — Autonomous Market Intelligence & Competitor War-Room Backend

InsightOps AI is an autonomous, multi-agent market intelligence platform built with **FastAPI** and **LangGraph**. It continually extracts, analyzes, verifies, and reports competitive market movements (pricing shifts, feature deprecations, SLA changes) using stateful multi-agent workflows with human-in-the-loop (HITL) breakpoints.

---

## 📊 Feature & Implementation Status

| Component | Status | Details |
| :--- | :--- | :--- |
| **Multi-Agent Workflow** | **Implemented** | Stateful cyclical graph built with LangGraph (`Supervisor` -> `Researcher` -> `Analyst` -> `Fact-Checker` -> `Human Review` / `Writer`). |
| **Human-in-the-Loop (HITL)** | **Implemented** | Pauses paused runs via `langgraph.types.interrupt()`. Resumes cleanly with `Command(resume={"approved": ..., "feedback": ...})`. |
| **Persistent Checkpointer** | **Implemented** | State persistence across server restarts using `SqliteSaver` (`checkpointer.db`). |
| **SSRF Protection** | **Implemented** | Restricts target URLs to competitor domains and blocks private/loopback/reserved IP ranges. |
| **DuckDB Snapshot Diffing** | **Implemented** | Quantitative diffing of parsed snapshot data using DuckDB SQL; computes numeric `pct_change` and derives threat severity. |
| **Adversarial Fact-Checking** | **Implemented** | Programmatically verifies supporting quotes and numerical evidence against raw scraped text; unclamped confidence score (0.0 - 1.0). |
| **Prompt-Injection Defense** | **Implemented** | Sanitizes raw scraped text before LLM synthesis to prevent prompt injection vectors. |
| **Auth & RBAC** | **Implemented** | PBKDF2 SHA-256 password hashing, JWT authentication with live DB role verification, public signup restricted to `Viewer`, and admin-only user creation/promotion endpoints. |
| **Rate Limiting** | **Implemented** | SlowAPI rate limits on login/register/agent endpoints with `X-Forwarded-For` proxy IP resolution. |
| **Scraper Engine** | **Implemented** | Dual-mode: `DEMO` mode with versioned JSON fixtures (`v1`/`v2`) and `LIVE` mode with `robots.txt` compliance, User-Agent, and timeouts. |
| **LLM Interface & Cost Control**| **Implemented** | Abstract `LLMClient` with schema retries, token usage tracking, and content hash change detection. |
| **Automated Scheduler** | **Implemented** | APScheduler background service enforcing competitor `scraping_cadence`. |
| **Telemetry & Analytics** | **Implemented** | Real database metrics and `TTLCache` hit/miss telemetry. |
| **Distributed Streaming** | **Roadmap** | Single-worker in-memory SSE buffers are active; Redis Pub/Sub recommended for multi-worker scale. |

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

## 🚀 Quickstart & Setup

### Prerequisites
* **Python 3.11+**
* **Docker & Docker Compose** (Optional for containerized run)

### 1. Local Environment Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy example environment configuration
cp .env.example .env

# Run FastAPI development server
uvicorn app.main:app --reload --port 8000
```

### 2. Running with Docker Compose

```bash
# From project root directory
docker-compose up --build
```
The backend API will be available at `http://localhost:8000`. API Documentation is hosted at `http://localhost:8000/docs`.

---

## 🧪 Testing

The backend includes a comprehensive pytest suite covering auth RBAC, SSRF protection, price parsing, DuckDB snapshot diffing, fact-checker evidence verification, cache telemetry, and end-to-end graph interrupts/resumes.

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
* `GET /api/v1/agent/stream/{job_id}?token=...`: Real-time Server-Sent Events (SSE) telemetry log stream.
* `GET /api/v1/agent/pending`: Inbox returning paused agent runs awaiting Human-in-the-Loop review.
* `POST /api/v1/agent/resume/{thread_id}`: Resume paused graph run with `approved: true/false` and analyst feedback.

### Analytics & System Health
* `GET /api/v1/analytics/overview`: Dynamic metrics summary and competitor anomaly bar chart.
* `GET /api/v1/health`: System health status (DB connection, cache telemetry, LLM provider, scheduler state).

---

## ⚠️ Known Limitations

1. **In-Memory SSE Stream Buffer**: Real-time event buffers are stored in-memory per process. In multi-worker production deployments behind a load balancer, event streaming should use Redis Pub/Sub.
2. **Scraper Capabilities**: Live mode parses static HTML via BeautifulSoup with `robots.txt` compliance. JavaScript-heavy single-page applications (SPAs) require headless browser integration (e.g., Playwright).
