"""分镜片段导出 / Export per-shot clips.

交付要求：**每个分镜一个视频文件，不渲染字幕**（片段用于二次修改；
字幕是独立交付物）。音频也一并关掉 —— 切碎后每段音频大多停在句子中间，
单独听没有意义，静音还能显著减小体积。

Delivery: one clip per shot, **no captions**, no audio. Clips exist so a single
shot can be revised in isolation; captions are a separate deliverable.

复测指令 / How to re-run:
    $py = "C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe"
    cd C:\\Users\\75203\\Downloads\\xd\\VideoGenResearch-deepseek

    # 某素材集的两个方向都切（默认）
    & $py scripts\\export_shots.py --set omni-io-skills

    # 只切竖屏 / 指定 CRF（片段不需要高分，23 足够）
    & $py scripts\\export_shots.py --set omni-io-skills --aspect portrait --crf 23

    # 先看看会切出什么、不渲染（零费用、秒级）
    & $py scripts\\export_shots.py --set omni-io-skills --dry-run

输出 / Output:
    out/<set>/<kind>/shots/<aspect>/NN_<type>.mp4
    out/<set>/<kind>/shots/<aspect>/manifest.json   每段的帧范围与时长

零费用：本地算力渲染，不调用任何 API。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from videogen.compile import COMPOSITION_IDS, compile_props  # noqa: E402
from videogen.paths import (  # noqa: E402
    logs_dir,
    shots_dir as set_shots_dir,
    storyboard_dir,
)
from videogen.render.remotion import build_env, remotion_dir  # noqa: E402
from videogen.sources import AssetSetError, load_set  # noqa: E402
from videogen.spec import VideoSpec  # noqa: E402
from videogen.timeline import build_timeline  # noqa: E402

# 片段用较低画质即可：它是「给你看清画面」的工作素材，不是成片。
# 成片的 CRF 见 docs/design/00_platform_output_spec.md §3。
DEFAULT_CLIP_CRF = 23


def main() -> int:
    ap = argparse.ArgumentParser(description="分镜片段导出 / Export per-shot clips")
    ap.add_argument("--set", dest="set_name", required=True, help="素材集名")
    ap.add_argument("--kind", default="short", choices=("short", "mid"))
    ap.add_argument("--aspect", default="both",
                    choices=("landscape", "portrait", "both"))
    ap.add_argument("--crf", type=int, default=DEFAULT_CLIP_CRF)
    ap.add_argument("--concurrency", type=int, default=3,
                    help="并行渲染的片段数（默认 3；过高会与 Remotion 内部的帧并行争抢 CPU）")
    ap.add_argument("--dry-run", action="store_true",
                    help="只列出将要导出的片段，不渲染（零费用）")
    args = ap.parse_args()

    try:
        asset_set = load_set(args.set_name)
    except AssetSetError as exc:
        print(f"素材集错误 / asset set error: {exc}")
        return 2

    # ── 读 spec 与时间轴 / Load spec and timeline ──────────────────────────
    spec_path = storyboard_dir(asset_set.name, args.kind) / "spec.json"
    if not spec_path.exists():
        print(f"缺少 spec / no spec: {spec_path}")
        print(f"  先跑 / run first: scripts\\plan.py --set {asset_set.name} --kind {args.kind}")
        return 2
    spec = VideoSpec.from_dict(json.loads(spec_path.read_text(encoding="utf-8")))

    timeline = build_timeline(asset_set.srt(), asset_set.audio, fps=30,
                              title=asset_set.title, subtitle=asset_set.subtitle)

    print(f"素材集 / set: {asset_set.describe()}")
    print(f"分镜 / shots: {len(spec.shots)}  总帧 {timeline.duration_frames}"
          f"（{timeline.audio_duration:.2f}s @{timeline.fps}fps）")
    print()

    aspects = ("landscape", "portrait") if args.aspect == "both" else (args.aspect,)
    remotion = remotion_dir()
    cli = remotion / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"

    failures = 0
    for orientation in aspects:
        composition = COMPOSITION_IDS[(args.kind, orientation)]
        shots_dir = set_shots_dir(asset_set.name, args.kind) / orientation
        shots_dir.mkdir(parents=True, exist_ok=True)

        # 清掉上一次导出的片段。**必须清**：spec 一旦重新规划，镜头编号与类型都会
        # 重排，旧文件不会自动消失 —— 实测出现过目录里混着两版共 18 个片段
        # （`06_scan-annotate.mp4` 与 `06_slow-push.mp4` 并存），二次修改时根本
        # 分不清哪个是当前的。
        #
        # Clear stale clips first: re-planning reorders shot indices and types, so
        # leftovers would silently mix two versions in one folder.
        for stale in (
            list(shots_dir.glob("*.mp4"))
            + list(shots_dir.glob("_props*.json"))
            + list(shots_dir.glob("*.log"))
        ):
            stale.unlink()

        # 切片专用 props：**关闭字幕与音频**
        props = compile_props(spec, timeline, asset_set)
        props["captionsEnabled"] = False
        props["audioEnabled"] = False
        # 切片专用 props 归到 storyboard/（它是「分镜数据」而非片段产物）
        props_path = storyboard_dir(asset_set.name, args.kind) / "_props_shots.json"
        props_path.write_text(
            json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        manifest: list[dict] = []
        print(f"== {orientation}  ({composition}) ==")
        pending: list[tuple[int, str, int, int, Path]] = []
        for idx, shot in enumerate(spec.shots):
            start = shot.from_frame
            end = shot.from_frame + shot.duration_in_frames - 1  # --frames 是闭区间
            name = f"{idx:02d}_{shot.type}.mp4"
            out_path = shots_dir / name
            manifest.append({
                "index": idx,
                "type": shot.type,
                "file": name,
                "from": start,
                "to": end,
                "durationInFrames": shot.duration_in_frames,
                "seconds": round(shot.duration_in_frames / timeline.fps, 2),
                "text": shot.text,
            })
            print(f"  [{idx:>2}] {shot.type:<16} f{start:>5}-{end:<5} "
                  f"{shot.duration_in_frames / timeline.fps:4.2f}s  {shot.text[:24]}")
            if not args.dry_run:
                pending.append((idx, shot.type, start, end, out_path))

        # ── 并行渲染 / Render in parallel ──────────────────────────────────
        # 每个片段都是一次独立的 Remotion 冷启动（bundle ≈5–8s），串行跑 11 个片段
        # 要 5 分钟以上，而这段时间几乎全花在 bundle 上、CPU 是闲的。
        # 并行 3 路能把墙钟时间压到约 1/3，且不影响单片段画质（Remotion 内部
        # 已在多帧之间并行，所以并行度不宜过高，避免 CPU 过度争抢）。
        #
        # Each clip pays a full Remotion cold start (bundle ≈5–8 s); serially that
        # is minutes of mostly-idle CPU. Three-way parallelism cuts wall time to
        # roughly a third without touching per-clip quality.
        def render_one(job: tuple[int, str, int, int, Path]) -> tuple[int, bool, str]:
            idx, _type, start, end, out_path = job
            # 片段日志归到 logs/（不散落在片段目录里）
            log_path = clip_logs / f"shots_{orientation}_{idx:02d}.log"
            with log_path.open("w", encoding="utf-8") as log:
                code = subprocess.call(
                    ["node", str(cli), "render", "src/index.ts", composition,
                     str(out_path.resolve()), f"--props={props_path.resolve()}",
                     f"--frames={start}-{end}", "--codec=h264",
                     "--pixel-format=yuv420p", f"--crf={args.crf}",
                     # 静音：不写音频轨（props 也已关掉音源）
                     "--muted"],
                    cwd=str(remotion), env=build_env(),
                    stdout=log, stderr=subprocess.STDOUT,
                )
            ok = code == 0 and out_path.exists()
            return idx, ok, log_path.name

        if pending:
            clip_logs = logs_dir(asset_set.name, args.kind)
            clip_logs.mkdir(parents=True, exist_ok=True)
            with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
                results = list(pool.map(render_one, pending))
            for idx, ok, log_name in sorted(results):
                if not ok:
                    failures += 1
                    print(f"    [失败 / FAILED] 片段 {idx:02d}，见 {log_name}")
            done = sum(1 for _, ok, _ in results if ok)
            print(f"  → {done}/{len(pending)} 个片段渲染成功")

        (shots_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "set": asset_set.name,
                    "kind": args.kind,
                    "aspect": orientation,
                    "composition": composition,
                    "fps": timeline.fps,
                    "captionsRendered": False,
                    "audioRendered": False,
                    "shots": manifest,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"  → {len(manifest)} 个片段 + manifest.json  ({shots_dir})")
        print()

    if args.dry_run:
        print("--dry-run：只列清单，未渲染 / listed only, nothing rendered")
        return 0

    if failures:
        print(f"完成，但有 {failures} 个片段失败 / {failures} clips failed")
        return 1
    print("全部片段导出完成 / all clips exported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
