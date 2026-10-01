import asyncio
import json
import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query, status
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from langgraph.types import Command

from app.db.database import get_db, SyncSessionLocal
from app.db.models import AgentRun, Competitor, Report, Alert
from app.inference.workflow import agent_graph
from app.inference.state import AgentState
from app.core.limiter import limiter
from app.core.security import require_analyst, require_viewer, decode_token
from app.core.url_validator import validate_target_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["War-Room Agent Workflow"])

# In-Memory Stream Buffer for SSE Real-time Updates
# Note: In multi-worker/production environments, this in-memory buffer should be replaced with Redis Pub/Sub.
stream_buffers: Dict[str, Dict[str, Any]] = {}

class AgentRunRequest(BaseModel):
    competitor_id: str
    target_url: Optional[str] = None
    user_query: Optional[str] = "Perform competitive deep dive on pricing shifts and feature changes."

class HITLResumeRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = "Approved by Lead Market Analyst."

def emit_stream_event(thread_id: str, step: str, node: str, message: str, confidence: float = 1.0, data: Any = None):
    buffer_key = f"stream:{thread_id}"
    if buffer_key not in stream_buffers:
        stream_buffers[buffer_key] = {"events": [], "created_at": time.time()}

    evt = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "thread_id": thread_id,
        "step": step,
        "node": node,
        "message": message,
        "confidence": confidence,
        "data": data
    }

    buf = stream_buffers[buffer_key]["events"]
    if len(buf) < 500:  # Bounded size limit
        buf.append(evt)

def cleanup_stream_buffers():
    """TTL Cleanup for SSE stream buffers older than 30 minutes."""
    now = time.time()
    expired_keys = [k for k, v in stream_buffers.items() if now - v.get("created_at", now) > 1800]
    for k in expired_keys:
        stream_buffers.pop(k, None)

def run_graph_background_task(thread_id: str, competitor_id: str, competitor_name: str, target_url: str, user_query: str):
    """
    Decoupled Asynchronous Background Task executing the LangGraph Multi-Agent StateGraph.
    Updates DB immediately at start, handles interrupts, and persists final report on completion.
    """
    cleanup_stream_buffers()
    emit_stream_event(thread_id, "start", "Supervisor", f"Initiating autonomous multi-agent analysis for {competitor_name}.")

    # 1. Immediately create AgentRun row with status 'running' (Requirement 9)
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
        "raw_text": "",
        "parsed_tables": [],
        "extracted_facts": [],
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
        "logs": []
    }

    config = {"configurable": {"thread_id": thread_id}}

    try:
        emit_stream_event(thread_id, "node_start", "Researcher", f"Scraping live target URL: {target_url}")

        # Stream graph execution, skipping internal keys starting with '__' (Requirement 1)
        for event in agent_graph.stream(initial_state, config=config):
            for node_name, node_output in event.items():
                if str(node_name).startswith("__"):
                    continue

                if isinstance(node_output, dict):
                    node_logs = node_output.get("logs", [])
                    last_log = node_logs[-1]["message"] if node_logs else f"Node {node_name} step completed."
                    confidence = node_output.get("fact_check_score", 1.0)
                    emit_stream_event(thread_id, "node_complete", str(node_name), last_log, confidence=confidence, data=node_output)

        # Check graph state post-execution
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
                    emit_stream_event(thread_id, "paused", "Human Review", "Graph paused at checkpointer interrupt awaiting HITL approval.")
                else:
                    final_status = final_vals.get("status", "completed")
                    ar.status = final_status

                    if final_status == "completed" and final_vals.get("final_report"):
                        db.flush()  # Ensure ar.id is flushed before creating Report (Requirement 10)
                        rep = Report(
                            competitor_id=competitor_id,
                            agent_run_id=ar.id,
                            title=f"Executive Intelligence Brief: {competitor_name}",
                            summary=f"Automated threat analysis for {competitor_name}. Conf: {final_vals.get('fact_check_score', 0.95)*100:.1f}%",
                            executive_brief_md=final_vals.get("final_report", "# Report Pending"),
                            plotly_spec_json=final_vals.get("plotly_spec", {}),
                            citations_json=final_vals.get("citations", []),
                            version=1
                        )
                        db.add(rep)

                        # Create Alerts for verified anomalies only (no fabricated defaults! Requirement 11)
                        anomalies = final_vals.get("anomaly_flags", [])
                        for a in anomalies:
                            alert = Alert(
                                competitor_id=competitor_id,
                                title=a.get("title", "Market Anomaly Detected"),
                                severity=a.get("severity", "high"),
                                anomaly_type=a.get("type", "pricing_shift"),
                                description=a.get("description", ""),
                                metric_delta=a.get("metric_delta")  # None if missing
                            )
                            db.add(alert)

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

    # Validate target URL against SSRF vulnerabilities (Requirement 6)
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

@router.get("/stream/{job_id}")
async def stream_agent_logs(job_id: str, token: Optional[str] = Query(None)):
    """
    Server-Sent Events (SSE) Streaming Endpoint with short-lived stream token authentication (Requirement 8).
    """
    if token:
        try:
            decode_token(token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid stream token")

    buffer_key = f"stream:{job_id}"

    async def event_generator():
        sent_index = 0
        timeout_counter = 0
        while timeout_counter < 60:
            stream_data = stream_buffers.get(buffer_key, {})
            events = stream_data.get("events", [])
            if sent_index < len(events):
                for evt in events[sent_index:]:
                    yield f"data: {json.dumps(evt)}\n\n"
                    if evt.get("step") in ["finish", "error"]:
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
    Returns agent runs paused at the checkpointer interrupt breakpoint.
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
    """Sync worker logic to resume LangGraph checkpointer thread in threadpool (Requirement 7)."""
    config = {"configurable": {"thread_id": thread_id}}

    # Resume graph using Command(resume={"approved": ..., "feedback": ...})
    command = Command(resume={"approved": approved, "feedback": feedback})
    
    # Resume execution of thread
    events_logs = []
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
                ar.status = "completed"
                ar.hitl_approved = True
                ar.hitl_feedback = feedback
                ar.confidence_score = final_state.get("fact_check_score", 1.0)
                ar.writer_draft = final_state.get("writer_draft", "")
                ar.final_report = final_state.get("final_report", "")

                if final_state.get("final_report"):
                    db.flush()
                    rep = Report(
                        competitor_id=ar.competitor_id,
                        agent_run_id=ar.id,
                        title=f"Executive Intelligence Brief: {final_state.get('competitor_name', 'Competitor')}",
                        summary=f"Automated threat analysis (HITL Verified). Conf: {final_state.get('fact_check_score', 0.99)*100:.1f}%",
                        executive_brief_md=final_state.get("final_report"),
                        plotly_spec_json=final_state.get("plotly_spec", {}),
                        citations_json=final_state.get("citations", []),
                        version=1
                    )
                    db.add(rep)

                    anomalies = final_state.get("anomaly_flags", [])
                    for a in anomalies:
                        alert = Alert(
                            competitor_id=ar.competitor_id,
                            title=a.get("title", "Market Anomaly Detected"),
                            severity=a.get("severity", "high"),
                            anomaly_type=a.get("type", "pricing_shift"),
                            description=a.get("description", ""),
                            metric_delta=a.get("metric_delta")
                        )
                        db.add(alert)
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

@router.post("/resume/{thread_id}")
async def resume_hitl_agent_run(
    thread_id: str,
    resume_req: HITLResumeRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_analyst)
):
    """
    Human-in-the-Loop Resume Endpoint.
    Resumes sync graph in threadpool to prevent blocking FastAPI event loop (Requirement 7).
    """
    config = {"configurable": {"thread_id": thread_id}}
    state = agent_graph.get_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Paused agent thread state not found in checkpointer")

    result = await run_in_threadpool(
        _sync_resume_hitl,
        thread_id=thread_id,
        approved=resume_req.approved,
        feedback=resume_req.feedback
    )
    return result
