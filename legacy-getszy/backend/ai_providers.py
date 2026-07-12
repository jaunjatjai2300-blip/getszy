"""Unified AI provider routing — connects to user's existing API keys."""
import os
import httpx
import logging

logger = logging.getLogger('getszy.ai')

# Provider config from env
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'meta-llama/llama-3.3-70b-instruct:free')

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash')

HF_API_KEY = os.environ.get('HF_API_KEY', '')
HF_MODEL = os.environ.get('HF_MODEL', 'Qwen/Qwen2.5-72B-Instruct')

OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://host.docker.internal:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'qwen2.5:7b')

# Legacy compat
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
EMERGENT_MODEL = os.environ.get('EMERGENT_MODEL', 'gpt-4o-mini')
LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'auto')


def _get_provider():
    """Auto-select best available provider."""
    if LLM_PROVIDER != 'auto':
        return LLM_PROVIDER
    if GROQ_API_KEY:
        return 'groq'
    if OPENROUTER_API_KEY:
        return 'openrouter'
    if GEMINI_API_KEY:
        return 'gemini'
    if HF_API_KEY:
        return 'huggingface'
    return 'ollama'


async def chat_completion(messages: list[dict], model: str = None, temperature: float = 0.7) -> str:
    """Send chat completion to the best available provider."""
    provider = _get_provider()
    logger.info(f'AI request via {provider}')

    try:
        if provider == 'groq':
            return await _groq_chat(messages, model or GROQ_MODEL, temperature)
        elif provider == 'openrouter':
            return await _openrouter_chat(messages, model or OPENROUTER_MODEL, temperature)
        elif provider == 'gemini':
            return await _gemini_chat(messages, model or GEMINI_MODEL, temperature)
        elif provider == 'huggingface':
            return await _hf_chat(messages, model or HF_MODEL, temperature)
        else:
            return await _ollama_chat(messages, model or OLLAMA_MODEL, temperature)
    except Exception as e:
        logger.error(f'AI provider {provider} failed: {e}')
        # Fallback to ollama if available
        if provider != 'ollama':
            try:
                return await _ollama_chat(messages, OLLAMA_MODEL, temperature)
            except Exception:
                pass
        return f'AI temporarily unavailable. Provider error: {str(e)}'


async def _groq_chat(messages: list[dict], model: str, temperature: float) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {GROQ_API_KEY}'},
            json={'model': model, 'messages': messages, 'temperature': temperature},
        )
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content']


async def _openrouter_chat(messages: list[dict], model: str, temperature: float) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'HTTP-Referer': 'https://getszy.com',
                'X-Title': 'Getszy',
            },
            json={'model': model, 'messages': messages, 'temperature': temperature},
        )
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content']


async def _gemini_chat(messages: list[dict], model: str, temperature: float) -> str:
    # Convert messages to Gemini format
    contents = []
    for m in messages:
        role = 'user' if m['role'] == 'user' else 'model'
        contents.append({'role': role, 'parts': [{'text': m['content']}]})

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}',
            json={'contents': contents, 'generationConfig': {'temperature': temperature}},
        )
        resp.raise_for_status()
        return resp.json()['candidates'][0]['content']['parts'][0]['text']


async def _hf_chat(messages: list[dict], model: str, temperature: float) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f'https://api-inference.huggingface.co/models/{model}',
            headers={'Authorization': f'Bearer {HF_API_KEY}'},
            json={'inputs': messages[-1]['content'], 'parameters': {'temperature': temperature}},
        )
        resp.raise_for_status()
        return resp.json()[0]['generated_text']


async def _ollama_chat(messages: list[dict], model: str, temperature: float) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f'{OLLAMA_BASE_URL}/api/chat',
            json={'model': model, 'messages': messages, 'stream': False, 'options': {'temperature': temperature}},
        )
        resp.raise_for_status()
        return resp.json()['message']['content']
