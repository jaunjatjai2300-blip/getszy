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
        # Ken Burns via zoompan
        zoom_expr = {
            'ken-burns-in': f"zoompan=z='min(zoom+0.0015,1.15)':d={secs*25}:s={w}x{h}:fps=25",
            'ken-burns-out': f"zoompan=z='if(eq(on,1),1.15,max(1.0,zoom-0.0015))':d={secs*25}:s={w}x{h}:fps=25",
            'static': f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps=25"
        }.get(motion, f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps=25")
        # Subtitle overlay
        vf = f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,crop={w*2}:{h*2},{zoom_expr}"
        if subtitles and sc.get('narration_chunk'):
            line = _escape_drawtext(sc['narration_chunk'][:120])
            # Bottom-middle, large bold white with shadow
            vf += (",drawtext=text='" + line + "':fontcolor=white:fontsize=48:"
                   "box=1:boxcolor=black@0.55:boxborderw=18:"
                   f"x=(w-text_w)/2:y=h-text_h-120")
        cmd = [
            FFMPEG, '-y', '-loop', '1', '-t', str(secs), '-i', img,
            '-vf', vf, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', '25',
            '-preset', 'veryfast', '-crf', '23', '-an', clip_path,
        ]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        _, err = await proc.communicate()
        if proc.returncode != 0:
            print(f'[compose] clip {i} failed: {(err or b"")[:300]}')
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
    _, err = await proc.communicate()
    if proc.returncode != 0:
        return {'error': f'concat failed: {(err or b"")[:200].decode("utf-8", "ignore")}'}
    # 3. Mux with audio (shortest)
    final_cmd = [
        FFMPEG, '-y', '-i', silent_concat, '-i', audio_path,
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-shortest', out_path,
    ]
    proc = await asyncio.create_subprocess_exec(*final_cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()
    if proc.returncode != 0:
        # If no audio, just copy silent
        os.replace(silent_concat, out_path)
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
