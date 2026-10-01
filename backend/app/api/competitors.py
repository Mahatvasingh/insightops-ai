from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import Competitor, ScrapingTarget
from app.core.security import require_admin, require_analyst, require_viewer
from app.core.url_validator import validate_target_url

router = APIRouter(prefix="/competitors", tags=["Competitor CRUD"])

class CompetitorCreate(BaseModel):
    name: str
    domain: str
    industry: Optional[str] = "Cloud SaaS"
    pricing_url: Optional[str] = None
    features_url: Optional[str] = None
    news_url: Optional[str] = None
    tier: Optional[str] = "Tier 1 Direct"
    scraping_cadence: Optional[str] = "Hourly"

class CompetitorUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    pricing_url: Optional[str] = None
    features_url: Optional[str] = None
    tier: Optional[str] = None
    scraping_cadence: Optional[str] = None
    health_status: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("", response_model=List[dict])
async def list_competitors(db: AsyncSession = Depends(get_db), user=Depends(require_viewer)):
    result = await db.execute(select(Competitor).where(Competitor.is_active == True))
    competitors = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "domain": c.domain,
            "industry": c.industry,
            "pricing_url": c.pricing_url,
            "features_url": c.features_url,
            "news_url": c.news_url,
            "tier": c.tier,
            "scraping_cadence": c.scraping_cadence,
            "health_status": c.health_status,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in competitors
    ]

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_competitor(comp_in: CompetitorCreate, db: AsyncSession = Depends(get_db), user=Depends(require_analyst)):
    # Validate URLs against competitor domain
    if comp_in.pricing_url:
        try:
            validate_target_url(comp_in.pricing_url, allowed_domain=comp_in.domain)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=f"Invalid pricing_url: {err}")

    competitor = Competitor(
        name=comp_in.name,
        domain=comp_in.domain,
        industry=comp_in.industry,
        pricing_url=comp_in.pricing_url,
        features_url=comp_in.features_url,
        news_url=comp_in.news_url,
        tier=comp_in.tier,
        scraping_cadence=comp_in.scraping_cadence,
        health_status="Healthy"
    )
    db.add(competitor)
    await db.commit()
    await db.refresh(competitor)

    if comp_in.pricing_url:
        target = ScrapingTarget(competitor_id=competitor.id, url=comp_in.pricing_url, target_type="pricing")
        db.add(target)
        await db.commit()

    return {"id": competitor.id, "message": f"Competitor '{competitor.name}' tracked successfully."}

@router.put("/{id}")
async def update_competitor(id: str, comp_in: CompetitorUpdate, db: AsyncSession = Depends(get_db), user=Depends(require_analyst)):
    result = await db.execute(select(Competitor).where(Competitor.id == id))
    competitor = result.scalars().first()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor profile not found")

    target_domain = comp_in.domain or competitor.domain
    if comp_in.pricing_url:
        try:
            validate_target_url(comp_in.pricing_url, allowed_domain=target_domain)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=f"Invalid pricing_url: {err}")

    for field, value in comp_in.dict(exclude_unset=True).items():
        setattr(competitor, field, value)

    await db.commit()
    return {"message": "Competitor profile updated successfully"}

@router.delete("/{id}")
async def delete_competitor(id: str, db: AsyncSession = Depends(get_db), user=Depends(require_admin)):
    result = await db.execute(select(Competitor).where(Competitor.id == id))
    competitor = result.scalars().first()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor profile not found")

    competitor.is_active = False  # Soft delete
    await db.commit()
    return {"message": f"Competitor '{competitor.name}' deactivated."}
