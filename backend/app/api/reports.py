import io
import xml.sax.saxutils
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.db.database import get_db
from app.db.models import Report, Competitor
from app.core.security import require_viewer

router = APIRouter(prefix="/reports", tags=["Reports & Intelligence Vault"])

@router.get("", response_model=List[dict])
async def list_reports(db: AsyncSession = Depends(get_db), user=Depends(require_viewer)):
    result = await db.execute(
        select(Report, Competitor.name.label("competitor_name"))
        .join(Competitor, Report.competitor_id == Competitor.id)
        .order_by(Report.created_at.desc())
    )
    rows = result.all()
    return [
        {
            "id": rep.id,
            "competitor_id": rep.competitor_id,
            "competitor_name": comp_name,
            "title": rep.title,
            "summary": rep.summary,
            "version": rep.version,
            "created_at": rep.created_at.isoformat() if rep.created_at else None
        }
        for rep, comp_name in rows
    ]

@router.get("/{id}")
async def get_report_detail(id: str, db: AsyncSession = Depends(get_db), user=Depends(require_viewer)):
    result = await db.execute(
        select(Report, Competitor.name.label("competitor_name"))
        .join(Competitor, Report.competitor_id == Competitor.id)
        .where(Report.id == id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Report brief not found")
    
    rep, comp_name = row
    return {
        "id": rep.id,
        "competitor_id": rep.competitor_id,
        "competitor_name": comp_name,
        "title": rep.title,
        "summary": rep.summary,
        "executive_brief_md": rep.executive_brief_md,
        "plotly_spec_json": rep.plotly_spec_json,
        "citations_json": rep.citations_json,
        "version": rep.version,
        "created_at": rep.created_at.isoformat() if rep.created_at else None
    }

@router.get("/{id}/export")
async def export_report_pdf(id: str, db: AsyncSession = Depends(get_db), user=Depends(require_viewer)):
    """
    Generates and returns an executive PDF brief for offline distribution.
    Escapes all dynamic text using xml.sax.saxutils.escape to prevent ReportLab XML parsing errors.
    """
    result = await db.execute(select(Report).where(Report.id == id))
    rep = result.scalars().first()
    if not rep:
        raise HTTPException(status_code=404, detail="Report brief not found")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    story = []
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, spaceAfter=12)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=14, spaceAfter=8)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=6)

    safe_title = xml.sax.saxutils.escape(rep.title or "Executive Brief")
    story.append(Paragraph("InsightOps AI - Executive Intelligence Brief", title_style))
    story.append(Paragraph(f"Report Title: {safe_title}", heading_style))
    story.append(Spacer(1, 12))

    brief_md = rep.executive_brief_md or ""
    for line in brief_md.split('\n'):
        safe_line = xml.sax.saxutils.escape(line.strip())
        if not safe_line:
            continue
        if safe_line.startswith('#'):
            clean_heading = safe_line.lstrip('#').strip()
            story.append(Paragraph(clean_heading, heading_style))
        else:
            story.append(Paragraph(safe_line, body_style))

    doc.build(story)
    buffer.seek(0)

    filename = f"InsightOps_Brief_{rep.id[:8]}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
