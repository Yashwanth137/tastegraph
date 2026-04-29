"""Prompt parser — converts natural language library commands to structured actions."""

import re
from dataclasses import dataclass, field


# Ordered by specificity: more specific patterns first
INTENT_PATTERNS = [
    (r"\b(hate[ds]?|hating|dislike[ds]?|awful|terrible|worst)\b", "dislike", "disliked"),
    (r"\b(love[ds]?|loving|like[ds]?|amazing|great|fantastic|favou?rite)\b", "like", "liked"),
    (r"\b(remove|delete|drop)\b.+\b(list|library|watchlist)\b", "remove", None),
    (r"\b(remove|delete|drop)\b", "remove", None),
    (r"\b(watch(?:ed)?)\b(?!list)", "mark_watched", None),
    (r"\b(add|save|bookmark|watchlist)\b", "add_watchlist", None),
]

DEFAULT_ACTION = "add_watchlist"

# Words to strip when extracting titles
STOP_WORDS = (
    r"\b(add|remove|delete|watched|watch|liked?|disliked?|hated?|loved?|"
    r"to|from|my|the|list|watchlist|library|mark|as|i|have|already|seen|"
    r"it|was|is|really|very|so|just|also|both|all|them|these|those|movie|movies|film|films)\b"
)


@dataclass
class ParsedCommand:
    action: str
    movies: list[str]
    metadata: dict = field(default_factory=dict)


def parse_library_prompt(prompt: str) -> ParsedCommand:
    """Convert natural language → structured library command."""
    prompt_lower = prompt.lower().strip()

    # 1. Detect action intent
    action = DEFAULT_ACTION
    sentiment = None
    for pattern, act, sent in INTENT_PATTERNS:
        if re.search(pattern, prompt_lower):
            action = act
            sentiment = sent
            break

    # 2. Extract movie titles
    movies = _extract_movie_titles(prompt)

    return ParsedCommand(
        action=action,
        movies=movies,
        metadata={"source": "prompt", "raw_prompt": prompt, "sentiment": sentiment},
    )


def _extract_movie_titles(prompt: str) -> list[str]:
    """Extract movie titles from prompt text."""
    # Strategy 1: Quoted titles — "Inception", 'The Dark Knight'
    quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', prompt)
    if quoted:
        return [q[0] or q[1] for q in quoted]

    # Strategy 2: Remove action/stop words, split on 'and' / commas
    cleaned = re.sub(STOP_WORDS, " ", prompt, flags=re.IGNORECASE)
    parts = re.split(r"\s*(?:,|\band\b|&)\s*", cleaned)
    titles = [p.strip() for p in parts if len(p.strip()) > 1]
    return titles
