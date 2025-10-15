import os
import requests
from dotenv import load_dotenv
import pprint

load_dotenv()

API_KEY = os.environ["GOOGLE_PSE_API_KEY"]
CX = os.environ["GOOGLE_PSE_CX"]

def google_search(query: str, count: int = 10, search_type: str = "web"):
    endpoint = "https://www.googleapis.com/customsearch/v1"
    results = []
    start = 1
    while len(results) < count:
        num = min(10, count - len(results))
        params = {
            "key": API_KEY,
            "cx": CX,
            "q": query,
            "num": num,
            "start": start,
        }
        # Add image search if requested
        if search_type == "image":
            params["searchType"] = "image"

        r = requests.get(endpoint, params=params, timeout=30)
        r.raise_for_status()
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
                entry["image_context_link"] = i.get("image", {}).get("contextLink")
                entry["thumbnail_link"] = i.get("image", {}).get("thumbnailLink")
            results.append(entry)
        next_page = data.get("queries", {}).get("nextPage", [{}])[0].get("startIndex")
        if not next_page:
            break
        start = next_page
    return results[:count]

if __name__ == "__main__":
    query = "Miami Beach Florida"
    print("=== Web Results ===")
    pprint.pprint(google_search(query, count=5, search_type="web"))

    print("\n=== Image Results ===")
    pprint.pprint(google_search(query, count=5, search_type="image"))
