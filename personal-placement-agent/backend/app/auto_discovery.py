"""Opt-in periodic discovery using the local, visible Naukri browser session."""
import asyncio
import json
from datetime import datetime, timedelta

from .db import connect
from .browser import auto_search_naukri

_TASK = None
_STOP = False


def _get_config():
    with connect() as db:
        row = db.execute("SELECT * FROM naukri_discovery_config WHERE id=1").fetchone()
    return dict(row) if row else {
        "enabled": 0, "interval_hours": 6, "last_run": "", "last_status": "Disabled",
        "last_added": 0, "last_error": ""
    }


def get_config():
    config = _get_config()
    config["enabled"] = bool(config.get("enabled"))
    return config


def configure(enabled: bool, interval_hours: int):
    interval_hours = max(1, min(int(interval_hours), 24))
    with connect() as db:
        db.execute(
            "UPDATE naukri_discovery_config SET enabled=?, interval_hours=?, last_status=?, last_error='' WHERE id=1",
            (1 if enabled else 0, interval_hours, "Scheduled" if enabled else "Disabled")
        )
    return get_config()


def _due(config):
    if not config.get("enabled"):
        return False
    last_run = (config.get("last_run") or "").strip()
    if not last_run:
        return True
    try:
        last = datetime.fromisoformat(last_run)
    except ValueError:
        return True
    return datetime.now() >= last + timedelta(hours=max(1, int(config.get("interval_hours") or 6)))


def _set_status(status, added=None, error=None, set_run=False):
    fields = ["last_status=?", "last_error=?"]
    values = [status, (error or "")[:1000]]
    if added is not None:
        fields.append("last_added=?")
        values.append(int(added))
    if set_run:
        fields.append("last_run=?")
        values.append(datetime.now().isoformat(timespec="seconds"))
    values.append(1)
    with connect() as db:
        db.execute(f"UPDATE naukri_discovery_config SET {', '.join(fields)} WHERE id=?", values)


def _save_listings(listings):
    added = 0
    with connect() as db:
        for item in listings:
            url = (item.get("source_url") or "").strip()
            title = (item.get("title") or "").strip()
            if not url or not title:
                continue
            if db.execute("SELECT id FROM jobs WHERE source_url=?", (url,)).fetchone():
                continue
            skills = item.get("skills") or []
            db.execute(
                "INSERT INTO jobs(title,company,location,job_type,experience,graduation_years,required_skills,description,source_url,source) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (title, item.get("company", ""), item.get("location", ""), "Full-time",
                 item.get("experience", "Unverified"), "[]", json.dumps(skills),
                 item.get("description", ""), url, "Naukri scheduled discovery")
            )
            added += 1
    return added


async def run_discovery_cycle():
    """Run one bounded discovery cycle now; caller controls whether it is scheduled."""
    from .main import profile_data, audit, add_notification
    from .browser import open_naukri_login

    config = _get_config()
    profile = profile_data()
    roles = profile.get("target_roles") or []
    locations = profile.get("preferred_locations") or ["India"]
    _set_status("Running", error="")
    try:
        # Reopen the persistent local profile after backend restarts when discovery
        # was already enabled. Login itself remains manual; no credentials are stored.
        await open_naukri_login()
        result = await auto_search_naukri(roles, locations, max_queries=6, per_query_limit=25)
        added = _save_listings(result.get("listings", []))
        if result.get("verification_needed"):
            status = "Needs manual verification"
            error = result.get("message", "Complete verification in the local browser.")
        else:
            status = "Completed"
            error = ""
        _set_status(status, added=added, error=error, set_run=True)
        audit("naukri_auto_discovery", f"queries={len(result.get('queries', []))}; found={result.get('found', 0)}; added={added}; status={status}")
        if added:
            add_notification(
                "New Naukri jobs discovered",
                f"Added {added} new listing(s) from scheduled Naukri searches. Review match scores, eligibility and listing freshness.",
                "success"
            )
        elif result.get("verification_needed"):
            add_notification("Naukri discovery needs verification", error, "warning")
        return {**result, "added": added, "status": status}
    except Exception as exc:
        message = str(exc)[:1000]
        _set_status("Error", added=0, error=message, set_run=True)
        try:
            audit("naukri_auto_discovery_error", message)
        except Exception:
            pass
        return {"found": 0, "added": 0, "status": "Error", "error": message}


async def _runner():
    global _STOP
    while not _STOP:
        try:
            config = _get_config()
            if _due(config):
                await run_discovery_cycle()
        except asyncio.CancelledError:
            raise
        except Exception:
            # Keep the service alive; the last status is surfaced through the API.
            pass
        await asyncio.sleep(30)


def start_auto_discovery_task():
    global _TASK, _STOP
    if _TASK is not None and not _TASK.done():
        return
    _STOP = False
    _TASK = asyncio.create_task(_runner(), name="naukri-auto-discovery")

async def stop_auto_discovery_task():
    global _TASK, _STOP
    _STOP = True
    if _TASK is not None:
        _TASK.cancel()
        try:
            await _TASK
        except asyncio.CancelledError:
            pass
        _TASK = None
