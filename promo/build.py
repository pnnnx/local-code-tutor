"""Ролик для TikTok к релизу: шаблон + тексты релиза → MP4 1080×1920, 60 fps, со звуком. Без Claude.

  python3 promo/build.py v0.4.0            # promo/releases/v0.4.0.json поверх promo/base.json → promo/out/v0.4.0.mp4
  python3 promo/build.py v0.4.0 --probe    # только 6 контрольных кадров в promo/out/v0.4.0_probe.png (секунды)

Нужно один раз: pip install playwright numpy scipy && python3 -m playwright install chromium; ffmpeg (brew install ffmpeg).
Файла релиза нет — берутся базовые тексты с версией из названия. В конце — проверка готового MP4 (кадры, fps, звук).
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC, OUT = HERE / "src", HERE / "out"
FPS, DUR = 60, 10


def merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return {k: merge(a.get(k), b[k]) if k in b else a[k] for k in {**a, **b}}
    return b if b is not None else a


def load(release: str) -> dict:
    data = json.loads((HERE / "base.json").read_text(encoding="utf-8"))
    rel = HERE / "releases" / f"{release}.json"
    over = json.loads(rel.read_text(encoding="utf-8")) if rel.exists() else {"cta": {"version": release}}
    if not rel.exists():
        print(f"нет {rel.relative_to(HERE.parent)} — базовые тексты, версия {release}")
    d = merge(data, over)
    d.pop("_comment", None)
    return d


async def render(frames: list[tuple[str, float]], outdir: Path) -> None:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        await pg.goto((SRC / "video.html").as_uri())
        await pg.evaluate("""async () => {
            for (const w of [500, 600, 700, 800, 900]) await document.fonts.load(`${w} 100px "Inter Display"`);
            await document.fonts.load('600 40px "Promo Mono"'); await document.fonts.load('700 40px "Promo Mono"');
            await document.fonts.ready;
            await Promise.all(Object.values(window.LO).map(s => new Promise(r => { const i = new Image(); i.onload = r; i.src = s; })));
        }""")
        bad = await pg.evaluate("""() => [...document.fonts].filter(f => f.status !== 'loaded').map(f => f.family + ' ' + f.weight)""")
        if bad:
            print("⚠ не загрузились шрифты:", bad)
        await pg.wait_for_timeout(200)
        for i, (name, t) in enumerate(frames):
            data = await pg.evaluate(f"renderFrame({t}); document.getElementById('c').toDataURL('image/png')")
            (outdir / f"{name}.png").write_bytes(base64.b64decode(data.split(",")[1]))
            if len(frames) > 50 and i % 100 == 0:
                print(f"  кадры: {i}/{len(frames)}", flush=True)
        await b.close()


def probe_mp4(path: Path) -> list[str]:
    q = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,pix_fmt,"
                        "avg_frame_rate,nb_frames", "-show_entries", "format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    info = json.loads(q.stdout)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = [s for s in info["streams"] if s["codec_type"] == "audio"]
    problems = []
    if (v["codec_name"], v["width"], v["height"], v["pix_fmt"], v["avg_frame_rate"]) != ("h264", 1080, 1920, "yuv420p", "60/1"):
        problems.append(f"видео {v}")
    if int(v.get("nb_frames", 0)) != FPS * DUR:
        problems.append(f"кадров {v.get('nb_frames')} вместо {FPS * DUR}")
    if not a or a[0]["codec_name"] != "aac":
        problems.append("нет AAC-звука")
    if abs(float(info["format"]["duration"]) - DUR) > 0.02:
        problems.append(f"длительность {info['format']['duration']}")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("release")
    ap.add_argument("--probe", action="store_true")
    a = ap.parse_args(argv)
    OUT.mkdir(exist_ok=True)
    (SRC / "data.js").write_text("window.DATA = " + json.dumps(load(a.release), ensure_ascii=False) + ";\n", encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if a.probe:
            ts = [0.3, 1.4, 3.6, 5.0, 7.0, 8.9]
            asyncio.run(render([(f"p{i}", t) for i, t in enumerate(ts)], tmp))
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp / "p%d.png"), "-vf", "scale=360:640,tile=6x1",
                            "-frames:v", "1", str(OUT / f"{a.release}_probe.png")], check=True)
            print("кадры для проверки:", OUT / f"{a.release}_probe.png", "(секунды", ts, ")")
            return
        print("звук…", flush=True)
        subprocess.run([sys.executable, str(SRC / "audio.py")], cwd=tmp, check=True, capture_output=True)
        print("кадры (≈3–4 мин)…", flush=True)
        (tmp / "f").mkdir()
        asyncio.run(render([(f"{i:04d}", i / FPS) for i in range(FPS * DUR)], tmp / "f"))
        out = OUT / f"{a.release}.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", str(tmp / "f" / "%04d.png"),
                        "-i", str(tmp / "audio.wav"), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "slow",
                        "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
                        "-ar", "48000", "-movflags", "+faststart", "-t", str(DUR), str(out)], check=True)
        shutil.copy(tmp / "f" / f"{int(8.9 * FPS):04d}.png", OUT / f"{a.release}_cover.png")
    problems = probe_mp4(out)
    if problems:
        sys.exit("✗ проверка MP4: " + "; ".join(problems))
    print(f"✓ {out} ({out.stat().st_size / 2**20:.1f} МБ, 1080×1920, 60 fps, 10 с, H.264 + AAC) · обложка: {out.with_name(out.stem + '_cover.png')}")


if __name__ == "__main__":
    main()
