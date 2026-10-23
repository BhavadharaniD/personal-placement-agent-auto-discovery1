"""Optional local headed browser launcher.

This does not automate applications or bypass login controls. User signs in manually.
Persistent browser state is sensitive and remains in a local, gitignored directory.
"""
import os
from pathlib import Path

# Hold references so the headed browser remains open during this backend process.
_ACTIVE_PLAYWRIGHT = None
_ACTIVE_CONTEXT = None

async def open_naukri_login():
    if os.getenv("ENABLE_LOCAL_BROWSER", "false").lower() != "true":
        raise RuntimeError("Browser integration is disabled. Set ENABLE_LOCAL_BROWSER=true after reviewing the security notes.")
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError("Install Playwright and its browser: pip install playwright; playwright install chromium") from exc
    profile_dir = Path(__file__).resolve().parents[1] / "playwright_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    # Browser is headed and user-driven. No credentials are collected by this app.
    global _ACTIVE_PLAYWRIGHT, _ACTIVE_CONTEXT
    if _ACTIVE_CONTEXT is not None:
        return {"opened": True, "message": "The local browser session is already open."}
    playwright = await async_playwright().start()
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=False,
        args=["--disable-extensions"]
    )
    page = context.pages[0] if context.pages else await context.new_page()
    await page.goto("https://www.naukri.com/", wait_until="domcontentloaded", timeout=30000)
    _ACTIVE_PLAYWRIGHT = playwright
    _ACTIVE_CONTEXT = context
    # Keep context and playwright alive in the local process for the browser session.
    return {"opened": True, "message": "Naukri opened. Sign in manually; this MVP will not store your password or submit applications."}


async def fill_reviewed_profile_fields(field_map, profile_values):
    """Fill only explicitly mapped, non-sensitive text fields on a Naukri page.

    This never clicks submit. The caller must verify a user-approved draft first.
    field_map is a list of {"selector": "...", "profile_key": "..."}.
    """
    if _ACTIVE_CONTEXT is None:
        raise RuntimeError("Open the local Naukri browser first.")
    pages = _ACTIVE_CONTEXT.pages
    page = pages[-1] if pages else await _ACTIVE_CONTEXT.new_page()
    host = __import__("urllib.parse", fromlist=["urlparse"]).urlparse(page.url).hostname or ""
    if not (host == "naukri.com" or host.endswith(".naukri.com")):
        raise RuntimeError("The active browser page is not on naukri.com.")
    allowed_keys = {"full_name", "degree", "graduation_year", "skills"}
    filled = []
    blocked = []
    sensitive_words = ("password", "passwd", "otp", "captcha", "token", "aadhaar",
                       "aadhar", "pan", "salary", "notice", "birth", "gender",
                       "disability", "authorization", "email", "phone", "mobile")
    for item in field_map:
        selector = str(item.get("selector", "")).strip()
        key = str(item.get("profile_key", "")).strip()
        if not selector or key not in allowed_keys:
            blocked.append({"selector": selector, "reason": "Only explicitly mapped verified profile fields are allowed."})
            continue
        locator = page.locator(selector)
        count = await locator.count()
        if count != 1:
            blocked.append({"selector": selector, "reason": "Selector must match exactly one field."})
            continue
        field = locator.first
        field_type = (await field.get_attribute("type") or "text").lower()
        field_name = ((await field.get_attribute("name")) or "").lower()
        field_id = ((await field.get_attribute("id")) or "").lower()
        identity = field_name + " " + field_id
        if field_type in {"password", "hidden", "file", "submit", "button", "checkbox", "radio", "image"}:
            blocked.append({"selector": selector, "reason": f"Field type '{field_type}' is not fillable."})
            continue
        if any(word in identity for word in sensitive_words):
            blocked.append({"selector": selector, "reason": "Potentially sensitive field is blocked."})
            continue
        tag = (await field.evaluate("(el) => el.tagName.toLowerCase()")).lower()
        if tag not in {"input", "textarea"}:
            blocked.append({"selector": selector, "reason": "Only text inputs and textareas are supported."})
            continue
        value = profile_values.get(key)
        if value is None or value == "":
            blocked.append({"selector": selector, "reason": "No verified profile value is available."})
            continue
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        await field.fill(str(value))
        filled.append({"selector": selector, "profile_key": key})
    return {"filled": filled, "blocked": blocked, "submitted": False}


def _slug(value: str) -> str:
    import re
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:100].strip("-")


def build_naukri_search_url(role: str, location: str = "India") -> str:
    """Build a normal, user-visible Naukri search URL without querying the site."""
    role_slug = _slug(role)
    location_slug = _slug(location or "India") or "india"
    if not role_slug:
        raise ValueError("Enter a target role from your placement profile.")
    return f"https://www.naukri.com/{role_slug}-jobs-in-{location_slug}"


async def open_naukri_search(role: str, location: str = "India"):
    """Open an official Naukri search URL; does not extract or scrape listings.

    Search navigation is user-visible. Naukri results stay on the official site;
    this module deliberately does not parse page content or automate result collection.
    """
    url = build_naukri_search_url(role, location)
    # Open the local persistent browser if the user has not opened it yet.
    if _ACTIVE_CONTEXT is None:
        await open_naukri_login()
    pages = _ACTIVE_CONTEXT.pages
    page = pages[-1] if pages else await _ACTIVE_CONTEXT.new_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    return {
        "opened": True,
        "url": url,
        "role": role.strip(),
        "location": (location or "India").strip(),
        "message": "Opened the official Naukri search page. Results are not scraped or copied; use Naukri's own filters and save/import listings through permitted sources.",
        "listings_extracted": False,
    }


async def _collect_jobs_from_page(page, limit: int = 30):
    limit = max(1, min(int(limit), 30))
    results = await page.evaluate(r"""(limit) => {
      const clean = (el) => (el?.innerText || el?.textContent || '').replace(/\s+/g, ' ').trim();
      const unique = new Map();
      const anchors = Array.from(document.querySelectorAll('a[href*="job-listings"]')).filter(a => a.getClientRects().length > 0 && getComputedStyle(a).visibility !== 'hidden');
      for (const a of anchors) {
        const href = new URL(a.href, location.href).href.split('?')[0];
        if (!/^https?:\/\/(www\.)?naukri\.com\//i.test(href)) continue;
        if (unique.has(href)) continue;
        let card = a.closest('.srp-jobtuple-wrapper, .cust-job-tuple, article, [data-job-id]');
        if (!card) {
          let node = a;
          for (let i = 0; i < 5 && node.parentElement; i++, node = node.parentElement) {
            const text = clean(node);
            if (text.length >= 80 && text.length <= 3500) { card = node; break; }
          }
        }
        if (!card) continue;
        const pick = (selectors) => {
          for (const selector of selectors) {
            const el = card.querySelector(selector);
            const value = clean(el);
            if (value) return value;
          }
          return '';
        };
        const title = pick(['.title', 'a.title', 'h2 a', 'h3 a']) || clean(a);
        const company = pick(['.comp-name', '.comp-name a', '.companyInfo a', '[class*="company"] a']);
        const jobLocation = pick(['.locWdth', '[class*="location"]', '[class*="locWdth"]']);
        const experience = pick(['.expwdth', '[class*="experience"]', '[class*="expwdth"]']);
        const description = pick(['.job-desc', '[class*="job-description"]', '[class*="description"]']) || clean(card).slice(0, 1800);
        const skills = Array.from(card.querySelectorAll('.tags-gt, [class*="skill"]'))
          .map(clean).filter(Boolean).filter((x, i, arr) => arr.indexOf(x) === i).slice(0, 20);
        if (!title || title.length > 250) continue;
        unique.set(href, {title, company, location: jobLocation, experience, description, skills, source_url: href});
        if (unique.size >= limit) break;
      }
      return Array.from(unique.values());
    }""", limit)
    return results


def _page_requires_user_verification(url: str, text: str) -> bool:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.hostname and not (parsed.hostname == "naukri.com" or parsed.hostname.endswith(".naukri.com")):
        return True
    url_lower = url.lower()
    text_lower = (text or "").lower()[:12000]
    signals = ("captcha", "verify you are human", "security verification", "unusual traffic",
               "login to continue", "sign in to continue", "enter otp", "one time password")
    return any(x in url_lower for x in ("/login", "/signin", "/captcha", "/verify")) or any(x in text_lower for x in signals)


async def collect_visible_naukri_jobs(limit: int = 30):
    """Collect visible cards from the currently open Naukri results page."""
    if _ACTIVE_CONTEXT is None:
        raise RuntimeError("Open the local Naukri browser and sign in first.")
    pages = _ACTIVE_CONTEXT.pages
    page = pages[-1] if pages else await _ACTIVE_CONTEXT.new_page()
    from urllib.parse import urlparse
    host = urlparse(page.url).hostname or ""
    if not (host == "naukri.com" or host.endswith(".naukri.com")):
        raise RuntimeError("Navigate to a Naukri job search results page first.")
    if "job-listings" not in page.url and "jobs-in-" not in page.url:
        raise RuntimeError("Open a Naukri job search results page before importing listings.")
    results = await _collect_jobs_from_page(page, limit)
    return {
        "url": page.url,
        "listings": results,
        "count": len(results),
        "note": "Only currently rendered search-result cards were checked. No pagination was performed."
    }


async def auto_search_naukri(roles, locations, max_queries: int = 6, per_query_limit: int = 25):
    """Run a bounded, user-enabled cycle through visible Naukri search results.

    Uses ordinary visible search URLs and DOM-rendered cards only. It does not use
    hidden APIs, click pagination, bypass CAPTCHA/MFA, or submit applications.
    """
    if _ACTIVE_CONTEXT is None:
        raise RuntimeError("Open the local Naukri browser and sign in once before enabling scheduled discovery.")
    roles = [str(x).strip() for x in roles if str(x).strip()][:10]
    locations = [str(x).strip() for x in locations if str(x).strip()] or ["India"]
    locations = locations[:5]
    if not roles:
        raise RuntimeError("Add at least one target role in My profile before enabling discovery.")

    queries = []
    for role in roles:
        for location in locations:
            queries.append((role, location))
            if len(queries) >= max(1, min(max_queries, 6)):
                break
        if len(queries) >= max(1, min(max_queries, 6)):
            break

    collected = []
    searched = []
    verification_needed = False
    for role, location in queries:
        page = await _ACTIVE_CONTEXT.new_page()
        try:
            url = build_naukri_search_url(role, location)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3500)
            body_text = await page.locator("body").inner_text(timeout=5000)
            if _page_requires_user_verification(page.url, body_text):
                verification_needed = True
                searched.append({"role": role, "location": location, "count": 0, "status": "user_verification_required"})
                break
            jobs = await _collect_jobs_from_page(page, per_query_limit)
            collected.extend(jobs)
            searched.append({"role": role, "location": location, "count": len(jobs), "status": "checked"})
        finally:
            await page.close()
    # Deduplicate within this cycle, too.
    unique = {}
    for item in collected:
        unique.setdefault(item.get("source_url"), item)
    return {
        "listings": list(unique.values()),
        "found": len(unique),
        "queries": searched,
        "verification_needed": verification_needed,
        "message": "Complete the requested Naukri verification in the local browser before the next scheduled run." if verification_needed else "Checked bounded visible search results; no pagination or application submission was performed."
    }
