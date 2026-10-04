"""spec 校验与降级修复 / Spec validation and degraded repair.

对应 ``docs/architecture/00_pipeline.md`` 的**阶段 3**：spec 是数据契约，
校验失败要**就地修复并留痕**，绝不让坏 spec 进入渲染。

Implements stage 3 of the pipeline: validate, repair in place, and log every
repair — a bad spec must never reach the renderer.

设计要点 / Design notes:
    - 修复策略**按固定顺序**尝试，每条都记进 ``repair_log``
    - 修不动的（未知镜头类型）直接报错 —— 枚举错误不可猜测修复
    - 兜底：全部失败时返回内置 spec，保证「一定能出片」
"""

from __future__ import annotations

from pathlib import Path

from videogen.models import ImageAsset, Timeline
from videogen.spec import (
    REQUIRED_FIELDS,
    SHOT_TYPES,
    RepairEntry,
    ShotSpec,
    VideoSpec,
)

# 单卡时长区间（帧）—— 与 docs/architecture/01_spec_schema.md §5 一致
MIN_SHOT_FRAMES = 45
# **单镜硬上限**：超过 5 秒视频节奏就明显变慢（用户反馈）。
# 30fps 下 5s = 150 帧。仅在素材严重不足时才允许适度放宽，且必须留痕。
#
# Hard per-shot ceiling: past ~5 s the pacing reads as slow. Only放宽 when
# material is genuinely insufficient, and the relaxation is always logged.
MAX_SHOT_FRAMES = 150
# 放宽后的绝对上限（帧）：超出这个值必须切分或报错，不允许无限延展
ABSOLUTE_MAX_SHOT_FRAMES = 700

# 卡数区间 —— **必须与 docs/architecture/01_spec_schema.md §5 和
# plan/planner.py 的 SHOT_COUNT_RANGE 三处一致**。
# 实测教训：这条约束文档里写了、prompt 里也告诉了模型，但校验器**漏了实现** ——
# 中视频真实调用给出 11 镜（超出 8–10）却直接通过。契约写了就必须有代码兜底。
#
# Shot-count bounds. Must agree with the schema doc and the planner's range.
# Observed in practice: the model returned 11 shots for a mid video (limit 10)
# and nothing caught it, because the validator never implemented this rule.
SHOT_COUNT_RANGE: dict[str, tuple[int, int]] = {"short": (5, 6), "mid": (8, 10)}

# 各类型指标数量上限 / Per-type metric count caps.
MAX_METRICS = 3
MIN_METRICS = 1
MAX_TARGETS = 4
MIN_STOPS = 2
MAX_STOPS = 4

# 文案长度上限（字符）/ Text length caps.
MAX_TEXT = 40


class SpecValidationError(ValueError):
    """不可修复的 spec 错误 / An unrepairable spec error."""


def _clip(value: float, lo: float, hi: float) -> float:
    """把值钳到 [lo, hi] / Clamp into range."""
    return max(lo, min(hi, value))


def validate_and_repair(
    spec: VideoSpec,
    timeline: Timeline,
    images: list[ImageAsset] | None = None,
) -> VideoSpec:
    """校验 spec 并就地修复 / Validate a spec and repair it in place.

    :param spec: 待校验的 spec（会被就地修改）/ Spec to validate (mutated).
    :param timeline: 权威时间轴（提供总帧数与字幕段数）/ Authoritative timeline.
    :param images: 可用素材索引；为空时不做素材存在性校验。
    :returns: 同一个 spec 对象（带 ``repair_log``）。
    :raises SpecValidationError: 出现不可修复的问题（未知镜头类型、无镜头）。
    """
    log = spec.repair_log

    if not spec.shots:
        raise SpecValidationError("spec 没有任何镜头 / spec has no shots")

    valid_images = {a.file for a in images} if images else None
    cue_count = len(timeline.segments)

    # ── 逐镜修复 / Per-shot repairs ────────────────────────────────────────
    for idx, shot in enumerate(spec.shots):
        _repair_type(shot, idx, log)
        _repair_required(shot, idx, log)
        _repair_image(shot, idx, log, valid_images)
        _repair_targets(shot, idx, log)
        _repair_metrics(shot, idx, log)
        _repair_stops(shot, idx, log)
        _repair_text(shot, idx, log)
        _repair_caption_segments(shot, idx, log, cue_count)
        _repair_duration(shot, idx, log)

    # ── 时间轴与节奏的迭代收敛 / Iterate to a fixed point ─────────────────
    # `_relayout` 把总时长对齐到音频，`_split_long_shots` 把超 5s 的镜头切开 ——
    # 两者互相影响，需要迭代。上限 8 轮，正常输入 2 轮内收敛。
    for _ in range(8):
        _relayout(spec, timeline, log)
        if all(s.duration_in_frames <= MAX_SHOT_FRAMES for s in spec.shots):
            break
        _split_long_shots(spec, log)

    # **5 秒上限优先于镜数上限**：宁可镜数超标，也不要一镜拖 8 秒
    # （用户明确反馈"超过 5 秒视频节奏就变慢"）。
    # The 5-second ceiling outranks the shot-count cap: more shots beat one long one.
    _split_long_shots(spec, log)
    _relayout(spec, timeline, log)

    # 最后收敛卡数：切分会把镜数顶出上限，这一步把它拉回区间。
    # 注意它只能在**所有时长约束都满足之后**执行，否则会与切分互相打架。
    _converge_shot_count(spec, log)

    # 收尾对齐：合并会改变帧数，`from` 与总帧数都要重算一次。
    # 这一步只做顺序对齐与均摊，**不再切分**（否则镜数会立刻反弹出上限）。
    _resequence(spec, timeline, log)

    # 把时间轴信息回填，保证 spec 自洽（可复现性的前提）
    spec.fps = timeline.fps
    spec.duration_in_frames = timeline.duration_frames
    spec.total_seconds = round(timeline.audio_duration, 2)
    if not spec.title:
        spec.title = timeline.title
    if not spec.subtitle:
        spec.subtitle = timeline.subtitle

    return spec


# ── 单项修复 / Individual repairs ──────────────────────────────────────────


def _repair_type(shot: ShotSpec, idx: int, log: list[RepairEntry]) -> None:
    """未知镜头类型**不可修复**，直接报错。

    An unknown shot type is unrepairable: guessing would silently change the
    creative intent. Fail loudly instead.
    """
    if shot.type not in SHOT_TYPES:
        raise SpecValidationError(
            f"镜头 {idx} 的类型不在封闭集合内 / unknown shot type: {shot.type!r}\n"
            f"可用类型 / available: {', '.join(SHOT_TYPES)}"
        )


def _repair_required(shot: ShotSpec, idx: int, log: list[RepairEntry]) -> None:
    """缺必填字段时，尝试降级为纯文字卡（title-reveal 版式）。

    Missing required fields degrade to a plain text card rather than dropping
    the shot — the narration still needs a visual.
    """
    required = REQUIRED_FIELDS.get(shot.type, ())
    for name in required:
        value = getattr(shot, name, None)
        if value:
            continue
        log.append(
            RepairEntry(idx, name, f"{shot.type} 缺必填字段 / missing {name}", "降级为纯文字卡")
        )
        shot.type = "title-reveal"
        if not shot.text:
            shot.text = shot.subtext or "（缺内容）"
        return


def _repair_image(
    shot: ShotSpec, idx: int, log: list[RepairEntry], valid: set[str] | None
) -> None:
    """素材不存在 → 保留类型但清空 image，由组件按无图分支处理。

    A missing asset clears ``image`` instead of dropping the shot; components
    already handle the no-image branch.
    """
    if not shot.image or valid is None:
        return
    if shot.image not in valid:
        log.append(
            RepairEntry(idx, "image", f"素材不存在 / asset missing: {shot.image}", "清空 image")
        )
        shot.image = ""


def _repair_targets(shot: ShotSpec, idx: int, log: list[RepairEntry]) -> None:
    """标注目标超量则截断；坐标越界则钳制。

    Truncate excess annotation targets and clamp out-of-range coordinates.
    """
    if not shot.targets:
        return
    if len(shot.targets) > MAX_TARGETS:
        log.append(
            RepairEntry(
                idx,
                "targets",
                f"标注过多 / too many targets: {len(shot.targets)}",
                f"截断到 {MAX_TARGETS}",
            )
        )
        shot.targets = shot.targets[:MAX_TARGETS]

    for t in shot.targets:
        x, y, w, h = t.x, t.y, t.w, t.h
        t.x = _clip(t.x, 0.0, 1.0)
        t.y = _clip(t.y, 0.0, 1.0)
        t.w = _clip(t.w, 0.01, 1.0 - t.x)
        t.h = _clip(t.h, 0.01, 1.0 - t.y)
        if (t.x, t.y, t.w, t.h) != (x, y, w, h):
            log.append(
                RepairEntry(idx, "targets", f"坐标越界 / bbox out of range: {t.label}", "钳制到 [0,1]")
            )


def _repair_metrics(shot: ShotSpec, idx: int, log: list[RepairEntry]) -> None:
    """指标数量与长度封顶 / Cap metric count and value length."""
    if not shot.metrics:
        return
    if len(shot.metrics) > MAX_METRICS:
        log.append(
            RepairEntry(
                idx,
                "metrics",
                f"指标过多 / too many metrics: {len(shot.metrics)}",
                f"截断到 {MAX_METRICS}",
            )
        )
        shot.metrics = shot.metrics[:MAX_METRICS]
    for m in shot.metrics:
        if len(m.value) > 8:
            log.append(
                RepairEntry(idx, "metrics", f"数值过长 / value too long: {m.value}", "截断到 8 字符")
            )
            m.value = m.value[:8]


def _repair_stops(shot: ShotSpec, idx: int, log: list[RepairEntry]) -> None:
    """时间轴刻度数量必须在 [MIN_STOPS, MAX_STOPS] 内。

    Timeline ticks must stay within a readable range; too few have no travel
    feel, too many blur past.
    """
    if not shot.stops:
        return
    if len(shot.stops) > MAX_STOPS:
        log.append(
            RepairEntry(idx, "stops", f"刻度过多 / too many stops: {len(shot.stops)}", f"截断到 {MAX_STOPS}")
        )
        shot.stops = shot.stops[:MAX_STOPS]
    if len(shot.stops) < MIN_STOPS:
        log.append(
            RepairEntry(idx, "stops", f"刻度过少 / too few stops: {len(shot.stops)}", "降级为纯文字卡")
        )
        shot.type = "title-reveal"
        if not shot.text:
            shot.text = "（缺内容）"


def _repair_text(shot: ShotSpec, idx: int, log: list[RepairEntry]) -> None:
    """主文案超长则截断（会渲成一行标题，必须放得下）。"""
    if len(shot.text) > MAX_TEXT:
        log.append(
            RepairEntry(idx, "text", f"文案过长 / text too long: {len(shot.text)} 字", f"截断到 {MAX_TEXT} 字")
        )
        shot.text = shot.text[:MAX_TEXT]


def _repair_caption_segments(
    shot: ShotSpec, idx: int, log: list[RepairEntry], cue_count: int
) -> None:
    """字幕段号越界则丢弃 / Drop out-of-range cue references."""
    kept = [c for c in shot.caption_segments if 0 <= c < cue_count]
    if len(kept) != len(shot.caption_segments):
        log.append(
            RepairEntry(
                idx,
                "caption_segments",
                f"字幕段号越界 / cue index out of range（共 {cue_count} 段）",
                "丢弃越界引用",
            )
        )
        shot.caption_segments = kept


def _repair_duration(shot: ShotSpec, idx: int, log: list[RepairEntry]) -> None:
    """单镜时长钳到 [MIN_SHOT_FRAMES, MAX_SHOT_FRAMES]。

    **超上限不再"延长"，而是标记为需要切分** —— 因为延长会拖慢节奏，
    而节奏是本项目最贵的东西（用户明确反馈"超过 5 秒就明显变慢"）。

    切分由 :func:`_split_long_shots` 在同一步内完成；这里只做下限保护。
    """
    d = shot.duration_in_frames
    if d < MIN_SHOT_FRAMES:
        log.append(
            RepairEntry(
                idx,
                "durationInFrames",
                f"时长过短 / duration too short: {d}",
                f"补到下限 {MIN_SHOT_FRAMES} 帧",
            )
        )
        shot.duration_in_frames = MIN_SHOT_FRAMES
    elif d > ABSOLUTE_MAX_SHOT_FRAMES:
        log.append(
            RepairEntry(
                idx,
                "durationInFrames",
                f"时长超绝对上限 / beyond absolute max: {d}",
                f"钳到 {ABSOLUTE_MAX_SHOT_FRAMES} 帧（仍会被切分）",
            )
        )
        shot.duration_in_frames = ABSOLUTE_MAX_SHOT_FRAMES


def _split_long_shots(spec: VideoSpec, log: list[RepairEntry]) -> None:
    """把超过 ``MAX_SHOT_FRAMES`` 的镜头**切成等长的若干段**。

    Split shots longer than the 5-second ceiling into equal parts.

    为什么用"切分"而不是"延长"：单镜超过 5 秒节奏就垮，而总时长由音频锁定，
    所以只能靠**增加镜数**来消化时长。切分时复制该镜的全部内容文案 ——
    观众看到的是同一张图/同一份图文停得更短，而不是内容被删掉。

    Splitting (rather than stretching) is the only option that preserves pacing:
    total duration is pinned by the audio, so extra time must become more shots.
    """
    out: list[ShotSpec] = []
    for idx, shot in enumerate(spec.shots):
        d = shot.duration_in_frames
        if d <= MAX_SHOT_FRAMES:
            out.append(shot)
            continue

        parts = -(-d // MAX_SHOT_FRAMES)  # 向上取整 / ceil
        # 每段必须 ≤ 上限：向上取整已保证，但 d 远大于上限时要多切几段
        while -(-d // parts) > MAX_SHOT_FRAMES:
            parts += 1
        base = d // parts
        remainder = d - base * parts
        for k in range(parts):
            seg = ShotSpec(**{**shot.__dict__})
            seg.duration_in_frames = base + (1 if k < remainder else 0)
            # 只保留一次诊断信息；后续片段共享同一份内容
            out.append(seg)
        log.append(
            RepairEntry(
                idx,
                "durationInFrames",
                f"单镜超过 {MAX_SHOT_FRAMES} 帧（5s）上限 / over the 5s ceiling: {d}",
                f"切成 {parts} 段（每段约 {base} 帧）以保住节奏",
            )
        )
    spec.shots = out


# ── 卡数收敛 / Shot-count convergence ─────────────────────────────────────


def _converge_shot_count(spec: VideoSpec, log: list[RepairEntry]) -> None:
    """把卡数收敛到契约区间 / Bring the shot count into the contract range.

    过多 → **合并相邻最短的一对**，绝不丢镜头（丢镜头等于丢旁白覆盖）。

    合并对的选择有优先级，因为首末镜有结构语义：
        1. 优先合并**内部相邻对**（不碰第一镜与最后一镜）
        2. 内部没有可选对时（卡数 ≤2 就超限的极端情况）才允许碰首末镜

    这一条是硬要求：``title-reveal`` 必须在首镜、``outro-lockup`` 必须在末镜
    （system prompt 的硬规则）。合并若吃掉它俩，片头片尾就没了。

    过少 → 记警告性修复但**不硬凑**（凑镜头需要创作，不该由校验器瞎编）。

    Pairs are chosen to avoid the first and last shots, because those carry the
    opening and closing structure. Merging never drops a shot — dropping one
    would lose narration coverage.
    """
    lo, hi = SHOT_COUNT_RANGE.get(spec.kind, (1, 999))
    merges = 0
    # 因节奏约束而放弃合并的次数 —— 要留痕，否则「镜数超标」会被当成 bug
    skipped_for_pacing = 0

    while len(spec.shots) > hi:
        # 候选对：优先内部对（排除首末镜），退而求其次才用全部对
        interior = [
            i
            for i in range(len(spec.shots) - 1)
            if i > 0 and i + 1 < len(spec.shots) - 1
        ]
        candidates = interior or list(range(len(spec.shots) - 1))

        # **只考虑合并后仍在 5s 上限内的对** —— 节奏优先于镜数。
        # 全都不合规时放弃合并，宁可镜数超标也不要一镜拖 8 秒。
        safe = [
            i
            for i in candidates
            if spec.shots[i].duration_in_frames + spec.shots[i + 1].duration_in_frames
            <= MAX_SHOT_FRAMES
        ]
        if not safe:
            skipped_for_pacing += 1
            break

        best = min(
            safe,
            key=lambda i: (
                spec.shots[i].duration_in_frames + spec.shots[i + 1].duration_in_frames
            ),
        )

        keep, absorbed = spec.shots[best], spec.shots[best + 1]
        merged_into = keep if keep.duration_in_frames >= absorbed.duration_in_frames else absorbed
        other = absorbed if merged_into is keep else keep

        merged_into.duration_in_frames += other.duration_in_frames
        # 字幕段取并集（审计链完整：这两段旁白由同一个镜头承载）
        merged_into.caption_segments = sorted(
            set(merged_into.caption_segments) | set(other.caption_segments)
        )
        # 文案：两句话都要在，用「·」拼起来。
        # **不静默丢弃** —— 合并的代价是"两句挤一镜"，而不是"一句消失"。
        # 超过单镜文案上限时由后面的 _repair_text 统一截断并留痕。
        if other.text and other.text != merged_into.text:
            merged_into.text = (
                f"{merged_into.text}·{other.text}" if merged_into.text else other.text
            )
        if not merged_into.subtext:
            merged_into.subtext = other.subtext
        if not merged_into.image:
            merged_into.image = other.image

        removed_index = best if merged_into is absorbed else best + 1
        spec.shots.pop(removed_index)
        merges += 1
        log.append(
            RepairEntry(
                removed_index,
                "shots",
                f"卡数超上限 / too many shots（上限 {hi}）",
                f"合并相邻最短一对（{keep.type} + {absorbed.type}）",
            )
        )

    if len(spec.shots) < lo:
        # 不硬凑：凑镜头需要创作。但必须留痕，否则「片子比预期短/空」会无从追查。
        log.append(
            RepairEntry(
                None,
                "shots",
                f"卡数不足 / too few shots: {len(spec.shots)} < {lo}",
                "保留原样（凑镜头需要创作，校验器不代劳）",
            )
        )

    if merges:
        # 合并后总时长会超出时间轴，交给 _resequence 统一归位
        log.append(
            RepairEntry(
                None,
                "shots",
                f"合并 {merges} 次后总时长变化 / total changed by merges",
                "由收尾对齐重新分配 from 与总帧数",
            )
        )

    if skipped_for_pacing:
        log.append(
            RepairEntry(
                None,
                "shots",
                f"镜数仍超上限 / shot count still over {hi}: {len(spec.shots)}",
                "**主动放弃合并**：合并后必然超过 5s 上限，节奏优先于镜数"
                "（用户明确反馈超过 5 秒节奏就变慢）",
            )
        )


# ── 时间轴重排 / Timeline re-layout ────────────────────────────────────────


def _resequence(spec: VideoSpec, timeline: Timeline, log: list[RepairEntry]) -> None:
    """把 ``from`` 顺序对齐，并把总帧数精确对齐到音频 —— **不切分**。

    Re-sequence ``from`` and match the audio length exactly, without splitting.

    为什么不复用 :func:`_relayout`：那个函数会与切分互相迭代，
    而这里是**合并之后**的收尾 —— 再切分会让镜数立刻反弹出上限。
    所以本函数只做两件事：顺序对齐 + 余数均摊。
    """
    cursor = 0
    for shot in spec.shots:
        shot.from_frame = cursor
        cursor += shot.duration_in_frames

    delta = timeline.duration_frames - cursor
    if delta == 0:
        return

    n = len(spec.shots)
    base, rem = divmod(delta, n)
    for i, shot in enumerate(spec.shots):
        shot.duration_in_frames = max(
            MIN_SHOT_FRAMES, shot.duration_in_frames + base + (1 if i < rem else 0)
        )

    # 钳制可能破坏总和，补差额
    drift = timeline.duration_frames - sum(s.duration_in_frames for s in spec.shots)
    if drift:
        spec.shots[-1].duration_in_frames += drift

    cursor = 0
    for shot in spec.shots:
        shot.from_frame = cursor
        cursor += shot.duration_in_frames

    log.append(
        RepairEntry(
            None,
            "durationInFrames",
            f"合并后收尾对齐 / post-merge re-sequence: 差 {delta} 帧",
            f"均摊到 {n} 个镜头；from 重新顺序对齐",
        )
    )


def _relayout(spec: VideoSpec, timeline: Timeline, log: list[RepairEntry]) -> None:
    """按顺序重排 ``from``，并把总帧数对齐到音频时长。

    Re-lay ``from`` sequentially and reconcile the sum with the audio length.

    **余数均摊到所有镜头**，不是塞给末镜。塞给末镜会让它变成 1000+ 帧的巨物，
    再切分时必然产生超长段（实测踩过）。均摊后每镜的增幅一致，切分也均匀。

    The remainder is spread across all shots rather than dumped on the last one:
    concentrating it produces a single enormous shot that then splits badly.
    """
    total = timeline.duration_frames
    cursor = 0
    for shot in spec.shots:
        if shot.from_frame != cursor:
            shot.from_frame = cursor
        cursor += shot.duration_in_frames

    delta = total - cursor
    if delta == 0:
        return

    n = len(spec.shots)
    # 均匀分配；用最大余额法保证总和精确
    base = delta // n
    rem = delta - base * n
    for i, shot in enumerate(spec.shots):
        shot.duration_in_frames = max(
            MIN_SHOT_FRAMES,
            min(ABSOLUTE_MAX_SHOT_FRAMES, shot.duration_in_frames + base + (1 if i < abs(rem) else 0)),
        )

    # 钳制可能破坏总和，把差额再补到最后一个仍有余量的镜头上
    drift = total - sum(s.duration_in_frames for s in spec.shots)
    if drift:
        for shot in reversed(spec.shots):
            room = ABSOLUTE_MAX_SHOT_FRAMES - shot.duration_in_frames
            take = min(room, drift) if drift > 0 else max(
                MIN_SHOT_FRAMES - shot.duration_in_frames, drift
            )
            shot.duration_in_frames += take
            drift -= take
            if drift == 0:
                break

    log.append(
        RepairEntry(
            None,
            "durationInFrames",
            f"总帧数差 {delta} / total frame mismatch",
            f"均摊到 {n} 个镜头；超出 5s 上限的会在下一步被切分",
        )
    )

    # 重排 from
    cursor = 0
    for s in spec.shots:
        s.from_frame = cursor
        cursor += s.duration_in_frames
