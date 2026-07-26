"""Session Memory — Multi-turn conversation context for the AI agent.

Stores conversation history in MongoDB so the agent remembers previous
interactions within a session. Supports context window management.
"""
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional
from db import db

MAX_CONTEXT_MESSAGES = int(os.environ.get('CHAT_CONTEXT_LIMIT', '20'))
MAX_CONTEXT_TOKENS = int(os.environ.get('CHAT_CONTEXT_TOKENS', '8000'))


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (1 token ≈ 4 chars)."""
    return len(text) // 4


async def get_session(session_id: str) -> Optional[Dict]:
    """Retrieve a chat session."""
    return await db.chat_sessions.find_one({'session_id': session_id}, {'_id': 0})


async def create_session(session_id: str, user_id: str, metadata: Dict = None) -> Dict:
    """Create a new chat session."""
    doc = {
        'session_id': session_id,
        'user_id': user_id,
        'messages': [],
        'metadata': metadata or {},
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.chat_sessions.insert_one(doc)
    return doc


async def add_message(
    session_id: str,
    role: str,
    content: str,
    metadata: Dict = None,
) -> None:
    """Add a message to the session history."""
    msg = {
        'role': role,
        'content': content,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        **(metadata or {}),
    }
    await db.chat_sessions.update_one(
        {'session_id': session_id},
        {
            '$push': {'messages': msg},
            '$set': {'updated_at': datetime.now(timezone.utc).isoformat()},
        },
    )


async def get_context_messages(
    session_id: str,
    max_messages: int = None,
    max_tokens: int = None,
) -> List[Dict]:
    """Get the context window for an LLM call.

    Returns messages trimmed to fit within token limits.
    Most recent messages are kept; older ones are dropped.
    """
    max_messages = max_messages or MAX_CONTEXT_MESSAGES
    max_tokens = max_tokens or MAX_CONTEXT_TOKENS

    session = await db.chat_sessions.find_one(
        {'session_id': session_id},
        {'_id': 0, 'messages': 1},
    )
    if not session:
        return []

    messages = session.get('messages', [])
    # Take the last N messages
    messages = messages[-max_messages:]

    # Trim by token count (keep most recent)
    total_tokens = 0
    trimmed = []
    for msg in reversed(messages):
        msg_tokens = _estimate_tokens(msg.get('content', ''))
        if total_tokens + msg_tokens > max_tokens:
            break
        trimmed.append(msg)
        total_tokens += msg_tokens

    trimmed.reverse()
    return trimmed


async def get_system_prompt(session_id: str) -> str:
    """Build a system prompt enriched with session context."""
    messages = await get_context_messages(session_id)
    if not messages:
        return ''

    context_lines = []
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')[:200]
        context_lines.append(f'{role}: {content}')

    return (
        'Previous conversation context:\n' +
        '\n'.join(context_lines) +
        '\n\nContinue the conversation naturally. '
        'Reference previous context when relevant.'
    )


async def clear_session(session_id: str) -> bool:
    """Clear all messages from a session."""
    result = await db.chat_sessions.update_one(
        {'session_id': session_id},
        {'$set': {'messages': [], 'updated_at': datetime.now(timezone.utc).isoformat()}},
    )
    return result.modified_count > 0


async def delete_session(session_id: str) -> bool:
    """Delete an entire session."""
    result = await db.chat_sessions.delete_one({'session_id': session_id})
    return result.deleted_count > 0


async def list_sessions(user_id: str, limit: int = 20) -> List[Dict]:
    """List recent sessions for a user."""
    cursor = db.chat_sessions.find(
        {'user_id': user_id},
        {'_id': 0, 'messages': 0},
    ).sort('updated_at', -1).limit(limit)
    return [s async for s in cursor]
