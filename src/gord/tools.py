


import requests
import optparse

BRAVE_SEARCH_URL = 'https://api.search.brave.com/res/v1/web/search'
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")


def call_api(q: str) -> dict:
    headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": BRAVE_API_KEY,
    }

    response = requests.get(BRAVE_SEARCH_URL, params=dict(query=q), headers=headers)
    response.raise_for_status()
    return response.json()