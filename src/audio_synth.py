"""Procedural soundtrack. No samples: sines, saws, noise, and a drop."""

import math
import wave
from pathlib import Path

import numpy as np

from config import (
    BAR,
    BEAT,
    DURATION,
    FPS,
    FRAMES,
    SR,
    T_BACK,
    T_BANANA,
    T_CLINK,
    T_CLICK,
    T_CRUNCH,
    T_DROP,
    T_FLAG,
    T_GLITCH,
    T_GRAV,
    T_HONK,
    T_IMPACT,
    T_JUGGLE,
    T_LAND,
    T_RISER,
    T_STAMP,
    T_WELCOME,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"


def one_pole(x, cutoff_hz):
    x = np.asarray(x, np.float64)
    a = math.exp(-2.0 * math.pi * float(np.mean(cutoff_hz)) / SR) if np.ndim(cutoff_hz) == 0 else None
    y = np.empty_like(x)
    acc = 0.0
    if a is not None:
        b = 1.0 - a
        for i in range(x.shape[0]):
            acc = a * acc + b * x[i]
            y[i] = acc
        return y
    cut = np.asarray(cutoff_hz, np.float64)
    for i in range(x.shape[0]):
        ai = math.exp(-2.0 * math.pi * cut[i] / SR)
        acc = ai * acc + (1.0 - ai) * x[i]
        y[i] = acc
    return y


def env_ar(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(1.0, t / max(attack, 1e-4)) * np.exp(-t / max(decay, 1e-4))


def kick():
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    f = 168.0 * np.exp(-t * 26.0) + 46.0
    phase = 2.0 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase) * np.exp(-t * 8.5)
    click = np.random.default_rng(2).standard_normal(n) * np.exp(-t * 220.0) * 0.28
    return body + click


def snare(rng):
    n = int(0.2 * SR)
    t = np.arange(n) / SR
    noise = np.diff(rng.standard_normal(n), prepend=0.0)
    tone = np.sin(2.0 * np.pi * 196.0 * t) * np.exp(-t * 28.0)
    return (noise * 0.65 + tone * 0.45) * np.exp(-t * 16.0)


def hat(rng, open_=False):
    dur = 0.14 if open_ else 0.045
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = np.diff(rng.standard_normal(n), prepend=0.0)
    return noise * np.exp(-t * (10.0 if open_ else 48.0))


def crash(rng):
    n = int(2.0 * SR)
    t = np.arange(n) / SR
    noise = np.diff(rng.standard_normal(n), prepend=0.0)
    return noise * np.exp(-t * 1.45)


def bass(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    saw = 2.0 * np.mod(freq * t, 1.0) - 1.0
    saw = one_pole(saw, 520.0)
    sub = np.sin(2.0 * np.pi * freq * t)
    sub2 = np.sin(2.0 * np.pi * freq * 0.5 * t)
    env = np.minimum(1.0, t * 250.0) * np.exp(-t * 2.4)
    return (saw * 0.35 + sub * 0.45 + sub2 * 0.55) * env


def supersaw(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for i, det in enumerate((-0.018, -0.008, 0.0, 0.009, 0.02)):
        ph = np.mod(freq * (1.0 + det) * t, 1.0)
        y += (2.0 * ph - 1.0) * (1.0 if i == 2 else 0.62)
    y = one_pole(y / 3.2, 2800.0)
    env = np.minimum(1.0, t * 40.0) * np.clip(1.0 - (t / dur), 0.0, 1.0) ** 0.6
    return y * env


def square(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.sign(np.sin(2.0 * np.pi * freq * t + 1e-6))
    return y * np.exp(-t * 7.0) * np.minimum(1.0, t * 500.0)


def pad(freq, dur, attack_t=1.4):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t)
    y += 0.5 * np.sin(2 * np.pi * freq * 1.004 * t)
    y += 0.22 * np.sin(2 * np.pi * freq * 2.0 * t)
    attack = np.minimum(1.0, t / max(attack_t, 1e-3))
    release = np.clip((dur - t) / 1.4, 0.0, 1.0)
    return y * attack * release


def bell(freq, dur=1.8):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t) * np.exp(-t * 2.1)
    y += 0.5 * np.sin(2 * np.pi * freq * 2.01 * t) * np.exp(-t * 3.3)
    y += 0.22 * np.sin(2 * np.pi * freq * 3.0 * t) * np.exp(-t * 4.6)
    return y


def boing(f0=210.0):
    n = int(0.62 * SR)
    t = np.arange(n) / SR
    freq = f0 * (1.0 + 1.7 * np.exp(-t * 6.0) * np.cos(2 * np.pi * 13.0 * t))
    phase = 2 * np.pi * np.cumsum(freq) / SR
    return np.sin(phase) * np.exp(-t * 3.1)


def honk():
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    y = np.sign(np.sin(2 * np.pi * 494.0 * t)) * 0.55
    y += np.sign(np.sin(2 * np.pi * 740.0 * t)) * 0.4
    env = np.minimum(1.0, t * 180.0) * np.exp(-t * 6.0)
    return y * env


def scratch(rng):
    n = int(0.38 * SR)
    t = np.arange(n) / SR
    f = 2400.0 * np.exp(-t * 7.5)
    phase = 2 * np.pi * np.cumsum(f) / SR
    noise = rng.standard_normal(n) * 0.25
    return (np.sin(phase) * 0.7 + noise) * np.linspace(1.0, 0.0, n)


def slide(f0, f1, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = t / dur
    f = f0 + (f1 - f0) * (x ** 1.4)
    phase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(phase) * np.sin(np.pi * np.clip(x, 0, 1)) ** 0.8


def clink():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * 1760 * t) + 0.55 * np.sin(2 * np.pi * 2340 * t)
    y += 0.25 * np.sin(2 * np.pi * 3520 * t)
    return y * np.exp(-t * 5.5)


def crunch(rng):
    n = int(0.28 * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    bursts = (0.5 + 0.5 * np.sin(2 * np.pi * 38.0 * t)) * np.exp(-t * 14.0)
    return noise * bursts


def riser(rng, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = t / max(dur, 1e-4)
    f = 160.0 * np.exp(math.log(4200.0 / 160.0) * x)
    phase = 2 * np.pi * np.cumsum(f) / SR
    saw = np.sin(phase) + 0.4 * np.sin(phase * 2.0)
    noise = rng.standard_normal(n)
    noise = one_pole(noise, 300.0 + 7000.0 * x * x)
    return (saw * 0.4 + noise * 0.45) * (x ** 1.5)


def whoosh(rng, dur=0.7):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = t / dur
    noise = one_pole(rng.standard_normal(n), 200.0 + 5000.0 * x)
    return noise * np.sin(np.pi * x) ** 1.4


def metal(freq=640.0):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t)
    y += 0.6 * np.sin(2 * np.pi * freq * 2.37 * t)
    y += 0.3 * np.sin(2 * np.pi * freq * 4.1 * t)
    return y * np.exp(-t * 8.0)


def slap(rng):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    return rng.standard_normal(n) * np.exp(-t * 40.0)


def click():
    n = int(0.04 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * 1400 * t) * np.exp(-t * 80.0)


def add(buf, t, sig, gain=1.0, pan=0.0):
    sig = np.asarray(sig, np.float64) * gain
    ang = (pan + 1.0) * 0.25 * math.pi
    left = sig * math.cos(ang)
    right = sig * math.sin(ang)
    start = int(round(t * SR))
    if start >= buf.shape[0] or start < -sig.shape[0]:
        return
    if start < 0:
        left = left[-start:]
        right = right[-start:]
        start = 0
    end = min(buf.shape[0], start + left.shape[0])
    n = end - start
    if n <= 0:
        return
    buf[start:end, 0] += left[:n]
    buf[start:end, 1] += right[:n]


def add_kick_env(env, t):
    n = int(0.18 * SR)
    tt = np.arange(n) / SR
    e = np.exp(-tt * 18.0)
    start = int(round(t * SR))
    end = min(env.shape[0], start + n)
    if start < 0 or end <= start:
        return
    env[start:end] = np.maximum(env[start:end], e[: end - start])


NOTE = {
    "D2": 73.42, "A2": 110.00, "Bb2": 116.54, "C3": 130.81, "D3": 146.83,
    "F3": 174.61, "G3": 196.00, "A3": 220.00, "Bb3": 233.08, "C4": 261.63,
    "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.00, "A4": 440.00,
    "Bb4": 466.16, "C5": 523.25, "D5": 587.33, "E5": 659.25, "F5": 698.46,
    "G5": 783.99, "A5": 880.00, "C6": 1046.50,
}

CHORDS = [
    ("D3", ("D4", "F4", "A4", "C5")),
    ("Bb2", ("Bb3", "D4", "F4", "A4")),
    ("F3", ("F3", "A3", "C4", "E4")),
    ("C3", ("C4", "E4", "G4", "Bb4")),
]


def synth():
    rng = np.random.default_rng(47)
    n = int(DURATION * SR)
    music = np.zeros((n, 2))
    sfx = np.zeros((n, 2))
    kick_env = np.zeros(n)
    k = kick()
    sn = snare(rng)
    hh = hat(rng, False)
    ho = hat(rng, True)
    cr = crash(rng)

    def beat_time(i):
        return T_IMPACT + i * BEAT

    last_beat = int((T_CLICK - T_IMPACT) / BEAT)
    for i in range(last_beat + 1):
        t = beat_time(i)
        if t >= T_CLICK:
            break
        bar_pos = i % 4
        in_drop = T_DROP <= t < T_GRAV or T_BACK <= t < 47.2
        in_groove = T_IMPACT <= t < T_RISER
        in_float = T_GRAV <= t < T_BACK
        in_end = 47.2 <= t < T_CLICK
        if in_groove or in_drop:
            if in_drop or bar_pos in (0, 2):
                add(music, t, k, 0.92, 0.0)
                add_kick_env(kick_env, t)
            if bar_pos in (1, 3):
                add(music, t, sn, 0.42, 0.04)
            if i % 2 == 1 and in_drop:
                add(music, t, ho, 0.16, 0.35)
            elif in_groove or in_drop:
                add(music, t, hh, 0.09, 0.28)
                add(music, t + BEAT * 0.5, hh, 0.06, -0.2)
        elif in_float and bar_pos == 0:
            add(music, t, k, 0.55, 0.0)
            add_kick_env(kick_env, t)
        elif in_end and bar_pos == 0 and t < 56.0:
            add(music, t, k, 0.22, 0.0)

    # Snare rush into the drop.
    t = T_RISER
    step = BEAT * 0.5
    while t < T_DROP:
        add(music, t, sn, 0.28 + 0.3 * ((t - T_RISER) / (T_DROP - T_RISER)), 0.0)
        step *= 0.86
        t += max(step, 0.045)

    # Bass + supersaw chords on the bar grid from the impact.
    bar_i = 0
    t = T_IMPACT
    while t < 47.2:
        root_name, tones = CHORDS[bar_i % 4]
        muffled = t < T_DROP
        dur = BAR * 0.98
        if t < T_GRAV or t >= T_BACK:
            add(music, t, bass(NOTE[root_name], dur * 0.92), 0.34 if muffled else 0.72, 0.0)
        if t >= T_DROP - 1e-6 and (t < T_GRAV or t >= T_BACK):
            pan = -0.35
            for name in tones:
                add(music, t, supersaw(NOTE[name], dur), 0.13, pan)
                pan += 0.22
            # 16th arp, a little smug.
            step_n = 8 if t >= T_GRAV else 16
            arp_notes = [NOTE[tones[k % len(tones)]] * 2 for k in range(step_n)]
            for s, freq in enumerate(arp_notes):
                add(music, t + s * (BAR / step_n), square(freq, BAR / step_n * 0.9), 0.045, 0.15 if s % 2 else -0.15)
        elif T_GRAV <= t < T_BACK:
            add(music, t, pad(NOTE[root_name] * 2, BAR, 0.05), 0.22, -0.2)
            add(music, t, pad(NOTE[tones[1]], BAR, 0.05), 0.16, 0.25)
        bar_i += 1
        t += BAR

    # Ending pad, wide and a bit ridiculous.
    for name, pan in (("D3", -0.4), ("F3", -0.15), ("A3", 0.15), ("C4", 0.4), ("D4", 0.0)):
        add(music, 47.0, pad(NOTE[name], 13.0), 0.1, pan)

    melody = ["D5", "F5", "A5", "C6", "A5", "G5", "F5", "E5", "D5", "A4", "D5"]
    for i, name in enumerate(melody):
        add(music, 49.1 + i * 0.72, bell(NOTE[name], 1.5), 0.22, -0.25 if i % 2 == 0 else 0.25)

    # Sound effects, synced to the gags.
    add(sfx, T_GLITCH + 0.15, scratch(rng), 0.45, 0.0)
    add(sfx, T_GLITCH, riser(rng, T_IMPACT - T_GLITCH), 0.28, 0.0)
    add(sfx, T_RISER, riser(rng, T_DROP - T_RISER), 0.55, 0.0)
    add(sfx, T_IMPACT, k, 1.05, 0.0)
    add(sfx, T_IMPACT, crash(rng), 0.35, 0.0)
    add(sfx, T_HONK, honk(), 0.5, 0.05)
    add(sfx, T_WELCOME - 0.05, boing(180), 0.4, -0.2)
    add(sfx, T_JUGGLE, boing(240), 0.28, -0.4)
    add(sfx, T_JUGGLE + 0.7, boing(280), 0.26, 0.4)
    add(sfx, T_JUGGLE + 1.4, boing(220), 0.24, -0.3)
    add(sfx, T_JUGGLE + 2.1, boing(300), 0.22, 0.35)
    add(sfx, T_DROP, crash(rng), 0.55, 0.0)
    add(sfx, T_DROP, whoosh(rng, 1.1), 0.4, 0.0)
    add(sfx, T_LAND, k, 0.8, 0.0)
    dust_n = int(0.5 * SR)
    dust = rng.standard_normal(dust_n) * np.exp(-np.arange(dust_n) / SR * 6.0)
    add(sfx, T_LAND, dust, 0.35, 0.0)
    add(sfx, T_FLAG, metal(520), 0.4, 0.1)
    add(sfx, T_FLAG + 0.12, metal(780), 0.22, -0.1)
    add(sfx, T_CLINK, clink(), 0.42, 0.0)
    add(sfx, T_GRAV, slide(320, 1400, 1.6), 0.42, 0.0)
    add(sfx, T_CRUNCH, crunch(rng), 0.5, 0.0)
    add(sfx, T_BACK, slide(900, 220, 0.6), 0.22, 0.0)
    add(sfx, T_STAMP, slap(rng), 0.55, 0.15)
    add(sfx, T_CLICK, click(), 0.4, 0.0)
    add(sfx, T_CLICK + 0.08, bell(1174.0, 0.8), 0.12, 0.0)

    # A quiet heartbeat under the glitch, so the silent end card doesn't just pop.
    for i in range(6):
        tt = 1.15 + i * 0.42
        if tt >= T_IMPACT:
            break
        pulse = np.sin(2 * np.pi * 58.0 * np.arange(int(0.18 * SR)) / SR)
        pulse *= np.exp(-np.arange(pulse.size) / SR * 14.0)
        add(sfx, tt, pulse, 0.18, 0.0)

    duck = np.clip(1.0 - 0.78 * kick_env, 0.2, 1.0)
    mix = music * duck[:, None] + sfx
    # Short room on the whole mix, mostly for the drop.
    delay = int(0.11 * SR)
    room = np.zeros_like(mix)
    room[delay:] += mix[:-delay] * 0.16
    room[delay:, 0] += mix[:-delay, 1] * 0.05
    room[delay:, 1] += mix[:-delay, 0] * 0.05
    mix = mix + room
    mix = np.tanh(mix * 1.25)
    peak = float(np.max(np.abs(mix))) + 1e-9
    mix *= 0.93 / peak
    return mix.astype(np.float32)


def bands_from(mix):
    mono = mix.mean(axis=1)
    win_n = 2048
    window = np.hanning(win_n).astype(np.float32)
    freqs = np.fft.rfftfreq(win_n, 1.0 / SR)
    edges = np.geomspace(45.0, 14000.0, 33)
    out = np.zeros((FRAMES, 32), np.float32)
    for i in range(FRAMES):
        c = int((i + 0.5) / FPS * SR)
        a = c - win_n // 2
        seg = np.zeros(win_n, np.float32)
        src_a = max(0, a)
        src_b = min(mono.shape[0], a + win_n)
        dst_a = src_a - a
        dst_b = dst_a + (src_b - src_a)
        seg[dst_a:dst_b] = mono[src_a:src_b]
        spec = np.abs(np.fft.rfft(seg * window))
        for k in range(32):
            m = (freqs >= edges[k]) & (freqs < edges[k + 1])
            out[i, k] = float(spec[m].mean()) if np.any(m) else 0.0
    out = np.log1p(out * 6.0)
    scale = float(np.percentile(out, 97)) + 1e-6
    return np.clip(out / scale, 0.0, 1.0).astype(np.float32)


def write_wav(path, mix):
    pcm = np.clip(mix, -1.0, 1.0)
    interleaved = (pcm * 32767.0).astype(np.int16)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(interleaved.tobytes())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mix = synth()
    write_wav(OUT / "finale.wav", mix)
    np.save(OUT / "bands.npy", bands_from(mix))
    peak = float(np.max(np.abs(mix)))
    rms = float(np.sqrt(np.mean(mix ** 2)))
    print(f"audio {DURATION:.0f}s  peak {peak:.3f}  rms {rms:.3f}")


if __name__ == "__main__":
    main()
