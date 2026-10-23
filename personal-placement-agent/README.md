# Personal Placement Agent — Extended MVP

A local-first job-search assistant using **Python FastAPI + React + SQLite**.

## Included
- Candidate profile, resume text, job listings, match scores and application tracker
- AI resume-tailoring endpoint with a deterministic fallback when no LLM is configured
- Explainable job matching and graduation-year eligibility rules
- Job discovery from RSS/Atom feeds that permit automated access, plus manual job entry
- Optional local, headed Playwright browser launch for manual Naukri sign-in and profile-guided official search URL launching (role + location)
- Application draft preparation and review queue; draft approval does not submit
- Optional daily in-app reminder scheduler
- Opt-in periodic Naukri discovery through a local, visible Playwright browser session: bounded role/location searches, visible-card extraction, duplicate prevention, saved listings, and in-app notifications
- Interview/skill plan endpoint
- Notifications and audit log
- Explicit policy endpoint showing that actual portal submission remains disabled

## Run backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

## Run frontend
In another terminal:
```bash
cd frontend
npm install
npm run dev
```
Open http://127.0.0.1:5173.

## Optional LLM
Copy `backend/.env.example` to a local untracked environment file or set the variables in your shell:
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`

The app never sends Naukri credentials, cookies, or browser state to the LLM. Resume and job content will be sent to your configured LLM provider when using AI tailoring/interview features; only enable this if that provider's privacy terms are acceptable to you. Never commit secrets.

## Optional browser
Install browser binaries with `playwright install chromium`, then set `ENABLE_LOCAL_BROWSER=true` in the backend environment. Use the endpoint `POST /api/browser/open-naukri` to open a local headed browser. Sign in manually. The profile-guided search launcher opens an official Naukri results page using a target role and preferred location from your profile. It does not scrape/copy listings or extract page content; use Naukri’s own interface and permitted job-alert/feed sources. The optional field-filling helper only fills explicitly mapped, non-sensitive text fields from verified profile data after a draft is approved; it does not discover form fields automatically or submit applications. It does not bypass CAPTCHA, MFA or anti-bot controls. Browser profile data is sensitive and gitignored.

## Optional scheduler
Set `ENABLE_SCHEDULER=true` to refresh explicitly configured public RSS/Atom feeds and create a daily in-app digest at 09:00 according to the backend machine's local time. Feed refresh only uses URLs you add and does not search Naukri or apply automatically.

## API endpoints added
- `GET /api/ai/status`
- `POST /api/ai/explain-match`
- `POST /api/ai/tailor-resume`
- `POST /api/discovery/feed`
- `POST /api/browser/open-naukri`
- `POST /api/browser/search-naukri` (opens a role/location search on the official Naukri site)
- `POST /api/browser/import-visible-jobs` (user-triggered import of currently rendered search-result cards, up to 30)
- `GET /api/browser/auto-discovery` (automatic discovery status)
- `PUT /api/browser/auto-discovery` (enable/disable scheduled searches; interval 1–24 hours)
- `POST /api/browser/auto-discovery/run-now` (run a bounded discovery cycle immediately)
- `POST /api/browser/fill-reviewed-fields` (fills explicitly mapped, non-sensitive profile text fields after draft approval; never submits)
- `POST /api/applications/prepare`
- `GET /api/reviews`
- `POST /api/reviews/{review_id}` (approves/rejects a draft only)
- `POST /api/agent/interview-plan`
- `GET /api/notifications`
- `POST /api/notifications/{notification_id}/read`
- `GET /api/automation/policy`

## Important limits
The Naukri import is a user-triggered, local-browser read of currently rendered result cards, limited to 30 per click. It is not an official Naukri API integration, and site markup or terms may change. Do not use it if the current terms for your account prohibit automated collection. Automatic Naukri discovery is opt-in and bounded; it searches only the configured profile roles/locations and currently rendered results, without pagination. Automatic form submission and unattended auto-apply are not enabled. No CAPTCHA/MFA/access-control bypass. Approval of an application draft is not a portal submission. Add authentication and HTTPS before exposing the service beyond localhost.

## React feature toolbox
The **AI tools** section includes profile-guided Naukri search launching, permitted RSS/Atom feed discovery with automatic deduplication and profile-based ranking, resume draft generation, interview-plan generation, application draft preparation, a review queue, notifications, and AI/browser status. It uses fallback generation when no LLM provider is configured.

## Run tests
```bash
cd backend
pytest -q
```
