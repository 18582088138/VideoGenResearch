"""字幕解析与时间轴构建 / Subtitle parsing and timeline construction.

这是生成流水线的**阶段 1（素材理解）**，纯确定性、零 LLM 调用。
字幕时轴是分镜的权威骨架，所以解析必须容忍真实文件里的常见脏数据：
BOM、CRLF、多行文本、毫秒分隔符为 ``.`` 而非 ``,``、空行数量不定。

Pipeline stage 1 (material understanding): deterministic, no LLM calls.
The SRT time axis is the authoritative skeleton for shot planning, so parsing
tolerates the usual real-world dirt: BOM, CRLF, multi-line cues, ``.`` instead
of ``,`` in the millisecond separator, and irregular blank lines.
"""

from __future__ import annotations

import re
import wave
from pathlib import Path

from videogen.models import SubtitleSegment, Timeline

# 00:00:09,892 / 00:00:09.892 → 秒
_TIMECODE = re.compile(
    r"(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{1,3})"
)


def _timecode_to_seconds(h: str, m: str, s: str, ms: str) -> float:
    """``HH:MM:SS,mmm`` → 秒 / Timecode to seconds."""
    # 毫秒位数可能不足 3 位（脏数据），右侧补零
    millis = int(ms.ljust(3, "0"))
    return int(h) * 3600 + int(m) * 60 + int(s) + millis / 1000.0


def parse_srt(text: str) -> list[SubtitleSegment]:
    """解析 SRT 文本为字幕段列表 / Parse SRT text into subtitle segments.

    容错策略：**按时间码行切块**，而不是按「序号行 + 空行」切块 ——
    真实文件里序号可能缺失或重复，时间码才是可靠的锚。

    Splits on timecode lines rather than on "index line + blank line" pairs,
    because real files sometimes drop or duplicate indices while the timecode
    line is always present.
    """
    # 统一换行 + 去 BOM
    normalized = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")

    segments: list[SubtitleSegment] = []
    # 逐行扫描：遇到时间码行就取其后的非空行作为文本
    lines = normalized.split("\n")
    i = 0
    cue_index = 0
    while i < len(lines):
        line = lines[i]
        if "-->" not in line:
            i += 1
            continue

        parts = line.split("-->")
        if len(parts) != 2:
            i += 1
            continue
        start_m = _TIMECODE.search(parts[0])
        end_m = _TIMECODE.search(parts[1])
        if not start_m or not end_m:
            i += 1
            continue

        start = _timecode_to_seconds(**start_m.groupdict())
        end = _timecode_to_seconds(**end_m.groupdict())

        # 收集紧跟其后的非空文本行（可能多行）
        i += 1
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip() and "-->" not in lines[i]:
            text_lines.append(lines[i].strip())
            i += 1
        # 跳过块间空行
        while i < len(lines) and not lines[i].strip():
            i += 1

        cue_index += 1
        segments.append(
            SubtitleSegment(
                index=cue_index,
                start=start,
                end=end,
                text=" ".join(text_lines) if text_lines else "",
            )
        )

    return segments


def parse_srt_file(path: Path) -> list[SubtitleSegment]:
    """读取并解析 SRT 文件 / Read and parse an SRT file.

    SRT 是 UTF-8 with BOM；显式指定 ``utf-8-sig`` 让 BOM 自动剥离。
    """
    return parse_srt(path.read_text(encoding="utf-8-sig"))


def wav_duration(path: Path) -> float:
    """读取 WAV 时长（秒）/ Read WAV duration in seconds.

    只支持未压缩 PCM WAV（本项目素材即 24kHz/mono/16bit PCM）。
    用标准库 ``wave``，避免为一个读头部动作引入音频依赖。
    """
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def build_timeline(
    srt_path: Path,
    audio_path: Path,
    fps: int = 30,
    title: str = "",
    subtitle: str = "",
) -> Timeline:
    """由字幕 + 音频构建时间轴 / Build a timeline from subtitles and audio.

    总时长取**音频实测时长**：字幕末条可能早于或晚于音频，
    而画面必须完整覆盖音频，否则片尾会被截断。

    Total duration comes from the **measured audio length**, not the last cue.
    """
    segments = parse_srt_file(srt_path)
    duration = wav_duration(audio_path)
    return Timeline(
        segments=tuple(segments),
        audio_duration=duration,
        fps=fps,
        title=title,
        subtitle=subtitle,
    )


def seconds_to_frames(seconds: float, fps: int) -> int:
    """秒 → 帧（四舍五入）/ Seconds to frames, rounded.

    与 :func:`videogen.timeline.frames_to_seconds` 互逆；
    字幕边界一律经此换算，保证横竖屏两版帧号完全一致。
    """
    return int(round(seconds * fps))


def frames_to_seconds(frames: int, fps: int) -> float:
    """帧 → 秒 / Frames to seconds."""
    return frames / float(fps)
