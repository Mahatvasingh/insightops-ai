from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="Analyst")  # Admin, Analyst, Viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Competitor(Base):
    __tablename__ = "competitors"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)
    domain = Column(String, nullable=False)
    industry = Column(String, default="Cloud SaaS")
    pricing_url = Column(String, nullable=True)
    features_url = Column(String, nullable=True)
    news_url = Column(String, nullable=True)
    tier = Column(String, default="Tier 1 Direct") # Tier 1 Direct, Tier 2 Emerging, Indirect
    scraping_cadence = Column(String, default="Hourly") # Hourly, Daily, Weekly
    health_status = Column(String, default="Healthy") # Healthy, Warning, Error
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    targets = relationship("ScrapingTarget", back_populates="competitor", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="competitor", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="competitor", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="competitor", cascade="all, delete-orphan")

class ScrapingTarget(Base):
    __tablename__ = "scraping_targets"

    id = Column(String, primary_key=True, default=generate_uuid)
    competitor_id = Column(String, ForeignKey("competitors.id"), nullable=False)
    url = Column(String, nullable=False)
    target_type = Column(String, default="pricing")  # pricing, features, release_notes, news
    last_scraped_at = Column(DateTime, nullable=True)
    status_code = Column(Integer, default=200)
    content_hash = Column(String, nullable=True)

    competitor = relationship("Competitor", back_populates="targets")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=generate_uuid)
    competitor_id = Column(String, ForeignKey("competitors.id"), nullable=False)
    title = Column(String, nullable=False)
    severity = Column(String, default="high")  # critical, high, medium, info
    anomaly_type = Column(String, nullable=False)  # stealth_price_hike, Enterprise_cut_20%, feature_removal, churn_spike
    description = Column(Text, nullable=False)
    metric_delta = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    competitor = relationship("Competitor", back_populates="alerts")

class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    thread_id = Column(String, unique=True, index=True, nullable=False)
    competitor_id = Column(String, ForeignKey("competitors.id"), nullable=False)
    status = Column(String, default="running")  # running, awaiting_hitl, approved, completed, failed
    confidence_score = Column(Float, default=1.0)
    raw_data_summary = Column(Text, nullable=True)
    extracted_facts = Column(JSON, nullable=True)
    quantitative_analysis = Column(JSON, nullable=True)
    plotly_spec = Column(JSON, nullable=True)
    writer_draft = Column(Text, nullable=True)
    final_report = Column(Text, nullable=True)
    hitl_feedback = Column(Text, nullable=True)
    logs_json = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    competitor = relationship("Competitor", back_populates="agent_runs")

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    competitor_id = Column(String, ForeignKey("competitors.id"), nullable=False)
    agent_run_id = Column(String, ForeignKey("agent_runs.id"), nullable=True)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    executive_brief_md = Column(Text, nullable=False)
    plotly_spec_json = Column(JSON, nullable=True)
    citations_json = Column(JSON, nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    competitor = relationship("Competitor", back_populates="reports")
