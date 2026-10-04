"""字幕解析与时间轴单测 / Unit tests for subtitle parsing and timeline.

测试说明文档 / Test documentation
    见 docs/03_unit_tests.md 「timeline」一节。
    覆盖设计意图见 docs/architecture/00_pipeline.md 阶段 1（素材理解）。

复测指令 / How to re-run
    cd C:\\Users\\75203\\Downloads\\xd\\VideoGenResearch-deepseek

    # 本次改动只跑本文件（开发守则 §2：不做全量测试）
    C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe -m pytest tests/test_timeline.py -v

    # 只跑某一个节点
    C:\\Users\\75203\\miniforge3\\envs\\ov_env_py312\\python.exe -m pytest tests/test_timeline.py::test_build_timeline_duration_comes_from_audio -v

预期结果 / Expected
    全部通过（含 2 条用真实素材的集成用例，不联网、不产生费用）。

费用说明 / Cost
    零。本文件不调用任何 LLM，也不触发 Remotion 渲染。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from videogen.paths import assets_dir
from videogen.timeline import (
    build_timeline,
    frames_to_seconds,
    parse_srt,
    parse_srt_file,
    seconds_to_frames,
    wav_duration,
)

# 真实素材路径（只读）/ Real asset paths (read-only).
AUDIO_DIR = assets_dir() / "audio"
SHORT_SRT = AUDIO_DIR / "shortvideo.zh.srt"
SHORT_WAV = AUDIO_DIR / "shortvideo.zh.wav"
MID_SRT = AUDIO_DIR / "narration.zh.srt"
MID_WAV = AUDIO_DIR / "narration.zh.wav"


# ── 解析容错 / Parsing robustness ──────────────────────────────────────────


def test_parse_srt_basic() -> None:
    """标准 SRT 应解析出正确的序号、起止与文本。"""
    text = (
        "1\n"
        "00:00:00,000 --> 00:00:01,500\n"
        "第一句\n"
        "\n"
        "2\n"
        "00:00:01,500 --> 00:00:03,250\n"
        "第二句\n"
    )
    segs = parse_srt(text)

    assert len(segs) == 2
    assert segs[0].index == 1
    assert segs[0].start == 0.0
    assert segs[0].end == 1.5
    assert segs[0].text == "第一句"
    assert segs[1].start == 1.5
    assert segs[1].end == 3.25


def test_parse_srt_tolerates_bom_crlf_and_dot_millis() -> None:
    """BOM + CRLF + 毫秒用点号，都不应导致解析失败。

    These three脏数据在真实文件里都出现过，任一未处理都会静默丢字幕。
    """
    text = "\ufeff1\r\n00:00:00.000 --> 00:00:02.000\r\n带 BOM 和 CRLF\r\n"
    segs = parse_srt(text)

    assert len(segs) == 1
    assert segs[0].start == 0.0
    assert segs[0].end == 2.0
    assert segs[0].text == "带 BOM 和 CRLF"


def test_parse_srt_multiline_text_joined() -> None:
    """多行字幕文本应合并为一行，避免渲染时出现意外的换行。"""
    text = "1\n00:00:00,000 --> 00:00:02,000\n上半句\n下半句\n"
    segs = parse_srt(text)

    assert len(segs) == 1
    assert segs[0].text == "上半句 下半句"


def test_parse_srt_survives_missing_index() -> None:
    """缺序号行的块仍应被解析 —— 时间码才是可靠锚点。

    这是有意的设计选择：按「序号 + 空行」切块会在缺序号时整体错位。
    """
    text = "00:00:00,000 --> 00:00:01,000\n无序号\n"
    segs = parse_srt(text)

    assert len(segs) == 1
    assert segs[0].text == "无序号"


def test_parse_srt_empty_input() -> None:
    """空输入返回空列表，不抛异常。"""
    assert parse_srt("") == []
    assert parse_srt("\n\n\n") == []


# ── 帧/秒换算 / Frame↔second conversion ────────────────────────────────────


def test_seconds_frames_roundtrip_at_30fps() -> None:
    """秒↔帧在 30fps 下应稳定（字幕边界换算的根基）。"""
    assert seconds_to_frames(0.0, 30) == 0
    assert seconds_to_frames(1.0, 30) == 30
    assert seconds_to_frames(49.664, 30) == 1490  # 49.664*30 = 1489.92 → 1490

    assert frames_to_seconds(30, 30) == 1.0
    assert frames_to_seconds(0, 30) == 0.0


# ── 真实素材集成 / Integration against the real assets ─────────────────────


def test_parse_real_short_srt_has_five_cues() -> None:
    """短视频字幕实测为 5 条，末条收在 49.664s。"""
    segs = parse_srt_file(SHORT_SRT)

    assert len(segs) == 5
    assert segs[0].start == 0.0
    assert segs[-1].end == pytest.approx(49.664, abs=1e-3)


def test_parse_real_mid_srt_has_eleven_cues() -> None:
    """中视频字幕实测为 11 条，末条收在 155.480s。"""
    segs = parse_srt_file(MID_SRT)

    assert len(segs) == 11
    assert segs[-1].end == pytest.approx(155.480, abs=1e-3)


def test_wav_duration_matches_measured_short() -> None:
    """短视频音频实测 49.66s（±0.05）。"""
    assert wav_duration(SHORT_WAV) == pytest.approx(49.66, abs=0.05)


def test_wav_duration_matches_measured_mid() -> None:
    """中视频音频实测 155.48s（±0.05）。"""
    assert wav_duration(MID_WAV) == pytest.approx(155.48, abs=0.05)


def test_build_timeline_duration_comes_from_audio() -> None:
    """时间轴总时长必须取音频时长，而不是字幕末条。

    本素材两者恰好接近，但这是**语义保证**：画面必须覆盖完整音频，
    否则片尾被截断。此处用断言锁定「优先音频」这一行为。
    """
    tl = build_timeline(SHORT_SRT, SHORT_WAV, fps=30)

    assert tl.audio_duration == pytest.approx(49.66, abs=0.05)
    assert len(tl.segments) == 5
    # 49.66s @30fps → 1490 帧（向上取整）
    assert tl.duration_frames == 1490


def test_build_timeline_mid_frames() -> None:
    """中视频 155.48s @30fps → 4665 帧（向上取整）。

    这个数字是渲染时长的直接依据，锁定它可防止 fps 被误改。
    """
    tl = build_timeline(MID_SRT, MID_WAV, fps=30)

    assert tl.duration_frames == 4665


def test_build_timeline_segments_are_contiguous_after_gaps() -> None:
    """相邻字幕段之间只应有短暂空隙（停顿时长可控）。

    真实配音在段间有 0.25s 左右停顿；若出现负数或超长空隙，说明解析错位。
    """
    tl = build_timeline(MID_SRT, MID_WAV, fps=30)

    for prev, nxt in zip(tl.segments, tl.segments[1:]):
        gap = nxt.start - prev.end
        assert gap >= 0, f"段 {prev.index}→{nxt.index} 时间重叠"
        assert gap < 3.0, f"段 {prev.index}→{nxt.index} 空隙异常大：{gap:.2f}s"
