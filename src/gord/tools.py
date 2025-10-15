from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import Optional
import requests
import os

####################################
# Configuration
####################################
BRAVE_SEARCH_URL = 'https://api.search.brave.com/res/v1/web/search'
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")

####################################
# Schema
####################################
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

####################################
# Tool
####################################
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
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": BRAVE_API_KEY,
    }
    
    params = {"q": q, "count": count}
    if country:
        params["country"] = country
    
    response = requests.get(BRAVE_SEARCH_URL, params=params, headers=headers)
    response.raise_for_status()
    return response.json()

####################################
# Tool List (for agent use)
####################################
TOOLS = [brave_search]