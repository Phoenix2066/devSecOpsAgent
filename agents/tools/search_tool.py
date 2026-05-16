import httpx
from bs4 import BeautifulSoup
from config import settings
import logging

logger = logging.getLogger(__name__)

async def search(query: str, num_results: int = 5) -> list[dict]:
    """
    Calls Serper API (preferred) or Tavily API.
    Returns list of {title, url, snippet}.
    """
    if settings.serper_api_key:
        return await _search_serper(query, num_results)
    elif settings.tavily_api_key:
        return await _search_tavily(query, num_results)
    else:
        logger.warning("No search API key configured (SERPER_API_KEY or TAVILY_API_KEY)")
        return []


async def _search_serper(query: str, num_results: int) -> list[dict]:
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": settings.serper_api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "q": query,
        "num": num_results
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            results = []
            for organic in data.get("organic", []):
                results.append({
                    "title": organic.get("title"),
                    "url": organic.get("link"),
                    "snippet": organic.get("snippet")
                })
            return results[:num_results]
        except Exception as e:
            logger.error(f"Serper search failed: {e}")
            return []


async def _search_tavily(query: str, num_results: int) -> list[dict]:
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "max_results": num_results
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            results = []
            for result in data.get("results", []):
                results.append({
                    "title": result.get("title"),
                    "url": result.get("url"),
                    "snippet": result.get("content")
                })
            return results
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []


async def fetch_page(url: str) -> str:
    """
    Fetches and extracts text content from a URL.
    Returns plain text (max 4000 chars).
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0, follow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove script and style elements
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()
            
            # Get text
            text = soup.get_text(separator=" ")
            
            # Break into lines and remove leading/trailing whitespace
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = "\n".join(chunk for chunk in chunks if chunk)
            
            return text[:4000]
        except Exception as e:
            logger.error(f"Failed to fetch page {url}: {e}")
            return ""
