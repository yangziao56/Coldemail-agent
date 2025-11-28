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

# Default model for Gemini
DEFAULT_MODEL = "gemini-2.0-flash"


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

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def search_person(self, name: str, field: str, max_results: int = 5) -> list[WebSearchResult]:
        """
        Search for a person using DuckDuckGo HTML search.
        
        Args:
            name: The person's name
            field: The field/domain they work in (e.g., "AI research", "machine learning")
            max_results: Maximum number of results to return
            
        Returns:
            List of WebSearchResult objects
        """
        # Build search query with name and field
        query = f"{name} {field}"
        
        # Try DuckDuckGo HTML search (no API key required)
        results = self._search_duckduckgo(query, max_results)
        
        if not results:
            # Fallback: try Bing search
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
            
            # Find search result elements
            for result_div in soup.select(".result")[:max_results]:
                title_elem = result_div.select_one(".result__title a")
                snippet_elem = result_div.select_one(".result__snippet")
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    href = title_elem.get("href", "")
                    # DuckDuckGo wraps URLs, try to extract actual URL
                    if "uddg=" in str(href):
                        # Extract URL from DuckDuckGo redirect
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(str(href)).query)
                        href = parsed.get("uddg", [str(href)])[0]
                    
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    results.append(WebSearchResult(
                        title=title,
                        url=str(href),
                        snippet=snippet,
                    ))
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
                    
                    results.append(WebSearchResult(
                        title=title,
                        url=str(href),
                        snippet=snippet,
                    ))
        except Exception as e:
            print(f"Bing search error: {e}")
        
        return results

    def fetch_page_content(self, url: str, max_chars: int = 10000) -> str:
        """
        Fetch and extract main text content from a webpage.
        
        Args:
            url: The URL to fetch
            max_chars: Maximum characters to return
            
        Returns:
            Extracted text content
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()
            
            # Try to find main content area
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
            
            # Clean up whitespace
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)
            
            return text[:max_chars]
            
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ""

    def scrape_person_info(
        self,
        name: str,
        field: str,
        max_pages: int = 3,
    ) -> tuple[str, list[str]]:
        """
        Scrape information about a person from multiple web pages.
        
        Args:
            name: The person's name
            field: Their field/domain
            max_pages: Maximum number of pages to scrape
            
        Returns:
            Tuple of (combined text content, list of source URLs)
        """
        search_results = self.search_person(name, field, max_results=max_pages + 2)
        
        if not search_results:
            raise ValueError(f"No search results found for '{name}' in field '{field}'")
        
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
            
            # Skip certain URLs that might not have useful content
            if any(skip in result.url.lower() for skip in ["youtube.com", "twitter.com", "facebook.com", "instagram.com"]):
                continue
            
            content = self.fetch_page_content(result.url)
            if content and len(content) > 100:
                all_text.append(f"--- Source: {result.url} ---\n{content}")
                sources.append(result.url)
                pages_fetched += 1
        
        combined_text = "\n\n".join(all_text)
        
        if not combined_text.strip():
            raise ValueError(f"Could not fetch any content for '{name}' in field '{field}'")
        
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
    Search the web for a person and extract structured profile information.
    
    Args:
        name: The person's name
        field: Their field/domain (e.g., "AI research", "machine learning professor")
        model: Gemini model to use for extraction
        max_pages: Maximum pages to scrape
        
    Returns:
        ScrapedPersonInfo with extracted profile data
    """
    scraper = WebScraper()
    
    # Scrape raw content from the web
    raw_text, sources = scraper.scrape_person_info(name, field, max_pages=max_pages)
    
    # Use Gemini to extract structured information
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
        f"{raw_text[:15000]}\n\n"  # Limit to avoid token limits
        "Return JSON only with the structured profile."
    )
    
    _configure_gemini()
    
    gemini_model = genai.GenerativeModel(
        model,
        generation_config={"response_mime_type": "application/json"}
    )
    response = gemini_model.generate_content(prompt)
    
    content = response.text
    if not content:
        raise RuntimeError("Gemini response did not contain any content")
    
    try:
        profile_data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse profile extraction response as JSON: {exc}") from exc
    
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
