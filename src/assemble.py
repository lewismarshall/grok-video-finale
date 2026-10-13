"""Concat the trilogy, check the joins, publish the pages files."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import FPS, HEIGHT, WIDTH  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
DOCS = ROOT / "docs"
INPUT = ROOT / "input"
LIMIT = 94 * 1024 * 1024


def run(cmd):
    print(" ".join(str(c) for c in cmd))
    subprocess.check_call(cmd)


def probe(path):
    raw = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size:stream=codec_name,codec_type,width,height,avg_frame_rate,sample_rate,channels",
            "-of", "json", str(path),
        ]
    )
    return json.loads(raw)


def extract(path, frame, dest):
    run(
        [
            "ffmpeg", "-y", "-i", str(path),
            "-vf", f"select=eq(n\\,{frame})",
            "-frames:v", "1", str(dest),
        ]
    )


def mae(a, b):
    aa = np.asarray(Image.open(a).convert("RGB"), np.float32)
    bb = np.asarray(Image.open(b).convert("RGB"), np.float32)
    if aa.shape != bb.shape:
        raise SystemExit(f"shape {a} {aa.shape} vs {b} {bb.shape}")
    return float(np.mean(np.abs(aa - bb)))


def require_video(path, duration, audio=True):
    info = probe(path)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    if v["width"] != WIDTH or v["height"] != HEIGHT:
        raise SystemExit(f"{path} is {v['width']}x{v['height']}")
    if v["avg_frame_rate"] not in ("30/1", "30/1"):
        if v["avg_frame_rate"] != "30/1":
            raise SystemExit(f"{path} fps {v['avg_frame_rate']}")
    got = float(info["format"]["duration"])
    if abs(got - duration) > 0.08:
        raise SystemExit(f"{path} duration {got} != {duration}")
    if audio:
        a = next(s for s in info["streams"] if s["codec_type"] == "audio")
        if a["codec_name"] != "aac":
            raise SystemExit(f"{path} audio {a['codec_name']}")
        if a.get("sample_rate") != "48000":
            raise SystemExit(f"{path} sample rate {a.get('sample_rate')}")
    print(f"ok {path.name}  {got:.3f}s  {info['format'].get('size')} bytes")
    return info


def build_trilogy():
    lst = OUT / "trilogy.txt"
    lst.write_text(
        "file '../input/argon-act1.mp4'\n"
        "file '../input/deepseek-spoof.mp4'\n"
        "file 'finale.mp4'\n"
    )
    dest = OUT / "trilogy.mp4"
    run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
            "-c", "copy", "-movflags", "+faststart", str(dest),
        ]
    )
    size = dest.stat().st_size
    if size > LIMIT:
        print(f"trilogy {size/1e6:.1f} MB, re-encoding under 94 MB")
        tmp = OUT / "trilogy-small.mp4"
        run(
            [
                "ffmpeg", "-y", "-i", str(dest),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26", "-preset", "veryfast",
                "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                "-movflags", "+faststart", str(tmp),
            ]
        )
        tmp.replace(dest)
        size = dest.stat().st_size
        if size > LIMIT:
            tmp = OUT / "trilogy-smaller.mp4"
            run(
                [
                    "ffmpeg", "-y", "-i", str(dest),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "30", "-preset", "veryfast",
                    "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
                    "-movflags", "+faststart", str(tmp),
                ]
            )
            tmp.replace(dest)
    print(f"trilogy {dest.stat().st_size/1e6:.1f} MB")


def check_frames():
    work = OUT / "check"
    work.mkdir(exist_ok=True)
    extract(INPUT / "deepseek-spoof.mp4", 1799, work / "ds_last.png")
    extract(OUT / "finale.mp4", 0, work / "fin_first.png")
    err = mae(work / "ds_last.png", work / "fin_first.png")
    print(f"finale frame 0 vs deepseek last  mae {err:.2f}")
    if err > 12:
        raise SystemExit("opening frame does not match the DeepSeek end card")

    extract(OUT / "trilogy.mp4", 0, work / "tri_0.png")
    extract(INPUT / "argon-act1.mp4", 0, work / "ar_0.png")
    extract(OUT / "trilogy.mp4", 1259, work / "tri_ar_last.png")
    extract(INPUT / "argon-act1.mp4", 1259, work / "ar_last.png")
    extract(OUT / "trilogy.mp4", 1260, work / "tri_ds.png")
    extract(INPUT / "deepseek-spoof.mp4", 0, work / "ds_0.png")
    extract(OUT / "trilogy.mp4", 3059, work / "tri_ds_last.png")
    extract(OUT / "trilogy.mp4", 3060, work / "tri_fin.png")

    checks = {
        "trilogy start vs argon start": mae(work / "tri_0.png", work / "ar_0.png"),
        "argon join": mae(work / "tri_ar_last.png", work / "ar_last.png"),
        "deepseek join": mae(work / "tri_ds.png", work / "ds_0.png"),
        "finale join vs deepseek last": mae(work / "tri_ds_last.png", work / "ds_last.png"),
        "finale join vs finale first": mae(work / "tri_fin.png", work / "fin_first.png"),
    }
    for name, err in checks.items():
        print(f"{name}: mae {err:.2f}")
        if err > 18:
            raise SystemExit(f"join failed: {name}")


def publish():
    DOCS.mkdir(exist_ok=True)
    for name in ("finale.mp4", "trilogy.mp4", "poster.png"):
        src = OUT / name
        dst = DOCS / name
        dst.write_bytes(src.read_bytes())
        print(f"docs/{name}  {dst.stat().st_size/1e6:.1f} MB")


def main():
    require_video(OUT / "finale.mp4", 60.0)
    if not (OUT / "poster.png").exists():
        raise SystemExit("missing poster")
    build_trilogy()
    require_video(OUT / "trilogy.mp4", 162.0)
    check_frames()
    publish()
    print("assemble ok")


if __name__ == "__main__":
    main()
