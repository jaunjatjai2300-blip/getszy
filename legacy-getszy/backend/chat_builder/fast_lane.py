"""Fast Lane router — skip the classifier LLM for obvious simple requests.

Heuristic-only (no LLM), sub-millisecond. Falls back to full classifier for anything
not confidently matched. This is the core of \"Adaptive Pipeline Routing\":
  Simple request  → direct capability dispatch  (5–10s total)
  Complex request → full classifier + orchestrator (30–60s)

Based on the user\'s architectural feedback: don\'t over-engineer every request.
"""
import re
from typing import Dict, Any, Tuple, Optional

# Keyword → (intent, param_extractor) map.
# Every extractor returns a dict of params suitable for the capability.

_IMAGE_TRIGGERS = re.compile(r'\b(logo|banner|thumbnail|poster|image|photo|picture|hero image)\b', re.I)
_VIDEO_TRIGGERS = re.compile(r'\b(video|reel|short|shorts)\b', re.I)
_SCRIPT_TRIGGERS = re.compile(r'\b(script|caption|hook|copy|write)\b', re.I)
_WEBAPP_TRIGGERS = re.compile(r'\b(landing page|web app|webapp|website|homepage|site)\b', re.I)
_TRENDS_TRIGGERS = re.compile(r'\b(trending|trends|what.s hot|viral topics|content ideas)\b', re.I)
_CHANNEL_TRIGGERS = re.compile(r'\b(channel plan|content calendar|30.day plan|monthly plan)\b', re.I)


def _clean_topic(msg: str) -> str:
    """Strip obvious command words to get to the topic."""
    m = re.sub(r'^(please|bhai|kya|ek|please|make|create|generate|build|design|write|banao|banado|likho|dedo)\s+', '', msg.strip(), flags=re.I)
    m = re.sub(r'\b(please|for me|please|now|abhi|jaldi|fast)\b', '', m, flags=re.I)
    return m.strip(' .!?,')


def detect(message: str, history_len: int = 0) -> Optional[Tuple[str, Dict[str, Any], str]]:
    """Return (intent, params, human_reply) if this is a simple request, else None."""
    text = message.strip()
    if len(text) < 3:
        return None
    lower = text.lower()
    word_count = len(text.split())

    # Very short or greeting → general_chat immediately (skip classifier)
    if word_count < 3 or re.match(r'^(hi|hello|hey|hii|namaste|hola|yo|sup)\b', lower):
        return ('general_chat', {}, 'Hey! Bata kya banana hai?')

    # Simple image / logo
    if _IMAGE_TRIGGERS.search(text) and word_count < 20 and not _VIDEO_TRIGGERS.search(text) and not _WEBAPP_TRIGGERS.search(text):
        # Route as a script/media generation — but we don\'t have a direct image cap; fall through.
        # Reserved for future direct pollinations capability.
        return None

    # Trends (very common request)
    if _TRENDS_TRIGGERS.search(text) and word_count < 25:
        niche = _clean_topic(re.sub(_TRENDS_TRIGGERS, '', text)).strip(' forabout')
        return ('predict_trends', {'niche': niche or 'general'}, f'Fetching trending topics{f" for {niche}" if niche else ""}…')

    # 30-day channel plan
    if _CHANNEL_TRIGGERS.search(text) and word_count < 30:
        niche = _clean_topic(re.sub(_CHANNEL_TRIGGERS, '', text))
        return ('plan_channel', {'niche': niche or 'creator content', 'posts_per_week': 5, 'language': 'hinglish'},
                f'Planning 30-day channel for {niche or "you"}…')

    # Simple script (short request, single verb+object)
    if _SCRIPT_TRIGGERS.search(text) and word_count < 25 and not _VIDEO_TRIGGERS.search(text):
        topic = _clean_topic(re.sub(_SCRIPT_TRIGGERS, '', text))
        fmt = 'youtube_short' if re.search(r'\b(short|reel|30.sec)\b', lower) else 'youtube_long'
        return ('write_script', {'topic': topic, 'format': fmt, 'language': 'hinglish', 'tone': 'energetic'},
                f'Writing {fmt.replace("_", " ")} script on “{topic[:60]}”…')

    # Direct single video request
    if _VIDEO_TRIGGERS.search(text) and word_count < 25 and re.search(r'\b(make|create|generate|build|banao)\b', lower):
        topic = _clean_topic(re.sub(_VIDEO_TRIGGERS, '', text))
        return ('generate_video', {'topic': topic, 'orientation': '9:16', 'language': 'hinglish',
                                    'target_seconds': 25, 'subtitles': False, 'tone': 'energetic'},
                f'Queuing faceless video: “{topic[:60]}”…')

    # Landing page / web app
    if _WEBAPP_TRIGGERS.search(text) and word_count < 30:
        return ('build_webapp', {'prompt': text, 'name': _clean_topic(re.sub(_WEBAPP_TRIGGERS, '', text))[:40]},
                f'Building the page…')

    # Nothing matched confidently — fall back to LLM classifier
    return None
