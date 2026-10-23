"""Optional OpenAI-compatible LLM adapter. No credentials are sent to the model.

Configure LLM_BASE_URL, LLM_API_KEY and LLM_MODEL in the backend environment.
If not configured, endpoints return deterministic, local fallbacks.
"""
import os
import json
import urllib.request
import urllib.error

def configured():
    return bool(os.getenv("LLM_BASE_URL") and os.getenv("LLM_API_KEY") and os.getenv("LLM_MODEL"))

def generate(system_prompt: str, user_prompt: str) -> str:
    if not configured():
        raise RuntimeError("LLM is not configured. Set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL in the backend environment.")
    base = os.getenv("LLM_BASE_URL").rstrip("/")
    # Accept either the API root or a root already ending in /v1.
    url = base if base.endswith("/chat/completions") else base + "/chat/completions"
    payload = {
        "model": os.getenv("LLM_MODEL"),
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + os.getenv("LLM_API_KEY"),
                 "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc
