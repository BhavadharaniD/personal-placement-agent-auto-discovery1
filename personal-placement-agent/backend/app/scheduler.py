"""Opt-in local scheduler for feed refreshes and in-app reminders."""
import os
import asyncio
from .db import connect
from .discovery import fetch_feed

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:
    BackgroundScheduler = None

scheduler = None

def daily_digest():
    added = 0
    with connect() as db:
        sources = db.execute("SELECT url FROM discovered_sources WHERE enabled=1").fetchall()
    for source in sources:
        try:
            items = asyncio.run(fetch_feed(source["url"]))
            with connect() as db:
                for item in items:
                    title, url = (item.get("title") or "").strip(), (item.get("url") or "").strip()
                    if not title or not url:
                        continue
                    exists = db.execute("SELECT id FROM jobs WHERE source_url=?", (url,)).fetchone()
                    if exists:
                        continue
                    db.execute(
                        "INSERT INTO jobs(title,description,source_url,source,job_type,experience) VALUES(?,?,?,?,?,?)",
                        (title, item.get("description", ""), url, source["url"], "Full-time", "Unverified")
                    )
                    added += 1
        except Exception:
            # A failing feed should not stop other feeds or the reminder.
            continue
    with connect() as db:
        count = db.execute("SELECT COUNT(*) AS n FROM jobs").fetchone()["n"]
        title = "Daily job-search digest"
        body = f"Saved listings: {count}. Newly collected from configured feeds: {added}. Verify eligibility and expiry."
        db.execute("INSERT INTO notifications(title,body,kind) VALUES(?,?,?)", (title, body, "reminder"))

def start_scheduler():
    global scheduler
    if os.getenv("ENABLE_SCHEDULER", "false").lower() != "true" or scheduler is not None:
        return
    if BackgroundScheduler is None:
        return
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(daily_digest, "cron", hour=9, minute=0, id="daily_digest", replace_existing=True)
    scheduler.start()

def stop_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None
