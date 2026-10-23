from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db

init_db()
client = TestClient(app)

def test_health_and_ai_status():
    assert client.get("/api/health").status_code == 200
    status = client.get("/api/ai/status")
    assert status.status_code == 200
    assert status.json()["auto_submit_enabled"] is False

def test_job_match_and_plan():
    profile = {
        "full_name": "Test Candidate", "degree": "B.E.", "graduation_year": 2027,
        "skills": ["Python", "FastAPI"], "preferred_locations": ["Remote"],
        "target_roles": ["Python Developer"], "include_internships": True,
        "resume_text": "Built a Python FastAPI project."
    }
    assert client.put("/api/profile", json=profile).status_code == 200
    job = {
        "title": "Python Developer Intern", "company": "Example",
        "location": "Remote", "job_type": "Internship", "experience": "Fresher",
        "graduation_years": [2027], "required_skills": ["Python", "FastAPI"],
        "description": "Build APIs", "source_url": "https://example.com/job/1",
        "source": "Test"
    }
    created = client.post("/api/jobs", json=job)
    assert created.status_code == 200
    job_id = created.json()["id"]
    matches = client.get("/api/matches").json()
    assert any(x["id"] == job_id and x["eligible"] for x in matches)
    plan = client.get(f"/api/agent/plan/{job_id}")
    assert plan.status_code == 200
    assert client.get("/api/automation/policy").json()["enabled"] is False

def test_application_prepare_and_review():
    jobs = client.get("/api/jobs").json()
    assert jobs
    job_id = jobs[0]["id"]
    response = client.post("/api/application-drafts/prepare", json={"job_id": job_id, "answers": {}})
    # Test job may be ineligible depending on database state; accept clear conflict response.
    assert response.status_code in (200, 409)
    policy = client.get("/api/automation/policy")
    assert policy.status_code == 200
    assert policy.json()["enabled"] is False

def test_notifications_and_reviews():
    assert client.get("/api/notifications").status_code == 200
    assert client.get("/api/reviews").status_code == 200


def test_naukri_search_url_uses_official_domain():
    from app.browser import build_naukri_search_url
    url = build_naukri_search_url("Python Developer", "Chennai")
    assert url == "https://www.naukri.com/python-developer-jobs-in-chennai"
    try:
        build_naukri_search_url("", "India")
        assert False, "empty role should be rejected"
    except ValueError:
        pass


def test_naukri_auto_discovery_status_and_disabled_guard(monkeypatch):
    monkeypatch.setenv("ENABLE_LOCAL_BROWSER", "false")
    status = client.get("/api/browser/auto-discovery")
    assert status.status_code == 200
    assert status.json()["enabled"] is False
    response = client.put("/api/browser/auto-discovery", json={"enabled": True, "interval_hours": 6})
    assert response.status_code == 400


def test_naukri_scheduler_due_logic():
    from app.auto_discovery import _due
    from datetime import datetime, timedelta
    assert not _due({"enabled": 0, "last_run": "", "interval_hours": 6})
    assert _due({"enabled": 1, "last_run": "", "interval_hours": 6})
    old = (datetime.now() - timedelta(hours=7)).isoformat(timespec="seconds")
    recent = datetime.now().isoformat(timespec="seconds")
    assert _due({"enabled": 1, "last_run": old, "interval_hours": 6})
    assert not _due({"enabled": 1, "last_run": recent, "interval_hours": 6})
