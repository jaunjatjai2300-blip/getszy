---
name: ffmpeg drawtext captions
description: Notes on burning captions into video with ffmpeg's drawtext filter when no system fontconfig is available
---

This sandbox has no fontconfig set up for ffmpeg, so `drawtext` without an explicit `fontfile=` will fail or silently render no glyphs.

**Why:** discovered while fixing a bug where a `subtitles: bool` param was accepted end-to-end but never actually wired into the ffmpeg filter graph — captions were never burned in.

**How to apply:**
- Locate a real TTF at `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` (present on this system) and pass it via `fontfile='<path>'` in the drawtext filter, guarded with `os.path.exists()` so the feature degrades gracefully if the font is missing.
- Escape drawtext text manually (backslash, quote, colon, percent, brackets, comma) — ffmpeg filter syntax treats these as special.
- Greedy word-wrap text yourself before passing to drawtext (no auto-wrap support); cap line count so long narration never overflows the video's safe area.
- Scale fontsize relative to output width (e.g. `w/22`) so captions look correct across different aspect ratios (9:16, 16:9, 1:1).
- Apply the same caption filter string in any fallback/retry ffmpeg command path too, or captions silently disappear only on the fallback branch.
