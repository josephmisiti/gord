from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import Optional
import requests
import os
import json
import pingintel_api


from gord.utils.logger import Logger

pingclient = pingintel_api.PingDataAPIClient(environment="staging")

BRAVE_SEARCH_URL = 'https://api.search.brave.com/res/v1/web/search'
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
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
    ret = pingclient.enhance(address=address, sources=["PG", "PH"], include_raw_response=True)
    _LOGGER._log(f"[ping_aoa_search] Address: {address}\nResponse: {json.dumps(ret, indent=2)[:8000]}")  
    return ret


@tool(args_schema=BraveSearchInput)
def brave_search(
    q: str,
    count: Optional[int] = 10,
    country: Optional[str] = None
) -> dict:
    """
    Searches the web using Brave Search API and returns relevant results.
    
    Use this tool to find current information, news, company details, market data,
    or any other information available on the public web. Returns web page titles,
    snippets, URLs, and other metadata from the search results.
    """
    if not BRAVE_API_KEY:
        _LOGGER._log("BRAVE_API_KEY is not set; cannot call Brave Search API.")

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": BRAVE_API_KEY,
    }
    
    params = {"q": q, "count": count}
    if country:
        params["country"] = country
    
    _LOGGER._log(f"[brave_search] GET {BRAVE_SEARCH_URL} params={params}")
    response = requests.get(BRAVE_SEARCH_URL, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    try:
        pretty = json.dumps(data, indent=2)
        # Log up to 8000 characters to avoid excessive spam
        snippet = pretty if len(pretty) <= 8000 else pretty[:8000] + "\n... (truncated)"
        _LOGGER._log(f"[brave_search] status={response.status_code}\n{snippet}")
    except Exception as e:
        _LOGGER._log(f"[brave_search] Failed to pretty-print response: {e}")
    return data


TOOLS = [brave_search, ping_aoa_search]
