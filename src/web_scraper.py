"""Web scraper module for fetching person information from the internet."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
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
    sources: list[str]


class WebScraper:
    """Scraper for fetching person information from the web."""

    # Common headers to mimic a browser request
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def search_person(self, name: str, field: str, max_results: int = 5) -> list[WebSearchResult]:
        """Search for a person using multiple search engines."""
        query = f"{name} {field}"
        
        # Try DuckDuckGo first
        results = self._search_duckduckgo(query, max_results)
        
        if not results:
            # Fallback: try Bing
            results = self._search_bing(query, max_results)
        
        return results

    def _search_duckduckgo(self, query: str, max_results: int) -> list[WebSearchResult]:
        """Search using DuckDuckGo HTML interface."""
        results: list[WebSearchResult] = []
        
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
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

    def _search_bing(self, query: str, max_results: int) -> list[WebSearchResult]:
        """Fallback search using Bing."""
        results: list[WebSearchResult] = []
        
        try:
            url = f"https://www.bing.com/search?q={quote_plus(query)}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            for result_li in soup.select(".b_algo")[:max_results]:
                title_elem = result_li.select_one("h2 a")
                snippet_elem = result_li.select_one(".b_caption p")
                
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
    Get information about a person using Gemini's knowledge.
    Falls back to web scraping if needed.
    
    Args:
        name: The person's name
        field: Their field/domain (e.g., "AI research", "machine learning professor")
        model: Gemini model to use for extraction
        max_pages: Maximum pages to scrape (for fallback)
        
    Returns:
        ScrapedPersonInfo with extracted profile data
    """
    _configure_gemini()
    
    # First, try to get information directly from Gemini's knowledge
    prompt = f"""You are a research assistant. Please provide detailed, factual information about {name} who works in the field of {field}.

Return a JSON object with the following structure:
{{
    "name": "Full name of the person",
    "found": true or false (whether you have reliable information about this person),
    "education": ["list of educational background - degrees, universities, years"],
    "experiences": ["list of work experiences - companies, positions, notable roles"],
    "skills": ["list of technical skills and expertise areas"],
    "projects": ["list of notable projects, research papers, companies founded, achievements"],
    "summary": "A brief 2-3 sentence summary about this person and their contributions"
}}

Important:
- If this is a well-known person (like Elon Musk, Andrew Ng, etc.), you should have information about them.
- Only set "found" to false if you truly have no information about this person.
- Include real, verifiable information only.
- Do not make up information.

Return JSON only."""

    try:
        gemini_model = genai.GenerativeModel(
            model,
            generation_config={"response_mime_type": "application/json"}
        )
        response = gemini_model.generate_content(prompt)
        
        content = response.text
        if not content:
            raise RuntimeError("Gemini response did not contain any content")
        
        profile_data = json.loads(content)
        
        # Check if Gemini found information
        if profile_data.get("found", False):
            def get_str_list(data: dict, key: str) -> list[str]:
                value = data.get(key, [])
                if not isinstance(value, list):
                    return []
                return [str(item).strip() for item in value if item and str(item).strip()]
            
            summary = profile_data.get("summary", "")
            raw_text = f"Summary: {summary}" if summary else f"Information about {name} in {field}"
            
            return ScrapedPersonInfo(
                name=profile_data.get("name", name).strip() or name,
                field=field,
                raw_text=raw_text,
                education=get_str_list(profile_data, "education"),
                experiences=get_str_list(profile_data, "experiences"),
                skills=get_str_list(profile_data, "skills"),
                projects=get_str_list(profile_data, "projects"),
                sources=["Gemini AI Knowledge Base"],
            )
    except Exception as e:
        print(f"Gemini knowledge extraction error: {e}")
    
    # Fallback: try web scraping
    try:
        scraper = WebScraper()
        raw_text, sources = scraper.scrape_person_info(name, field, max_pages=max_pages)
        
        if raw_text.strip():
            # Use Gemini to extract structured info from scraped content
            return _extract_from_scraped_text(name, field, raw_text, sources, model)
    except Exception as e:
        print(f"Web scraping fallback error: {e}")
    
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
        "Extract accurate information only - do not make up or guess information that isn't clearly stated. "
        "Return strict JSON with the keys: "
        "name (string - the person's full name), "
        "education (list of strings - degrees, institutions, years if available), "
        "experiences (list of strings - work experience, positions, affiliations), "
        "skills (list of strings - technical skills, expertise areas), "
        "projects (list of strings - notable projects, research, publications, achievements). "
        "If information for a category is not found, return an empty list for that category.\n\n"
        f"Extract profile information for {name} (field: {field}) from the following web content:\n\n"
        f"{raw_text[:15000]}\n\n"
        "Return JSON only with the structured profile."
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
    
    def get_str_list(data: dict, key: str) -> list[str]:
        value = data.get(key, [])
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if item and str(item).strip()]
    
    return ScrapedPersonInfo(
        name=profile_data.get("name", name).strip() or name,
        field=field,
        raw_text=raw_text,
        education=get_str_list(profile_data, "education"),
        experiences=get_str_list(profile_data, "experiences"),
        skills=get_str_list(profile_data, "skills"),
        projects=get_str_list(profile_data, "projects"),
        sources=sources,
    )
