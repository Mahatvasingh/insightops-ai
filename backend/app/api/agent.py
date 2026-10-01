import asyncio
import json
import uuid
import time
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query, status
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import jwt
from langgraph.types import Command

from app.config import settings
from app.db.database import get_db, SyncSessionLocal
from app.db.models import AgentRun, Competitor, Report, Alert
from app.inference.workflow import agent_graph
from app.inference.state import AgentState
from app.core.limiter import limiter
from app.core.security import require_analyst, require_viewer, decode_token
from app.core.url_validator import validate_target_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["War-Room Agent Workflow"])

# In-Memory Stream Buffer for SSE Real-time Updates (protected by threading.Lock)
stream_buffers: Dict[str, Dict[str, Any]] = {}
stream_buffers_lock = threading.Lock()

class AgentRunRequest(BaseModel):
    competitor_id: str
    target_url: Optional[str] = None
    user_query: Optional[str] = "Perform competitive deep dive on pricing shifts and feature changes."

class HITLResumeRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = "Approved by Lead Market Analyst."

def create_stream_token(thread_id: str, user_email: str) -> str:
    """Issues a short-lived (60 seconds) stream token scoped to one thread_id."""
    expire = datetime.now(timezone.utc) + timedelta(seconds=60)
    payload = {
        "sub": user_email,
        "thread_id": thread_id,
        "type": "stream",
        "exp": expire
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_stream_token(token: str, expected_thread_id: str) -> str:
    """Verifies short-lived stream token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "stream":
            raise ValueError("Token is not a stream token")
        if payload.get("thread_id") != expected_thread_id:
            raise ValueError("Token thread_id mismatch")
        return str(payload.get("sub", ""))
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired stream token: {e}")

def emit_stream_event(thread_id: str, step: str, node: str, message: str, confidence: float = 1.0, data: Any = None):
    buffer_key = f"stream:{thread_id}"
    evt = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "thread_id": thread_id,
        "step": step,
        "node": node,
        "message": message,
        "status": step,
        "confidence": confidence
    }

    with stream_buffers_lock:
        if buffer_key not in stream_buffers:
            stream_buffers[buffer_key] = {"events": [], "created_at": time.time()}

        buf = stream_buffers[buffer_key]["events"]
        # Allow terminal events to be appended even if cap is reached
        if len(buf) < 500 or step in ["finish", "error", "paused"]:
            buf.append(evt)

def cleanup_stream_buffers():
    """TTL Cleanup for SSE stream buffers older than 30 minutes."""
    now = time.time()
    with stream_buffers_lock:
        expired_keys = [k for k, v in stream_buffers.items() if now - v.get("created_at", now) > 1800]
        for k in expired_keys:
            stream_buffers.pop(k, None)

def _persist_report_and_alerts(db, ar: AgentRun, final_vals: Dict[str, Any], competitor_name: str):
    """Single shared helper for persisting Report and Alert records from graph state."""
    final_status = final_vals.get("status", "completed")
    ar.status = final_status

    if final_status == "completed" and final_vals.get("final_report"):
        db.flush()
        fact_score = final_vals.get("fact_check_score", 1.0)
        rep = Report(
            competitor_id=ar.competitor_id,
            agent_run_id=ar.id,
            title=f"Executive Intelligence Brief: {competitor_name}",
            summary=f"Automated threat analysis for {competitor_name}. Confidence: {fact_score*100:.1f}%",
            executive_brief_md=final_vals.get("final_report", "# Report Pending"),
            plotly_spec_json=final_vals.get("plotly_spec", {}),
            citations_json=final_vals.get("citations", []),
            version=1
        )
        db.add(rep)

        anomalies = final_vals.get("anomaly_flags", [])
        for a in anomalies:
            if a.get("verification_status") != "unverified":
                alert = Alert(
                    competitor_id=ar.competitor_id,
                    title=a.get("title", "Market Anomaly Detected"),
                    severity=a.get("severity", "high"),
                    anomaly_type=a.get("type", "pricing_shift"),
                    description=a.get("description", ""),
                    metric_delta=a.get("metric_delta")
                )
                db.add(alert)

def run_graph_background_task(thread_id: str, competitor_id: str, competitor_name: str, target_url: str, user_query: str):
    """
    Decoupled Asynchronous Background Task executing the LangGraph Multi-Agent StateGraph.
    """
    cleanup_stream_buffers()
    emit_stream_event(thread_id, "start", "Supervisor", f"Initiating autonomous multi-agent analysis for {competitor_name}.")

    db = SyncSessionLocal()
    try:
        agent_run = AgentRun(
            thread_id=thread_id,
            competitor_id=competitor_id,
            status="running",
            confidence_score=1.0,
            raw_data_summary="",
            extracted_facts=[],
            quantitative_analysis={},
            plotly_spec={},
            writer_draft="",
            final_report="",
            logs_json=[]
        )
        db.add(agent_run)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create initial AgentRun record: {e}")
    finally:
        db.close()

    initial_state: AgentState = {
        "thread_id": thread_id,
        "competitor_id": competitor_id,
        "competitor_name": competitor_name,
        "target_url": target_url,
        "user_query": user_query,
        "force_refresh": False,
        "raw_text": "",
        "parsed_tables": [],
        "extracted_facts": [],
        "content_hash": "",
        "source": "demo",
        "scrape_time": None,
        "previous_snapshot": None,
        "previous_content_hash": None,
        "quantitative_metrics": {},
        "anomaly_flags": [],
        "plotly_spec": {},
        "fact_check_score": 1.0,
        "fact_check_feedback": "",
        "revision_count": 0,
        "hitl_required": False,
        "hitl_approved": None,
        "hitl_feedback": None,
        "writer_draft": "",
        "final_report": "",
        "citations": [],
        "status": "running",
        "current_node": "Supervisor",
        "token_usage": {"calls": 0, "tokens": 0, "nodes": {}},
        "logs": []
    }

    config = {"configurable": {"thread_id": thread_id}}

    try:
        emit_stream_event(thread_id, "node_start", "Researcher", f"Scraping web data for target: {target_url}")

        for event in agent_graph.stream(initial_state, config=config):
            for node_name, node_output in event.items():
                if str(node_name).startswith("__"):
                    continue

                if isinstance(node_output, dict):
                    node_logs = node_output.get("logs", [])
                    last_log = node_logs[-1]["message"] if node_logs else f"Node {node_name} completed."
                    confidence = node_output.get("fact_check_score", 1.0)
                    emit_stream_event(thread_id, "node_complete", str(node_name), last_log, confidence=confidence)

        current_state = agent_graph.get_state(config)
        is_paused = bool(current_state.next)

        db = SyncSessionLocal()
        try:
            ar = db.query(AgentRun).filter(AgentRun.thread_id == thread_id).first()
            if ar:
                final_vals = current_state.values or {}
                ar.confidence_score = final_vals.get("fact_check_score", 1.0)
                ar.raw_data_summary = (final_vals.get("raw_text", "") or "")[:500]
                ar.extracted_facts = final_vals.get("extracted_facts", [])
                ar.quantitative_analysis = final_vals.get("quantitative_metrics", {})
                ar.plotly_spec = final_vals.get("plotly_spec", {})
                ar.writer_draft = final_vals.get("writer_draft", "")
                ar.final_report = final_vals.get("final_report", "")
                ar.logs_json = final_vals.get("logs", [])

                if is_paused:
                    ar.status = "awaiting_hitl"
                    emit_stream_event(thread_id, "paused", "Human Review", "Graph paused at interrupt awaiting HITL approval.")
                else:
                    _persist_report_and_alerts(db, ar, final_vals, competitor_name)

                db.commit()
        except Exception as ex:
            db.rollback()
            logger.error(f"Error persisting agent run state: {ex}")
        finally:
            db.close()

        if not is_paused:
            emit_stream_event(thread_id, "finish", "Workflow", "LangGraph multi-agent run completed successfully.")
    except Exception as err:
        logger.error(f"Background agent execution error: {err}")
        db = SyncSessionLocal()
        try:
            ar = db.query(AgentRun).filter(AgentRun.thread_id == thread_id).first()
            if ar:
                ar.status = "failed"
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        emit_stream_event(thread_id, "error", "Workflow", f"Execution error: {str(err)}", confidence=0.0)

@router.post("/run", status_code=202)
@limiter.limit("10/minute")
async def trigger_agent_run(
    request: Request,
    req_data: AgentRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_analyst)
):
    result = await db.execute(select(Competitor).where(Competitor.id == req_data.competitor_id))
    competitor = result.scalars().first()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor target not found")

    target_url = req_data.target_url or competitor.pricing_url or f"https://{competitor.domain}/pricing"

    try:
        validated_url = validate_target_url(target_url, allowed_domain=competitor.domain)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=f"SSRF validation error: {err}")

    thread_id = f"thread_{uuid.uuid4().hex[:12]}"

    background_tasks.add_task(
        run_graph_background_task,
        thread_id=thread_id,
        competitor_id=competitor.id,
        competitor_name=competitor.name,
        target_url=validated_url,
        user_query=req_data.user_query
    )

    return {
        "status": "accepted",
        "job_id": thread_id,
        "thread_id": thread_id,
        "competitor_name": competitor.name,
        "message": f"Multi-agent LangGraph run initiated for {competitor.name}.",
        "stream_url": f"/api/v1/agent/stream/{thread_id}"
    }

@router.post("/stream-token/{thread_id}")
async def get_stream_token(thread_id: str, user=Depends(require_viewer)):
    """Generates a short-lived (60s) stream token for SSE connection."""
    stream_token = create_stream_token(thread_id, user.email)
    return {"stream_token": stream_token, "expires_in_seconds": 60}

@router.get("/stream/{job_id}")
async def stream_agent_logs(job_id: str, token: str = Query(...)):
    """
    Server-Sent Events (SSE) Streaming Endpoint.
    Requires short-lived stream token verification.
    """
    verify_stream_token(token, job_id)
    buffer_key = f"stream:{job_id}"

    async def event_generator():
        sent_index = 0
        timeout_counter = 0
        while timeout_counter < 60:
            events = []
            with stream_buffers_lock:
                stream_data = stream_buffers.get(buffer_key, {})
                events = list(stream_data.get("events", []))

            if sent_index < len(events):
                for evt in events[sent_index:]:
                    yield f"data: {json.dumps(evt)}\n\n"
                    if evt.get("step") in ["finish", "error", "paused"]:
                        return
                sent_index = len(events)
                timeout_counter = 0
            else:
                yield f": heartbeat {datetime.now().isoformat()}\n\n"
                await asyncio.sleep(0.5)
                timeout_counter += 0.5

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/pending")
async def get_pending_hitl_reviews(db: AsyncSession = Depends(get_db), user=Depends(require_analyst)):
    """
    Human-in-the-Loop Pending Approval Inbox.
    """
    result = await db.execute(select(AgentRun).where(AgentRun.status == "awaiting_hitl"))
    runs = result.scalars().all()
    return [
        {
            "id": r.id,
            "thread_id": r.thread_id,
            "competitor_id": r.competitor_id,
            "confidence_score": r.confidence_score,
            "extracted_facts": r.extracted_facts,
            "quantitative_analysis": r.quantitative_analysis,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in runs
    ]

def _sync_resume_hitl(thread_id: str, approved: bool, feedback: str) -> Dict[str, Any]:
    """Sync worker logic executing graph resume in threadpool."""
    config = {"configurable": {"thread_id": thread_id}}
    command = Command(resume={"approved": approved, "feedback": feedback})
    
    events_logs = []
    try:
        for event in agent_graph.stream(command, config=config):
            for node_name, node_output in event.items():
                if str(node_name).startswith("__"):
                    continue
                events_logs.append({"node": str(node_name), "status": "completed"})

        final_state = agent_graph.get_state(config).values or {}

        db = SyncSessionLocal()
        try:
            ar = db.query(AgentRun).filter(AgentRun.thread_id == thread_id).first()
            if ar:
                if approved:
                    ar.hitl_approved = True
                    ar.hitl_feedback = feedback
                    ar.confidence_score = final_state.get("fact_check_score", 1.0)
                    ar.writer_draft = final_state.get("writer_draft", "")
                    ar.final_report = final_state.get("final_report", "")

                    _persist_report_and_alerts(db, ar, final_state, final_state.get("competitor_name", "Competitor"))
                else:
                    ar.status = "rejected"
                    ar.hitl_approved = False
                    ar.hitl_feedback = feedback

                db.commit()
        except Exception as ex:
            db.rollback()
            logger.error(f"Error persisting resumed agent run: {ex}")
        finally:
            db.close()

        return {
            "thread_id": thread_id,
            "approved": approved,
            "message": f"Graph resumed successfully ({'approved' if approved else 'rejected'}).",
            "steps": events_logs
        }
    except Exception as err:
        logger.error(f"Error during resumed graph execution: {err}")
        db = SyncSessionLocal()
        try:
            ar = db.query(AgentRun).filter(AgentRun.thread_id == thread_id).first()
            if ar:
                ar.status = "failed"
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        raise err

@router.post("/resume/{thread_id}")
async def resume_hitl_agent_run(
    thread_id: str,
    resume_req: HITLResumeRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_analyst)
):
    """
    Human-in-the-Loop Resume Endpoint.
    Enforces thread existence, status == 'awaiting_hitl', and atomic status flip to prevent double-resumes.
    """
    result = await db.execute(select(AgentRun).where(AgentRun.thread_id == thread_id))
    agent_run = result.scalars().first()

    if not agent_run:
        raise HTTPException(status_code=404, detail="Agent run thread not found")
    
    if agent_run.status != "awaiting_hitl":
        raise HTTPException(status_code=400, detail=f"Agent run is not awaiting HITL approval (current status: '{agent_run.status}')")

    # Atomic status flip to prevent concurrent resumes
    agent_run.status = "resuming"
    await db.commit()

    config = {"configurable": {"thread_id": thread_id}}
    state = await run_in_threadpool(agent_graph.get_state, config)

    if not state or not state.values:
        agent_run.status = "awaiting_hitl"
        await db.commit()
        raise HTTPException(status_code=404, detail="Paused agent thread state not found in checkpointer")

    try:
        resume_res = await run_in_threadpool(
            _sync_resume_hitl,
            thread_id=thread_id,
            approved=resume_req.approved,
            feedback=resume_req.feedback
        )
        return resume_res
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to resume graph thread: {err}")
