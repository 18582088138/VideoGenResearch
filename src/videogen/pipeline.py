"""对外唯一稳定入口 / The single stable entry point.

``generate_video`` 是 ``Agent_VideoGen_Module`` 唯一需要知道的函数。
**调用方不需要知道 Remotion 存在** —— 这是本模块的分层边界。

``generate_video`` is the only function ``Agent_VideoGen_Module`` needs to know.
Callers never have to know Remotion exists.

流程 / Pipeline（对应 docs/architecture/00_pipeline.md 的五个阶段）::

    1 素材理解   纯 Python 解析 srt/wav + 盘点素材        零成本
    2 LLM 规划   DeepSeek 一次调用产出 spec              唯一花钱处
    3 校验编译   validate_and_repair → props JSON        零成本
    4 渲染       调 Remotion CLI（Node 薄壳）             本地算力
    5 归档       spec + props + mp4 + manifest 同目录      零成本
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from videogen.assets import load_images
from videogen.compile import (
    compile_props,
    composition_for,
    missing_assets,
    write_props,
)
from videogen.models import Timeline
from videogen.paths import assets_dir, out_dir
from videogen.plan.planner import PlanRequest, plan_video
from videogen.render.remotion import RenderError, render_still, render_video
from videogen.shot_catalog import load_catalog
from videogen.spec import VideoSpec
from videogen.timeline import build_timeline
from videogen.validate import validate_and_repair

Aspect = Literal["landscape", "portrait", "both"]
Kind = Literal["short", "mid"]


@dataclass
class GenerateOptions:
    """生成选项 / Generation options."""

    kind: Kind = "short"
    aspect: Aspect = "both"
    theme: str = "cyan-noir"
    fps: int = 30
    title: str = ""
    subtitle: str = ""
    # 覆盖输出根目录；默认 out/
    out_root: Path | None = None
    # 只编译不渲染（零渲染成本，用于检查 spec 与 props）
    plan_only: bool = False
    # 真实 LLM 调用；False 时用内置假响应（零费用演练）
    live_llm: bool = True
    # 渲染并发；None 表示用 remotion.config.ts 的值
    concurrency: int | None = None


@dataclass
class VideoResult:
    """一次生成的完整结果 / Full result of one generation run.

    调用方需要的所有东西都在这里：成片路径、spec、修复记录、开销。
    """

    kind: str
    run_dir: Path
    spec_path: Path
    spec: VideoSpec
    outputs: list[Path] = field(default_factory=list)
    props_paths: list[Path] = field(default_factory=list)
    timeline: Timeline | None = None
    llm_tokens: int = 0
    llm_seconds: float = 0.0
    render_seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def repairs(self) -> int:
        """修复条数 / Number of repairs applied."""
        return len(self.spec.repair_log)

    def summary(self) -> str:
        """一行摘要，用于日志 / One-line summary for logs."""
        return (
            f"{self.kind}: {len(self.outputs)} 个成片, {len(self.spec.shots)} 镜, "
            f"{self.repairs} 条修复, LLM {self.llm_tokens} token/{self.llm_seconds:.1f}s, "
            f"渲染 {self.render_seconds:.1f}s"
        )


def generate_video(
    srt: Path,
    audio: Path,
    *,
    options: GenerateOptions | None = None,
    images: list | None = None,
    client: object | None = None,
) -> VideoResult:
    """字幕 + 配音 + 素材 → 成片。

    Narration + voiceover + assets → rendered video(s).

    确定性 / Determinism:
        LLM 温度固定 0，且 spec 落盘归档 —— **同一组输入必得同一支视频**。

    :param srt: 字幕文件（权威时间轴）/ Subtitle file (the authoritative timeline).
    :param audio: 配音文件（决定总时长）/ Voiceover file (determines total length).
    :param options: 生成选项；为空时用默认（短视频 / 横竖屏都要）。
    :param images: 素材索引；为空时从 ``assets/images/index.json`` 读。
    :param client: 注入 LLM 客户端（供单测 mock）；为空时按 ``.env`` 构造。
    :raises RenderError: 渲染失败（沙箱管道受限时消息会给出沙箱外执行的指引）。
    """
    opts = options or GenerateOptions()
    started = time.monotonic()

    # ── 阶段 1：素材理解 / Stage 1: material understanding ──
    timeline = build_timeline(
        srt, audio, fps=opts.fps, title=opts.title, subtitle=opts.subtitle
    )
    image_index = images if images is not None else load_images()
    cards = load_catalog()

    # ── 阶段 2：LLM 规划 / Stage 2: LLM planning ──
    llm_started = time.monotonic()
    if client is not None:
        spec, resp = plan_video(
            PlanRequest(
                kind=opts.kind, timeline=timeline, cards=cards,
                images=image_index, theme=opts.theme, aspect=opts.aspect,
            ),
            client=client,  # type: ignore[arg-type]
        )
    elif opts.live_llm:
        spec, resp = plan_video(
            PlanRequest(
                kind=opts.kind, timeline=timeline, cards=cards,
                images=image_index, theme=opts.theme, aspect=opts.aspect,
            )
        )
    else:
        # 零费用演练：走 plan.py 同款的假响应构造器
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
        from plan import dry_run_payload  # type: ignore[import-not-found]

        from videogen.llm import LLMResponse, LLMUsage

        class _Canned:
            def complete_json(self, *, system: str, user: str, max_tokens: int = 8000):
                return LLMResponse(
                    content=json.dumps(dry_run_payload(opts.kind), ensure_ascii=False),
                    usage=LLMUsage(),
                )

        spec, resp = plan_video(
            PlanRequest(
                kind=opts.kind, timeline=timeline, cards=cards,
                images=image_index, theme=opts.theme, aspect=opts.aspect,
            ),
            client=_Canned(),  # type: ignore[arg-type]
        )
    llm_seconds = time.monotonic() - llm_started

    # ── 阶段 3：校验与编译 / Stage 3: validate and compile ──
    spec = validate_and_repair(spec, timeline, image_index)

    warnings: list[str] = []
    missing = missing_assets(spec)
    if missing:
        warnings.append(f"素材缺失 / missing assets: {', '.join(missing)}")

    # 归档目录：时间戳 + spec 摘要，便于回溯「这一版是用哪份 spec 渲的」
    run_dir = _run_dir(opts, spec)
    run_dir.mkdir(parents=True, exist_ok=True)
    spec_path = run_dir / "spec.json"
    spec.save(spec_path)

    aspects: list[str] = (
        ["landscape", "portrait"] if opts.aspect == "both" else [opts.aspect]
    )
    props_paths: list[Path] = []
    for aspect in aspects:
        target = composition_for(opts.kind, aspect)
        props_paths.append(write_props(spec, timeline, target, run_dir))

    outputs: list[Path] = []
    render_seconds = 0.0

    # ── 阶段 4：渲染 / Stage 4: render ──
    if not opts.plan_only:
        out_base = (opts.out_root or out_dir()) / opts.kind
        out_base.mkdir(parents=True, exist_ok=True)
        for aspect, props_path in zip(aspects, props_paths):
            target = composition_for(opts.kind, aspect)
            output = out_base / target.output_name
            result = render_video(
                target, props_path, output, concurrency=opts.concurrency
            )
            outputs.append(result.output)
            render_seconds += result.seconds

    total_seconds = time.monotonic() - started

    # ── 阶段 5：归档 / Stage 5: archive ──
    _write_manifest(
        run_dir=run_dir,
        opts=opts,
        spec=spec,
        timeline=timeline,
        outputs=outputs,
        props_paths=props_paths,
        llm_tokens=resp.usage.total_tokens,
        llm_seconds=llm_seconds,
        render_seconds=render_seconds,
        total_seconds=total_seconds,
        warnings=warnings,
    )

    return VideoResult(
        kind=opts.kind,
        run_dir=run_dir,
        spec_path=spec_path,
        spec=spec,
        outputs=outputs,
        props_paths=props_paths,
        timeline=timeline,
        llm_tokens=resp.usage.total_tokens,
        llm_seconds=llm_seconds,
        render_seconds=render_seconds,
        warnings=warnings,
    )


def plan_only(
    srt: Path,
    audio: Path,
    *,
    options: GenerateOptions | None = None,
    client: object | None = None,
) -> VideoResult:
    """只规划不渲染的便捷入口 / Convenience: plan without rendering.

    零渲染成本，用于检查 spec 与 props 是否符合预期。
    """
    opts = options or GenerateOptions()
    opts.plan_only = True
    return generate_video(srt, audio, options=opts, client=client)


def render_props_still(
    run_dir: Path,
    kind: str,
    aspect: str,
    frame: int,
    output: Path,
) -> Path:
    """用已归档的 props 出一张静帧 / Render a still from archived props.

    开发期最高频的验收手段（秒级），也是**沙箱内唯一可行的视觉验收**。
    """
    target = composition_for(kind, aspect)
    props_path = run_dir / f"props_{kind}_{aspect}.json"
    if not props_path.exists():
        raise FileNotFoundError(f"props 不存在 / props not found: {props_path}")
    result = render_still(target, props_path, frame, output)
    return result.output


# ── 内部 / Internals ───────────────────────────────────────────────────────


def _run_dir(opts: GenerateOptions, spec: VideoSpec) -> Path:
    """构造本次运行的归档目录 / Build this run's archive directory.

    命名：``<kind>-<theme>-<ISO时间戳>``。时间戳让多次运行不互相覆盖，
    也便于人工按时间回溯。
    """
    stamp = time.strftime("%Y%m%d-%H%M%S")
    root = opts.out_root or out_dir()
    return root / "runs" / f"{opts.kind}-{spec.theme}-{stamp}"


def _write_manifest(**kw: object) -> Path:
    """写 manifest：本次运行的成本与产物台账 / Write the run manifest.

    这是「成本核算」与「可复现」的凭证 —— 开发守则要求记录真实开销。
    """
    run_dir: Path = kw["run_dir"]  # type: ignore[assignment]
    opts: GenerateOptions = kw["opts"]  # type: ignore[assignment]
    spec: VideoSpec = kw["spec"]  # type: ignore[assignment]
    timeline: Timeline = kw["timeline"]  # type: ignore[assignment]

    manifest = {
        "kind": spec.kind,
        "theme": spec.theme,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "timeline": {
            "audio_seconds": round(timeline.audio_duration, 3),
            "fps": timeline.fps,
            "duration_frames": timeline.duration_frames,
            "segments": len(timeline.segments),
        },
        "shots": len(spec.shots),
        "repairs": [asdict(r) for r in spec.repair_log],
        "llm": {
            "tokens": kw["llm_tokens"],
            "seconds": round(float(kw["llm_seconds"]), 2),  # type: ignore[arg-type]
        },
        "render": {
            "seconds": round(float(kw["render_seconds"]), 2),  # type: ignore[arg-type]
            "total_seconds": round(float(kw["total_seconds"]), 2),  # type: ignore[arg-type]
        },
        "outputs": [str(p) for p in kw["outputs"]],  # type: ignore[union-attr]
        "props": [str(p) for p in kw["props_paths"]],  # type: ignore[union-attr]
        "warnings": kw["warnings"],
        "options": {
            "aspect": opts.aspect,
            "plan_only": opts.plan_only,
            "live_llm": opts.live_llm,
            "concurrency": opts.concurrency,
        },
    }
    path = run_dir / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
