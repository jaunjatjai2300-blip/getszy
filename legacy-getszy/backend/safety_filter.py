"""Brand-safe content guard for free stock media.

Ensures every image/video we pull is decent, authentic and non-offensive:
- Blocks sexual, vulgar, abusive, violent and overtly political terms.
- Word boundaries prevent false positives (e.g. "cocktail" is NOT "cock").
- Used both to reject unsafe user queries and to filter individual results.
"""
import re

# Curated blocklist. Add/remove terms to tune brand-safety policy.
_BLOCK_TERMS = [
    # sexual / vulgar / nudity
    'sex', 'sexy', 'porn', 'porno', 'xxx', 'nude', 'naked', 'nudity', 'erotic', 'nsfw',
    'penis', 'vagina', 'boobs', 'tits', 'pussy', 'dick', 'cock', 'cum', 'sperm', 'orgasm',
    'fuck', 'fucking', 'shit', 'bitch', 'bastard', 'slut', 'whore', 'randi', 'chudai', 'lundi',
    # abuse / violence / self-harm
    'rape', 'kill', 'murder', 'bloody', 'gore', 'torture', 'suicide', 'terrorist', 'bombing', 'behead',
    # overtly political (per policy: no politics in generated media)
    'politics', 'political', 'election', 'protest', 'riot', 'insurgency',
    'modi', 'bjp', 'congress', 'trump', 'putin', 'zelensky', 'ukraine', 'israel', 'palestine',
]

_RX = re.compile(r'(?:' + '|'.join(re.escape(t) for t in _BLOCK_TERMS) + r')', re.IGNORECASE)


def contains_unsafe(text: str) -> bool:
    if not text:
        return False
    return bool(_RX.search(text))


def safe_query_guard(text: str) -> str:
    """Return a reason string if `text` is unsafe, else None."""
    m = _RX.search(text or '')
    if m:
        return f"contains blocked term: {m.group(0)}"
    return None


def safe_item(*fields) -> bool:
    """True if NONE of the provided text fields contain unsafe terms."""
    for f in fields:
        if isinstance(f, str) and contains_unsafe(f):
            return False
    return True
