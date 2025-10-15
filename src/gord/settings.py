import os

# Primary search engine to use for standard modes.
# Valid values: 'google', 'brave'
SEARCH_ENGINE = os.getenv('SEARCH_ENGINE', 'google').strip().lower()
if SEARCH_ENGINE not in ('google', 'brave'):
    SEARCH_ENGINE = 'google'

