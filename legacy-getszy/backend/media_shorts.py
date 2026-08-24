"""Shorts / Reel Generator pipeline (free, no paid services).

Flow: resolve source (file upload OR YouTube URL via yt-dlp) -> transcribe
(Whisper, free) -> plan captions on a timeline -> render a 9:16 (or other)
vertical cut with burned captions using ffmpeg.

Heavy tools (yt-dlp, ffmpeg, ffprobe) are imported/resolved lazily and every
public function degrades to a clear ``{'error': ...}`` dict instead of raising,
so a missing binary never 500s a customer request.
"""
import os
import re
import logging
import tempfile
import subprocess
from typing import List, Dict, Any, Optional

from video.ffmpeg_bin import get_ffmpeg

logger = logging.getLogger('getszy.media_shorts')


def split_sentences(text: str) -> List[str]:
    text = re.sub(r'\s+', ' ', (text or '')).strip()
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p for p in parts if p.strip()]


def assign_timeline(sentences: List[str], duration: float) -> List[Dict[str, Any]]:
    """Evenly spread sentences across the clip duration."""
    if not sentences or duration <= 0:
        return []
    n = len(sentences)
    step = duration / n
    caps = []
    for i, s in enumerate(sentences):
        start = round(i * step, 2)
        end = round((i + 1) * step, 2)
        caps.append({'text': s, 'start': start, 'end': end})
    return caps


def make_srt(captions: List[Dict[str, Any]]) -> str:
    out = []
    for i, c in enumerate(captions, 1):
        def fmt(t):
            ms = int(round((t - int(t)) * 1000))
            h = int(t) // 3600
            m = (int(t) % 3600) // 60
            s = int(t) % 60
            return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
        out.append(f'{i}\n{fmt(c["start"])} --> {fmt(c["end"])}\n{c["text"]}\n')
    return '\n'.join(out)


def build_shorts_command(input_path: str, output_path: str, srt_path: Optional[str] = None,
                         orientation: str = '9:16') -> List[str]:
    ffmpeg = get_ffmpeg()
    if orientation == '9:16':
        vf = 'scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280'
    elif orientation == '1:1':
        vf = 'scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080'
    elif orientation == '16:9':
        vf = 'scale=1280:720'
    else:
        vf = 'scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280'
    if srt_path:
        vf += f",subtitles='{srt_path}'"
    return [ffmpeg, '-i', input_path, '-vf', vf, '-c:a', 'copy', '-y', output_path]


def _resolve_source(source: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Return {'path': ...} or {'error': ...}. Accepts a file path, raw bytes,
    or a YouTube URL (fetched via yt-dlp when available)."""
    # YouTube URL
    if isinstance(source, str) and re.match(r'https?://(www\.)?(youtube\.com|youtu\.be)/', source):
        try:
            from yt_dlp import YoutubeDL
        except ImportError:
            return {'error': 'yt-dlp not installed on this server'}
        tmp = tempfile.mkdtemp(prefix='shorts_')
        out_tmpl = os.path.join(tmp, '%(id)s.%(ext)s')
        try:
            with YoutubeDL({'outtmpl': out_tmpl, 'format': 'mp4/best', 'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(source, download=True)
                # find the downloaded file
                for f in os.listdir(tmp):
                    if f.endswith(('.mp4', '.webm', '.mkv', '.mov')):
                        return {'path': os.path.join(tmp, f)}
                return {'error': 'yt-dlp downloaded but no video file found'}
        except Exception as e:  # noqa: BLE001
            return {'error': f'yt-dlp failed: {e}'}

    # Raw bytes (uploaded file)
    if isinstance(source, (bytes, bytearray)):
        tmp = tempfile.mkdtemp(prefix='shorts_')
        path = os.path.join(tmp, 'input.mp4')
        with open(path, 'wb') as fh:
            fh.write(source)
        return {'path': path}

    # Existing path
    if isinstance(source, str) and os.path.exists(source):
        return {'path': source}

    return {'error': 'no usable video source provided'}


def run_shorts(source: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """End-to-end shorts generation. Returns {'output': path, 'captions': [...],
    'provider': ...} or {'error': ...}. Never raises on missing tools."""
    orientation = params.get('orientation', '9:16')
    resolved = _resolve_source(source, params)
    if 'error' in resolved:
        return resolved
    input_path = resolved['path']

    # Transcribe (free Whisper) -> captions with timeline.
    captions: List[Dict[str, Any]] = []
    try:
        from whisper_stt import transcribe as whisper_transcribe
        with open(input_path, 'rb') as fh:
            audio = fh.read()
        result = whisper_transcribe(audio, os.path.basename(input_path))
        text = result.get('text', '')
        # Duration via ffprobe (guarded)
        duration = _ffprobe_duration(input_path) or 30.0
        captions = assign_timeline(split_sentences(text), duration)
    except Exception as e:  # noqa: BLE001
        logger.warning('shorts transcription failed: %s', e)
        return {'error': f'transcription failed: {e}'}

    if not captions:
        return {'error': 'no speech detected to caption'}

    srt_path = input_path + '.srt'
    with open(srt_path, 'w', encoding='utf-8') as fh:
        fh.write(make_srt(captions))

    out_dir = os.path.dirname(input_path)
    output_path = os.path.join(out_dir, 'shorts_out.mp4')
    cmd = build_shorts_command(input_path, output_path, srt_path, orientation)
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
    except Exception as e:  # noqa: BLE001
        return {'error': f'ffmpeg render failed: {e}'}

    return {'output': output_path, 'captions': captions, 'provider': 'whisper+ffmpeg', 'orientation': orientation}


def _ffprobe_duration(path: str) -> Optional[float]:
    try:
        import subprocess as sp
        ffprobe = os.environ.get('FFPROBE_BIN') or 'ffprobe'
        res = sp.run(
            [ffprobe, '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', path],
            capture_output=True, text=True, timeout=30,
        )
        return float(res.stdout.strip()) if res.stdout.strip() else None
    except Exception:  # noqa: BLE001
        return None
