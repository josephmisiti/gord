import os
import hashlib
from typing import Optional, Tuple


def _strip_quotes(s: str) -> str:
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        return s[1:-1]
    return s


def _from_file_url(s: str) -> Optional[str]:
    # Basic file:// handler (macOS drag sometimes uses plain path, not file://)
    if s.startswith("file://"):
        # naive: strip scheme
        p = s[len("file://"):]
        return p
    return None


def extract_pdf_path(text: str) -> Optional[str]:
    """Deprecated: use extract_dropped_file. Kept for backward compatibility."""
    return extract_dropped_file(text, exts={'.pdf'})


def extract_dropped_file(text: str, exts: Optional[set] = None) -> Optional[str]:
    """Try to extract a local file path with an allowed extension from arbitrary input text.
    Handles quoted paths, file:// URLs, and simple tokens.
    exts: set of extensions (lowercase with dot), default {'.pdf', '.xls', '.xlsx'}
    """
    if exts is None:
        exts = {'.pdf', '.xls', '.xlsx'}
    raw = text.strip()
    # Direct path attempt
    candidates = [raw]

    # Unescaped/stripped variants
    candidates.append(_strip_quotes(raw))
    candidates.append(raw.replace("\\ ", " "))

    # file:// form
    fu = _from_file_url(raw)
    if fu:
        candidates.append(fu)

    # Also check space-split tokens (quoted paths often come as one token; unquoted might be broken)
    parts = raw.split()
    for p in parts:
        candidates.append(_strip_quotes(p))

    seen = set()
    for c in candidates:
        if not c or c in seen:
            continue
        seen.add(c)
        try:
            expanded = os.path.expanduser(c)
            norm = os.path.normpath(expanded)
        except Exception:
            continue
        if any(norm.lower().endswith(e) for e in exts) and os.path.exists(norm) and os.path.isfile(norm):
            return norm
    return None


def summarize_pdf(path: str) -> Tuple[str, int, str]:
    """Return (filename, size_bytes, sha256) for the given PDF path."""
    fname = os.path.basename(path)
    size = os.path.getsize(path)
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return fname, size, h.hexdigest()
