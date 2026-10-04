"""ASR 字幕生成入口 / ASR subtitle generation entry script.

薄壳：`音频 → MiniMax ASR → 按停顿/标点/字数切分 → SRT`。
**零业务逻辑** —— 逻辑都在 ``videogen.asr`` 与 ``videogen.subtitle``。

Thin shell: audio → MiniMax ASR → segmentation → SRT. No business logic here.

复测指令 / How to re-run:
    $py = "C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe"
    cd C:\\Users\\75203\\Downloads\\xd\\VideoGenResearch-deepseek

    # 短视频（**会产生 1 次 ASR 计费**，按音频时长计）
    & $py scripts\\asr_subtitles.py --kind short

    # **任意素材集**（assets/sets/<name>）；--reuse 复用缓存、零费用调参
    & $py scripts\\asr_subtitles.py --set omni-io-skills
    & $py scripts\\asr_subtitles.py --set omni-io-skills --reuse --max-chars 16

    # 直接指定音频文件（素材还没建成素材集时）
    & $py scripts\\asr_subtitles.py --audio "D:\\a.wav" --out "D:\\a.asr.srt"

输出 / Output:
    <素材集>/audio/asr_<name>.json    ASR 原始结果（缓存，避免重复计费）
    <素材集>/audio/<name>.asr.srt     切分后的字幕

为什么缓存：ASR 按音频时长计费，调切分参数时不该重复调用。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from videogen.asr import ASRResult, ASRUnit, transcribe  # noqa: E402
from videogen.paths import assets_dir  # noqa: E402
from videogen.sources import load_set  # noqa: E402
from videogen.subtitle import SubtitleParams, segment, to_srt, weight  # noqa: E402

# 本项目最早两套素材（尚未纳入素材集体系）的名字
LEGACY_AUDIO = {
    "short": "shortvideo.zh.wav",
    "mid": "narration.zh.wav",
}


def load_cached(path: Path) -> ASRResult:
    """读缓存的 ASR 结果 / Load a cached ASR result."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ASRResult(
        text=raw["text"],
        duration=raw["duration"],
        units=[ASRUnit(**u) for u in raw["units"]],
        speakers=raw.get("speakers", 0),
        base_url=raw.get("base_url", "cache"),
    )


def save_cache(result: ASRResult, path: Path) -> None:
    """缓存 ASR 结果 / Cache an ASR result."""
    payload = {
        "text": result.text,
        "duration": result.duration,
        "speakers": result.speakers,
        "base_url": result.base_url,
        "units": [asdict(u) for u in result.units],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="ASR 字幕生成 / ASR subtitle generation")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--kind", choices=tuple(LEGACY_AUDIO), default=None,
                     help="本项目内置素材 / built-in asset set")
    src.add_argument("--set", dest="set_name", default=None,
                     help="素材集名（assets/sets/<name>）/ named asset set")
    src.add_argument("--audio", default=None,
                     help="直接指定音频文件 / explicit audio file path")
    ap.add_argument("--out", default=None,
                    help="--audio 模式下的字幕输出路径 / SRT path for --audio mode")
    ap.add_argument("--max-chars", type=int, default=SubtitleParams.max_chars)
    ap.add_argument("--min-chars", type=int, default=SubtitleParams.min_chars)
    ap.add_argument("--pause-gap", type=float, default=SubtitleParams.pause_gap)
    ap.add_argument("--soft-gap", type=float, default=SubtitleParams.soft_gap)
    ap.add_argument("--max-seconds", type=float, default=SubtitleParams.max_seconds)
    ap.add_argument(
        "--reuse",
        action="store_true",
        help="复用已缓存的 ASR 结果，不重新调用 API（零费用）",
    )
    args = ap.parse_args()

    # ── 解析素材位置 / Resolve where the audio and cache live ─────────────
    # 三种入口统一到 (audio_path, cache_path, srt_path, label)
    if args.audio:
        audio_path = Path(args.audio)
        if not audio_path.exists():
            print(f"音频不存在 / audio not found: {audio_path}")
            return 2
        out = Path(args.out) if args.out else audio_path.with_suffix(".asr.srt")
        cache_path = out.parent / f"asr_{audio_path.stem}.json"
        srt_path, label = out, audio_path.stem
    elif args.set_name:
        asset_set = load_set(args.set_name)
        audio_path, srt_path, label = asset_set.audio, asset_set.asr_srt, asset_set.name
        cache_path = audio_path.parent / f"asr_{asset_set.name}.json"
        print(f"素材集 / set: {asset_set.describe()}")
    else:
        kind = args.kind or "short"
        audio_dir = assets_dir() / "audio"
        audio_path = audio_dir / LEGACY_AUDIO[kind]
        cache_path = audio_dir / f"asr_{kind}.json"
        srt_path, label = audio_dir / f"{kind}.asr.srt", kind

    srt_path.parent.mkdir(parents=True, exist_ok=True)

    # ── ASR ────────────────────────────────────────────────────────────────
    if args.reuse and cache_path.exists():
        result = load_cached(cache_path)
        print(f"复用缓存 / reused cache: {cache_path.name}")
    else:
        print(f"调用 ASR / calling ASR: {audio_path.name} "
              f"({audio_path.stat().st_size / 1024 / 1024:.1f} MB)")
        result = transcribe(audio_path, language="zh", timestamp_level="word")
        save_cache(result, cache_path)
        print(f"识别完成 / done: {result.summary()}")
        print(f"已缓存 / cached: {cache_path.name}")

    # ── 切分 ───────────────────────────────────────────────────────────────
    params = SubtitleParams(
        max_chars=args.max_chars,
        min_chars=args.min_chars,
        pause_gap=args.pause_gap,
        soft_gap=args.soft_gap,
        max_seconds=args.max_seconds,
    )
    cues = segment(result.units, params)
    srt_path.write_text(to_srt(cues), encoding="utf-8")

    # ── 报告 ───────────────────────────────────────────────────────────────
    total = sum(c.duration for c in cues)
    print()
    print(f"素材 / source: {label}")
    print(f"音频总长 / audio: {result.duration:.2f}s")
    print(f"字级单元 / units: {len(result.units)}")
    print(f"切出字幕 / cues: {len(cues)}")
    if cues:
        print(f"单条时长 / duration: "
              f"avg {total / len(cues):.2f}s  min {min(c.duration for c in cues):.2f}s  "
              f"max {max(c.duration for c in cues):.2f}s")
        print(f"单条字数 / chars: "
              f"avg {sum(weight(c.text) for c in cues) / len(cues):.1f}  "
              f"max {max(weight(c.text) for c in cues):.0f}")
        print()
        print("前 12 条 / first 12 cues:")
        for i, c in enumerate(cues[:12], start=1):
            print(f"  {i:>2}. [{c.start:6.2f}-{c.end:6.2f}] {c.duration:4.2f}s "
                  f"{weight(c.text):4.0f}字  {c.text}")

    print()
    print(f"已落盘 / saved: {srt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
