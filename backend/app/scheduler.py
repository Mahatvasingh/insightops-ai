import logging
import uuid
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db.database import SyncSessionLocal
from app.db.models import Competitor, AgentRun, ScrapingTarget
from app.api.agent import run_graph_background_task

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
executor = ThreadPoolExecutor(max_workers=4)

CADENCE_HOURS = {
    "Hourly": 1,
    "Daily": 24,
    "Weekly": 168
}

def is_competitor_due(comp: Competitor, db_session) -> bool:
    """
    Computes whether a competitor is due for scheduled scraping based on:
    1. Cadence interval (Hourly: 1h, Daily: 24h, Weekly: 168h).
    2. Time since last completed AgentRun or ScrapingTarget.last_scraped_at.
    3. Skipping if a run is currently active ('running' or 'awaiting_hitl').
    """
    # 1. Skip if a run is currently active
    active_run = db_session.query(AgentRun).filter(
        AgentRun.competitor_id == comp.id,
        AgentRun.status.in_(["running", "awaiting_hitl"])
    ).first()
    if active_run and active_run.status in ["running", "awaiting_hitl"]:
        logger.info(f"Skipping scheduled run for '{comp.name}': active run in progress ({active_run.status}).")
        return False

    # 2. Determine required interval
    cadence = comp.scraping_cadence or "Hourly"
    interval_hours = CADENCE_HOURS.get(cadence, 1)

    # 3. Check last run or scrape time
    last_run = db_session.query(AgentRun).filter(
        AgentRun.competitor_id == comp.id,
        AgentRun.status == "completed"
    ).order_by(AgentRun.created_at.desc()).first()

    last_target = db_session.query(ScrapingTarget).filter(
        ScrapingTarget.competitor_id == comp.id
    ).order_by(ScrapingTarget.last_scraped_at.desc()).first()

    last_time = None
    if last_run and last_run.created_at:
        last_time = last_run.created_at
    elif last_target and last_target.last_scraped_at:
        last_time = last_target.last_scraped_at

    if not last_time:
        return True  # Never scraped before, due immediately

    now = datetime.now(timezone.utc)
    if last_time.tzinfo is None:
        last_time = last_time.replace(tzinfo=timezone.utc)

    elapsed_hours = (now - last_time).total_seconds() / 3600.0
    return elapsed_hours >= interval_hours

def check_and_run_cadence_jobs():
    """
    Scheduled job that queries active competitors and dispatches due runs
    to background worker threads honoring their configured scraping cadence.
    """
    logger.info("Scheduler evaluating cadence due-ness for active competitors...")
    db = SyncSessionLocal()
    try:
        competitors = db.query(Competitor).filter(Competitor.is_active == True).all()
        for comp in competitors:
            if is_competitor_due(comp, db):
                target_url = comp.pricing_url or f"https://{comp.domain}/pricing"
                thread_id = f"sched_{uuid.uuid4().hex[:12]}"
                logger.info(f"Submitting scheduled background job for competitor '{comp.name}' (Cadence: {comp.scraping_cadence}).")
                
                executor.submit(
                    run_graph_background_task,
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
        scheduler.add_job(
            check_and_run_cadence_jobs,
            trigger=IntervalTrigger(minutes=15),
            id="cadence_check_job",
            replace_existing=True
        )
        scheduler.start()
        logger.info("APScheduler started successfully (Interval: 15m cadence check).")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        executor.shutdown(wait=False)
        logger.info("APScheduler and worker pool shut down.")
