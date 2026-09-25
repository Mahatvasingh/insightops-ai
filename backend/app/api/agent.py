import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.database import get_db, SyncSessionLocal
from app.db.models import AgentRun, Competitor, Report, Alert
from app.inference.workflow import agent_graph
from app.inference.state import AgentState
from app.core.limiter import limiter
from app.core.security import require_analyst, require_viewer

router = APIRouter(prefix="/agent", tags=["War-Room Agent Workflow"])

# In-Memory Stream Buffer for SSE Real-time Updates
stream_buffers: Dict[str, List[Dict[str, Any]]] = {}

class AgentRunRequest(BaseModel):
    competitor_id: str
    target_url: Optional[str] = None
    user_query: Optional[str] = "Perform competitive deep dive on pricing shifts and feature changes."

class HITLResumeRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = "Approved by Lead Market Analyst."

def run_graph_background_task(thread_id: str, competitor_id: str, competitor_name: str, target_url: str, user_query: str):
    """
    Decoupled Asynchronous Background Task executing the LangGraph Multi-Agent StateGraph.
    Updates thread state, logs telemetry, and persists final report to DB upon completion.
    """
    buffer_key = f"stream:{thread_id}"
    stream_buffers[buffer_key] = []

    def emit_event(step: str, node: str, message: str, confidence: float = 1.0, data: Any = None):
        evt = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "thread_id": thread_id,
            "step": step,
            "node": node,
            "message": message,
            "confidence": confidence,
            "data": data
        }
        stream_buffers[buffer_key].append(evt)

    emit_event("start", "Supervisor", f"Initiating autonomous multi-agent analysis for {competitor_name}.")

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
        # Step 1: Supervisor -> Researcher
        emit_event("node_start", "Researcher", f"Scraping live target URL: {target_url}")
        
        # Stream execution of graph steps
        for event in agent_graph.stream(initial_state, config=config):
            for node_name, node_output in event.items():
                node_status = node_output.get("status", "running")
                node_logs = node_output.get("logs", [])
                last_log = node_logs[-1]["message"] if node_logs else f"Node {node_name} completed."

                confidence = node_output.get("fact_check_score", 1.0)
                emit_event("node_complete", node_name, last_log, confidence=confidence, data=node_output)

        # Final state check
        final_state = agent_graph.get_state(config).values

        # Persist run state to DB using Sync Session
        db = SyncSessionLocal()
        try:
            agent_run = db.query(AgentRun).filter(AgentRun.thread_id == thread_id).first()
            if not agent_run:
                agent_run = AgentRun(
                    thread_id=thread_id,
                    competitor_id=competitor_id,
                    status=final_state.get("status", "completed"),
                    confidence_score=final_state.get("fact_check_score", 1.0),
                    raw_data_summary=final_state.get("raw_text", "")[:500],
                    extracted_facts=final_state.get("extracted_facts", []),
                    quantitative_analysis=final_state.get("quantitative_metrics", {}),
                    plotly_spec=final_state.get("plotly_spec", {}),
                    writer_draft=final_state.get("writer_draft", ""),
                    final_report=final_state.get("final_report", ""),
                    logs_json=final_state.get("logs", [])
                )
                db.add(agent_run)
            else:
                agent_run.status = final_state.get("status", "completed")
                agent_run.confidence_score = final_state.get("fact_check_score", 1.0)
                agent_run.final_report = final_state.get("final_report", "")

            # If completed, create Report & Alert
            if final_state.get("status") in ["completed", "writing_complete"] or final_state.get("final_report"):
                rep = Report(
                    competitor_id=competitor_id,
                    agent_run_id=agent_run.id if agent_run.id else None,
                    title=f"Executive Intelligence Brief: {competitor_name}",
                    summary=f"Automated threat analysis for {competitor_name}. Conf: {final_state.get('fact_check_score', 0.95)*100:.1f}%",
                    executive_brief_md=final_state.get("final_report", "# Report Pending"),
                    plotly_spec_json=final_state.get("plotly_spec", {}),
                    citations_json=final_state.get("citations", []),
                    version=1
                )
                db.add(rep)

                # Add alert if anomaly detected
                anomalies = final_state.get("anomaly_flags", [])
                for a in anomalies:
                    alert = Alert(
                        competitor_id=competitor_id,
                        title=a.get("title", "Market Anomaly Detected"),
                        severity=a.get("severity", "high"),
                        anomaly_type=a.get("type", "pricing_shift"),
                        description=a.get("description", ""),
                        metric_delta=a.get("metric_delta", "-20%")
                    )
                    db.add(alert)

            db.commit()
        except Exception as ex:
            db.rollback()
            print(f"Error persisting agent run: {ex}")
        finally:
            db.close()

        emit_event("finish", "Workflow", "LangGraph multi-agent run finished successfully.", confidence=final_state.get("fact_check_score", 1.0))
    except Exception as err:
        emit_event("error", "Workflow", f"Execution error: {str(err)}", confidence=0.0)

@router.post("/run", status_code=202)
@limiter.limit("10/minute")
async def trigger_agent_run(
    request: Request,
    req_data: AgentRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    token=Depends(require_analyst)
):
    result = await db.execute(select(Competitor).where(Competitor.id == req_data.competitor_id))
    competitor = result.scalars().first()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor target not found")

    thread_id = f"thread_{uuid.uuid4().hex[:12]}"
    target_url = req_data.target_url or competitor.pricing_url or f"https://{competitor.domain}/pricing"

    # Schedule decoupled background task
    background_tasks.add_task(
        run_graph_background_task,
        thread_id=thread_id,
        competitor_id=competitor.id,
        competitor_name=competitor.name,
        target_url=target_url,
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
async def stream_agent_logs(job_id: str):
    """
    Server-Sent Events (SSE) Streaming Endpoint.
    Yields real-time step updates as LangGraph agents execute.
    """
    buffer_key = f"stream:{job_id}"

    async def event_generator():
        sent_index = 0
        timeout_counter = 0
        while timeout_counter < 60:
            events = stream_buffers.get(buffer_key, [])
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
async def get_pending_hitl_reviews(db: AsyncSession = Depends(get_db), token=Depends(require_analyst)):
    """
    Human-in-the-Loop Pending Approval Inbox.
    Returns agent runs paused at the checkpointer breakpoint.
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

@router.post("/resume/{thread_id}")
async def resume_hitl_agent_run(
    thread_id: str,
    resume_req: HITLResumeRequest,
    db: AsyncSession = Depends(get_db),
    token=Depends(require_analyst)
):
    """
    Human-in-the-Loop Resume Endpoint.
    Passes user approval or correction feedback to LangGraph checkpointer and resumes execution.
    """
    config = {"configurable": {"thread_id": thread_id}}
    state_values = agent_graph.get_state(config).values
    if not state_values:
        raise HTTPException(status_code=404, detail="Active agent thread state not found in checkpointer")

    # Update state with human approval and feedback
    updated_state = {
        "hitl_approved": resume_req.approved,
        "hitl_feedback": resume_req.feedback,
        "hitl_required": False
    }

    agent_graph.update_state(config, updated_state)

    # Resume graph execution
    resume_events = []
    for event in agent_graph.stream(None, config=config):
        for node_name, output in event.items():
            resume_events.append({"node": node_name, "status": output.get("status")})

    # Persist finalized state & generate report/alerts
    final_state = agent_graph.get_state(config).values
    if final_state:
        db_sync = SyncSessionLocal()
        try:
            agent_run = db_sync.query(AgentRun).filter(AgentRun.thread_id == thread_id).first()
            if agent_run:
                agent_run.status = final_state.get("status", "completed")
                agent_run.confidence_score = final_state.get("fact_check_score", 1.0)
                agent_run.final_report = final_state.get("final_report", "")
                agent_run.hitl_feedback = resume_req.feedback

                if final_state.get("final_report"):
                    rep = Report(
                        competitor_id=agent_run.competitor_id,
                        agent_run_id=agent_run.id,
                        title=f"Executive Intelligence Brief: {final_state.get('competitor_name', 'Competitor')}",
                        summary=f"Automated threat analysis (HITL Verified). Conf: {final_state.get('fact_check_score', 0.99)*100:.1f}%",
                        executive_brief_md=final_state.get("final_report"),
                        plotly_spec_json=final_state.get("plotly_spec", {}),
                        citations_json=final_state.get("citations", []),
                        version=1
                    )
                    db_sync.add(rep)

                    anomalies = final_state.get("anomaly_flags", [])
                    for a in anomalies:
                        alert = Alert(
                            competitor_id=agent_run.competitor_id,
                            title=a.get("title", "Market Anomaly Detected"),
                            severity=a.get("severity", "high"),
                            anomaly_type=a.get("type", "pricing_shift"),
                            description=a.get("description", ""),
                            metric_delta=a.get("metric_delta", "-20%")
                        )
                        db_sync.add(alert)

            db_sync.commit()
        except Exception as ex:
            db_sync.rollback()
            print(f"Error persisting resumed run: {ex}")
        finally:
            db_sync.close()

    return {
        "thread_id": thread_id,
        "approved": resume_req.approved,
        "message": "Graph execution resumed successfully and report persisted.",
        "steps": resume_events
    }
