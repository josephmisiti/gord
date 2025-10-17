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

# Document ingest / webhook
DOC_WEBHOOK_URL = os.getenv('DOC_WEBHOOK_URL', '').strip() or None
DOC_WEBHOOK_TIMEOUT = int(os.getenv('DOC_WEBHOOK_TIMEOUT', '10').strip() or '10')
DOC_WEBHOOK_AUTH = os.getenv('DOC_WEBHOOK_AUTH', '').strip() or None  # optional Bearer token
DOC_PREVIEW_BYTES = int(os.getenv('DOC_PREVIEW_BYTES', '50000').strip() or '50000')

# ------------------------------
# LLM Provider selection
# ------------------------------
# One of: 'openai', 'anthropic', 'gemini', 'grok'
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'openai').strip().lower()
if LLM_PROVIDER not in ('openai', 'anthropic', 'gemini', 'grok'):
    LLM_PROVIDER = 'openai'

# OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')

# Anthropic (Claude)
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ANTHROPIC_MODEL = os.getenv('ANTHROPIC_MODEL', 'claude-3-7-sonnet-2025-02-19')

# Google Gemini
# LangChain Google Generative AI uses GOOGLE_API_KEY
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_GENAI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')

# xAI Grok (OpenAI-compatible API)
XAI_API_KEY = os.getenv('XAI_API_KEY') or os.getenv('GROK_API_KEY')
XAI_BASE_URL = os.getenv('XAI_BASE_URL', 'https://api.x.ai/v1')
GROK_MODEL = os.getenv('GROK_MODEL', 'grok-2-latest')
