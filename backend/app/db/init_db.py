from app.config import settings
from app.db.database import sync_engine, SyncSessionLocal, Base
from app.db.models import User, Competitor, ScrapingTarget, Alert, Report
from app.core.security import get_password_hash

def init_db():
    Base.metadata.create_all(bind=sync_engine)
    if not settings.DEMO_MODE:
        return

    session = SyncSessionLocal()
    try:
        # Seed users if none exist
        if not session.query(User).filter_by(email="admin@insightops.ai").first():
            admin_user = User(
                email="admin@insightops.ai",
                hashed_password=get_password_hash("admin123"),
                full_name="Chief Intelligence Officer (Admin)",
                role="Admin"
            )
            analyst_user = User(
                email="analyst@insightops.ai",
                hashed_password=get_password_hash("analyst123"),
                full_name="Lead Market Analyst",
                role="Analyst"
            )
            viewer_user = User(
                email="viewer@insightops.ai",
                hashed_password=get_password_hash("viewer123"),
                full_name="Executive Viewer",
                role="Viewer"
            )
            session.add_all([admin_user, analyst_user, viewer_user])

        # Seed competitors & sample intelligence if DB is empty
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

            # Add seed alerts
            a1 = Alert(
                competitor_id=c1.id,
                title="SaaSify Cloud slashed Enterprise Tier pricing by 20%",
                severity="critical",
                anomaly_type="Enterprise_cut_20%",
                description="Detected unannounced price update on Enterprise plan from $499/mo to $399/mo, offering free SSO integration.",
                metric_delta="-20.0%",
                is_read=False
            )
            a2 = Alert(
                competitor_id=c2.id,
                title="DataPulse AI silently removed legacy API rate-limit guarantees",
                severity="high",
                anomaly_type="feature_removal",
                description="Terms of Service & API docs updated to remove SLA guarantee of 10,000 req/min for Pro users.",
                metric_delta="-100% SLA Guarantee",
                is_read=False
            )
            a3 = Alert(
                competitor_id=c3.id,
                title="ApexScale Enterprise negative churn reviews spike",
                severity="medium",
                anomaly_type="churn_spike",
                description="Spike in user review complaints on G2 & Reddit regarding recent v3.4 migration breaking changes.",
                metric_delta="+42% Negative Sentiment",
                is_read=True
            )
            session.add_all([a1, a2, a3])

            # Seed report
            plotly_demo_spec = {
                "data": [
                    {
                        "x": ["Q1 2026", "Q2 2026", "Q3 2026", "Q4 2026 (Est)"],
                        "y": [499, 499, 399, 349],
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": "SaaSify Enterprise Pricing ($/mo)",
                        "line": {"color": "#6366f1", "width": 3}
                    },
                    {
                        "x": ["Q1 2026", "Q2 2026", "Q3 2026", "Q4 2026 (Est)"],
                        "y": [599, 549, 549, 549],
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": "DataPulse AI Pro Tier ($/mo)",
                        "line": {"color": "#ec4899", "dash": "dot", "width": 3}
                    }
                ],
                "layout": {
                    "title": "Quarterly Enterprise Pricing Shift Comparison",
                    "paper_bgcolor": "rgba(0,0,0,0)",
                    "plot_bgcolor": "rgba(0,0,0,0)",
                    "font": {"color": "#e2e8f0"},
                    "xaxis": {"gridcolor": "#334155"},
                    "yaxis": {"gridcolor": "#334155"}
                }
            }

            r1 = Report(
                competitor_id=c1.id,
                title="Executive Market Brief: SaaSify Cloud Q3 Strategic Pricing Shift",
                summary="SaaSify Cloud has executed an aggressive 20% price cut on its core Enterprise tier, attempting to capture mid-market accounts. Immediate response recommended.",
                executive_brief_md="""# Executive Intelligence Brief: SaaSify Cloud

## Strategic Overview
On September 24, 2026, **SaaSify Cloud** executed an unannounced **20% price reduction** on its Enterprise subscription tier (lowered from **$499/mo** to **$399/mo**). Additionally, enterprise SAML/SSO enforcement—previously a $150 add-on—is now bundled at zero extra charge.

## Extracted Anomalies & Metrics
* **Enterprise Plan Base Rate**: Decreased from **$499/mo to $399/mo** (-20.0%).
* **Feature Bundling**: Added native SAML/SSO & Audit Logging without tier upgrading.
* **Target Segment Shift**: Positioned to undercut mid-market competitors during Q4 budget planning cycles.

## Fact-Checker Validation & Citations
* **Source 1**: `https://saasify.cloud/pricing` (Scraped 2026-09-24 14:02:11 UTC) - Confirmed `$399/month billed annually`.
* **Fact Check Confidence Score**: **96.4%** (Verified against primary web extraction).

## Strategic Threat Level: HIGH
This aggressive pricing maneuver is designed to block renewal conversations for competing SaaS platforms. 

### Recommended Counter-Actions
1. **Sales Enablement**: Release competitive battlecard highlighting our superior 99.99% uptime SLA vs SaaSify's recent outage history.
2. **Flexible Tiering**: Introduce annual prepay discount incentives to secure renewals prior to competitor outreach.
3. **Value Proposition**: Emphasize native AI workflows which SaaSify still charges as an add-on module.
""",
                plotly_spec_json=plotly_demo_spec,
                citations_json=[
                    {"source": "https://saasify.cloud/pricing", "claim": "Enterprise Plan $399/mo", "confidence": 0.98},
                    {"source": "Archive Snapshot 2026-08-15", "claim": "Previous Enterprise Rate $499/mo", "confidence": 0.95}
                ],
                version=1
            )
            session.add(r1)

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error seeding database: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    init_db()
