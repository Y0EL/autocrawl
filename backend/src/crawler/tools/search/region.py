"""Region detection from a query string.

Quick heuristic: look for country/region keywords or local-script characters
in the query and return the regions to fan out to. A query may match
multiple regions ("Asia defense expo" → CN + KR + JP), and global queries
match no region (use only Western engines).
"""

from __future__ import annotations

import re

# Unicode block detection (Chinese/Japanese/Korean/Cyrillic).
_HAN_RX = re.compile(r"[一-鿿]")  # CJK Unified Ideographs (Chinese / Kanji)
_KANA_RX = re.compile(r"[぀-ヿ]")  # Hiragana + Katakana (Japanese only)
_HANGUL_RX = re.compile(r"[가-힯ᄀ-ᇿ㄰-㆏]")  # Korean
_CYRILLIC_RX = re.compile(r"[Ѐ-ӿ]")  # Russian / Cyrillic

_KEYWORD_REGIONS: dict[str, list[str]] = {
    "china": ["cn"],
    "chinese": ["cn"],
    "beijing": ["cn"],
    "shanghai": ["cn"],
    "zhuhai": ["cn"],
    "shenzhen": ["cn"],
    "japan": ["jp"],
    "japanese": ["jp"],
    "tokyo": ["jp"],
    "osaka": ["jp"],
    "korea": ["kr"],
    "korean": ["kr"],
    "seoul": ["kr"],
    "russia": ["ru"],
    "russian": ["ru"],
    "moscow": ["ru"],
    "asia": ["cn", "kr", "jp"],  # broad-asia → fan out to all 3
    "asia-pacific": ["cn", "kr", "jp"],
    "apac": ["cn", "kr", "jp"],
}


def all_region_engines() -> list[str]:
    """Engine keys for the regional Tier-6 providers. Used by force-multilingual
    callers that want to bypass `detect_regions()` gating and fire all three."""
    return ["baidu", "naver", "yahoo_japan"]


def detect_regions(query: str) -> list[str]:
    """Returns a list of region codes (cn, jp, kr, ru) for which to use the
    region-specific search engine. Empty list = use only Western engines."""
    if not query:
        return []
    out: set[str] = set()
    if _HAN_RX.search(query):
        # could be Chinese or Japanese Kanji
        out.add("cn")
        if _KANA_RX.search(query):
            out.add("jp")
            out.discard("cn")  # JP wins if kana present
    if _KANA_RX.search(query):
        out.add("jp")
    if _HANGUL_RX.search(query):
        out.add("kr")
    if _CYRILLIC_RX.search(query):
        out.add("ru")

    lower = query.lower()
    for kw, regions in _KEYWORD_REGIONS.items():
        if kw in lower:
            out.update(regions)
    return sorted(out)
