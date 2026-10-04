"""spec → Remotion props 编译 / Compile a spec into Remotion props.

阶段 3 的最后一环（见 ``docs/architecture/00_pipeline.md``）：
把校验过的 :class:`VideoSpec` 编译成 Remotion 侧能直接吃的 props JSON。

The last step of stage 3: compile a validated ``VideoSpec`` into the props JSON
that the Remotion side consumes directly.

为什么必须落盘成文件而不是内联传：
    Remotion 官方明确警告 —— **Windows 上 ``--props`` 不能传内联 JSON**
    （shell 会剥掉双引号）。文件路径是跨平台唯一可靠的形式。

Why a file rather than inline JSON: Remotion warns that inline ``--props``
breaks on Windows because the shell strips the quotes. A file path is the only
reliable cross-platform form.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from videogen.models import Timeline
from videogen.paths import assets_dir
from videogen.spec import ShotSpec, VideoSpec

Aspect = Literal["landscape", "portrait"]

# Composition id 映射 / Composition id mapping.
COMPOSITION_IDS: dict[tuple[str, str], str] = {
    ("short", "landscape"): "ShortLandscape",
    ("short", "portrait"): "ShortPortrait",
    ("mid", "landscape"): "MidLandscape",
    ("mid", "portrait"): "MidPortrait",
}

# 规范里的 CRF（见 docs/design/00_platform_output_spec.md §3）
CRF_BY_ASPECT: dict[str, int] = {"landscape": 18, "portrait": 20}

# 成片命名约定 / Output naming convention.
OUTPUT_NAMES: dict[tuple[str, str], str] = {
    ("short", "landscape"): "short_landscape_1080p.mp4",
    ("short", "portrait"): "short_portrait_1080x1920.mp4",
    ("mid", "landscape"): "mid_landscape_1080p.mp4",
    ("mid", "portrait"): "mid_portrait_1080x1920.mp4",
}


@dataclass(frozen=True)
class RenderTarget:
    """一个待渲染目标 / One render target."""

    kind: str
    aspect: str
    composition_id: str
    crf: int
    output_name: str


def composition_for(kind: str, aspect: str) -> RenderTarget:
    """取某个 (kind, aspect) 的渲染目标 / Resolve a render target.

    :raises KeyError: 组合非法（kind/aspect 不在枚举内）。
    """
    key = (kind, aspect)
    if key not in COMPOSITION_IDS:
        raise KeyError(
            f"非法组合 / invalid combo: kind={kind!r} aspect={aspect!r}；"
            f"可选 / available: {sorted(COMPOSITION_IDS)}"
        )
    return RenderTarget(
        kind=kind,
        aspect=aspect,
        composition_id=COMPOSITION_IDS[key],
        crf=CRF_BY_ASPECT[aspect],
        output_name=OUTPUT_NAMES[key],
    )


def compile_shot(shot: ShotSpec, asset_set: object | None = None) -> dict:
    """编译单个镜头 / Compile one shot.

    字段名转成 TS 侧的 camelCase 形态（见 ``remotion/src/compositions/types.ts``）。

    :param asset_set: 素材集；图片路径会带上 ``<set>/images/`` 前缀。
        组件侧统一经 ``theme/assetPath.ts`` 解析，**不再自己拼前缀** ——
        两边都拼就会变成 ``images/<set>/images/...`` 而 404（实测踩过）。
    """
    compiled: dict = {
        "type": shot.type,
        "from": shot.from_frame,
        "durationInFrames": shot.duration_in_frames,
    }
    # 只输出非空字段，减小 props 体积（Remotion 官方提示 defaultProps 过大会变慢）
    if shot.text:
        compiled["text"] = shot.text
    if shot.subtext:
        compiled["subtext"] = shot.subtext
    if shot.tagline:
        compiled["tagline"] = shot.tagline
    if shot.metrics:
        compiled["metrics"] = [{"label": m.label, "value": m.value} for m in shot.metrics]
    if shot.image:
        # 路径相对 Remotion 的 public/：素材集在 public/<set>/images/ 下。
        name = getattr(asset_set, "name", "") if asset_set is not None else ""
        compiled["image"] = f"{name}/images/{shot.image}" if name else shot.image
    if shot.image2:
        # 第二张图（``image-pair`` 用）。**必须和 image 用同一套路径口径** ——
        # 漏了这一步的话，spec 校验能过（REQUIRED_FIELDS 有 image2）、
        # 但传到 Remotion 的 props 里没有它，镜头会静默退化成单图。
        #
        # Second image for `image-pair`; must use the same path convention as
        # `image`, or the shot silently degrades to a single image.
        name = getattr(asset_set, "name", "") if asset_set is not None else ""
        compiled["image2"] = f"{name}/images/{shot.image2}" if name else shot.image2
    if shot.targets:
        compiled["targets"] = [
            {"x": t.x, "y": t.y, "w": t.w, "h": t.h, "label": t.label, "side": t.side}
            for t in shot.targets
        ]
    if shot.stops:
        compiled["stops"] = [{"label": s.label, "note": s.note} for s in shot.stops]
    if shot.source:
        compiled["source"] = shot.source
    # 图文类字段 / Figure-shot fields
    if shot.eyebrow:
        compiled["eyebrow"] = shot.eyebrow
    if shot.footer:
        compiled["footer"] = shot.footer
    if shot.bullets:
        compiled["bullets"] = list(shot.bullets)
    if shot.nodes:
        compiled["nodes"] = [{"label": n.label, "sub": n.sub} for n in shot.nodes]
    if shot.sides:
        compiled["sides"] = [
            {"label": x.label, "value": x.value, "display": x.display, "better": x.better}
            for x in shot.sides
        ]
    if shot.metric:
        compiled["metric"] = shot.metric
    return compiled


def _media_paths(spec: VideoSpec, asset_set: object | None) -> tuple[str, str]:
    """解析 props 里的音频与字幕路径 / Resolve audio and SRT paths for props.

    路径是**相对 Remotion ``public/`` 的**：
    - 内置素材放在 ``public/audio/`` → ``shortvideo.zh.wav``
    - 素材集放在 ``public/<set>/audio/`` → ``omni-io-skills/audio/shortvideo.zh.wav``

    必须用素材集自己的字幕文件名（ASR 重切后叫 ``<name>.asr.srt``），
    不能再按 kind 猜 —— 否则换一篇文章就会指向不存在的文件。
    """
    if asset_set is not None:
        name = getattr(asset_set, "name", "")
        audio_name = getattr(asset_set, "audio", None)
        srt = asset_set.srt()  # type: ignore[attr-defined]
        return f"{name}/audio/{Path(str(audio_name)).name}", f"{name}/audio/{srt.name}"

    audio_prefix = "shortvideo" if spec.kind == "short" else "narration"
    asr = assets_dir() / "audio" / f"{spec.kind}.asr.srt"
    srt_name = asr.name if asr.exists() else f"{audio_prefix}.zh.srt"
    return f"{audio_prefix}.zh.wav", srt_name


def compile_props(
    spec: VideoSpec,
    timeline: Timeline,
    asset_set: object | None = None,
) -> dict:
    """编译成 Remotion props / Compile into Remotion props.

    注意 ``durationInFrames`` 取自**时间轴的音频实测时长**，不是 spec 里
    模型给的值 —— 与 Composition 注册的帧数必须一致，否则片尾会被截断。

    :param asset_set: 素材集；为空则按内置素材（``kind``）解析音频与字幕。
    """
    audio_path, srt_path = _media_paths(spec, asset_set)
    # 来源标注：优先素材集自己的 source_label；否则取分镜里写过的 source。
    # 原来写死在 FilmShell 里，换一篇文章会继续显示上一家的来源（见 issues/006）。
    source_label = ""
    if asset_set is not None:
        source_label = str(getattr(asset_set, "source_label", "") or "")
    if not source_label:
        source_label = next((s.source for s in spec.shots if s.source), "")
    return {
        "kind": spec.kind,
        "themeId": spec.theme,
        "srtPath": srt_path,
        "audioPath": audio_path,
        "title": spec.title,
        "subtitle": spec.subtitle,
        "source": source_label,
        # 通用 Composition 用 calculateMetadata 读这两个值；写死在
        # Composition 上的帧数只对本项目最早两套素材成立（见 docs/issues/006）。
        "durationInFrames": timeline.duration_frames,
        "fps": timeline.fps,
        "shots": [compile_shot(s, asset_set) for s in spec.shots],
    }


def write_props(
    spec: VideoSpec,
    timeline: Timeline,
    target: RenderTarget,
    out_dir: Path,
    asset_set: object | None = None,
) -> Path:
    """把 props 落盘 / Persist props to disk.

    文件名带 (kind, aspect) 后缀，便于人工核对与排查。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"props_{target.kind}_{target.aspect}.json"
    path.write_text(
        json.dumps(compile_props(spec, timeline, asset_set), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def missing_assets(spec: VideoSpec, base: Path | None = None) -> list[str]:
    """列出 spec 引用但不存在的素材 / Assets referenced by the spec but absent.

    这是渲染前的最后一道闸：素材缺失不必等渲染到一半才发现。
    """
    root = base or (assets_dir() / "images")
    seen: dict[str, None] = {}
    for shot in spec.shots:
        if shot.image and not (root / shot.image).exists():
            seen.setdefault(shot.image, None)
    return sorted(seen)
