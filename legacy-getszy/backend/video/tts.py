"""Free TTS using edge-tts (Microsoft Edge online voices, no API key).

Indian voices supported:
  hi-IN-MadhurNeural   (Hindi male)
  hi-IN-SwaraNeural    (Hindi female)
  en-IN-NeerjaNeural   (Indian English female)
  en-IN-PrabhatNeural  (Indian English male)

When ELEVENLABS_KEY or MURF_KEY is configured, those providers can be used (stubbed for now).
"""
import asyncio
import os
import uuid
from typing import Optional

VOICE_MAP = {
    ('hindi', 'female'):    'hi-IN-SwaraNeural',
    ('hindi', 'male'):      'hi-IN-MadhurNeural',
    ('hinglish', 'female'): 'hi-IN-SwaraNeural',
    ('hinglish', 'male'):   'hi-IN-MadhurNeural',
    ('english', 'female'):  'en-IN-NeerjaNeural',
    ('english', 'male'):    'en-IN-PrabhatNeural',
}

LIST_VOICES = [
    {'id': 'hi-IN-SwaraNeural',   'lang': 'Hindi', 'gender': 'female', 'label': 'Swara (Hindi female)'},
    {'id': 'hi-IN-MadhurNeural',  'lang': 'Hindi', 'gender': 'male',   'label': 'Madhur (Hindi male)'},
    {'id': 'en-IN-NeerjaNeural',  'lang': 'Indian English', 'gender': 'female', 'label': 'Neerja (IN English F)'},
    {'id': 'en-IN-PrabhatNeural', 'lang': 'Indian English', 'gender': 'male',   'label': 'Prabhat (IN English M)'},
]


def pick_voice(language: str = 'hinglish', gender: str = 'female') -> str:
    return VOICE_MAP.get((language.lower(), gender.lower()), 'hi-IN-SwaraNeural')


async def synth(text: str, out_path: str, voice: Optional[str] = None, rate: str = '+0%') -> str:
    """Synthesize narration to MP3. Returns the output path. Falls back to silent file on failure."""
    voice = voice or 'hi-IN-SwaraNeural'
    try:
        import edge_tts  # noqa: F401
        comm = edge_tts.Communicate(text=text, voice=voice, rate=rate)
        await comm.save(out_path)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            return out_path
    except Exception as e:
        print(f'[tts] edge-tts failed: {e}')
    # Fallback: 3 second silent mp3 via ffmpeg
    await _silent(out_path, seconds=max(3, int(len(text.split()) / 2.5)))
    return out_path


async def _silent(out_path: str, seconds: int = 3):
    from video.ffmpeg_bin import FFMPEG
    proc = await asyncio.create_subprocess_exec(
        FFMPEG, '-y', '-f', 'lavfi', '-i', f'anullsrc=r=24000:cl=mono',
        '-t', str(seconds), '-q:a', '9', out_path,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
