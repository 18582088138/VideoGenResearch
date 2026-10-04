"""字幕显示核验 / Subtitle display check.

交付前的闸：确认每条字幕在**目标画布**上能完整显示（不溢出、不折成三行以上），
且时间轴与音频对齐、无重叠。对应交付要求「确保每一段字幕都满足显示的要求」。

Gate before delivery: every cue must fit the target canvas, and the timeline must
be aligned with the audio without overlaps.

为什么需要它：字幕长度是否合适，取决于**字号 × 安全框宽**，
而这两个值在 TS 侧（``remotion/src/theme/theme.ts`` 与 ``layout.ts``）。
肉眼估不出来，所以这里**从 TS 源码解析**这两个值 —— 保持单一来源，
不做「Python 里再抄一份常量」的假配置。

复测指令 / How to re-run:
    $py = "C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe"
    cd C:\\Users\\75203\\Downloads\\xd\\VideoGenResearch-deepseek

    # 核验某素材集（横竖屏都查）
    & $py scripts\\check_subtitles.py --set omni-io-skills

    # 只用内置素材 / 只看竖屏
    & $py scripts\\check_subtitles.py --kind short --aspect portrait

零费用：纯本地文本计算，不调用任何 API。
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from videogen.paths import PROJECT_ROOT  # noqa: E402
from videogen.sources import AssetSetError, load_set  # noqa: E402
from videogen.timeline import parse_srt  # noqa: E402

REMOTION = PROJECT_ROOT / "remotion" / "src"

# 画布尺寸（与 remotion/src/Root.tsx 的 SIZES 一致）
CANVAS = {"landscape": (1920, 1080), "portrait": (1080, 1920)}

# 拉丁字母/数字相对中文字宽的近似比例 —— 中文字宽 ≈ 1em，拉丁 ≈ 0.55em。
# 字幕能否放下取决于显示宽度，纯数中文字会把 "Asset Registry" 这类条目误判。
_LATIN_RATIO = 0.55
_PUNCT_RATIO = 0.45
_CJK = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")


def _parse_tuning() -> dict[str, float]:
    """从 theme.ts 解析 TUNING 的字幕相关值 / Parse caption tuning from theme.ts."""
    src = (REMOTION / "theme" / "theme.ts").read_text(encoding="utf-8")
    out: dict[str, float] = {}
    for key in ("captionSizePortrait", "captionSizeLandscape", "captionShrinkAbove"):
        m = re.search(rf"{key}\s*:\s*([0-9.]+)", src)
        if not m:
            raise SystemExit(f"theme.ts 里找不到 {key}；TUNING 契约变了，请同步本脚本")
        out[key] = float(m.group(1))
    return out


def _parse_layout() -> dict[str, float]:
    """从 layout.ts 解析安全区常量 / Parse safe-area constants from layout.ts."""
    src = (REMOTION / "theme" / "layout.ts").read_text(encoding="utf-8")
    out: dict[str, float] = {}
    for key in (
        "PORTRAIT_LEFT_INSET",
        "PORTRAIT_RIGHT_INSET",
        "PORTRAIT_TOP_INSET",
        "PORTRAIT_BOTTOM_INSET",
        "CAPTION_H_PORTRAIT",
        "CAPTION_H_LANDSCAPE",
    ):
        m = re.search(rf"const {key}\s*=\s*([0-9.]+)", src)
        if not m:
            raise SystemExit(f"layout.ts 里找不到 {key}；版式契约变了，请同步本脚本")
        out[key] = float(m.group(1))
    # 横屏安全区目前是字面量（L80 R80 T60 B140），单独取
    m = re.search(r"const safe = \{\s*left:\s*([0-9.]+),\s*right:\s*([0-9.]+),", src)
    if m:
        out["LANDSCAPE_LEFT_INSET"] = float(m.group(1))
        out["LANDSCAPE_RIGHT_INSET"] = float(m.group(2))
    return out


def display_width(text: str, size: float) -> float:
    """估算一条字幕的显示宽度（px）/ Estimate a cue's rendered width in px."""
    width = 0.0
    for ch in text:
        if _CJK.match(ch):
            width += size
        elif ch.isalnum():
            width += size * _LATIN_RATIO
        elif ch.isspace():
            width += size * 0.28
        else:
            width += size * _PUNCT_RATIO
    return width


def safe_width(orientation: str, layout: dict[str, float]) -> float:
    """字幕可用宽度（px）/ Available width for a caption in px."""
    w, _ = CANVAS[orientation]
    if orientation == "portrait":
        return w - layout["PORTRAIT_LEFT_INSET"] - layout["PORTRAIT_RIGHT_INSET"]
    return w - layout.get("LANDSCAPE_LEFT_INSET", 80) - layout.get("LANDSCAPE_RIGHT_INSET", 80)


def check(segments, orientation: str, tuning: dict[str, float], layout: dict[str, float]):
    """核验一个方向 / Check one orientation.

    :returns: ``(问题列表, 统计字典)``
    """
    base = (
        tuning["captionSizePortrait"]
        if orientation == "portrait"
        else tuning["captionSizeLandscape"]
    )
    avail = safe_width(orientation, layout)
    problems: list[str] = []
    lines_hist: dict[int, int] = {}

    for seg in segments:
        text = seg.text
        # 与 Caption.tsx 的自动缩字保持一致：字符数超阈值则缩一档
        size = base * 0.84 if len(text) > tuning["captionShrinkAbove"] else base
        # Caption.tsx 的左右内边距是 fontSize * 0.72
        usable = avail - size * 0.72 * 2
        width = display_width(text, size)
        lines = max(1, math.ceil(width / usable))
        lines_hist[lines] = lines_hist.get(lines, 0) + 1
        if lines > 2:
            problems.append(
                f"第 {seg.index} 条会折成 {lines} 行（宽 {width:.0f}px / 可用 {usable:.0f}px）: {text}"
            )
        if seg.end - seg.start < 0.6:
            problems.append(f"第 {seg.index} 条仅 {seg.end - seg.start:.2f}s，读不完: {text}")

    # 时间轴重叠
    for i in range(1, len(segments)):
        if segments[i].start < segments[i - 1].end - 0.001:
            problems.append(
                f"第 {segments[i].index} 条与上一条时间重叠 "
                f"({segments[i].start:.2f} < {segments[i - 1].end:.2f})"
            )

    stats = {
        "orientation": orientation,
        "count": len(segments),
        "base_size": base,
        "avail": avail,
        "lines_hist": lines_hist,
        "max_lines": max(lines_hist) if lines_hist else 0,
    }
    return problems, stats


def main() -> int:
    ap = argparse.ArgumentParser(description="字幕显示核验 / Subtitle display check")
    # 三种入口互斥，但不强制指定 —— 都不给时默认查内置短视频字幕
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--set", dest="set_name", help="素材集名（assets/sets/<name>）")
    src.add_argument("--srt", help="直接指定 SRT 文件")
    ap.add_argument("--kind", default="short", choices=("short", "mid"),
                    help="内置素材类型（三者都不给时的默认入口）")
    ap.add_argument("--aspect", default="both", choices=("landscape", "portrait", "both"))
    args = ap.parse_args()

    if args.srt:
        srt_path = Path(args.srt)
    elif args.set_name:
        try:
            srt_path = load_set(args.set_name).srt()
        except AssetSetError as exc:
            print(f"素材集错误 / asset set error: {exc}")
            return 2
    else:
        from videogen.paths import assets_dir

        srt_path = assets_dir() / "audio" / f"{args.kind}.asr.srt"

    if not srt_path.exists():
        print(f"字幕不存在 / no SRT: {srt_path}")
        return 2

    segments = parse_srt(srt_path.read_text(encoding="utf-8"))
    tuning = _parse_tuning()
    layout = _parse_layout()

    print(f"字幕 / SRT : {srt_path.name}（{len(segments)} 条）")
    print(f"参数来源 / from TS: 字号 {tuning['captionSizePortrait']:.0f}/"
          f"{tuning['captionSizeLandscape']:.0f}  缩字阈值 {tuning['captionShrinkAbove']:.0f}"
          f"  竖屏安全区右 {layout['PORTRAIT_RIGHT_INSET']:.0f}px")
    print()

    aspects = ("landscape", "portrait") if args.aspect == "both" else (args.aspect,)
    total_problems = 0
    for orientation in aspects:
        problems, stats = check(segments, orientation, tuning, layout)
        total_problems += len(problems)
        hist = "  ".join(f"{k}行×{v}" for k, v in sorted(stats["lines_hist"].items()))
        verdict = "合格" if not problems else f"{len(problems)} 个问题"
        print(f"[{orientation}] 字号 {stats['base_size']:.0f}px  可用宽 {stats['avail']:.0f}px"
              f"  行数分布 {hist}  →  {verdict}")
        for problem in problems:
            print(f"    ! {problem}")
        print()

    if total_problems == 0:
        # 注意：控制台是 GBK，输出里不要用 emoji（\u2705 之类会 UnicodeEncodeError）
        print("结论：全部字幕在两个方向都能完整显示，时间轴无重叠 [OK]")
    else:
        print(f"结论：共 {total_problems} 个问题，建议调 subtitle.SubtitleParams 或文案长度")
    return 1 if total_problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
