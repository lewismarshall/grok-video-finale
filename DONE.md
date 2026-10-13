# DONE

A 60-second finale that opens on the last frame of `deepseek-spoof.mp4`, then crashes the party. Output is `out/finale.mp4`, `out/trilogy.mp4`, `out/poster.png`, and the same three files under `docs/` with `docs/index.html`. `make.sh` rebuilds all of it.

## What it is

Frame 0 is the DeepSeek end card, held, then glitched. A rocket punches out of the nucleus, honks, and waves Argon and DeepSeek in as guests. The drop is the moon arriving. They picnic. Gravity clocks off and back on. A second moon shows up in a party hat. The sign-off is a snow globe of that picnic, the line "I brought rockets to a triangle fight.", a credits crawl for Gemini 4 Argon, DeepSeek, and Grok 4.7, and a crooked APPROVED stamp.

Numbers on screen are metric: `g = 9.81 m/s²`, then `g = VIBES`, and `384400 km`.

The trilogy is Argon (42 s) + DeepSeek (60 s) + this film (60 s) = 162 s, continuous.

## Tools

- Python 3.14, moderngl 5.13, OpenGL 4.1 on the Apple M1 GPU. Headless CGL. Raymarched scene at 1600×900, HUD and type at 1920×1080, bloom, a short directional shutter blur, additive particles.
- numpy for the score and the 32-band FFT drawn in the HUD. No samples, no stock footage, no logos.
- Pillow for captions, the end card, the stamp, and the poster, using the system fonts already on the machine.
- ffmpeg: libx264, AAC, 48 kHz stereo, 30 fps, 1920×1080.

## Timings

- Picture: 1800 frames in 83 s (about 22 fps). Early frames that are just the still are much faster.
- Score: a few seconds of numpy.
- Trilogy: stream copy was 119 MB, over the 95 MB cap, so `assemble.py` re-encoded at CRF 26. That pass plus the frame checks took 34 s. Result is 67.8 MB, 162.033 s.
- Well under the 35-minute render budget.

## Checks

ffprobe: finale is 60.000 s, 1920×1080, 30 fps, H.264, AAC LC 48 kHz stereo, 43.9 MB. Trilogy matches the geometry and audio format.

Mean absolute error between frames, 0–255:

- Finale frame 0 vs DeepSeek frame 1799: 0.69
- Trilogy open vs Argon open: 0.45
- Argon cut: 1.07
- DeepSeek cut: 0.11
- Finale cut vs DeepSeek last frame: 0.31
- Finale cut vs finale frame 0: 0.33

`docs/index.html` was not opened in a browser. The page is a static player with the trilogy first, then the finale, then the poster.

## Problems

- The first full render died at the impact frame. A shockwave falloff went slightly negative and a fractional power became complex. Clamped the base at zero.
- An unused composite uniform was stripped by the driver and the render crashed looking it up. Removed it.
- Stills grabbed by jumping the clock fire every cue at once and do not age particles, so those previews look like a blizzard. The 30 fps movie ages them and is much cleaner.
- During the honk the rocket is mostly below the frame. The face reads a couple of seconds later, when it waves.
- The credits crawl shows one name at a time. Gemini 4 Argon, DeepSeek, and Grok 4.7 each land on screen before the stamp.

## Rating

8/10. The open is seamless, the rocket reads as a character, the moon gag and the end card land, and the score has a real drop. The props are still simple SDFs, and one of the best sound cues plays while the rocket is cropped.
