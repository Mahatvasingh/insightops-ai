from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import Alert, Competitor
from app.core.security import require_viewer, require_analyst

router = APIRouter(prefix="/alerts", tags=["Alerts & Anomaly Feed"])

@router.get("", response_model=List[dict])
async def get_recent_alerts(db: AsyncSession = Depends(get_db), token=Depends(require_viewer)):
    result = await db.execute(
        select(Alert, Competitor.name.label("competitor_name"))
        .join(Competitor, Alert.competitor_id == Competitor.id)
        .order_by(Alert.created_at.desc())
        .limit(20)
    )
    rows = result.all()
    return [
        {
            "id": alert.id,
            "competitor_id": alert.competitor_id,
            "competitor_name": comp_name,
            "title": alert.title,
            "severity": alert.severity,
            "anomaly_type": alert.anomaly_type,
            "description": alert.description,
            "metric_delta": alert.metric_delta,
            "is_read": alert.is_read,
            "created_at": alert.created_at.isoformat() if alert.created_at else None
        }
        for alert, comp_name in rows
    ]

@router.post("/{id}/read")
async def mark_alert_read(id: str, db: AsyncSession = Depends(get_db), token=Depends(require_analyst)):
    result = await db.execute(select(Alert).where(Alert.id == id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    await db.commit()
    return {"message": "Alert marked as read"}
