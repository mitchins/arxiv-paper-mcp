from __future__ import annotations

import re

# Matches both old-style (e.g. hep-th/9901001) and new-style (e.g. 2301.12345v2) arXiv IDs
_ARXIV_ID_RE = re.compile(
    r"^(?:arXiv:)?"  # optional arXiv: prefix
    r"("
    r"[a-z\-]+/\d+"  # old-style: category/number
    r"|"
    r"\d{4}\.\d{4,5}"  # new-style: YYMM.NNNNN
    r")"
    r"(v\d+)?$",  # optional version suffix
    re.IGNORECASE,
)

_FTS_TOKEN_RE = re.compile(r"[A-Za-z0-9._]+")


def normalize_arxiv_id(raw: str) -> str | None:
    """Normalize an arXiv ID string.

    Strips the ``arXiv:`` prefix, trims whitespace, and preserves version
    suffixes.  Returns ``None`` if the input doesn't look like a valid ID.
    """
    cleaned = raw.strip()
    m = _ARXIV_ID_RE.match(cleaned)
    if not m:
        return None
    base = m.group(1)
    version = m.group(2) or ""
    return f"{base}{version}"


def normalize_query(raw: str) -> str:
    """Normalize free text into a safe FTS5 MATCH query.

    Converts user input into quoted terms joined by ``AND`` so punctuation
    (including ``-``) is treated as text separators rather than FTS operators.
    Returns an empty string when no searchable tokens remain.
    """
    tokens = _FTS_TOKEN_RE.findall(raw)
    if not tokens:
        return ""
    return " AND ".join(f'"{token}"' for token in tokens)
