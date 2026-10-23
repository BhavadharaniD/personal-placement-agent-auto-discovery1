"""Permitted discovery utilities. This module deliberately does not scrape Naukri.

The MVP accepts user-provided listings and can ingest RSS/Atom feeds from sources
that explicitly permit automated access. No login or anti-bot bypass is attempted.
"""
import re
import socket
import ipaddress
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import httpx

ALLOWED_SCHEMES = {"http", "https"}

def validate_public_feed_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.hostname:
        raise ValueError("Use a valid http(s) feed URL.")
    host = parsed.hostname.lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        raise ValueError("Local network URLs are not allowed.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(addr).is_global for addr in addresses):
            raise ValueError("Feed host must resolve only to public IP addresses.")
    except socket.gaierror as exc:
        raise ValueError("Could not resolve feed hostname.") from exc
    return url

async def fetch_feed(url: str):
    validate_public_feed_url(url)
    async with httpx.AsyncClient(timeout=12, follow_redirects=False,
                                 headers={"User-Agent": "PersonalPlacementAgent/0.2 (permitted-feed-reader)"}) as client:
        response = await client.get(url)
        if response.is_redirect:
            raise ValueError('Redirected feed URLs are not followed; enter the final public feed URL.')
        response.raise_for_status()
        if len(response.content) > 2_000_000:
            raise ValueError("Feed is larger than the 2 MB limit.")
        root = ET.fromstring(response.content)
    items = []
    # RSS 2.0
    for node in root.findall(".//item"):
        items.append({
            "title": (node.findtext("title") or "").strip(),
            "description": re.sub(r"<[^>]+>", " ", node.findtext("description") or "").strip()[:12000],
            "url": (node.findtext("link") or "").strip(),
            "published": (node.findtext("pubDate") or "").strip()
        })
    # Atom
    ns = {"a": "http://www.w3.org/2005/Atom"}
    if not items:
        for node in root.findall(".//a:entry", ns):
            link = node.find("a:link", ns)
            items.append({
                "title": (node.findtext("a:title", default="", namespaces=ns) or "").strip(),
                "description": re.sub(r"<[^>]+>", " ", node.findtext("a:summary", default="", namespaces=ns) or "").strip()[:12000],
                "url": link.attrib.get("href", "") if link is not None else "",
                "published": node.findtext("a:updated", default="", namespaces=ns) or ""
            })
    return items[:100]
