from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import Optional, List
import requests
import os
import json
import pingintel_api


from gord.utils.logger import Logger
from gord import metrics

from gord.settings import (
    NUMBER_SEARCH_RESULTS,
    BRAVE_SEARCH_URL,
    BRAVE_API_KEY,
    GOOGLE_PSE_API_KEY,
    GOOGLE_PSE_CX,
    GOOGLE_SEARCH_ENDPOINT
)

pingclient = pingintel_api.PingDataAPIClient(environment="staging", auth_token=os.environ['PING_DATA_STG_AUTH_TOKEN'])

_LOGGER = Logger()





class BraveSearchInput(BaseModel):
    q: str = Field(
        description="The search query string to send to Brave Search. Use natural language or keywords to find relevant web results."
    )
    count: Optional[int] = Field(
        default=10,
        description="Number of search results to return (default: 10, max: 20)"
    )
    country: Optional[str] = Field(
        default=None,
        description="Country code for localized results (e.g., 'US', 'GB', 'CA')"
    )


class PingAoaInput(BaseModel):
    address: str = Field(
        description="Address to enhance via Ping AOA"
    )

@tool(args_schema=PingAoaInput)
def ping_aoa_search(address: str) -> dict:
    """
    Enhances an address using the Ping Data API and returns detailed location information.
    
    If you provide an address to this tool, it will return enriched location data, specifically
    the information in the 'PG' and 'PH' sources. PG stands for Ping Geocoding, and PH stands for 
    Ping Hazard, which returns assessment data, flood zones, distance to coast ,etc about that location
    """
    metrics.increment('ping_aoa', 1)
    ret = pingclient.enhance(address=address, sources=["PG", "PH"], include_raw_response=True)
    _LOGGER._log(f"[ping_aoa_search] Address: {address}\nResponse: {json.dumps(ret, indent=2)[:8000]}")  
    return ret


@tool(args_schema=BraveSearchInput)
def brave_search(
    q: str,
    count: Optional[int] = NUMBER_SEARCH_RESULTS,
    country: Optional[str] = None
) -> dict:
    """
    Searches the web using Brave Search API and returns relevant results.
    
    Use this tool to find current information, news, company details, market data,
    or any other information available on the public web. Returns web page titles,
    snippets, URLs, and other metadata from the search results.
    """
    print('querying brave search api', q)
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": BRAVE_API_KEY,
    }
    
    params = {"q": q, "count": count}
    if country:
        params["country"] = country
    
    response = requests.get(BRAVE_SEARCH_URL, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    metrics.increment('brave', 1)
    return response.json()




# -------------------- Google PSE Search --------------------
class GoogleWebSearchInput(BaseModel):
    q: str = Field(description="Web search query for Google Programmable Search Engine.")
    count: Optional[int] = Field(default=10, description="Number of results to return (<= 50 recommended).")


class GoogleImageSearchInput(BaseModel):
    q: str = Field(description="Image search query for Google Programmable Search Engine.")
    count: Optional[int] = Field(default=10, description="Number of image results to return (<= 50 recommended).")


def _google_pse_search(query: str, count: int = 10, search_type: str = "web") -> List[dict]:
    if not GOOGLE_PSE_API_KEY or not GOOGLE_PSE_CX:
        raise RuntimeError("Missing GOOGLE_PSE_API_KEY or GOOGLE_PSE_CX env vars.")
    results: List[dict] = []
    start = 1
    while len(results) < count:
        num = min(10, count - len(results))
        params = {
            "key": GOOGLE_PSE_API_KEY,
            "cx": GOOGLE_PSE_CX,
            "q": query,
            "num": num,
            "start": start,
        }
        if search_type == "image":
            params["searchType"] = "image"
        r = requests.get(GOOGLE_SEARCH_ENDPOINT, params=params, timeout=30)
        r.raise_for_status()
        # Count by request and by type
        if search_type == "image":
            metrics.increment('google_image', 1)
        else:
            metrics.increment('google_web', 1)
        data = r.json()
        items = data.get("items", [])
        if not items:
            break
        for i in items:
            entry = {
                "title": i.get("title"),
                "link": i.get("link"),
                "snippet": i.get("snippet"),
            }
            if search_type == "image":
                img = i.get("image", {}) or {}
                entry["image_context_link"] = img.get("contextLink")
                entry["thumbnail_link"] = img.get("thumbnailLink")
            results.append(entry)
        next_page = (data.get("queries", {}).get("nextPage") or [{}])[0].get("startIndex")
        if not next_page:
            break
        start = next_page
    return results[:count]


@tool(args_schema=GoogleWebSearchInput)
def google_web_search(q: str, count: int = 10) -> dict:
    """
    Google Programmable Search (web). Returns {"results": [{title, link, snippet}, ...]}.
    Use for general web results; supports pagination up to 'count'.
    """
    try:
        items = _google_pse_search(q, count=count, search_type="web")
        _LOGGER._log(f"[google_web_search] q='{q}'\nResults: {json.dumps(items, indent=2)[:2000]}")
        return {"results": items}
    except Exception as e:
        _LOGGER._log(f"[google_web_search] Error: {e}")
        return {"error": str(e)}


@tool(args_schema=GoogleImageSearchInput)
def google_image_search(q: str, count: int = NUMBER_SEARCH_RESULTS) -> dict:
    """
    Google Programmable Search (image). Returns {"results": [{title, link, snippet, image_context_link, thumbnail_link}, ...]}.
    Use for image results with context and thumbnails; supports pagination up to 'count'.
    """
    try:
        # Run-wide cap: avoid more than 2 image requests total
        if (metrics.snapshot().get('google_image', 0) or 0) >= 2:
            _LOGGER._log("[google_image_search] Skipping: image request cap reached for this run")
            return {"results": [], "note": "image request cap reached"}
        # Hard cap to keep image searches minimal per call
        capped = min(count, 2)
        items = _google_pse_search(q, count=capped, search_type="image")
        _LOGGER._log(f"[google_image_search] q='{q}'\nResults: {json.dumps(items, indent=2)[:2000]}")
        return {"results": items}
    except Exception as e:
        _LOGGER._log(f"[google_image_search] Error: {e}")
        return {"error": str(e)}


TOOLS = [
    ping_aoa_search,
    google_web_search,
    google_image_search,
    brave_search,            # kept for now
]
