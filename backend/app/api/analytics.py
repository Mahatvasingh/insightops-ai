from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db
from app.db.models import Competitor, Alert, Report, AgentRun
from app.core.security import require_viewer
from app.core.cache import cache_manager

router = APIRouter(prefix="/analytics", tags=["Executive Analytics"])

@router.get("/overview")
async def get_analytics_overview(db: AsyncSession = Depends(get_db), user=Depends(require_viewer)):
    # Count totals from real database tables
    comp_count_res = await db.execute(select(func.count(Competitor.id)).where(Competitor.is_active == True))
    comp_count = comp_count_res.scalar() or 0

    alert_count_res = await db.execute(select(func.count(Alert.id)).where(Alert.is_read == False))
    active_alerts = alert_count_res.scalar() or 0

    report_count_res = await db.execute(select(func.count(Report.id)))
    total_reports = report_count_res.scalar() or 0

    run_count_res = await db.execute(select(func.count(AgentRun.id)))
    total_runs = run_count_res.scalar() or 0

    # Get real telemetry stats from TTLCache manager
    cache_stats = cache_manager.stats()
    hit_rate = cache_stats.get("hit_rate_pct", 0.0)
    llm_calls = cache_stats.get("llm_calls", 0)
    llm_tokens = cache_stats.get("llm_tokens_total", 0)

    # Compute actual alerts count per competitor for market pulse chart
    competitors_res = await db.execute(select(Competitor).where(Competitor.is_active == True))
    competitors = competitors_res.scalars().all()

    comp_names = []
    anomaly_counts = []

    for comp in competitors:
        c_alerts_res = await db.execute(select(func.count(Alert.id)).where(Alert.competitor_id == comp.id))
        count = c_alerts_res.scalar() or 0
        comp_names.append(comp.name)
        anomaly_counts.append(count)

    if not comp_names:
        comp_names = ["No Competitors"]
        anomaly_counts = [0]

    colors = ["#6366f1", "#ec4899", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6"]
    bar_colors = [colors[i % len(colors)] for i in range(len(comp_names))]

    market_pulse_chart = {
        "data": [
            {
                "x": comp_names,
                "y": anomaly_counts,
                "type": "bar",
                "name": "Active Anomaly Count",
                "marker": {
                    "color": bar_colors
                }
            }
        ],
        "layout": {
            "title": "Real-time Threat & Price Anomaly Count by Competitor",
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": {"color": "#94a3b8"},
            "xaxis": {"gridcolor": "#334155"},
            "yaxis": {"title": "Anomaly Count", "gridcolor": "#334155"}
        }
    }

    return {
        "metrics": {
            "tracked_competitors": comp_count,
            "active_anomalies": active_alerts,
            "intelligence_briefs": total_reports,
            "total_agent_runs": total_runs,
            "cache_hit_rate": f"{hit_rate:.1f}% Cache Hit Rate",
            "llm_telemetry": f"{llm_calls} Calls ({llm_tokens} Tokens)"
        },
        "market_pulse_chart": market_pulse_chart,
        "cache_stats": cache_stats
    }
