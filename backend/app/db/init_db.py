import logging
from app.config import settings
from app.db.database import sync_engine, SyncSessionLocal, Base
from app.db.models import User, Competitor, ScrapingTarget, Alert, Report
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)

def init_db():
    Base.metadata.create_all(bind=sync_engine)
    if not settings.DEMO_MODE:
        logger.info("DEMO_MODE is False: Skipping demo data seeding.")
        return

    logger.warning("DEMO_MODE is True: Seeding demo credentials and fixture data into database.")
    session = SyncSessionLocal()
    try:
        # Seed demo users if none exist
        if not session.query(User).filter_by(email="admin@insightops.ai").first():
            admin_user = User(
                email="admin@insightops.ai",
                hashed_password=get_password_hash("admin123"),
                full_name="Chief Intelligence Officer (Demo Admin)",
                role="Admin"
            )
            analyst_user = User(
                email="analyst@insightops.ai",
                hashed_password=get_password_hash("analyst123"),
                full_name="Lead Market Analyst (Demo Analyst)",
                role="Analyst"
            )
            viewer_user = User(
                email="viewer@insightops.ai",
                hashed_password=get_password_hash("viewer123"),
                full_name="Executive Viewer (Demo Viewer)",
                role="Viewer"
            )
            session.add_all([admin_user, analyst_user, viewer_user])

        # Seed competitors & demo intelligence if DB is empty
        if session.query(Competitor).count() == 0:
            c1 = Competitor(
                name="SaaSify Cloud",
                domain="saasify.cloud",
                industry="Enterprise Cloud Management",
                pricing_url="https://saasify.cloud/pricing",
                features_url="https://saasify.cloud/features",
                news_url="https://saasify.cloud/blog",
                tier="Tier 1 Direct",
                scraping_cadence="Hourly",
                health_status="Healthy"
            )
            c2 = Competitor(
                name="DataPulse AI",
                domain="datapulse.ai",
                industry="Autonomous Analytics & Ops",
                pricing_url="https://datapulse.ai/plans",
                features_url="https://datapulse.ai/docs",
                news_url="https://datapulse.ai/news",
                tier="Tier 1 Direct",
                scraping_cadence="Hourly",
                health_status="Warning"
            )
            c3 = Competitor(
                name="ApexScale Enterprise",
                domain="apexscale.io",
                industry="Scalable Infrastructure SaaS",
                pricing_url="https://apexscale.io/enterprise-pricing",
                features_url="https://apexscale.io/releases",
                news_url="https://apexscale.io/press",
                tier="Tier 2 Emerging",
                scraping_cadence="Daily",
                health_status="Healthy"
            )
            c4 = Competitor(
                name="CloudFlow Systems",
                domain="cloudflow.net",
                industry="Workflow Orchestration",
                pricing_url="https://cloudflow.net/pricing",
                features_url="https://cloudflow.net/features",
                news_url="https://cloudflow.net/updates",
                tier="Tier 2 Emerging",
                scraping_cadence="Daily",
                health_status="Healthy"
            )

            session.add_all([c1, c2, c3, c4])
            session.commit()

            # Add scraping targets
            t1 = ScrapingTarget(competitor_id=c1.id, url=c1.pricing_url, target_type="pricing", status_code=200)
            t2 = ScrapingTarget(competitor_id=c1.id, url=c1.features_url, target_type="features", status_code=200)
            t3 = ScrapingTarget(competitor_id=c2.id, url=c2.pricing_url, target_type="pricing", status_code=200)
            t4 = ScrapingTarget(competitor_id=c3.id, url=c3.pricing_url, target_type="pricing", status_code=200)
            session.add_all([t1, t2, t3, t4])

            # Add seed alerts marked explicitly as Demo Data
            a1 = Alert(
                competitor_id=c1.id,
                title="[Demo Data] SaaSify Cloud slashed Enterprise Tier pricing by 20%",
                severity="critical",
                anomaly_type="price_shift",
                description="[Demo Data] Enterprise plan updated from $499/mo to $399/mo (-20.0%).",
                metric_delta="-20.0%",
                is_read=False
            )
            a2 = Alert(
                competitor_id=c2.id,
                title="[Demo Data] DataPulse AI removed SLA rate-limit guarantees",
                severity="high",
                anomaly_type="feature_removal",
                description="[Demo Data] API docs updated to remove SLA guarantee of 10,000 req/min for Pro users.",
                metric_delta="SLA Removed",
                is_read=False
            )
            a3 = Alert(
                competitor_id=c3.id,
                title="[Demo Data] ApexScale Enterprise negative review ratio shift",
                severity="high",
                anomaly_type="text_table_inconsistency",
                description="[Demo Data] Negative review ratio shift detected (8.2% to 21.5%).",
                metric_delta="Data Discrepancy",
                is_read=True
            )
            session.add_all([a1, a2, a3])

            # Seed report marked explicitly as Demo Data
            plotly_demo_spec = {
                "data": [
                    {
                        "x": ["v1 Snapshot", "v2 Snapshot"],
                        "y": [499, 399],
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": "SaaSify Enterprise Pricing ($/mo)",
                        "line": {"color": "#6366f1", "width": 3}
                    }
                ],
                "layout": {
                    "title": "[Demo Data] Enterprise Pricing Shift Snapshot",
                    "paper_bgcolor": "rgba(0,0,0,0)",
                    "plot_bgcolor": "rgba(0,0,0,0)",
                    "font": {"color": "#e2e8f0"},
                    "xaxis": {"gridcolor": "#334155"},
                    "yaxis": {"gridcolor": "#334155"}
                }
            }

            r1 = Report(
                competitor_id=c1.id,
                title="[Demo Data] Executive Market Brief: SaaSify Cloud Pricing Shift",
                summary="[Demo Data] Automated threat analysis for SaaSify Cloud extracted from demo fixtures.",
                executive_brief_md="""# Executive Intelligence Brief: SaaSify Cloud [Demo Data]

## Strategic Overview
Automated analysis detected a 20% price reduction on SaaSify Cloud Enterprise subscription tier (lowered from $499/mo to $399/mo).

## Extracted Anomalies & Metrics
* **Enterprise Plan Base Rate**: Decreased from $499/mo to $399/mo (-20.0%).

## Fact-Checker Validation & Citations
* **Source**: `https://saasify.cloud/pricing`
* **Status**: Verified against fixture snapshot.
""",
                plotly_spec_json=plotly_demo_spec,
                citations_json=[
                    {"source": "https://saasify.cloud/pricing", "claim": "Enterprise Plan $399/mo", "confidence": 1.0}
                ],
                version=1
            )
            session.add(r1)

        session.commit()
        logger.info("Demo data seeding completed successfully.")
    except Exception as e:
        session.rollback()
        logger.error(f"Error seeding database: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    init_db()
