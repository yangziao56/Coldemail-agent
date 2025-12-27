"""
Advisor crawler utilities (Gemini-based) with dual search discovery (DuckDuckGo + Google CSE).
Returns JSON-friendly dicts so Flask can call directly.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from dataclasses import asdict, dataclass
from typing import Iterable, List, Optional

import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

from config import DEFAULT_MODEL

# Default headers to reduce blocking
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.8",
}


@dataclass
class AdvisorProfile:
    name: str
    title: str
    mentor_type: str
    department: str
    research: str
    email: str
    homepage_url: str
    source_url: str
    school: str = ""
    college: str = ""
    education: list = None
    experiences: list = None
    skills: list = None
    projects: list = None

    def __post_init__(self):
        # Normalize list fields
        for field_name in ["education", "experiences", "skills", "projects"]:
            val = getattr(self, field_name)
            if val is None:
                setattr(self, field_name, [])
            elif isinstance(val, str):
                setattr(self, field_name, [val])
            elif not isinstance(val, list):
                setattr(self, field_name, list(val))

    def to_dict(self) -> dict:
        return asdict(self)


def get_gemini_model(model_name: Optional[str] = None):
    """
    Configure and return a Gemini GenerativeModel.
    Requires GEMINI_API_KEY or GOOGLE_API_KEY in environment.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not set for advisor crawler.")
    genai.configure(api_key=api_key)
    name = model_name or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    return genai.GenerativeModel(name)


def polite_sleep():
    time.sleep(random.uniform(1.5, 3.5))


def get_html(url: str, retries: int = 3, timeout: int = 20) -> str:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    for i in range(retries):
        try:
            r = session.get(url, timeout=timeout)
            if r.status_code == 200 and r.text.strip():
                r.encoding = r.apparent_encoding
                return r.text
            if r.status_code in (403, 429):
                time.sleep(8 + i * 5)
            else:
                time.sleep(2 + i * 2)
        except requests.RequestException:
            time.sleep(2 + i * 2)
    return ""


def is_faculty_link(url: str) -> bool:
    u = url.lower()
    # Positive hints
    positives = ["/faculty", "/people", "/profile", "/researcher", "/researchers", "/bio", "/cv"]
    # Negative filters to avoid staff/offices/recruiting/nav
    negatives = ["staff", "office", "recruit", "apply", "give", "alumni", "news", "events", "support"]
    if any(neg in u for neg in negatives):
        return False
    return any(key in u for key in positives)


def extract_detail_links(list_html: str, base_url: str) -> list[tuple[str, str]]:
    """
    Extract candidate detail links from a faculty list page.
    Filters by same hostname or containing 'faculty', 'people', 'profile'.
    """
    soup = BeautifulSoup(list_html, "lxml")
    links = []
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        name = a.get_text(strip=True)
        if not href or not name:
            continue
        # Skip in-page anchors or javascript links
        if href.startswith("#") or href.lower().startswith("javascript"):
            continue
        if not href.startswith("http"):
            href = requests.compat.urljoin(base_url, href)
        if not href.lower().startswith("http"):
            continue
        parsed = urlparse(href)
        if is_faculty_link(parsed.path):
            # drop fragments
            clean_href = href.split("#", 1)[0]
            # skip nav-like link texts or generic labels
            skip_tokens = {"skip to main content", "apply now!", "faculty & researchers", "offices", "staff", "people", "faculty", "faculty a–d", "faculty ai+d"}
            name_lc = name.lower()
            if name_lc in skip_tokens:
                continue
            if any(tok in name_lc for tok in ["people", "faculty", "staff"]):
                continue
            links.append((name, clean_href))

    seen, uniq = set(), []
    for name, u in links:
        if u not in seen:
            uniq.append((name, u))
            seen.add(u)
    return uniq


def browser_get_visible_text(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(800)
        txt = page.inner_text("body")
        browser.close()
    return re.sub(r"\n{3,}", "\n\n", txt).strip()


def llm_extract(profile_text: str, source_url: str, fallback_name: str, model) -> AdvisorProfile:
    """
    Use Gemini to extract advisor fields from visible page text.
    """
    prompt = f"""
You are an advisor profile extractor. Only extract what is explicitly in the text; do NOT guess.
If a field is missing, leave it empty.

Return strict JSON with keys:
- name
- title
- mentor_type
- department
- research (max 200 chars)
- email (only if a valid email pattern appears)
- homepage_url
- source_url
- education (list of strings)
- experiences (list of strings)
- skills (list of strings)
- projects (list of strings)

fallback_name: {fallback_name}
source_url: {source_url}

Visible Page Text (truncated):
{profile_text[:12000]}
""".strip()

    resp = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
    )

    raw = resp.text if hasattr(resp, "text") else str(resp)

    def _heuristic_profile() -> AdvisorProfile:
        """Fallback when JSON parsing fails: basic email/name scrape."""
        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", profile_text)
        email = email_match.group(0) if email_match else ""
        return AdvisorProfile(
            name=fallback_name,
            title="",
            mentor_type="",
            department="",
            research=profile_text[:300],
            email=email,
            homepage_url=source_url,
            source_url=source_url,
            school="",
            college="",
            education=[],
            experiences=[],
            skills=[],
            projects=[],
        )

    try:
        obj = json.loads(raw)
        if isinstance(obj, list):
            obj = obj[0] if obj and isinstance(obj[0], dict) else {}
    except Exception as exc:
        # Fallback to heuristic extraction instead of raising
        return _heuristic_profile()

    if not isinstance(obj, dict):
        return _heuristic_profile()

    if not obj.get("name"):
        obj["name"] = fallback_name
    obj["source_url"] = source_url
    # Ensure required keys exist
    for key in ["title", "mentor_type", "department", "research", "email", "homepage_url", "education", "experiences", "skills", "projects"]:
        obj.setdefault(key, "")
    # Normalize list fields before dataclass init
    for key in ["education", "experiences", "skills", "projects"]:
        val = obj.get(key, [])
        if isinstance(val, str):
            obj[key] = [val] if val.strip() else []
        elif not isinstance(val, list):
            try:
                obj[key] = list(val)
            except Exception:
                obj[key] = []
    return AdvisorProfile(**obj)


def clean_profiles_with_gemini(profiles: list[dict], model, max_items: int = 40) -> list[dict]:
    """
    Use Gemini to deduplicate and clean parsed profiles.
    - Merge duplicates (same email or obviously same person)
    - Fix garbled characters
    - Drop empty/meaningless entries
    - Drop entries that are not person names (e.g., people/faculty/staff/office/department/center/lab labels)
    """
    if not profiles:
        return profiles
    subset = profiles[:max_items]
    prompt = (
        "You are cleaning a list of advisor profiles. Merge duplicates (same email or clearly same name), "
        "fix garbled characters, and keep the richer fields when merging. Remove records with no meaningful name or "
        "that are NOT a person (e.g., names containing people/faculty/staff/office/department/center/lab/research). "
        "Return ONLY JSON array; do not include explanations.\n\n"
        "Required keys per item: name, title, mentor_type, department, research, email, homepage_url, "
        "source_url, school, college, education (list), experiences (list), skills (list), projects (list).\n"
        f"Input JSON:\n{subset}\n"
    )
    def _is_person(name: str) -> bool:
        n = (name or "").strip()
        if not n:
            return False
        lower = n.lower()
        bad_tokens = ["people", "faculty", "staff", "office", "department", "center", "lab", "research"]
        if any(tok in lower for tok in bad_tokens):
            return False
        if any(ch.isdigit() for ch in n):
            return False
        if len(n) < 2 or len(n) > 80:
            return False
        return True

    try:
        resp = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        raw = resp.text if hasattr(resp, "text") else str(resp)
        data = json.loads(raw)
        if isinstance(data, dict):
            data = data.get("profiles") or []
        if not isinstance(data, list):
            return profiles

        cleaned: list[dict] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            if not (item.get("name") or "").strip():
                continue
            if not _is_person(item.get("name", "")):
                continue
            for key in ["title", "mentor_type", "department", "research", "email", "homepage_url", "source_url", "school", "college"]:
                item.setdefault(key, "")
            for key in ["education", "experiences", "skills", "projects"]:
                val = item.get(key, [])
                if isinstance(val, str):
                    item[key] = [val] if val.strip() else []
                elif not isinstance(val, list):
                    try:
                        item[key] = list(val)
                    except Exception:
                        item[key] = []
            cleaned.append(item)
        return cleaned or profiles
    except Exception as exc:
        print(f"[crawler] Gemini clean_profiles failed: {exc}", flush=True)
        return profiles


def discover_list_url(query: str) -> Optional[str]:
    """
    Try DuckDuckGo HTML first; if not found, try Google Custom Search (GOOGLE_SEARCH_KEY/GOOGLE_CX).
    """
    # DuckDuckGo HTML
    print(f"[crawler] Discovering list page via DuckDuckGo: {query}", flush=True)
    search_url = f"https://duckduckgo.com/html/?q={requests.utils.quote(query)}"
    search_html = get_html(search_url)
    if search_html:
        soup = BeautifulSoup(search_html, "lxml")
        first = soup.select_one("a.result__a")
        if first and first.get("href"):
            href = first.get("href")
            if href and href.startswith("http"):
                return href

    # Google Custom Search
    api_key = os.environ.get("GOOGLE_SEARCH_KEY")
    cx = os.environ.get("GOOGLE_CX")
    if not api_key or not cx:
        print("[crawler] Google CSE not configured; skipping Google search", flush=True)
        return None

    try:
        print(f"[crawler] Discovering list page via Google CSE: {query}", flush=True)
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={"key": api_key, "cx": cx, "q": query, "num": 5},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"[crawler] Google CSE HTTP {resp.status_code}: {resp.text}", flush=True)
            return None
        data = resp.json()
        for item in data.get("items", []):
            link = item.get("link")
            if link and is_faculty_link(link):
                return link
    except Exception as exc:
        print(f"[crawler] Google CSE search error: {exc}", flush=True)
    return None


def crawl_advisors(
    school: str,
    college: Optional[str] = None,
    field: Optional[str] = None,
    list_url: Optional[str] = None,
    limit: Optional[int] = 30,
    model: str = DEFAULT_MODEL,
) -> List[dict]:
    """
    Crawl advisor profiles for a given school/college.
    If list_url is not provided, this function will try DuckDuckGo then Google CSE
    to find a probable faculty directory and crawl that page.
    """
    gemini_model = get_gemini_model(model_name=model)
    query = " ".join([s for s in [school, college, field, "faculty list"] if s])

    target_url = list_url
    if not target_url:
        target_url = discover_list_url(query)

    if not target_url:
        raise RuntimeError("Failed to determine faculty list URL for the provided school/college.")

    print(f"[crawler] Using list page: {target_url}", flush=True)

    list_html = get_html(target_url)
    if not list_html:
        raise RuntimeError("Failed to fetch faculty list page.")

    links = extract_detail_links(list_html, target_url)
    # Deduplicate links by URL while preserving order
    seen_links = set()
    dedup_links: list[tuple[str, str]] = []
    for nm, href in links:
        if href in seen_links:
            continue
        seen_links.add(href)
        dedup_links.append((nm, href))
    links = dedup_links

    # If the provided URL is already a profile page (no links), fall back to crawling it directly.
    if not links:
        links = [(school or "Profile", target_url)]

    print(f"[crawler] Found {len(links)} detail links for {school} / {college or ''} from {target_url}", flush=True)
    for idx, (nm, href) in enumerate(links[:10], 1):
        print(f"[crawler] link[{idx}]: name='{nm}' url={href}", flush=True)

    if limit:
        links = links[:limit]

    results: List[dict] = []

    for idx, (name, url) in enumerate(links, 1):
        try:
            print(f"[crawler] [{idx}/{len(links)}] fetch detail: {url}", flush=True)
            txt = browser_get_visible_text(url)
            profile = llm_extract(txt, url, name, gemini_model)
            profile.school = school
            profile.college = college or ""
            results.append(profile.to_dict())
            print(f"[crawler] [{idx}/{len(links)}] OK: {profile.name} ({profile.school}/{profile.college})", flush=True)
        except Exception as e:
            print(f"[crawler] [{idx}/{len(links)}] FAIL: {name} -> {e}", flush=True)
            results.append(
                AdvisorProfile(
                    name=name,
                    title="",
                    mentor_type="",
                    department="",
                    research="",
                    email="",
                    homepage_url="",
                    source_url=url,
                    school=school,
                    college=college or "",
                ).to_dict()
            )
        polite_sleep()
    # Deduplicate final results by source_url (fallback to name+email), keep the richer record
    def _score(record: dict) -> int:
        fields = ["title", "mentor_type", "department", "research", "email", "education", "experiences", "skills", "projects"]
        score = 0
        for f in fields:
            val = record.get(f)
            if isinstance(val, list):
                if any(str(x).strip() for x in val):
                    score += 1
            elif val and str(val).strip():
                score += 1
        return score

    deduped: list[dict] = []
    key_to_index: dict = {}
    for r in results:
        key = r.get("source_url") or (r.get("name"), r.get("email"))
        if key in key_to_index:
            idx = key_to_index[key]
            if _score(r) > _score(deduped[idx]):
                deduped[idx] = r
            continue
        key_to_index[key] = len(deduped)
        deduped.append(r)

    # Final Gemini cleaning/dedup (batch)
    cleaned = clean_profiles_with_gemini(deduped, gemini_model)
    return cleaned


def crawl_bulk(items: Iterable[dict], *, model: str = DEFAULT_MODEL, limit: Optional[int] = 20) -> List[dict]:
    output: List[dict] = []
    for item in items:
        school = item.get("school") or ""
        college = item.get("college") or ""
        field = item.get("field") or ""
        list_url = item.get("list_url") or None
        count_limit = item.get("limit") or limit
        if not school:
            continue
        try:
            print(f"[crawler] start: school={school}, college={college or '-'}, field={field or '-'}, limit={count_limit}", flush=True)
            results = crawl_advisors(
                school=school,
                college=college,
                field=field,
                list_url=list_url,
                limit=count_limit,
                model=model,
            )
            print(f"[crawler] done: school={school}, scraped={len(results)}", flush=True)
            output.extend(results)
        except Exception as exc:
            print(f"[crawler] error for {school}/{college or ''}: {exc}", flush=True)
            continue
    return output
