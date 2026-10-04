"""素材集成片渲染入口 / Render an asset set into finished MP4s.

薄壳：`素材集 + spec → 编译 props → 镜像素材到 public/ → Remotion 渲染`。
**零业务逻辑** —— 编译在 ``videogen.compile``，渲染在 ``videogen.render``。

Thin shell: asset set + spec → compile props → mirror assets into ``public/`` →
Remotion render. No business logic here.

为什么要镜像素材：Remotion 只能读 ``remotion/public/`` 下的文件
（``staticFile()`` 的根就是它）。素材集放在 ``assets/sets/<name>/``，
所以渲染前要复制一份进 ``public/<name>/``。

Remotion can only read files under ``remotion/public/``; asset sets live under
``assets/sets/<name>/``, so they are mirrored into ``public/<name>/`` first.

复测指令 / How to re-run:
    $py = "C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe"
    cd C:\\Users\\75203\\Downloads\\xd\\VideoGenResearch-deepseek

    # 两个方向都渲（默认）
    & $py scripts\\render_set.py --set omni-io-skills

    # 只渲竖屏 / 只渲横屏
    & $py scripts\\render_set.py --set omni-io-skills --aspect portrait

    # 只算不渲（零费用、秒级）：校验素材完整性 + 看 props
    & $py scripts\\render_set.py --set omni-io-skills --check

注意：渲染是本地算力，不花钱；但它会跑几分钟（短视频约 3–6 分钟/方向）。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from videogen.compile import CRF_BY_ASPECT, missing_assets, write_props  # noqa: E402
from videogen.paths import (  # noqa: E402
    PROJECT_ROOT,
    ensure_deliverable_dirs,
    logs_dir,
    storyboard_dir,
    subtitles_dir,
    video_dir,
)
from videogen.render.remotion import build_env, remotion_dir  # noqa: E402
from videogen.sources import AssetSetError, load_set  # noqa: E402
from videogen.spec import VideoSpec  # noqa: E402
from videogen.timeline import build_timeline  # noqa: E402

# 通用 Composition（时长从 props 读，见 remotion/src/Root.tsx）
COMPOSITIONS = {"landscape": "SetLandscape", "portrait": "SetPortrait"}


def mirror_assets(asset_set, public_dir: Path) -> list[str]:
    """把素材集的音频与图片镜像到 ``public/<set>/``。

    Mirror the asset set's audio and images into ``public/<set>/``.
    用**复制**而不是软链：Remotion 会把 ``public/`` 下的软链转发成真符号链接，
    Windows 需要管理员或开发者模式（见 docs/issues/004）。

    :returns: 复制过去的相对路径列表 / relative paths that were copied.
    """
    target_audio = public_dir / asset_set.name / "audio"
    target_images = public_dir / asset_set.name / "images"
    target_audio.mkdir(parents=True, exist_ok=True)
    target_images.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for src in asset_set.audio_files():
        shutil.copy2(src, target_audio / src.name)
        copied.append(f"{asset_set.name}/audio/{src.name}")
    for src in asset_set.image_files():
        shutil.copy2(src, target_images / src.name)
        copied.append(f"{asset_set.name}/images/{src.name}")
    return copied


def main() -> int:
    ap = argparse.ArgumentParser(description="渲染素材集成片 / Render an asset set")
    ap.add_argument("--set", dest="set_name", required=True, help="素材集名")
    ap.add_argument("--kind", default="short", choices=("short", "mid"),
                    help="视频类型（只影响内置默认分镜的兜底）")
    ap.add_argument("--aspect", default="both", choices=("landscape", "portrait", "both"))
    ap.add_argument("--crf", type=int, default=0, help="覆盖 CRF（0 = 按方向取规范值）")
    ap.add_argument("--check", action="store_true",
                    help="只校验与编译，不渲染（零费用、秒级）")
    args = ap.parse_args()

    try:
        asset_set = load_set(args.set_name)
    except AssetSetError as exc:
        print(f"素材集错误 / asset set error: {exc}")
        return 2

    # ── 1) 时间轴与 spec / Timeline and spec ──────────────────────────────
    timeline = build_timeline(asset_set.srt(), asset_set.audio, fps=30,
                              title=asset_set.title, subtitle=asset_set.subtitle)
    spec_path = storyboard_dir(asset_set.name, args.kind) / "spec.json"
    if not spec_path.exists():
        print(f"缺少 spec / no spec: {spec_path}")
        print(f"  先跑 / run first: scripts\\plan.py --set {asset_set.name} --kind {args.kind}")
        return 2
    spec = VideoSpec.from_dict(json.loads(spec_path.read_text(encoding="utf-8")))

    print(f"素材集 / set : {asset_set.describe()}")
    print(f"时间轴 / timeline: {timeline.audio_duration:.2f}s = {timeline.duration_frames} 帧"
          f"（spec 里 {spec.duration_in_frames} 帧）")
    print(f"spec: {len(spec.shots)} 镜  {spec_path.name}")

    # ── 2) 素材完整性：渲染前最后一道闸 / Pre-render asset gate ───────────
    absent = missing_assets(spec, asset_set.images_dir)
    if absent:
        print(f"\n!! 缺素材 / missing assets（{len(absent)}）:")
        for name in absent:
            print(f"   - {name}")
        print("这些镜头会走无图分支；补齐后再渲效果更好。")
    else:
        print("素材校验 / asset check: 全部存在")

    # ── 3) 镜像素材到 public/ / Mirror into public/ ────────────────────────
    public_dir = remotion_dir() / "public"
    fonts_src = PROJECT_ROOT / "assets" / "fonts"
    if fonts_src.exists():
        (public_dir / "fonts").mkdir(parents=True, exist_ok=True)
        for font in fonts_src.iterdir():
            if font.is_file():
                shutil.copy2(font, public_dir / "fonts" / font.name)
    copied = mirror_assets(asset_set, public_dir)
    print(f"已镜像 / mirrored: {len(copied)} 个文件 → remotion/public/{asset_set.name}/")

    # ── 4) 每个方向编译 props / Compile props per aspect ──────────────────
    # 交付物目录按类型分好（video / shots / storyboard / qa / logs），
    # 结构定义见 videogen/paths.py 顶部注释。
    ensure_deliverable_dirs(asset_set.name, args.kind)

    # 把字幕归档进交付物的 subtitles/ —— 字幕是独立交付物（可单独替换），
    # 但它生成时落在素材集的 audio/ 下（那里是"输入"）。不归档的话
    # 交付目录里会缺这一类文件，二次修改时找不到。
    try:
        srt = asset_set.srt()
        if srt.exists():
            shutil.copy2(srt, subtitles_dir(asset_set.name, args.kind) / f"{asset_set.name}_{args.kind}.srt")
            print(f"字幕已归档 / subtitle archived: {srt.name}")
    except (OSError, FileNotFoundError):
        pass

    aspects = ("landscape", "portrait") if args.aspect == "both" else (args.aspect,)
    from videogen.compile import RenderTarget

    jobs: list[tuple[str, Path, Path]] = []
    for aspect in aspects:
        composition = COMPOSITIONS[aspect]
        crf = args.crf or CRF_BY_ASPECT[aspect]
        output = video_dir(asset_set.name, args.kind) / f"{aspect}.mp4"
        target = RenderTarget(kind=args.kind, aspect=aspect, composition_id=composition,
                              crf=crf, output_name=output.name)
        props_path = write_props(spec, timeline, target,
                                 storyboard_dir(asset_set.name, args.kind), asset_set)
        jobs.append((composition, props_path, output))
        print(f"props: {props_path.name}  →  {composition}  crf={crf}")

    if args.check:
        print("\n--check：只校验不渲染 / check only, nothing rendered")
        return 0

    # ── 5) 渲染 / Render ──────────────────────────────────────────────────
    remotion = remotion_dir()
    cli = remotion / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
    env = build_env()
    failures = 0
    for composition, props_path, output in jobs:
        # 日志按方向落到 logs/（原先散在成片旁边，混在 video/ 里不好找）
        log_path = logs_dir(asset_set.name, args.kind) / f"{output.stem}.log"
        print(f"\n==> {composition} → {output.name}（日志 logs/{log_path.name}）")
        with log_path.open("w", encoding="utf-8") as log:
            code = subprocess.call(
                ["node", str(cli), "render", "src/index.ts", composition,
                 str(output.resolve()), f"--props={props_path.resolve()}",
                 "--codec=h264", "--pixel-format=yuv420p",
                 "--audio-codec=aac", "--audio-bitrate=192K"],
                cwd=str(remotion), env=env, stdout=log, stderr=subprocess.STDOUT,
            )
        if code != 0 or not output.exists():
            failures += 1
            print(f"    [失败 / FAILED] 退出码 {code}，日志尾部：")
            tail = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-8:]
            for line in tail:
                print(f"      {line}")
        else:
            print(f"    [完成 / OK] {output.stat().st_size / 1024 / 1024:.1f} MB")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
