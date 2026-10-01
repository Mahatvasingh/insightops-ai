import pytest
from datetime import datetime, timezone, timedelta
from app.scheduler import is_competitor_due
from app.db.models import Competitor, AgentRun, ScrapingTarget

class DummyQuery:
    def __init__(self, items):
        self._items = items if isinstance(items, list) else ([items] if items else [])
    def filter(self, *args, **kwargs):
        # Return filtered query matching non-None items
        return self
    def order_by(self, *args, **kwargs):
        return self
    def first(self):
        return self._items[0] if self._items else None

class DummyDB:
    def __init__(self, active_run=None, last_run=None, last_target=None):
        self.active_run = active_run
        self.last_run = last_run
        self.last_target = last_target

    def query(self, model):
        if model == AgentRun:
            # First call in is_competitor_due is for active_run (running/awaiting_hitl).
            # Second call is for completed last_run.
            if self.active_run:
                items = [self.active_run]
                self.active_run = None  # Consume active_run for first call
                return DummyQuery(items)
            elif self.last_run:
                return DummyQuery([self.last_run])
            return DummyQuery([])
        if model == ScrapingTarget:
            return DummyQuery([self.last_target] if self.last_target else [])
        return DummyQuery([])

def test_scheduler_cadence_due_ness():
    comp_hourly = Competitor(id="c1", name="SaaSify", domain="saasify.cloud", scraping_cadence="Hourly")
    comp_daily = Competitor(id="c2", name="DataPulse", domain="datapulse.ai", scraping_cadence="Daily")

    # Active run running -> NOT due
    db_active = DummyDB(active_run=AgentRun(id="r1", competitor_id="c1", status="running"))
    assert is_competitor_due(comp_hourly, db_active) is False

    # Never scraped -> due immediately
    db_fresh = DummyDB(active_run=None, last_run=None, last_target=None)
    assert is_competitor_due(comp_hourly, db_fresh) is True

    # Scraped 30 mins ago (Hourly cadence) -> NOT due
    recent_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    db_recent = DummyDB(last_run=AgentRun(id="r2", competitor_id="c1", status="completed", created_at=recent_time))
    assert is_competitor_due(comp_hourly, db_recent) is False

    # Scraped 2 hours ago (Hourly cadence) -> DUE
    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    db_old = DummyDB(last_run=AgentRun(id="r3", competitor_id="c1", status="completed", created_at=old_time))
    assert is_competitor_due(comp_hourly, db_old) is True

    # Scraped 5 hours ago (Daily cadence) -> NOT due
    db_daily_recent = DummyDB(last_run=AgentRun(id="r4", competitor_id="c2", status="completed", created_at=old_time))
    assert is_competitor_due(comp_daily, db_daily_recent) is False
