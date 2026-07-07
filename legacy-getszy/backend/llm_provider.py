import os
import httpx
import uuid

PROVIDER = os.environ.get('LLM_PROVIDER', 'emergent').lower()
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_SECRET = os.environ.get('OLLAMA_SECRET', '')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'qwen2.5:7b')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
EMERGENT_MODEL = os.environ.get('EMERGENT_MODEL', 'gpt-4o-mini')


async def chat_completion(system: str, user: str, session_id: str | None = None, temperature: float = 0.4) -> str:
    session_id = session_id or str(uuid.uuid4())
    if PROVIDER == 'ollama':
        headers = {}
        if OLLAMA_SECRET:
            headers['Authorization'] = f'Bearer {OLLAMA_SECRET}'
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                headers=headers,
                json={
                    'model': OLLAMA_MODEL,
                    'messages': [
                        {'role': 'system', 'content': system},
                        {'role': 'user', 'content': user},
                    ],
                    'stream': False,
                    'options': {'temperature': temperature},
                },
            )
            r.raise_for_status()
            return r.json().get('message', {}).get('content', '')
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError:
        raise RuntimeError(
            'LLM provider not configured. Set LLM_PROVIDER=ollama for local testing, '
            'or wire up the Claude/Anthropic integration (emergentintegrations is not installed).'
        )
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system,
    ).with_model('openai', EMERGENT_MODEL)
    return await chat.send_message(UserMessage(text=user))


def provider_info() -> dict:
    # Admin-only context. Public endpoints should NOT expose this.
    return {
        'provider': PROVIDER,
        'model': OLLAMA_MODEL if PROVIDER == 'ollama' else EMERGENT_MODEL,
    }
