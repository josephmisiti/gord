import os


BRAVE_SEARCH_URL = 'https://api.search.brave.com/res/v1/web/search'
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")


# Google Programmable Search Engine (PSE)
GOOGLE_PSE_API_KEY = os.getenv("GOOGLE_PSE_API_KEY")
GOOGLE_PSE_CX = os.getenv("GOOGLE_PSE_CX")
GOOGLE_SEARCH_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

NUMBER_SEARCH_RESULTS = 3

SEARCH_ENGINE = os.getenv('SEARCH_ENGINE', 'google').strip().lower()
if SEARCH_ENGINE not in ('google', 'brave'):
    SEARCH_ENGINE = 'google'

# Debug flag to control verbosity (defaults to False)
DEBUG = os.getenv('DEBUG', 'false').strip().lower() in ('1', 'true', 'yes', 'on')
