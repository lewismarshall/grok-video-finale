#!/usr/bin/env bash
# Rebuild the finale, the trilogy, the poster, and the pages files.
# Needs input/argon-act1.mp4 and input/deepseek-spoof.mp4 already in place.
set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv .venv
.venv/bin/pip install -q numpy pillow moderngl

mkdir -p out docs
ffmpeg -y -i input/deepseek-spoof.mp4 -vf "select=eq(n\,1799)" -frames:v 1 out/last_deepseek.png

.venv/bin/python src/audio_synth.py
.venv/bin/python src/render_finale.py --movie
.venv/bin/python src/assemble.py

echo "built out/finale.mp4 out/trilogy.mp4 out/poster.png and docs/"
