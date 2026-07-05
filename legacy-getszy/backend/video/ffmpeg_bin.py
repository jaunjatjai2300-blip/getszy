"""Resilient ffmpeg binary resolver.

Order of preference:
  1. FFMPEG_BIN env var
  2. system ffmpeg (apt-installed)
  3. imageio-ffmpeg bundled binary (Python package, always available)
"""
import os
import shutil


def get_ffmpeg() -> str:
    explicit = os.environ.get('FFMPEG_BIN', '').strip()
    if explicit and os.path.exists(explicit):
        return explicit
    sys_bin = shutil.which('ffmpeg')
    if sys_bin:
        return sys_bin
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    return 'ffmpeg'  # last resort - will raise at call-time


FFMPEG = get_ffmpeg()
