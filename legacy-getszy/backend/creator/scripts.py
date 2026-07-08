"""Creator OS - script generation across formats."""
import json
from typing import Dict, Any, List
from llm_provider import chat_completion

FORMATS = {
    'youtube_long': {'label': 'YouTube long-form', 'duration': '5-15 min', 'sections': ['hook', 'intro', 'value', 'cta']},
    'youtube_short': {'label': 'YouTube Short', 'duration': '<60s', 'sections': ['hook', 'punchline']},
    'instagram_reel': {'label': 'Instagram Reel', 'duration': '15-30s', 'sections': ['hook', 'value', 'cta']},
    'facebook_reel': {'label': 'Facebook Reel', 'duration': '15-60s', 'sections': ['hook', 'value', 'cta']},
    'blog': {'label': 'Blog Article', 'duration': '800-1500 words', 'sections': ['intro', 'h2_sections', 'conclusion']},
    'tweet_thread': {'label': 'Twitter/X Thread', 'duration': '8-12 tweets', 'sections': ['hook_tweet', 'body', 'cta']},
    'linkedin': {'label': 'LinkedIn Post', 'duration': '150-300 words', 'sections': ['hook', 'story', 'lesson']},
}


async def generate(topic: str, fmt: str, audience: str = 'indian creators', tone: str = 'energetic', language: str = 'hinglish') -> Dict[str, Any]:
    if fmt not in FORMATS:
        raise ValueError(f'Unknown format: {fmt}')
    spec = FORMATS[fmt]
    system = (
        f'You are an elite short-form content writer and YouTube/Reels script doctor who has written '
        f'scripts for creators with 10M+ subscribers, writing for {audience}. '
        f'Write in {language} ({tone} tone) — natural, conversational, never robotic or textbook-sounding. '
        'The opening line (hook) is the single most important sentence: it must create a curiosity gap, '
        'contradict a common belief, or promise a specific concrete outcome within the first 3 seconds — '
        'never start with generic greetings like "Hey guys" or "In this video". '
        'Every sentence should earn the next one: cut filler, use short punchy lines, concrete numbers/specifics '
        'over vague claims, and a clear pattern-interrupt roughly every 8-10 seconds to fight scroll-away. '
        'Output ONLY valid JSON.'
    )
    user = (
        f'Topic: "{topic}"\n'
        f'Format: {spec["label"]} ({spec["duration"]})\n'
        f'Required JSON keys: title (catchy, under 60 chars), {", ".join(spec["sections"])}, '
        'hashtags (array of 8-12, mix of broad + niche), thumbnail_brief (1 vivid sentence describing a '
        'high-contrast, emotion-driven thumbnail concept), retention_hooks (3 specific mid-content pattern-interrupt '
        'lines placed at roughly 25%/50%/75% through the content to stop viewers from dropping off).\n'
        'Reply ONLY with the JSON object, no markdown fences.'
    )
    raw = await chat_completion(system, user, temperature=0.8)
    # Extract JSON
    txt = (raw or '').strip().strip('`').replace('json\n', '', 1)
    start = txt.find('{')
    end = txt.rfind('}')
    if start == -1 or end <= start:
        return _fallback_script(topic, fmt, language)
    try:
        data = json.loads(txt[start:end + 1])
    except Exception as e:
        return _fallback_script(topic, fmt, language)
    data['format'] = fmt
    data['topic'] = topic
    return data


def _fallback_script(topic: str, fmt: str, language: str) -> Dict[str, Any]:
    """Template-based script when Ollama fails or returns bad JSON.
    Guaranteed to produce usable narration for the video pipeline — never returns an error dict.
    """
    lang = language.lower()
    if lang in ('hindi',):
        hook    = f'क्या आप जानते हैं {topic} के बारे में ये ज़रूरी बात?'
        value   = f'{topic} एक ऐसा विषय है जो हर किसी के काम आता है। आज हम इसके बारे में सही जानकारी लेंगे।'
        punchline = f'{topic} को सही तरीके से समझना बहुत ज़रूरी है।'
        cta     = 'इस वीडियो को लाइक करें और चैनल को सब्सक्राइब करें!'
        hooks   = ['यह सुनकर हैरान हो जाएंगे', 'अब मैं सबसे ज़रूरी बात बताता हूँ', 'यही है असली राज़']
    elif lang in ('english',):
        hook    = f'The truth about {topic} that nobody tells you!'
        value   = f'{topic} is something everyone should know about. Today we will explore the key facts and tips.'
        punchline = f'Understanding {topic} properly can change how you approach this subject entirely.'
        cta     = 'Like this video and subscribe for more!'
        hooks   = ['You will be surprised by this', 'Here comes the most important part', 'And this is the real secret']
    else:  # hinglish default
        hook    = f'Aaj main {topic} ke baare mein ek khaas baat share karta hoon!'
        value   = (f'{topic} ek aisa topic hai jo sabke kaam aata hai. '
                   f'Iske baare mein sahi jaankari hona bahut zaruri hai. '
                   f'Aaj hum {topic} ke important points cover karenge.')
        punchline = f'{topic} ko sahi se samajhna bahut zaruri hai — aur aaj ke baad aapko sab pata chal jayega.'
        cta     = 'Like karo, share karo aur channel ko subscribe karo!'
        hooks   = ['Yeh sun ke hairan ho jaoge', 'Ab main sabse important baat bata raha hoon', 'Aur yahi hai asli raaz']

    tag = topic.replace(' ', '')
    return {
        'title': topic[:60],
        'hook': hook,
        'value': value,
        'punchline': punchline,
        'cta': cta,
        'hashtags': [f'#{tag}', '#India', '#trending', '#viral', '#reels', '#shorts', '#knowledge'],
        'thumbnail_brief': f'{topic} — bold colorful thumbnail with large Hindi/English text',
        'retention_hooks': hooks,
        'format': fmt,
        'topic': topic,
        '_fallback': True,
    }


async def score_hook(hook_text: str) -> Dict[str, Any]:
    """Predict how likely a hook is to retain viewers (first 3 seconds)."""
    system = (
        'You are a viral content analyst. Score the given video hook on a 1-100 scale based on '
        'curiosity gap, emotional pull, clarity, specificity, and pattern interrupt. '
        'Output ONLY JSON: {score, rationale, suggested_rewrite}.'
    )
    raw = await chat_completion(system, f'Hook: "{hook_text}"', temperature=0.3)
    start = (raw or '').find('{')
    end = (raw or '').rfind('}')
    if start == -1:
        return {'score': 50, 'rationale': 'LLM unavailable', 'suggested_rewrite': hook_text}
    try:
        return json.loads(raw[start:end + 1])
    except Exception:
        return {'score': 50, 'rationale': raw[:200] if raw else '', 'suggested_rewrite': hook_text}


async def viral_score(content: Dict[str, Any]) -> Dict[str, Any]:
    """Pre-publish viral probability check."""
    summary = json.dumps({k: v for k, v in content.items() if k in ('title', 'hook', 'topic', 'format')}, ensure_ascii=False)[:500]
    system = (
        'You are a viral content predictor for Indian audiences. Rate the given content piece on '
        'a 0-100 viral probability scale considering: hook strength, timing relevance, niche heat, '
        'shareability, emotion. Output ONLY JSON: {viral_score, drivers (array), risks (array), recommendation}.'
    )
    raw = await chat_completion(system, f'Content: {summary}', temperature=0.4)
    start = (raw or '').find('{')
    end = (raw or '').rfind('}')
    if start == -1:
        return {'viral_score': 60, 'drivers': [], 'risks': ['LLM unavailable'], 'recommendation': 'retry'}
    try:
        return json.loads(raw[start:end + 1])
    except Exception:
        return {'viral_score': 60, 'drivers': [], 'risks': [], 'recommendation': raw[:200] if raw else ''}
