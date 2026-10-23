import re

def words(values):
    return {re.sub(r"[^a-z0-9+#.]", "", str(v).lower().strip())
            for v in values if str(v).strip()}

def score_job(profile, job):
    skills = words(profile.get("skills", []))
    required = words(job.get("required_skills", []))
    roles = [r.lower().strip() for r in profile.get("target_roles", []) if r.strip()]
    locations = [x.lower().strip() for x in profile.get("preferred_locations", []) if x.strip()]
    reasons = []
    missing = sorted(required - skills)

    if required:
        matched = required & skills
        score = round(len(matched) / len(required) * 65)
        reasons.append(f"Skills match: {len(matched)}/{len(required)} listed skills")
    else:
        score = 25
        reasons.append("No structured skill requirements; score is provisional")

    if any(role in job.get("title", "").lower() for role in roles):
        score += 20
        reasons.append("Role matches a target role")
    if not locations or not job.get("location") or any(loc in job["location"].lower() for loc in locations):
        score += 10
        reasons.append("Location is compatible with preferences")
    if profile.get("include_internships", True) or "intern" not in job.get("job_type", "").lower():
        score += 5
    else:
        reasons.append("Internships are excluded by your preferences")

    eligible = True
    grad = profile.get("graduation_year")
    years = job.get("graduation_years", [])
    if grad and years and grad not in years:
        eligible = False
        reasons.append(f"Graduation-year requirement excludes {grad}")
    if missing:
        reasons.append("Skills to build: " + ", ".join(missing))
    return {"score": min(score, 100), "eligible": eligible, "reasons": reasons, "missing_skills": missing}
