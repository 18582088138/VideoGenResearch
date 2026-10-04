"""一条命令跑完全链 / One command from article to finished video.

用法 / Usage::

    # ① 从一篇文章出片（全链：导入 → 标注 → 字幕 → 规划 → 渲染 → 切片）
    & $py scripts\\make_video.py --article "<文章目录>" --kind short

    # ② 一键重渲（**不重新规划、不重复花 LLM 钱**，用已有 spec 重出片子）
    & $py scripts\\make_video.py --set h3-world --kind short --rerender

    # ③ 先看要做什么，不实际执行（零费用）
    & $py scripts\\make_video.py --article "<目录>" --kind short --dry-run

设计 / Design
-------------
本脚本**不实现任何业务逻辑**，只按顺序调用已有脚本（薄壳原则）：
每一步都能单独跑、单独调试，出问题时可以直接重跑那一步。

    import_article.py   文章目录 → 素材集（标题/副标/口播/图片）
    annotate_images.py  视觉模型自动标注图片语义（可用 --skip-annotate 跳过）
    asr_subtitles.py    ASR → 切分 → 中文数字规范化
    plan.py             LLM 规划分镜
    render_set.py       渲染成片
    export_shots.py     导出分镜片段

**每一步都有产物检查**：前一步没产出预期文件就立刻停下并说清原因，
不会带着残缺状态继续往下跑。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from videogen import ocr  # noqa: E402
from videogen.paths import (  # noqa: E402
    deliverable_dir,
    storyboard_dir,
    video_dir,
)
from videogen.sources import AssetSetError, find_set_by_source, list_sets, load_set  # noqa: E402

PYTHON = sys.executable
SCRIPTS = Path(__file__).resolve().parent


def step(title: str) -> None:
    """打印一个阶段的标题 / Print a stage header."""
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def run(script: str, *args: str, dry_run: bool = False) -> int:
    """跑一个子脚本，实时转发输出 / Run a child script, streaming its output."""
    cmd = [PYTHON, str(SCRIPTS / script), *args]
    print(f"  $ {' '.join(cmd[1:])}")
    if dry_run:
        return 0
    completed = subprocess.run(cmd, cwd=str(SCRIPTS.parent))
    return completed.returncode


def fail(message: str, hint: str = "") -> int:
    """报错退出 / Report a failure and stop."""
    print()
    print(f"!! {message}")
    if hint:
        print(f"   {hint}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description="一条命令从文章到成片 / Article → finished video in one command",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--article", help="文章目录（新素材，先导入）")
    src.add_argument("--set", dest="set_name", help="已有素材集名")
    ap.add_argument("--kind", default="short", choices=("short", "mid"))
    ap.add_argument("--aspect", default="landscape", choices=("landscape", "portrait", "both"),
                    help="默认 landscape（竖屏已暂停维护）")
    ap.add_argument("--rerender", action="store_true",
                    help="一键重渲：跳过导入/标注/字幕/规划，直接用已有 spec 重出片子")
    ap.add_argument("--skip-annotate", action="store_true", help="跳过图片语义标注")
    ap.add_argument("--skip-asr", action="store_true", help="跳过 ASR（复用已有字幕）")
    ap.add_argument("--annotate-force", action="store_true",
                    help="标注时覆盖已有语义标注（默认跳过已有，省钱）")
    ap.add_argument("--crf", type=int, default=None, help="覆盖成片 CRF")
    ap.add_argument("--concurrency", type=int, default=3, help="分镜片段并行度")
    ap.add_argument("--dry-run", action="store_true", help="只打印要做什么，不执行（零费用）")
    ap.add_argument("--name", default=None,
                    help="导入时给素材集指定短名（默认按标题自动生成，可能很长）")
    args = ap.parse_args()

    dry = args.dry_run

    # ── 0) 定位素材集 / Resolve the asset set ────────────────────────────────
    if args.article:
        article_dir = Path(args.article).expanduser()
        if not article_dir.exists():
            return fail(f"文章目录不存在 / article dir not found: {article_dir}")

        existing = find_set_by_source(article_dir)
        if existing:
            set_name = existing
            print(f"这篇文章已导入过 / already imported as: {set_name}")
        else:
            step("① 导入文章 / Import article")
            import_args = [str(article_dir)]
            if args.name:
                import_args += ["--name", args.name]
            code = run("import_article.py", *import_args, dry_run=dry)
            if code != 0:
                return fail("导入失败 / import failed", f"退出码 {code}")
            if dry:
                set_name = "<待导入>"
            else:
                found = find_set_by_source(article_dir)
                if not found:
                    return fail(
                        "导入后仍找不到素材集 / set not found after import",
                        "检查 import_article.py 的输出",
                    )
                set_name = found
    else:
        set_name = args.set_name or ""

    if not dry:
        try:
            asset_set = load_set(set_name)
        except AssetSetError as exc:
            return fail(f"素材集不可用 / asset set unusable: {exc}",
                        f"现有素材集 / available: {', '.join(list_sets()) or '（无）'}")
        print(f"素材集 / set: {asset_set.describe()}")
        print(f"交付目录 / deliverable: {deliverable_dir(set_name, args.kind)}")

    # ── 1) 图片语义标注 / Annotate images ───────────────────────────────────
    if args.rerender:
        print("\n--rerender：跳过 ①②③④，直接用已有 spec 重出片子")
    else:
        if args.skip_annotate:
            print("\n跳过图片标注 / annotate skipped")
        else:
            step("② 图片语义标注 / Annotate images")
            print(f"  OCR: {ocr.describe()}")
            cmd = ["--set", set_name]
            if args.annotate_force:
                cmd.append("--force")
            code = run("annotate_images.py", *cmd, dry_run=dry)
            if code != 0:
                print("  标注有失败项，但已有标注会被保留，继续往下走")
                print("  （想重试就再跑一次：已标注的会跳过，不会重复计费）")

        # ── 2) 字幕 / Subtitles ─────────────────────────────────────────────
        if args.skip_asr:
            print("\n跳过 ASR / ASR skipped")
        else:
            step("③ 字幕（ASR → 切分 → 数字规范化）/ Subtitles")
            # 注意：asr_subtitles.py 的 --kind / --set / --audio 是**互斥组**，
            # 给了 --set 就不要再给 --kind（实测踩过：argparse 直接报错退出）。
            code = run("asr_subtitles.py", "--set", set_name, dry_run=dry)
            if code != 0:
                return fail("字幕失败 / subtitle failed", f"退出码 {code}")

        # ── 3) 规划 / Plan ──────────────────────────────────────────────────
        step("④ 规划分镜 / Plan")
        code = run("plan.py", "--set", set_name, "--kind", args.kind,
                   "--aspect", args.aspect, dry_run=dry)
        if code != 0:
            return fail("规划失败 / plan failed", f"退出码 {code}")

    # ── 4) 渲染 / Render ────────────────────────────────────────────────────
    if not dry:
        spec_file = storyboard_dir(set_name, args.kind) / "spec.json"
        if not spec_file.exists():
            return fail(
                f"没有分镜数据 / no spec: {spec_file}",
                f"先跑规划 / run first: scripts\\plan.py --set {set_name} --kind {args.kind}",
            )

    step("⑤ 渲染成片 / Render")
    render_args = ["--set", set_name, "--kind", args.kind, "--aspect", args.aspect]
    if args.crf is not None:
        render_args += ["--crf", str(args.crf)]
    code = run("render_set.py", *render_args, dry_run=dry)
    if code != 0:
        return fail("渲染失败 / render failed", "看 out/<set>/<kind>/logs/ 下的日志")

    # ── 5) 分镜片段 / Shot clips ────────────────────────────────────────────
    step("⑥ 导出分镜片段 / Export shot clips")
    code = run("export_shots.py", "--set", set_name, "--kind", args.kind,
               "--aspect", args.aspect, "--concurrency", str(args.concurrency),
               dry_run=dry)
    if code != 0:
        return fail("片段导出失败 / clip export failed", f"退出码 {code}")

    # ── 汇总 / Summary ──────────────────────────────────────────────────────
    step("完成 / Done")
    root = deliverable_dir(set_name, args.kind)
    print(f"  交付目录: {root}")
    if not dry:
        for label, folder, pattern in (
            ("成片    ", video_dir(set_name, args.kind), "*.mp4"),
            ("分镜片段", root / "shots" / args.aspect, "*.mp4"),
            ("字幕    ", root / "subtitles", "*.srt"),
            ("分镜数据", storyboard_dir(set_name, args.kind), "*.json"),
        ):
            files = sorted(folder.glob(pattern)) if folder.exists() else []
            print(f"  {label}: {len(files):>3} 个  {folder}")
    print()
    print("  下一步 / next：想改内容就编辑 storyboard/spec.json，"
          "然后 `--rerender` 重出片子（不再花 LLM 钱）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
