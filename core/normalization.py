from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

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
_FTS_AND = " AND "
_FTS_OR = " OR "

_ROOT = Path(__file__).resolve().parent.parent

_JARGON_EXPAND_ENABLED = os.getenv("ARXIV_ENABLE_JARGON_EXPANSION", "").lower() in {"1", "true", "yes"}
_JARGON_GLOSSARY_PATH = os.getenv("ARXIV_JARGON_GLOSSARY")


_DEFAULT_JARGON_MAP: dict[str, list[str]] = {
    "mech_interp": [
        "mechanistic interpretability",
        "transformer circuits",
        "sparse autoencoders",
        "feature decomposition",
    ],
    "sae": ["sparse autoencoders", "feature decomposition"],
    "dpo": ["direct preference optimization", "preference alignment"],
    "rlhf": ["reinforcement learning from human feedback", "preference alignment"],
    "rag": ["retrieval augmented generation", "grounded generation", "retrieved evidence"],
}


def _normalize_alias(token: str) -> str:
    return token.strip().lower().replace("-", "_")


def _coerce_aliases(aliases: Any) -> dict[str, list[str]]:
    if not isinstance(aliases, dict):
        return {}

    out: dict[str, list[str]] = {}
    for key, values in aliases.items():
        if not isinstance(key, str) or not isinstance(values, list):
            continue
        # Skip section-comment sentinel keys (e.g. "===== SECTION =====")
        if key.startswith("="):
            continue
        cleaned = [str(v).strip() for v in values if str(v).strip() and v != "_comment"]
        if cleaned:
            out[_normalize_alias(key)] = cleaned
    return out


def _coerce_alias_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if cleaned:
            out.append(cleaned)
    return out


def _canonical_entry_phrases(raw_key: str, payload: dict[str, Any]) -> list[str]:
    canonical = payload.get("canonical", raw_key)
    if not isinstance(canonical, str):
        return []

    phrases: list[str] = []
    cleaned_canonical = canonical.strip()
    if cleaned_canonical:
        phrases.append(cleaned_canonical)

    for alias in _coerce_alias_strings(payload.get("aliases", [])):
        if alias not in phrases:
            phrases.append(alias)

    return phrases


def _coerce_canonical_entries(entries: Any) -> dict[str, list[str]]:
    if not isinstance(entries, dict):
        return {}

    out: dict[str, list[str]] = {}
    for raw_key, payload in entries.items():
        if not isinstance(raw_key, str) or not isinstance(payload, dict):
            continue

        phrases = _canonical_entry_phrases(raw_key, payload)
        if not phrases:
            continue

        for alias in _coerce_alias_strings(payload.get("aliases", [])):
            out[_normalize_alias(alias)] = phrases[:]

    return out


def _load_glossary_aliases(path: str | None) -> dict[str, list[str]]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    # Preferred format: {"aliases": {"acronym": ["expansion", ...]}}
    alias_map = _coerce_aliases(data.get("aliases", {}))

    # Also accept richer canonical-entry format used by jargon_glossary.json:
    # {"canonical phrase": {"aliases": [...], "canonical": "..."}}
    canonical_map = _coerce_canonical_entries(data)

    merged = canonical_map
    merged.update(alias_map)
    return merged


def _default_glossary_path() -> str | None:
    candidates = [
        _ROOT / "jargon_glossary.json",
        _ROOT / "benchmarks" / "queries" / "jargon_glossary.v2.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _load_jargon_map() -> dict[str, list[str]]:
    glossary_path = _JARGON_GLOSSARY_PATH or _default_glossary_path()
    from_file = _load_glossary_aliases(glossary_path)
    return from_file if from_file else _DEFAULT_JARGON_MAP


_JARGON_MAP = _load_jargon_map()


def _dedupe_preserve_order(tokens: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for tok in tokens:
        if tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out


_ALIAS_PHRASE_RE = re.compile(r"[^A-Za-z0-9._ ]+")
_MAX_ALIAS_PHRASES_PER_GROUP = 4


def _clean_alias_phrase(raw: str) -> str:
    cleaned = _ALIAS_PHRASE_RE.sub(" ", raw.lower()).strip()
    return " ".join(cleaned.split())


def _expand_jargon_groups(tokens: list[str]) -> tuple[list[list[str]], bool]:
    groups: list[list[str]] = []
    used_alias = False

    for token in tokens:
        key = _normalize_alias(token)
        aliases = _JARGON_MAP.get(key, [])
        if not aliases:
            groups.append([token])
            continue

        used_alias = True
        # Expand shorthand using phrase alternatives to keep recall high while
        # avoiding massive token-level OR fan-out.
        phrases: list[str] = [token.lower()]
        for phrase in aliases[:_MAX_ALIAS_PHRASES_PER_GROUP]:
            cleaned = _clean_alias_phrase(phrase)
            if cleaned:
                phrases.append(cleaned)

        groups.append(_dedupe_preserve_order(phrases))

    return groups, used_alias


def _render_grouped_match(groups: list[list[str]], use_or_within_group: bool) -> str:
    rendered: list[str] = []
    for group in groups:
        if not group:
            continue
        if len(group) == 1:
            rendered.append(f'"{group[0]}"')
            continue

        joiner = _FTS_OR if use_or_within_group else _FTS_AND
        inner = joiner.join(f'"{tok}"' for tok in group)
        rendered.append(f"({inner})")

    return _FTS_AND.join(rendered)


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

    if not _JARGON_EXPAND_ENABLED:
        return _FTS_AND.join(f'"{token}"' for token in tokens)

    groups, used_alias = _expand_jargon_groups(tokens)
    if not used_alias:
        return _FTS_AND.join(f'"{token}"' for token in tokens)

    # Keep original token boundaries via AND across groups, but broaden each
    # shorthand token to OR alternatives from the glossary.
    match_query = _render_grouped_match(groups, use_or_within_group=True)
    return match_query if match_query else ""
