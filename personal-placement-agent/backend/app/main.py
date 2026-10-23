import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .db import connect, init_db
from .models import ProfileIn, JobIn, StatusIn
from .matching import score_job

app = FastAPI(title="Personal Placement Agent API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

@app.on_event("startup")
def startup():
    init_db()

def profile_data():
    with connect() as db:
        row = db.execute("SELECT data FROM profile WHERE id=1").fetchone()
    return json.loads(row["data"]) if row else ProfileIn().model_dump()

def job_data(row):
    item = dict(row)
    item["graduation_years"] = json.loads(item.pop("graduation_years", "[]"))
    item["required_skills"] = json.loads(item.pop("required_skills", "[]"))
    return item

def audit(action, details):
    with connect() as db:
        db.execute("INSERT INTO audit_log(action,details) VALUES(?,?)", (action, details))

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/profile")
def get_profile():
    return profile_data()

@app.put("/api/profile")
def put_profile(profile: ProfileIn):
    data = profile.model_dump()
    with connect() as db:
        db.execute("INSERT INTO profile(id,data) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                   (json.dumps(data),))
    audit("profile_saved", "Candidate profile updated")
    return data

@app.get("/api/jobs")
def get_jobs():
    with connect() as db:
        rows = db.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    return [job_data(row) for row in rows]

@app.post("/api/jobs")
def post_job(job: JobIn):
    with connect() as db:
        cur = db.execute(
            "INSERT INTO jobs(title,company,location,job_type,experience,graduation_years,required_skills,description,source_url,source) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (job.title, job.company, job.location, job.job_type, job.experience,
             json.dumps(job.graduation_years), json.dumps(job.required_skills),
             job.description, job.source_url, job.source))
        job_id = cur.lastrowid
    audit("job_added", f"{job.title} at {job.company}")
    return {"id": job_id, **job.model_dump()}

@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int):
    with connect() as db:
        if not db.execute("SELECT id FROM jobs WHERE id=?", (job_id,)).fetchone():
            raise HTTPException(404, "Job not found")
        db.execute("DELETE FROM applications WHERE job_id=?", (job_id,))
        db.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    audit("job_deleted", f"Job id {job_id}")
    return {"deleted": True}

@app.get("/api/matches")
def get_matches():
    profile = profile_data()
    with connect() as db:
        rows = db.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
        apps = {r["job_id"]: dict(r) for r in db.execute("SELECT * FROM applications").fetchall()}
    result = []
    for row in rows:
        job = job_data(row)
        result.append({**job, **score_job(profile, job), "application": apps.get(job["id"])})
    return sorted(result, key=lambda x: (x["eligible"], x["score"]), reverse=True)

@app.post("/api/applications/{job_id}")
def set_application(job_id: int, body: StatusIn):
    allowed = {"Saved","Needs review","Ready to apply","Applied","Assessment","Interview","Rejected","Offer","Withdrawn"}
    if body.status not in allowed:
        raise HTTPException(400, "Unsupported application status")
    with connect() as db:
        if not db.execute("SELECT id FROM jobs WHERE id=?", (job_id,)).fetchone():
            raise HTTPException(404, "Job not found")
        db.execute("INSERT INTO applications(job_id,status,notes) VALUES(?,?,?) ON CONFLICT(job_id) DO UPDATE SET status=excluded.status, notes=excluded.notes, updated_at=CURRENT_TIMESTAMP",
                   (job_id, body.status, body.notes))
    audit("application_status_changed", f"Job {job_id}: {body.status}")
    return {"job_id": job_id, "status": body.status}

@app.get("/api/applications")
def get_applications():
    with connect() as db:
        rows = db.execute("SELECT a.*,j.title,j.company,j.source_url FROM applications a JOIN jobs j ON j.id=a.job_id ORDER BY a.updated_at DESC").fetchall()
    return [dict(row) for row in rows]

@app.get("/api/audit")
def get_audit():
    with connect() as db:
        rows = db.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 100").fetchall()
    return [dict(row) for row in rows]

@app.get("/api/agent/plan/{job_id}")
def get_plan(job_id: int):
    job = next((j for j in get_matches() if j["id"] == job_id), None)
    if not job:
        raise HTTPException(404, "Job not found")
    steps = [
        {"step":"verify_listing","description":"Open the original listing and verify that it is current."},
        {"step":"check_eligibility","description":"Verify graduation year, experience, location and skills."},
        {"step":"prepare_resume","description":"Prepare a truthful job-specific resume."},
        {"step":"prepare_answers","description":"Draft answers only from verified profile information."},
        {"step":"review","description":"Review the employer, role, resume and form fields before submission."},
        {"step":"track","description":"Record the outcome and future assessment or interview dates."}
    ]
    if not job["eligible"]:
        steps.insert(0, {"step":"eligibility_warning","description":"Eligibility mismatch detected. Do not apply until resolved."})
    return {"job_id":job_id,"title":job["title"],"score":job["score"],"eligible":job["eligible"],
            "reasons":job["reasons"],"steps":steps,"submission_enabled":False}


# --- Extended AI, discovery, review, notifications and interview endpoints ---
from pydantic import BaseModel, Field
from typing import Optional
try:
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

from .llm import generate as llm_generate, configured as llm_configured
from .discovery import fetch_feed, validate_public_feed_url
from .browser import open_naukri_login, open_naukri_search, collect_visible_naukri_jobs
import os

class TailorIn(BaseModel):
    job_id: int
    resume_text: Optional[str] = None

class DiscoverIn(BaseModel):
    feed_url: str

class NaukriSearchIn(BaseModel):
    role: str = Field(min_length=1, max_length=100)
    location: str = Field(default="India", max_length=100)

class NaukriAutoDiscoveryIn(BaseModel):
    enabled: bool
    interval_hours: int = Field(default=6, ge=1, le=24)

class DraftApplicationIn(BaseModel):
    job_id: int
    answers: dict = Field(default_factory=dict)

class ReviewIn(BaseModel):
    decision: str

class InterviewIn(BaseModel):
    job_id: int
    focus: str = "technical interview"

def add_notification(title, body, kind="info"):
    with connect() as db:
        db.execute("INSERT INTO notifications(title,body,kind) VALUES(?,?,?)", (title, body, kind))

def get_job_or_404(job_id):
    job = next((j for j in get_matches() if j["id"] == job_id), None)
    if not job:
        raise HTTPException(404, "Job not found")
    return job

@app.get("/api/ai/status")
def ai_status():
    return {
        "llm_configured": llm_configured(),
        "browser_enabled": os.getenv("ENABLE_LOCAL_BROWSER", "false").lower() == "true",
        "auto_submit_enabled": False,
        "notes": "AI calls use the configured LLM provider. Credentials are backend-only. Actual Naukri submission is not enabled."
    }

@app.post("/api/ai/tailor-resume")
def tailor_resume(body: TailorIn):
    job = get_job_or_404(body.job_id)
    profile = profile_data()
    resume = (body.resume_text or profile.get("resume_text") or "").strip()
    if not resume:
        raise HTTPException(400, "Add resume text in My profile first.")
    if llm_configured():
        try:
            output = llm_generate(
                "You are a careful career-writing assistant. Never invent experience, qualifications, dates, employers, projects, metrics or skills. Preserve factual claims. Return a tailored resume and a short list of changes.",
                "Tailor this resume to the job below. Keep all claims grounded in the resume. Clearly flag missing requirements instead of pretending the candidate has them.\\n\\nJOB:\\n" +
                json.dumps({k: job.get(k) for k in ["title","company","description","required_skills"]}, ensure_ascii=False) +
                "\\n\\nRESUME:\\n" + resume
            )
            mode = "llm"
        except RuntimeError as exc:
            output = "AI provider unavailable: " + str(exc) + "\\n\\n" + _resume_fallback(resume, job)
            mode = "fallback"
    else:
        output = _resume_fallback(resume, job)
        mode = "fallback"
    audit("resume_tailored", f"Prepared resume draft for job {body.job_id}; mode={mode}")
    return {"job_id": body.job_id, "mode": mode, "draft": output, "requires_user_review": True}

def _resume_fallback(resume, job):
    required = job.get("required_skills", [])
    resume_lower = resume.lower()
    matched = [s for s in required if s.lower() in resume_lower]
    missing = [s for s in required if s.lower() not in resume_lower]
    return (
        f"RESUME REVIEW FOR: {job.get('title')} — {job.get('company') or 'Company not specified'}\\n\\n"
        "Suggested truthful tailoring steps:\\n"
        f"• Put relevant skills near the top: {', '.join(matched) if matched else 'identify only skills you can substantiate'}\\n"
        "• Reorder existing projects and experience to emphasize relevant evidence.\\n"
        "• Keep dates, qualifications, employers and results exactly factual.\\n"
        f"• Requirements not found in the resume text (verify before claiming): {', '.join(missing) if missing else 'none detected by keyword scan'}\\n\\n"
        "ORIGINAL RESUME TEXT (edit manually after review):\\n" + resume
    )

@app.post("/api/discovery/feed")
async def discover_feed(body: DiscoverIn):
    try:
        validate_public_feed_url(body.feed_url)
        items = await fetch_feed(body.feed_url)
    except Exception as exc:
        raise HTTPException(400, f"Could not read feed: {exc}")
    added, skipped = 0, 0
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO discovered_sources(url,source_type,enabled) VALUES(?,?,1)",
                   (body.feed_url, "rss_atom"))
        for item in items:
            title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            if not title or not url:
                skipped += 1
                continue
            existing = db.execute("SELECT id FROM jobs WHERE source_url=?", (url,)).fetchone()
            if existing:
                skipped += 1
                continue
            db.execute(
                "INSERT INTO jobs(title,company,description,source_url,source,job_type,experience) VALUES(?,?,?,?,?,?,?)",
                (title, "", item.get("description", ""), url, body.feed_url, "Full-time", "Unverified")
            )
            added += 1
    audit("feed_discovery", f"Feed {body.feed_url}: added={added}, skipped={skipped}")
    if added:
        add_notification("New job listings collected", f"Added {added} listing(s) from a permitted feed.", "success")
    return {"fetched": len(items), "added": added, "skipped": skipped,
            "note": "Feed entries are unverified. Review employer, eligibility and expiry before applying."}

@app.post("/api/browser/open-naukri")
async def browser_open_naukri():
    try:
        result = await open_naukri_login()
        audit("browser_opened", "Opened local headed Naukri browser for manual sign-in")
        return result
    except Exception as exc:
        raise HTTPException(400, str(exc))

@app.post("/api/browser/search-naukri")
async def browser_search_naukri(body: NaukriSearchIn):
    """Open a profile-guided official Naukri search; do not scrape results."""
    try:
        result = await open_naukri_search(body.role, body.location)
        audit("naukri_search_opened", f"Opened official search for role={body.role!r}, location={body.location!r}")
        return result
    except Exception as exc:
        raise HTTPException(400, str(exc))


@app.post("/api/browser/import-visible-jobs")
async def browser_import_visible_jobs():
    """User-triggered import of currently rendered Naukri search result cards."""
    try:
        result = await collect_visible_naukri_jobs(limit=30)
    except Exception as exc:
        raise HTTPException(400, str(exc))
    added, skipped = 0, 0
    with connect() as db:
        for item in result["listings"]:
            url = item.get("source_url", "").strip()
            title = item.get("title", "").strip()
            if not url or not title:
                skipped += 1
                continue
            if db.execute("SELECT id FROM jobs WHERE source_url=?", (url,)).fetchone():
                skipped += 1
                continue
            skills = item.get("skills") or []
            db.execute(
                "INSERT INTO jobs(title,company,location,job_type,experience,graduation_years,required_skills,description,source_url,source) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (title, item.get("company", ""), item.get("location", ""), "Full-time",
                 item.get("experience", "Unverified"), "[]", json.dumps(skills),
                 item.get("description", ""), url, "Naukri browser (user-triggered import)")
            )
            added += 1
    audit("naukri_visible_import", f"Visible listings: added={added}, skipped={skipped}")
    if added:
        add_notification("Naukri listings imported", f"Imported {added} visible listing(s). Review eligibility and listing freshness.", "success")
    return {"found": result["count"], "added": added, "skipped": skipped,
            "url": result["url"], "note": result["note"]}


@app.get("/api/browser/auto-discovery")
def get_naukri_auto_discovery():
    from .auto_discovery import get_config
    return get_config()


@app.put("/api/browser/auto-discovery")
async def set_naukri_auto_discovery(body: NaukriAutoDiscoveryIn):
    from .auto_discovery import configure
    if body.enabled:
        if os.getenv("ENABLE_LOCAL_BROWSER", "false").lower() != "true":
            raise HTTPException(400, "Set ENABLE_LOCAL_BROWSER=true in backend/.env and restart the backend first.")
        profile = profile_data()
        if not profile.get("target_roles"):
            raise HTTPException(400, "Add at least one target role in My profile before enabling automatic discovery.")
        try:
            # Opens the local browser if needed; user still signs in manually.
            await open_naukri_login()
        except Exception as exc:
            raise HTTPException(400, str(exc))
    config = configure(body.enabled, body.interval_hours)
    audit("naukri_auto_discovery_config", f"enabled={body.enabled}; interval_hours={body.interval_hours}")
    return {**config, "message": "Automatic discovery enabled. Sign in manually in the opened browser; first cycle starts shortly." if body.enabled else "Automatic Naukri discovery disabled."}


@app.post("/api/browser/auto-discovery/run-now")
async def run_naukri_auto_discovery_now():
    from .auto_discovery import run_discovery_cycle
    if os.getenv("ENABLE_LOCAL_BROWSER", "false").lower() != "true":
        raise HTTPException(400, "Set ENABLE_LOCAL_BROWSER=true in backend/.env and restart the backend first.")
    result = await run_discovery_cycle()
    if result.get("status") == "Error":
        raise HTTPException(400, result.get("error", "Discovery failed."))
    return result


@app.post("/api/application-drafts/prepare")
def prepare_application(body: DraftApplicationIn):
    job = get_job_or_404(body.job_id)
    profile = profile_data()
    if not job.get("eligible"):
        raise HTTPException(409, "Eligibility mismatch. Resolve it before preparing an application.")
    # Only draft fields are returned. Nothing is sent to a job portal.
    allowed_profile = {
        "full_name": profile.get("full_name", ""),
        "degree": profile.get("degree", ""),
        "graduation_year": profile.get("graduation_year"),
        "skills": profile.get("skills", []),
        "resume_text": profile.get("resume_text", "")
    }
    payload = {
        "job": {"title": job["title"], "company": job["company"], "url": job["source_url"]},
        "verified_profile_fields": allowed_profile,
        "draft_answers": body.answers,
        "checks": [
            "Verify company and current listing",
            "Verify every personal declaration",
            "Review tailored resume",
            "Confirm there is no duplicate application",
            "Check site rules before submission"
        ],
        "submission_enabled": False
    }
    with connect() as db:
        cur = db.execute("INSERT INTO review_requests(job_id,action,payload) VALUES(?,?,?)",
                         (body.job_id, "prepare_application", json.dumps(payload)))
        review_id = cur.lastrowid
    audit("application_prepared", f"Created review request {review_id} for job {body.job_id}")
    add_notification("Application draft ready", f"Review the prepared draft for {job['title']}.", "review")
    return {"review_id": review_id, **payload, "status": "pending_review"}

@app.get("/api/reviews")
def list_reviews():
    with connect() as db:
        rows = db.execute("""
          SELECT r.*, j.title, j.company FROM review_requests r
          JOIN jobs j ON j.id=r.job_id ORDER BY r.id DESC
        """).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        result.append(item)
    return result

@app.post("/api/reviews/{review_id}")
def review_request(review_id: int, body: ReviewIn):
    if body.decision not in {"approve_draft", "reject"}:
        raise HTTPException(400, "Decision must be approve_draft or reject.")
    with connect() as db:
        row = db.execute("SELECT * FROM review_requests WHERE id=?", (review_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Review request not found")
        status = "draft_approved" if body.decision == "approve_draft" else "rejected"
        db.execute("UPDATE review_requests SET status=?, reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
                   (status, review_id))
    audit("review_decision", f"Review {review_id}: {status}")
    return {"review_id": review_id, "status": status,
            "note": "Approval approves the draft only; it does not submit anything to Naukri."}

@app.post("/api/agent/interview-plan")
def interview_plan(body: InterviewIn):
    job = get_job_or_404(body.job_id)
    profile = profile_data()
    prompt = (
        f"Create a practical 7-day {body.focus} plan for this candidate and job. "
        "Include topics, daily exercises, 5 sample questions and answer evaluation criteria. "
        "Do not claim to know actual confidential assessment questions.\\nJOB: " +
        json.dumps({"title": job["title"], "description": job["description"],
                    "skills": job["required_skills"]}, ensure_ascii=False) +
        "\\nCANDIDATE SKILLS: " + ", ".join(profile.get("skills", []))
    )
    if llm_configured():
        try:
            plan = llm_generate("You are a placement mentor. Give a specific, realistic plan. Do not invent employer assessment details.", prompt)
            mode = "llm"
        except RuntimeError as exc:
            plan = _interview_fallback(job, body.focus) + "\\n\\nLLM note: " + str(exc)
            mode = "fallback"
    else:
        plan = _interview_fallback(job, body.focus)
        mode = "fallback"
    audit("interview_plan_created", f"Job {body.job_id}; focus={body.focus}")
    return {"job_id": body.job_id, "mode": mode, "plan": plan}

def _interview_fallback(job, focus):
    skills = job.get("required_skills") or ["problem solving", "communication", "role fundamentals"]
    lines = [f"7-day preparation plan — {job.get('title')} ({focus})", ""]
    for i in range(7):
        skill = skills[i % len(skills)]
        lines.append(f"Day {i+1}: Study {skill}; write a short explanation; solve 3 practice questions; review mistakes.")
    lines += ["", "Practice questions:",
              "1. Explain a project where you used one relevant skill.",
              "2. How would you debug a problem you cannot reproduce?",
              "3. Describe a trade-off in a technical solution.",
              "4. What would you learn first if a requirement were unfamiliar?",
              "5. Explain your approach to testing and verifying a solution.",
              "", "Evaluate answers for correctness, clarity, concrete examples and honest acknowledgment of limits."]
    return "\\n".join(lines)

@app.get("/api/notifications")
def get_notifications():
    with connect() as db:
        rows = db.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT 100").fetchall()
    return [dict(row) for row in rows]

@app.post("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int):
    with connect() as db:
        cur = db.execute("UPDATE notifications SET read=1 WHERE id=?", (notification_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Notification not found")
    return {"read": True}

@app.get("/api/automation/policy")
def automation_policy():
    return {
        "enabled": False,
        "reason": "Portal submission is deliberately disabled until a permitted integration is confirmed and tested.",
        "required_checks": ["eligibility", "duplicate detection", "employer verification", "truthful answers", "user approval for uncertain or sensitive fields"],
        "safe_actions_available": ["prepare drafts", "create review requests", "track application status"]
    }


from .scheduler import start_scheduler, stop_scheduler

@app.on_event("startup")
def start_opt_in_scheduler():
    start_scheduler()

@app.on_event("shutdown")
def stop_opt_in_scheduler():
    stop_scheduler()

@app.on_event("startup")
async def start_naukri_auto_discovery_loop():
    from .auto_discovery import start_auto_discovery_task
    start_auto_discovery_task()

@app.on_event("shutdown")
async def stop_naukri_auto_discovery_loop():
    from .auto_discovery import stop_auto_discovery_task
    await stop_auto_discovery_task()


class FillReviewedFieldsIn(BaseModel):
    review_id: int
    fields: list[dict] = Field(default_factory=list)

@app.post("/api/browser/fill-reviewed-fields")
async def fill_reviewed_fields(body: FillReviewedFieldsIn):
    """Fill reviewed, explicitly mapped profile fields only; never submits the form."""
    with connect() as db:
        review = db.execute("SELECT * FROM review_requests WHERE id=?", (body.review_id,)).fetchone()
    if not review:
        raise HTTPException(404, "Review request not found")
    if review["status"] != "draft_approved":
        raise HTTPException(409, "Approve this application draft in the review queue first.")
    if not body.fields:
        raise HTTPException(400, "Provide explicit selector-to-profile-field mappings.")
    profile = profile_data()
    try:
        result = await __import__("app.browser", fromlist=["fill_reviewed_profile_fields"]).fill_reviewed_profile_fields(
            body.fields,
            {"full_name": profile.get("full_name", ""),
             "degree": profile.get("degree", ""),
             "graduation_year": profile.get("graduation_year"),
             "skills": profile.get("skills", [])}
        )
    except Exception as exc:
        raise HTTPException(400, str(exc))
    audit("reviewed_fields_filled", f"Review {body.review_id}: filled={len(result['filled'])}, blocked={len(result['blocked'])}")
    return {**result, "submitted": False,
            "warning": "Review all fields manually. This endpoint never clicks Submit."}


class ExplainMatchIn(BaseModel):
    job_id: int

@app.post("/api/ai/explain-match")
def explain_match(body: ExplainMatchIn):
    job = get_job_or_404(body.job_id)
    profile = profile_data()
    context = {
        "job": {"title": job["title"], "company": job["company"], "description": job["description"],
                "required_skills": job["required_skills"], "location": job["location"]},
        "candidate": {"degree": profile.get("degree"), "graduation_year": profile.get("graduation_year"),
                      "skills": profile.get("skills", []), "target_roles": profile.get("target_roles", [])},
        "deterministic_score": job["score"], "eligibility_rule_result": job["eligible"],
        "rule_reasons": job["reasons"], "missing_skills": job["missing_skills"]
    }
    if llm_configured():
        try:
            explanation = llm_generate(
                "You are a cautious job-match analyst. Use only the provided facts. Do not infer eligibility facts that are missing. Clearly distinguish hard eligibility blockers from skill gaps. Keep the answer concise.",
                "Analyze this candidate-job match. Return: overall assessment, evidence supporting the match, hard blockers or unknowns, skill gaps, and next steps. Context:\\n" +
                json.dumps(context, ensure_ascii=False)
            )
            mode = "llm"
        except RuntimeError as exc:
            explanation = "LLM unavailable; showing rule-based evidence. " + str(exc) + "\\n\\n" + "\\n".join(job["reasons"])
            mode = "fallback"
    else:
        explanation = (
            f"Rule-based match score: {job['score']}%. "
            + ("Graduation-year rules passed based on the data provided. " if job["eligible"] else "Graduation-year mismatch detected. ")
            + "\\nEvidence:\\n- " + "\\n- ".join(job["reasons"])
            + ("\\n\\nSkills to build: " + ", ".join(job["missing_skills"]) if job["missing_skills"] else "\\n\\nNo listed skill gaps detected by keyword matching.")
            + "\\n\\nThis is a prioritization aid, not a hiring prediction. Verify the original listing."
        )
        mode = "fallback"
    return {"job_id": body.job_id, "score": job["score"], "mode": mode,
            "explanation": explanation, "eligible_by_rules": job["eligible"]}
