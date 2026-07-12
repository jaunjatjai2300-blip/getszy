"""Voice generation + STT routes — Edge-TTS + Whisper."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth import get_current_user
from db import db
from voice_gen import generate_speech, generate_speech_stream, list_voices
from whisper_stt import transcribe

router = APIRouter(prefix='/ai/voice', tags=['ai-voice'])


class TTSIn(BaseModel):
    text: str
    voice: Optional[str] = None
    rate: Optional[str] = None
    pitch: Optional[str] = None


@router.post('/tts')
async def text_to_speech(payload: TTSIn, user=Depends(get_current_user)):
    result = await generate_speech(payload.text, payload.voice, payload.rate, payload.pitch)
    if 'error' in result:
        raise HTTPException(status_code=502, detail=result['error'])
    record = {
        'id': str(uuid.uuid4()), 'user_id': user['id'],
        'text': payload.text[:200], 'voice': payload.voice or 'default',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    await db.voice_records.insert_one(record)
    return {'audio': result.get('audio'), 'format': result.get('format'), 'voice': result.get('voice')}


@router.post('/tts/stream')
async def tts_stream(payload: TTSIn, user=Depends(get_current_user)):
    return StreamingResponse(
        generate_speech_stream(payload.text, payload.voice, payload.rate),
        media_type='audio/mpeg'
    )


@router.get('/voices')
async def voices():
    return {'voices': await list_voices()}


@router.post('/stt')
async def speech_to_text(file: UploadFile = File(...), user=Depends(get_current_user)):
    audio_bytes = await file.read()
    result = await transcribe(audio_bytes, file.filename or 'audio.wav')
    if 'error' in result:
        raise HTTPException(status_code=502, detail=result['error'])
    return {'text': result.get('text'), 'provider': result.get('provider')}


@router.get('/history')
async def voice_history(limit: int = 20, user=Depends(get_current_user)):
    cur = db.voice_records.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'records': [r async for r in cur]}
