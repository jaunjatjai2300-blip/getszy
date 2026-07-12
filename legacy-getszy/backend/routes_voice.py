"""Voice generation routes — TTS + STT."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional
from auth import get_current_user
from voice_gen import generate_voice, generate_video_voiceover, list_voices
from whisper_stt import transcribe_audio
from audit_log import log_action, ACTION_AI_REQUEST

router = APIRouter(prefix='/ai/voice', tags=['voice'])


class TTSIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice: str = 'english-indian-female'
    rate: str = '+0%'
    volume: str = '+0%'
    pitch: str = '+0Hz'


class VoiceoverIn(BaseModel):
    script: list[dict] = Field(..., min_length=1)
    voice: str = 'english-indian-female'


class TranscribeIn(BaseModel):
    language: Optional[str] = None


@router.post('/tts')
async def text_to_speech(body: TTSIn, user=Depends(get_current_user)):
    result = await generate_voice(body.text, body.voice, body.rate, body.volume, body.pitch)
    await log_action(ACTION_AI_REQUEST, user_id=user['id'], user_email=user.get('email'),
                     details={'type': 'tts', 'voice': body.voice, 'text_len': len(body.text)})
    return result


@router.post('/voiceover')
async def video_voiceover(body: VoiceoverIn, user=Depends(get_current_user)):
    return await generate_video_voiceover(body.script, body.voice)


@router.post('/transcribe')
async def transcribe(file: UploadFile = File(...), language: Optional[str] = None, user=Depends(get_current_user)):
    contents = await file.read()
    result = await transcribe_audio(file_bytes=contents, filename=file.filename, language=language)
    await log_action(ACTION_AI_REQUEST, user_id=user['id'], user_email=user.get('email'),
                     details={'type': 'transcription', 'filename': file.filename})
    return result


@router.get('/voices')
async def get_voices(language: Optional[str] = None):
    return await list_voices(language)
