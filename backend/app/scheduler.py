import logging
import uuid
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db.database import SyncSessionLocal
from app.db.models import Competitor
from app.api.agent import run_graph_background_task

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def check_and_run_cadence_jobs():
    """
    Scheduled job that queries active competitors and triggers agent runs
    based on their designated scraping cadence (Hourly, Daily, Weekly).
    """
    logger.info("Scheduler running cadence check for active competitors...")
    db = SyncSessionLocal()
    try:
        competitors = db.query(Competitor).filter(Competitor.is_active == True).all()
        for comp in competitors:
            target_url = comp.pricing_url or f"https://{comp.domain}/pricing"
            thread_id = f"sched_{uuid.uuid4().hex[:12]}"
            logger.info(f"Triggering scheduled run for competitor '{comp.name}' (Cadence: {comp.scraping_cadence})")
            
            run_graph_background_task(
                thread_id=thread_id,
                competitor_id=comp.id,
                competitor_name=comp.name,
                target_url=target_url,
                user_query=f"Scheduled automated market intelligence run ({comp.scraping_cadence})."
            )
    except Exception as e:
        logger.error(f"Error executing scheduled cadence jobs: {e}")
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        # Run cadence check job every 60 minutes
        scheduler.add_job(
            check_and_run_cadence_jobs,
            trigger=IntervalTrigger(minutes=60),
            id="cadence_check_job",
            replace_existing=True
        )
        scheduler.start()
        logger.info("APScheduler started successfully.")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler shut down.")
