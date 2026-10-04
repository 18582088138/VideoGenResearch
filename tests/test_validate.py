"""spec 校验与降级修复单测 / Unit tests for spec validation and repair.

测试说明文档 / Test documentation
    docs/03_unit_tests.md 「spec / validate」一节；
    字段级约束与修复顺序见 docs/architecture/01_spec_schema.md §3/§6。

复测指令 / How to re-run
    cd C:\\Users\\75203\\Downloads\\xd\\VideoGenResearch-deepseek
    C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe -m pytest tests/test_validate.py -v

    # 只跑某个修复分支
    ... -m pytest tests/test_validate.py::test_missing_image_is_cleared_not_dropped -v

预期结果 / Expected
    全部通过。零费用、不联网、不触发渲染。

为什么这些用例重要 / Why these matter
    这些正是 minimax 版「黑盒 spec」缺失的那一层：坏数据会直接渲成坏画面。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from videogen.models import ImageAsset, SubtitleSegment, Timeline
from videogen.spec import RepairEntry, ShotMetric, ShotSpec, ShotTarget, VideoSpec
from videogen.validate import (
    MAX_TEXT,
    MAX_SHOT_FRAMES,
    MIN_SHOT_FRAMES,
    SpecValidationError,
    validate_and_repair,
)


# ── 夹具 / Fixtures ────────────────────────────────────────────────────────


def make_timeline(total_frames: int = 600, cues: int = 3) -> Timeline:
    """造一条可控时间轴 / Build a controllable timeline."""
    segs = tuple(
        SubtitleSegment(index=i + 1, start=i * 1.0, end=i * 1.0 + 0.9, text=f"第{i + 1}句")
        for i in range(cues)
    )
    return Timeline(segments=segs, audio_duration=total_frames / 30, fps=30)


def make_images(*files: str) -> list[ImageAsset]:
    """造素材索引 / Build an image index."""
    return [
        ImageAsset(
            file=f, width=1080, height=608, aspect=1.78, role="diagram",
            kind="k", label=f"图 {f}",
        )
        for f in files
    ]


def make_spec(shots: list[ShotSpec], **overrides: object) -> VideoSpec:
    """造 spec / Build a spec with overridable top-level fields."""
    fields: dict[str, object] = {
        "kind": "short",
        "fps": 30,
        "duration_in_frames": 600,
        "theme": "cyan-noir",
    }
    fields.update(overrides)
    return VideoSpec(shots=shots, **fields)  # type: ignore[arg-type]


# ── 合法输入 / Happy path ──────────────────────────────────────────────────


def test_valid_spec_passes_untouched() -> None:
    """完全合法的 spec 不应产生任何修复记录。

    ⚠️ 用例必须**合法**才谈得上"不该被改" —— 早先这里用了 2 镜（短视频要求 5–6），
    卡数校验一上线就正确地报了 too few shots。这是测试数据的问题不是代码的问题。
    """
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=600, theme="cyan-noir",
        shots=[
            ShotSpec(type="title-reveal", from_frame=0, duration_in_frames=100, text="开场"),
            ShotSpec(type="page-spotlight", from_frame=100, duration_in_frames=100, image="a.png"),
            ShotSpec(
                type="number-roll", from_frame=200, duration_in_frames=100, text="指标",
                metrics=[ShotMetric(label="L", value="V")],
            ),
            ShotSpec(
                type="scan-annotate", from_frame=300, duration_in_frames=100, image="a.png",
                targets=[ShotTarget(x=0.1, y=0.1, w=0.2, h=0.2, label="T")],
            ),
            ShotSpec(type="radar-reveal", from_frame=400, duration_in_frames=100, image="a.png"),
            ShotSpec(type="outro-lockup", from_frame=500, duration_in_frames=100, text="收尾"),
        ],
    )
    out = validate_and_repair(spec, make_timeline(), make_images("a.png"))

    assert out.repair_log == []
    assert [s.from_frame for s in out.shots] == [0, 100, 200, 300, 400, 500]


def test_timeline_fields_backfilled() -> None:
    """时间轴的 fps/总帧数/时长必须回填进 spec —— 可复现性的前提。"""
    spec = VideoSpec(
        kind="short", fps=99, duration_in_frames=1, theme="cyan-noir",
        shots=[ShotSpec(type="title-reveal", from_frame=0, duration_in_frames=600, text="标题")],
    )
    tl = make_timeline(total_frames=600)
    out = validate_and_repair(spec, tl, [])

    assert out.fps == 30
    assert out.duration_in_frames == 600
    assert out.total_seconds == round(tl.audio_duration, 2)


# ── 不可修复 / Unrepairable ────────────────────────────────────────────────


def test_unknown_shot_type_raises() -> None:
    """未知镜头类型必须报错，不能猜。

    猜一个类型会静默改掉创作意图 —— 宁可失败得响亮。
    """
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=600, theme="cyan-noir",
        shots=[ShotSpec(type="flashy-thing", from_frame=0, duration_in_frames=300)],
    )
    with pytest.raises(SpecValidationError, match="unknown shot type"):
        validate_and_repair(spec, make_timeline(), [])


def test_empty_shot_list_raises() -> None:
    """没有镜头的 spec 无法出片 / A spec with no shots cannot render."""
    spec = VideoSpec(kind="short", fps=30, duration_in_frames=600, theme="cyan-noir", shots=[])
    with pytest.raises(SpecValidationError, match="no shots"):
        validate_and_repair(spec, make_timeline(), [])


# ── 逐项修复 / Individual repairs ──────────────────────────────────────────


def test_missing_required_field_degrades_to_text_card() -> None:
    """缺 image 的 page-spotlight 降级为纯文字卡，而不是被丢掉。

    旁白还在讲，画面不能没有东西。
    """
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=600, theme="cyan-noir",
        shots=[ShotSpec(type="page-spotlight", from_frame=0, duration_in_frames=600, subtext="证据")],
    )
    out = validate_and_repair(spec, make_timeline(), [])

    assert out.shots[0].type == "title-reveal"
    assert out.shots[0].text == "证据"
    assert any(r.field_name == "image" for r in out.repair_log)


def test_missing_image_is_cleared_not_dropped() -> None:
    """素材不在索引里 → 清空 image 并留痕（镜头仍在时间轴上）。"""
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=600, theme="cyan-noir",
        shots=[ShotSpec(type="page-spotlight", from_frame=0, duration_in_frames=600, image="不存在.png")],
    )
    out = validate_and_repair(spec, make_timeline(), make_images("a.png"))

    assert out.shots[0].image == ""
    assert any(r.field_name == "image" and "不存在.png" in r.problem for r in out.repair_log)


def test_duration_clipped_to_range() -> None:
    """单镜时长越界必须被钳制（过短读作闪切、过长读作拖沓）。"""
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=180, theme="cyan-noir",
        shots=[ShotSpec(type="title-reveal", from_frame=0, duration_in_frames=10, text="太短")],
    )
    out = validate_and_repair(spec, make_timeline(total_frames=180), [])

    assert out.shots[0].duration_in_frames >= MIN_SHOT_FRAMES
    assert any(r.field_name == "durationInFrames" for r in out.repair_log)


def test_targets_clamped_into_unit_square() -> None:
    """标注包围盒越界要钳到 [0,1] 内，否则会渲到画面外。"""
    from videogen.spec import ShotTarget

    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=600, theme="cyan-noir",
        shots=[
            ShotSpec(
                type="scan-annotate", from_frame=0, duration_in_frames=600, image="a.png",
                targets=[ShotTarget(x=0.9, y=0.9, w=0.5, h=0.5, label="越界")],
            )
        ],
    )
    out = validate_and_repair(spec, make_timeline(), make_images("a.png"))
    t = out.shots[0].targets[0]

    assert t.x + t.w <= 1.0 + 1e-9
    assert t.y + t.h <= 1.0 + 1e-9
    assert any(r.field_name == "targets" for r in out.repair_log)


def test_too_many_targets_truncated() -> None:
    """标注多于 4 个要截断 —— 一屏框太多就读不清了。"""
    from videogen.spec import ShotTarget

    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=600, theme="cyan-noir",
        shots=[
            ShotSpec(
                type="scan-annotate", from_frame=0, duration_in_frames=600, image="a.png",
                targets=[ShotTarget(x=0.1, y=0.1, w=0.1, h=0.1, label=f"T{i}") for i in range(7)],
            )
        ],
    )
    out = validate_and_repair(spec, make_timeline(), make_images("a.png"))

    assert len(out.shots[0].targets) == 4
    assert any(r.field_name == "targets" for r in out.repair_log)


def test_too_many_metrics_truncated() -> None:
    """指标多于 3 项要截断（number-roll 一屏放不下第四行）。"""
    from videogen.spec import ShotMetric

    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=600, theme="cyan-noir",
        shots=[
            ShotSpec(
                type="number-roll", from_frame=0, duration_in_frames=600, text="指标",
                metrics=[ShotMetric(label=f"L{i}", value=str(i)) for i in range(5)],
            )
        ],
    )
    out = validate_and_repair(spec, make_timeline(), [])

    assert len(out.shots[0].metrics) == 3
    assert any(r.field_name == "metrics" for r in out.repair_log)


def test_long_metric_value_truncated() -> None:
    """数值超过 8 字符要截断（会撑破版式）。"""
    from videogen.spec import ShotMetric

    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=600, theme="cyan-noir",
        shots=[
            ShotSpec(
                type="counter-burst", from_frame=0, duration_in_frames=600,
                metrics=[ShotMetric(label="降幅", value="百分之四十六点零")],
            )
        ],
    )
    out = validate_and_repair(spec, make_timeline(), [])

    assert len(out.shots[0].metrics[0].value) == 8


def test_long_text_truncated() -> None:
    """主文案超长要截断（渲成一行标题，放不下）。"""
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=600, theme="cyan-noir",
        shots=[
            ShotSpec(type="title-reveal", from_frame=0, duration_in_frames=600, text="字" * 80)
        ],
    )
    out = validate_and_repair(spec, make_timeline(), [])

    assert len(out.shots[0].text) == MAX_TEXT
    assert any(r.field_name == "text" for r in out.repair_log)


def test_out_of_range_caption_segments_dropped() -> None:
    """字幕段号越界要丢弃（防止指到不存在的旁白）。"""
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=600, theme="cyan-noir",
        shots=[
            ShotSpec(
                type="title-reveal", from_frame=0, duration_in_frames=600, text="标题",
                caption_segments=[0, 2, 99],
            )
        ],
    )
    out = validate_and_repair(spec, make_timeline(cues=3), [])

    assert out.shots[0].caption_segments == [0, 2]
    assert any(r.field_name == "caption_segments" for r in out.repair_log)


def test_too_few_stops_degrades() -> None:
    """时间轴只有 1 个刻度无法成立，降级为纯文字卡。"""
    from videogen.spec import ShotStop

    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=600, theme="cyan-noir",
        shots=[
            ShotSpec(
                type="timeline-travel", from_frame=0, duration_in_frames=600,
                stops=[ShotStop(label="2025")],
            )
        ],
    )
    out = validate_and_repair(spec, make_timeline(), [])

    assert out.shots[0].type == "title-reveal"
    assert any(r.field_name == "stops" for r in out.repair_log)


# ── 卡数收敛 / Shot-count convergence ──────────────────────────────────────


def _title(text: str, dur: int = 200) -> ShotSpec:
    """造一个 title-reveal 镜头 / A title-reveal shot."""
    return ShotSpec(type="title-reveal", from_frame=0, duration_in_frames=dur, text=text)


def test_too_many_shots_merged_not_dropped() -> None:
    """卡数超上限时合并相邻最短一对，**且不丢任何镜头内容**。

    注意合并受 5s 节奏上限约束：只有「合并后仍 ≤150 帧」的对才会被选中
    （见 test_pacing_outranks_shot_count）。
    """
    # 11 镜 × 60 帧 → 合并到 10 镜（max 120 帧，仍在 5s 内）。
    # 全部严格 <150 帧，因此不会触发切分 —— 测的纯粹是合并逻辑。
    durations = [60] * 11
    shots = [_title(f"S{i}", d) for i, d in enumerate(durations)]
    shots[0].type = "title-reveal"
    shots[-1].type = "outro-lockup"
    total = sum(durations)
    spec = VideoSpec(
        kind="mid", fps=30, duration_in_frames=total, theme="cyan-noir", shots=shots
    )

    out = validate_and_repair(spec, make_timeline(total_frames=total), [])

    assert len(out.shots) <= 10, [s.duration_in_frames for s in out.shots]
    assert any(r.field_name == "shots" for r in out.repair_log)
    # 所有原始文案必须都还在（合并 = 拼起来，不是丢弃）
    joined = "".join(s.text for s in out.shots)
    assert all(f"S{i}" in joined for i in range(11)), joined
    # 每镜仍须在 5s 内
    assert all(s.duration_in_frames <= MAX_SHOT_FRAMES + 1 for s in out.shots)


def test_merge_preserves_opening_and_closing_structure() -> None:
    """合并**不得吃掉首镜的 title-reveal 与末镜的 outro-lockup**。

    首末镜有结构语义（system prompt 硬规则）。合并策略必须优先选内部对，
    否则片头片尾就没了。
    """
    shots = [_title(f"S{i}", 140) for i in range(12)]
    shots[0].type = "title-reveal"
    shots[-1].type = "outro-lockup"
    spec = VideoSpec(
        kind="mid", fps=30, duration_in_frames=1680, theme="cyan-noir", shots=shots
    )

    out = validate_and_repair(spec, make_timeline(total_frames=1680), [])

    assert out.shots[0].type == "title-reveal", "首镜结构被合并破坏"
    assert out.shots[-1].type == "outro-lockup", "末镜结构被合并破坏"


def test_merged_shot_unions_caption_segments() -> None:
    """合并后字幕段取并集 —— 两段旁白由同一镜承载，审计链要完整。"""
    shots = [_title(f"S{i}", 140) for i in range(12)]
    for i, s in enumerate(shots):
        s.caption_segments = [i]
    shots[0].type = "title-reveal"
    shots[-1].type = "outro-lockup"
    spec = VideoSpec(
        kind="mid", fps=30, duration_in_frames=1680, theme="cyan-noir", shots=shots
    )

    out = validate_and_repair(spec, make_timeline(total_frames=1680, cues=12), [])

    covered = sorted({c for s in out.shots for c in s.caption_segments})
    assert covered == list(range(12)), "合并丢了字幕覆盖"


def test_short_video_within_range_untouched() -> None:
    """6 镜在短视频区间内，不应产生任何卡数修复。"""
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=900, theme="cyan-noir",
        shots=[_title(f"S{i}", 150) for i in range(6)],
    )

    out = validate_and_repair(spec, make_timeline(total_frames=900), [])

    assert len(out.shots) == 6
    assert not any(r.field_name == "shots" for r in out.repair_log)


def test_too_few_shots_logged_but_not_padded() -> None:
    """卡数不足要留痕，但**不硬凑** —— 凑镜头需要创作，校验器不代劳。"""
    spec = VideoSpec(
        kind="mid", fps=30, duration_in_frames=450, theme="cyan-noir",
        shots=[_title(f"S{i}", 150) for i in range(3)],
    )

    out = validate_and_repair(spec, make_timeline(total_frames=450), [])

    assert len(out.shots) == 3, "不应凭空增加镜头"
    entry = next(r for r in out.repair_log if r.field_name == "shots")
    assert "too few shots" in entry.problem


# ── 时间轴对齐 / Timeline reconciliation ───────────────────────────────────


def test_from_frames_relaid_sequentially() -> None:
    """from 由校验器重排，不信 LLM 自己算的帧号。"""
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=300, theme="cyan-noir",
        shots=[
            ShotSpec(type="title-reveal", from_frame=0, duration_in_frames=150, text="A"),
            ShotSpec(type="title-reveal", from_frame=999, duration_in_frames=150, text="B"),
        ],
    )
    out = validate_and_repair(spec, make_timeline(total_frames=300), [])

    assert [s.from_frame for s in out.shots] == [0, 150]


def test_last_shot_absorbs_frame_remainder() -> None:
    """总帧数不足由**末镜**吸收 —— 片尾不能留空（音频还在响）。

    注意末镜吸收后可能超过 5 秒上限，那时会被切分（这是有意的：
    宁可变多一镜，也不要一镜拖 8 秒）。
    """
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=700, theme="cyan-noir",
        shots=[
            ShotSpec(type="title-reveal", from_frame=0, duration_in_frames=120, text="A"),
            ShotSpec(type="title-reveal", from_frame=120, duration_in_frames=120, text="B"),
        ],
    )
    out = validate_and_repair(spec, make_timeline(total_frames=700), [])

    assert sum(s.duration_in_frames for s in out.shots) == 700
    # 末镜被撑到 460 帧 → 超过 5s 上限 → 被切成多段
    assert out.shots[-1].duration_in_frames <= 150
    assert len(out.shots) > 2


def test_shot_longer_than_five_seconds_is_split() -> None:
    """单镜超过 5 秒（150 帧）必须被**切分**，而不是延长。

    这是用户明确反馈的核心节奏约束：超过 5 秒视频节奏就明显变慢。
    总时长由音频锁定，所以多出来的时间只能变成**更多镜头**。
    """
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=1490, theme="cyan-noir",
        shots=[ShotSpec(type="title-reveal", from_frame=0, duration_in_frames=200, text=f"镜{i}")
                for i in range(12)],
    )

    out = validate_and_repair(spec, make_timeline(total_frames=1490), [])

    # 总帧数必须精确对齐音频（硬保证）
    assert sum(s.duration_in_frames for s in out.shots) == 1490
    # **每镜不得超过 5s 上限**（允许 1 帧舍入）
    assert all(s.duration_in_frames <= MAX_SHOT_FRAMES + 1 for s in out.shots), [
        s.duration_in_frames for s in out.shots
    ]


def test_pacing_outranks_shot_count() -> None:
    """节奏（≤5s）**优先于**镜数上限：合并会超限时主动放弃合并。

    这条规则是用户反馈的直接产物。原实现先无条件把镜数收敛到区间，
    合并出的长镜随后又被切分，来回震荡并最终产出超 5s 的镜头。
    """
    # 12 镜 × 124 帧 ≈ 1490 帧，卡数上限 6 —— 合并到 6 镜必然超 5s
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=1490, theme="cyan-noir",
        shots=[ShotSpec(type="title-reveal", from_frame=0, duration_in_frames=124, text=f"S{i}")
                for i in range(12)],
    )

    out = validate_and_repair(spec, make_timeline(total_frames=1490), [])

    assert sum(s.duration_in_frames for s in out.shots) == 1490
    assert all(s.duration_in_frames <= MAX_SHOT_FRAMES + 1 for s in out.shots), [
        s.duration_in_frames for s in out.shots
    ]
    # 必须留痕说明"为什么镜数超标"
    assert any("放弃合并" in r.action for r in out.repair_log)


def test_a_single_giant_shot_is_split_into_many() -> None:
    """一个 600 帧的巨镜必须被切成多段 —— 这是"不拖慢节奏"的核心机制。"""
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=600, theme="cyan-noir",
        shots=[ShotSpec(type="title-reveal", from_frame=0, duration_in_frames=600, text="巨镜")],
    )

    out = validate_and_repair(spec, make_timeline(total_frames=600), [])

    assert sum(s.duration_in_frames for s in out.shots) == 600
    assert any("切成" in r.action for r in out.repair_log)
    # 切完的片段应显著短于原镜头
    assert max(s.duration_in_frames for s in out.shots) < 600


def test_remainder_is_spread_not_dumped_on_last_shot() -> None:
    """余数必须**均摊**到所有镜头，而不是全塞给末镜。

    这是修掉的一个真 bug：原实现把余数塞给末镜，末镜变成 1490 帧的巨物，
    再切分时产生超长段。判断依据：末镜不应比其他镜头长一个数量级。
    """
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=1490, theme="cyan-noir",
        shots=[ShotSpec(type="title-reveal", from_frame=0, duration_in_frames=100, text=f"S{i}")
                for i in range(8)],
    )

    out = validate_and_repair(spec, make_timeline(total_frames=1490), [])

    assert sum(s.duration_in_frames for s in out.shots) == 1490
    durations = [s.duration_in_frames for s in out.shots]
    # 关键：末镜不应是"巨物"。原 bug 下这里会出现 1490 帧的单镜。
    assert max(durations) < 1490, durations
    assert any("均摊" in r.action for r in out.repair_log)
    # from 必须连续无空洞
    cursor = 0
    for s in out.shots:
        assert s.from_frame == cursor
        cursor += s.duration_in_frames


# ── 序列化 / Serialisation ─────────────────────────────────────────────────


def test_spec_roundtrip_preserves_fields() -> None:
    """dict 往返不丢字段 —— LLM 响应解析与落盘归档都依赖它。"""
    from videogen.spec import ShotMetric, ShotTarget

    spec = VideoSpec(
        kind="mid", fps=30, duration_in_frames=600, theme="cyan-noir",
        title="标题", subtitle="副标", total_seconds=20.0,
        shots=[
            ShotSpec(
                type="scan-annotate", from_frame=0, duration_in_frames=600, image="a.png",
                text="正文", subtext="副文", caption_segments=[0, 1],
                metrics=[ShotMetric(label="L", value="V")],
                targets=[ShotTarget(x=0.1, y=0.2, w=0.3, h=0.4, label="T")],
                source="来源",
            )
        ],
    )
    back = VideoSpec.from_dict(spec.to_dict())

    assert back.kind == "mid"
    assert back.title == "标题"
    assert back.shots[0].metrics[0].value == "V"
    assert back.shots[0].targets[0].label == "T"
    assert back.shots[0].caption_segments == [0, 1]


def test_save_writes_readable_utf8(tmp_path: Path) -> None:
    """落盘 JSON 的中文不转义 —— 这些文件要给人 grep。"""
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=600, theme="cyan-noir",
        title="清华团队登 Science Robotics",
        shots=[ShotSpec(type="title-reveal", from_frame=0, duration_in_frames=600, text="开场")],
    )
    p = tmp_path / "spec.json"
    spec.save(p)
    text = p.read_text(encoding="utf-8")

    assert "清华团队" in text
    assert "\\u" not in text
    assert json.loads(text)["shots"][0]["type"] == "title-reveal"


def test_repair_entry_serialises() -> None:
    """修复记录可序列化（要随 spec 一起归档）。"""
    spec = VideoSpec(
        kind="short", fps=30, duration_in_frames=600, theme="cyan-noir",
        shots=[ShotSpec(type="page-spotlight", from_frame=0, duration_in_frames=600)],
    )
    out = validate_and_repair(spec, make_timeline(), [])

    assert out.repair_log
    assert isinstance(out.repair_log[0], RepairEntry)
    assert out.to_dict()["repair_log"][0]["action"]
