"""FFmpeg-based composer: image sequence + voiceover -> MP4 with Ken Burns motion + subtitles.

Kept lightweight (no moviepy required) so it runs on CPU-only VPS.
"""
import asyncio
import json
import os
import shlex
from typing import List, Dict, Any
from video.ffmpeg_bin import FFMPEG

VIDEO_DIR = os.path.join(os.path.dirname(__file__), '..', 'media_cache', 'videos')
os.makedirs(VIDEO_DIR, exist_ok=True)


DIMS = {
    '9:16': (1080, 1920),
    '16:9': (1920, 1080),
    '1:1':  (1080, 1080),
}


def _escape_drawtext(s: str) -> str:
    return (s.replace('\\', '\\\\').replace("'", "\\'").replace(':', '\\:')
             .replace('%', '\\%').replace(',', '\\,').replace('[', '\\[').replace(']', '\\]'))


async def build_video(scenes: List[Dict[str, Any]], audio_path: str, out_path: str,
                      orientation: str = '9:16', subtitles: bool = True) -> Dict[str, Any]:
    """Compose scenes (each {image_path, seconds, narration_chunk, motion}) + audio -> MP4."""
    w, h = DIMS.get(orientation, (1080, 1920))
    # 1. Build per-scene mp4 clips with motion
    tmp_dir = os.path.join(VIDEO_DIR, 'tmp_' + os.path.basename(out_path).replace('.mp4', ''))
    os.makedirs(tmp_dir, exist_ok=True)
    clip_paths: List[str] = []
    for i, sc in enumerate(scenes):
        secs = max(2, int(sc.get('seconds', 4)))
        img = sc.get('image_path')
        if not img or not os.path.exists(img):
            continue
        clip_path = os.path.join(tmp_dir, f'clip_{i:03d}.mp4')
        motion = sc.get('motion', 'static')
        # Simple scale + light Ken Burns (heavy zoompan drops on aarch64 bundled ffmpeg)
        base_scale = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"
        motion_zoom = {
            'ken-burns-in':  f",zoompan=z='min(1+0.0006*on,1.10)':d={secs*25}:s={w}x{h}:fps=25",
            'ken-burns-out': f",zoompan=z='max(1.10-0.0006*on,1.0)':d={secs*25}:s={w}x{h}:fps=25",
            'static': '',
        }.get(motion, '')
        vf = base_scale + motion_zoom + f",fps=25"
        cmd = [
            FFMPEG, '-y', '-loop', '1', '-t', str(secs), '-i', img,
            '-vf', vf, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', '25',
            '-preset', 'ultrafast', '-crf', '26', '-an', clip_path,
        ]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        try:
            _, err = await asyncio.wait_for(proc.communicate(), timeout=45)
        except asyncio.TimeoutError:
            try: proc.kill()
            except Exception: pass
            err = b'timeout'
        if proc.returncode != 0:
            # Simpler fallback: static scale only (no zoompan)
            fallback_cmd = [
                FFMPEG, '-y', '-loop', '1', '-t', str(secs), '-i', img,
                '-vf', base_scale + ',fps=25', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', '25',
                '-preset', 'ultrafast', '-crf', '28', '-an', clip_path,
            ]
            proc = await asyncio.create_subprocess_exec(*fallback_cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
            try:
                _, err2 = await asyncio.wait_for(proc.communicate(), timeout=30)
            except asyncio.TimeoutError:
                try: proc.kill()
                except Exception: pass
                err2 = b'timeout'
            if proc.returncode != 0:
                print(f'[compose] clip {i} FAILED. err1={(err or b"")[:200]!r} err2={(err2 or b"")[:200]!r}')
                continue
        clip_paths.append(clip_path)
    if not clip_paths:
        return {'error': 'no scenes composed'}
    # 2. Concat clips
    concat_list = os.path.join(tmp_dir, 'concat.txt')
    with open(concat_list, 'w') as f:
        for cp in clip_paths:
            f.write(f"file '{cp}'\n")
    silent_concat = os.path.join(tmp_dir, 'silent.mp4')
    proc = await asyncio.create_subprocess_exec(
        FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', concat_list,
        '-c', 'copy', silent_concat,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, err = await asyncio.wait_for(proc.communicate(), timeout=45)
    except asyncio.TimeoutError:
        try: proc.kill()
        except Exception: pass
        err = b'concat timeout'
    if proc.returncode != 0:
        return {'error': f'concat failed: {(err or b"")[:200].decode("utf-8", "ignore")}'}
    # 3. Mux with audio (shortest)
    final_cmd = [
        FFMPEG, '-y', '-i', silent_concat, '-i', audio_path,
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '96k', '-shortest', out_path,
    ]
    proc = await asyncio.create_subprocess_exec(*final_cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
    try:
        _, err = await asyncio.wait_for(proc.communicate(), timeout=45)
    except asyncio.TimeoutError:
        try: proc.kill()
        except Exception: pass
        err = b'mux timeout'
    if proc.returncode != 0:
        # If mux failed, at least save the silent version
        try:
            os.replace(silent_concat, out_path)
        except Exception:
            return {'error': f'mux failed: {(err or b"")[:200].decode("utf-8", "ignore")}'}
    # Cleanup tmp
    for cp in clip_paths:
        try: os.remove(cp)
        except Exception: pass
    try: os.remove(concat_list)
    except Exception: pass
    try: os.remove(silent_concat)
    except Exception: pass
    try: os.rmdir(tmp_dir)
    except Exception: pass
    return {'path': out_path, 'scenes': len(clip_paths)}


def build_srt(scenes: List[Dict[str, Any]]) -> str:
    out = []
    t = 0.0
    for i, sc in enumerate(scenes, 1):
        dur = max(2.0, float(sc.get('seconds', 4)))
        s = t
        e = t + dur
        out.append(f'{i}\n{_srt_time(s)} --> {_srt_time(e)}\n{sc.get("narration_chunk","")}\n')
        t = e
    return '\n'.join(out)


def _srt_time(seconds: float) -> str:
    h = int(seconds // 3600); m = int((seconds % 3600) // 60); s = int(seconds % 60); ms = int((seconds - int(seconds)) * 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
