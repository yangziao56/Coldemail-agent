"""Web scraper module for fetching person information from the internet."""

from __future__ import annotations

import json
import os
import re
import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote_plus

import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

from config import DEFAULT_MODEL


@dataclass
class WebSearchResult:
    """Represents a single search result."""
    title: str
    url: str
    snippet: str


@dataclass
class ScrapedPersonInfo:
    """Scraped information about a person from the web."""
    name: str
    field: str
    raw_text: str
    education: list[str]
    experiences: list[str]
    skills: list[str]
    projects: list[str]
    honors: list[str] = field(default_factory=list)
    activities: list[str] = field(default_factory=list)
    contact_email: str | None = None
    papers: list[dict[str, Any]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


logger = logging.getLogger(__name__)


class WebScraper:
    """Scraper for fetching person information from the web."""

    # Common headers to mimic a browser request
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
    }

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def search_person(self, name: str, field: str, max_results: int = 5) -> list[WebSearchResult]:
        """Search for a person using multiple search engines."""
        query = f"{name} {field}"
        
        # Prefer Google CSE if configured, then Bing, Google HTML, then DDG
        results = self._search_google_api(query, max_results)

        if not results:
            results = self._search_bing(query, max_results)

        if not results:
            # Try Google HTML (may be blocked in some regions)
            results = self._search_google(query, max_results)
        
        if not results:
            # Fallback: try DuckDuckGo
            results = self._search_duckduckgo(query, max_results)
        
        logger.info("[search] query=%s results=%d", query, len(results))
        
        return results

    def _search_google_api(self, query: str, max_results: int) -> list[WebSearchResult]:
        """Search using Google Custom Search API if configured."""
        results: list[WebSearchResult] = []
        api_key = os.environ.get("GOOGLE_SEARCH_KEY") or os.environ.get("GOOGLE_CSE_KEY")
        cx = os.environ.get("GOOGLE_CX") or os.environ.get("GOOGLE_CSE_CX")
        if not api_key or not cx:
            return results
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {"q": query, "key": api_key, "cx": cx, "num": max_results}
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items") or []
            for item in items[:max_results]:
                title = item.get("title", "")
                link = item.get("link", "")
                snippet = item.get("snippet", "")
                if title and link:
                    results.append(WebSearchResult(title=title, url=str(link), snippet=snippet))
        except Exception as e:
            print(f"Google CSE error: {e}")
        return results

    def _search_duckduckgo(self, query: str, max_results: int) -> list[WebSearchResult]:
        """Search using DuckDuckGo HTML interface."""
        results: list[WebSearchResult] = []
        
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # If DDG returns anomaly/challenge page, skip
            if response.status_code != 200 or "anomaly" in response.text or "challenge-form" in response.text:
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            for result_div in soup.select(".result")[:max_results]:
                title_elem = result_div.select_one(".result__title a")
                snippet_elem = result_div.select_one(".result__snippet")
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    href = title_elem.get("href", "")
                    if "uddg=" in str(href):
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(str(href)).query)
                        href = parsed.get("uddg", [str(href)])[0]
                    
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    results.append(WebSearchResult(title=title, url=str(href), snippet=snippet))
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
        
        return results

    def _search_google(self, query: str, max_results: int) -> list[WebSearchResult]:
        """Fallback search using Google HTML (may be blocked in some regions)."""
        results: list[WebSearchResult] = []
        try:
            url = f"https://www.google.com/search?q={quote_plus(query)}&hl=zh-CN"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            # Google SERP structure varies; we look for h3 within result blocks.
            for g in soup.select("div.g")[:max_results]:
                title_elem = g.select_one("h3")
                link_elem = g.select_one("a")
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    href = link_elem.get("href", "")
                    snippet_elem = g.select_one("span.aCOpRe") or g.select_one("div.VwiC3b")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    results.append(WebSearchResult(title=title, url=str(href), snippet=snippet))
        except Exception as e:
            print(f"Google search error: {e}")
        return results

    def _search_bing(self, query: str, max_results: int) -> list[WebSearchResult]:
        """Fallback search using Bing."""
        results: list[WebSearchResult] = []
        
        try:
            url = f"https://www.bing.com/search?q={quote_plus(query)}&mkt=zh-CN&ensearch=0&FORM=HDRSC1"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            candidates = soup.select(".b_algo") or soup.select("li.b_algo") or soup.select("div.b_algo")
            for result_li in candidates[:max_results]:
                title_elem = result_li.select_one("h2 a") or result_li.select_one("a")
                snippet_elem = result_li.select_one(".b_caption p") or result_li.select_one("p")
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    href = title_elem.get("href", "")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    results.append(WebSearchResult(title=title, url=str(href), snippet=snippet))
        except Exception as e:
            print(f"Bing search error: {e}")
        
        return results

    def fetch_page_content(self, url: str, max_chars: int = 10000) -> str:
        """Fetch and extract main text content from a webpage."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()
            
            main_content = (
                soup.find("main")
                or soup.find("article")
                or soup.find(id=re.compile(r"content|main", re.I))
                or soup.find(class_=re.compile(r"content|main|article", re.I))
                or soup.body
            )
            
            if main_content:
                text = main_content.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)
            
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)
            
            return text[:max_chars]
            
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ""

    def scrape_person_info(self, name: str, field: str, max_pages: int = 3) -> tuple[str, list[str]]:
        """Scrape information about a person from multiple web pages."""
        search_results = self.search_person(name, field, max_results=max_pages + 2)
        
        if not search_results:
            return "", []
        
        all_text: list[str] = []
        sources: list[str] = []
        
        # Add search snippets first
        snippet_text = "\n".join(
            f"- {r.title}: {r.snippet}" 
            for r in search_results 
            if r.snippet
        )
        if snippet_text:
            all_text.append(f"Search Results Summary:\n{snippet_text}")
        
        # Fetch content from top pages
        pages_fetched = 0
        for result in search_results:
            if pages_fetched >= max_pages:
                break
            
            if any(skip in result.url.lower() for skip in ["youtube.com", "twitter.com", "facebook.com", "instagram.com"]):
                continue
            
            content = self.fetch_page_content(result.url)
            if content and len(content) > 100:
                all_text.append(f"--- Source: {result.url} ---\n{content}")
                sources.append(result.url)
                pages_fetched += 1
        
        combined_text = "\n\n".join(all_text)
        
        return combined_text, sources


def _enrich_papers_with_crossref(papers: list[dict[str, Any]], timeout: int = 10) -> list[dict[str, Any]]:
    """Fetch abstract and metadata from CrossRef using DOI or title."""
    if not papers:
        return []
    
    session = requests.Session()
    enriched: list[dict[str, Any]] = []
    
    for paper in papers:
        if not isinstance(paper, dict):
            continue  # skip non-dict items
        paper_copy = {**paper}
        doi = str(paper.get("doi") or "").strip()
        title = str(paper.get("title") or "").strip()
        if doi.lower() == "none":
            doi = ""

        url = None
        if doi:
            url = f"https://api.crossref.org/works/{quote_plus(doi)}"
        elif title:
            url = f"https://api.crossref.org/works?query.title={quote_plus(title)}&rows=1"
        
        if not url:
            enriched.append(paper_copy)
            continue
        
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            item = None
            if "message" in data:
                item = data["message"]
                # query endpoint returns a list
                if isinstance(item, dict) and "items" in item and isinstance(item["items"], list) and item["items"]:
                    item = item["items"][0]
            if not isinstance(item, dict):
                enriched.append(paper_copy)
                continue
            
            if not doi:
                paper_copy["doi"] = item.get("DOI", "") or paper_copy.get("doi", "")
            if not paper_copy.get("url"):
                urls = item.get("URL") or ""
                paper_copy["url"] = urls
            # Abstract may come in HTML-ish tags
            abstract = item.get("abstract", "")
            if abstract:
                cleaned = re.sub(r"<[^>]+>", "", abstract)
                paper_copy["abstract"] = cleaned.strip()
            else:
                # Try short description
                paper_copy["abstract"] = paper_copy.get("abstract", "")
            # Fill missing title/year/venue if available
            if not paper_copy.get("title") and item.get("title"):
                if isinstance(item.get("title"), list):
                    paper_copy["title"] = item["title"][0]
                else:
                    paper_copy["title"] = item["title"]
            if not paper_copy.get("year") and item.get("issued", {}).get("date-parts"):
                year = item["issued"]["date-parts"][0][0]
                paper_copy["year"] = str(year)
            if not paper_copy.get("venue") and item.get("container-title"):
                container = item.get("container-title")
                if isinstance(container, list) and container:
                    paper_copy["venue"] = container[0]
                elif isinstance(container, str):
                    paper_copy["venue"] = container
        except Exception as exc:
            print(f"CrossRef lookup failed for {title or doi}: {exc}")
        
        enriched.append(paper_copy)
    
    return enriched


def _configure_gemini() -> None:
    """Configure Gemini API with the API key from environment."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "Gemini API key not found. Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variable."
        )
    genai.configure(api_key=api_key)


def extract_person_profile_from_web(
    name: str,
    field: str,
    *,
    model: str = DEFAULT_MODEL,
    max_pages: int = 3,
) -> ScrapedPersonInfo:
    """
    Get information about a person using web search + scraped pages.
    Priority: scrape top search results, then use Gemini only for structuring.
    
    Args:
        name: The person's name
        field: Their field/domain (e.g., "AI research", "machine learning professor")
        model: Gemini model to use for extraction
        max_pages: Maximum pages to scrape (for fallback)
        
    Returns:
        ScrapedPersonInfo with extracted profile data
    """
    _configure_gemini()
    
    # Priority: web scraping (DuckDuckGo/Bing -> open top pages)
    try:
        scraper = WebScraper()
        raw_text, sources = scraper.scrape_person_info(name, field, max_pages=max_pages)
        
        if raw_text.strip():
            logger.info("[scrape] name=%s field=%s text_len=%d sources=%s", name, field, len(raw_text), sources)
            return _extract_from_scraped_text(name, field, raw_text, sources, model)
    except Exception as e:
        print(f"Web scraping error: {e}")
    
    # Final fallback: return basic info so user can still proceed
    return ScrapedPersonInfo(
        name=name,
        field=field,
        raw_text=f"Basic profile for {name} in {field}. Unable to fetch detailed information automatically.",
        education=[],
        experiences=[f"Works in {field}"],
        skills=[field],
        projects=[],
        sources=["Manual entry"],
    )


def _extract_from_scraped_text(
    name: str,
    field: str, 
    raw_text: str,
    sources: list[str],
    model: str
) -> ScrapedPersonInfo:
    """Extract structured profile from scraped text using Gemini."""
    prompt = (
        "You are an expert at extracting structured profile information about a person from web content. "
        "Extract accurate, non-hallucinated information only. "
        "Return strict JSON with keys:\n"
        "- name (string)\n"
        "- contact_email (string or null)\n"
        "- education (list of strings)\n"
        "- experiences (list of strings)\n"
        "- skills (list of strings)\n"
        "- projects (list of strings)\n"
        "- honors (list of strings)\n"
        "- activities (list of strings)\n"
        "- papers (list of objects with keys: title, venue, year, doi, url)\n\n"
        f"Extract profile information for {name} (field: {field}) from the following web content:\n\n"
        f"{raw_text[:15000]}\n\n"
        "Return JSON only with the structured profile. If a field is unknown, use empty list or null."
    )
    
    gemini_model = genai.GenerativeModel(
        model,
        generation_config={"response_mime_type": "application/json"}
    )
    response = gemini_model.generate_content(prompt)
    
    content = response.text
    if not content:
        raise RuntimeError("Gemini response did not contain any content")
    
    profile_data = json.loads(content)
    # Gemini 有时返回列表，取第一个 dict；若不是 dict，则视为无效
    if isinstance(profile_data, list):
        profile_data = profile_data[0] if profile_data and isinstance(profile_data[0], dict) else {}
    if not isinstance(profile_data, dict):
        raise RuntimeError("Gemini response is not a JSON object")
    
    def get_str_list(data: dict, key: str) -> list[str]:
        if not isinstance(data, dict):
            return []
        value = data.get(key, [])
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if item and str(item).strip()]
    
    def get_papers(data: dict) -> list[dict[str, Any]]:
        """Normalize papers to a list of dicts; accept strings as title-only."""
        papers_raw = data.get("papers", [])
        if not isinstance(papers_raw, list):
            return []
        cleaned: list[dict[str, Any]] = []
        for item in papers_raw:
            if isinstance(item, dict):
                title = str(item.get("title", "")).strip()
                venue = str(item.get("venue", "")).strip() if item.get("venue") else ""
                year = str(item.get("year", "")).strip() if item.get("year") else ""
                doi = str(item.get("doi", "")).strip()
                url = str(item.get("url", "")).strip()
                cleaned.append({
                    "title": title,
                    "venue": venue,
                    "year": year,
                    "doi": doi,
                    "url": url,
                })
            elif isinstance(item, str) and item.strip():
                cleaned.append({"title": item.strip(), "venue": "", "year": "", "doi": "", "url": ""})
        return cleaned
    
    papers = get_papers(profile_data)
    try:
        papers = _enrich_papers_with_crossref(papers)
    except Exception as e:
        print(f"CrossRef enrichment error: {e}")
    
    structured = ScrapedPersonInfo(
        name=profile_data.get("name", name).strip() or name,
        field=field,
        raw_text=raw_text,
        education=get_str_list(profile_data, "education"),
        experiences=get_str_list(profile_data, "experiences"),
        skills=get_str_list(profile_data, "skills"),
        projects=get_str_list(profile_data, "projects"),
        honors=get_str_list(profile_data, "honors"),
        activities=get_str_list(profile_data, "activities"),
        contact_email=str(profile_data.get("contact_email")).strip() if profile_data.get("contact_email") else None,
        papers=papers,
        sources=sources,
    )
    logger.info(
        "[scrape->struct] name=%s field=%s edu=%d exp=%d skills=%d projects=%d honors=%d activities=%d papers=%d sources=%d",
        structured.name,
        structured.field,
        len(structured.education),
        len(structured.experiences),
        len(structured.skills),
        len(structured.projects),
        len(structured.honors),
        len(structured.activities),
        len(structured.papers),
        len(structured.sources),
    )
    # Log paper titles and abstracts (if any) for debugging
    if structured.papers:
        titles = [p.get("title") for p in structured.papers]
        abstracts = [p.get("abstract") for p in structured.papers]
        logger.info("[papers] titles=%s", titles)
        logger.info("[papers] abstracts=%s", abstracts)
    return structured
